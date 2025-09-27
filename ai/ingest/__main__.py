from __future__ import annotations

import argparse
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np

from .cv_source import CvSource
from .gst_source import GstSource
from ..detect.yolo_detector import YoloDetector
from ..emit.json_emitter import JsonEmitter
from ..track.deepsort_tracker import DeepSortTracker, TrackResult


VideoSource = Union[CvSource, GstSource]


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    conf: float
    class_id: int
    class_name: str
    track_id: Optional[int] = None

# Nơi định nghĩa toàn bộ tham số dòng lệnh (command-line arguments)
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline ingest video tối giản với YOLOv8 và DeepSORT"
    )
    parser.add_argument("--backend", choices=["cv", "gst"], default="cv")
    parser.add_argument("--src", required=True, help="Đường dẫn file hoặc RTSP URL")
    parser.add_argument("--yolo", type=int, choices=[0, 1], default=1, help="Bật YOLOv8")
    parser.add_argument("--track", type=int, choices=[0, 1], default=1, help="Bật DeepSORT")
    parser.add_argument("--display", type=int, choices=[0, 1], default=1, help="Hiển thị preview")
    parser.add_argument("--emit", choices=["none", "detection"], default="none", help="Xuất NDJSON")
    parser.add_argument("--out", default="-", help="Đường dẫn file NDJSON hoặc '-' để in ra stdout")
    parser.add_argument("--model", default="yolov8n.pt", help="Model YOLOv8")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng confidence")
    parser.add_argument("--classes", default=None, help="Danh sách lớp, phân tách bởi dấu phẩy")
    parser.add_argument("--store_id", default="store_01")
    parser.add_argument("--camera_id", default="cam_01")
    parser.add_argument("--stream_id", default="stream_01")
    parser.add_argument("--run_id", default=None)
    parser.add_argument("--fps_log", type=int, default=30, help="Khoảng log FPS theo số frame")
    parser.add_argument("--track_max_age", type=int, default=30)
    parser.add_argument("--track_n_init", type=int, default=3)
    parser.add_argument("--track_iou", type=float, default=0.7)
    parser.add_argument("--track_nms_overlap", type=float, default=1.0)
    parser.add_argument("--track_embedder", default="mobilenet")
    parser.add_argument("--track_embedder_gpu", type=int, choices=[0, 1], default=0)
    parser.add_argument("--track_half", type=int, choices=[0, 1], default=0)
    return parser.parse_args()


def _parse_classes(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None:
        return ['person']
    classes = [token.strip().lower() for token in raw.split(',') if token.strip()]
    if not classes:
        return ['person']
    if any(token in {'all', '*'} for token in classes):
        return None
    return classes

# Lấy video bằng backend nào (OpenCV hay GStreamer)
def _build_source(backend: str, uri: str) -> VideoSource:
    if backend == "gst":
        try:
            gst_source = GstSource(uri)
            if gst_source.open():
                print(f"[INFO] Đang sử dụng backend GStreamer cho {uri}")
                return gst_source
            print("[WARN] GStreamer backend không khởi tạo được, chuyển sang OpenCV.")
        except Exception as exc:  # pragma: no cover - chỉ log cảnh báo
            print(f"[WARN] Lỗi GStreamer ({exc}), chuyển sang OpenCV.")
    cv_source = CvSource(uri)
    if not cv_source.open():
        raise RuntimeError(f"Không mở được nguồn video: {uri}")
    print(f"[INFO] Đang sử dụng backend OpenCV cho {uri}")
    return cv_source

# Chuẩn bị YOLO detect dựa trên tham số dòng lệnh.
def _prepare_detector(enable: bool, model: str, conf: float, classes: Optional[List[str]]) -> Optional[YoloDetector]:
    if not enable:
        return None
    return YoloDetector(model_path=model, conf=conf, classes=classes)

# Chuẩn bị DeepSORT tracker dựa trên tham số dòng lệnh.
def _prepare_tracker(enable: bool, args: argparse.Namespace) -> Optional[DeepSortTracker]:
    if not enable:
        return None
    return DeepSortTracker(
        max_age=args.track_max_age,
        n_init=args.track_n_init,
        max_iou_distance=args.track_iou,
        nms_max_overlap=args.track_nms_overlap,
        embedder=args.track_embedder,
        embedder_gpu=bool(args.track_embedder_gpu),
        half=bool(args.track_half),
    )

# Tính toán xem hai hộp “đè” lên nhau bao nhiêu phần trăm,
# và dùng kết quả đó để quyết định có gán detection cho track, 
# hay loại bỏ detection trùng lặp
def _compute_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    denom = area_a + area_b - inter_area
    return inter_area / denom if denom else 0.0

# Để gán track_id (ID theo dõi) cho từng detection dựa vào danh sách track mà DeepSORT đã tạo.
def _attach_track_ids(detections: List[Detection], tracks: Sequence[TrackResult], threshold: float = 0.3) -> None:
    for det in detections:
        best_id: Optional[int] = None
        best_iou = threshold
        for track in tracks:
            track_box = (track.x1, track.y1, track.x2, track.y2)
            iou = _compute_iou(det.bbox, track_box)
            if iou > best_iou:
                best_iou = iou
                best_id = track.track_id
        det.track_id = best_id

# Vẽ kết quả detection/tracking trực tiếp lên frame video để hiển thị cho người dùng.
def _draw_preview(frame: np.ndarray, detections: Sequence[Detection]) -> np.ndarray:
    canvas = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        color = (0, 255, 0) if det.track_id is not None else (0, 0, 255)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        label = f"{det.class_name}:{det.conf:.2f}"
        if det.track_id is not None:
            label = f"ID {det.track_id} | {label}"
        cv2.putText(
            canvas,
            label,
            (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    return canvas


def run() -> None:
    # Parse tham số từ dòng lệnh
    args = _parse_args()
    classes = _parse_classes(args.classes)
    enable_yolo = bool(args.yolo)
    enable_track = bool(args.track) and enable_yolo
    if args.track and not enable_track:
        print("[WARN] DeepSORT cần YOLO, bỏ qua --track=1 vì --yolo=0")

    # Khởi tạo các component chính
    source = _build_source(args.backend, args.src)  # Video source (CV/GStreamer)
    detector = _prepare_detector(enable_yolo, args.model, args.conf, classes)  # YOLO detector
    tracker = _prepare_tracker(enable_track, args)  # DeepSORT tracker
    emitter = JsonEmitter(args.out) if args.emit == "detection" else None  # JSON output

    # Setup runtime variables
    pipeline_run_id = args.run_id or uuid.uuid4().hex
    frame_index = 0
    started_at = time.time()
    window_name = "retail-video"

    try:
        # Main processing loop - xử lý từng frame
        while True:
            # Đọc frame từ video source
            ok, frame = source.read()
            if not ok or frame is None:
                break

            frame_index += 1
            detections: List[Detection] = []

            # Chạy YOLO detection nếu được bật
            if detector:
                raw_dets = detector.infer(frame)
                for x1, y1, x2, y2, conf, cls_id, cls_name in raw_dets:
                    detections.append(
                        Detection(
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            conf=float(conf),
                            class_id=int(cls_id),
                            class_name=str(cls_name),
                        )
                    )

            # Chạy tracking nếu có detections và tracker được bật
            tracks: Sequence[TrackResult] = []
            if tracker:
                tracker_input = [
                    (d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3], d.conf, d.class_id, d.class_name)
                    for d in detections
                ]
                tracks = tracker.update(tracker_input, frame)
                _attach_track_ids(detections, tracks)  # Gán track_id cho detections
            elif emitter and not detector:
                # Không có detection để ghi log -> bỏ qua frame
                detections = []

            # Xuất JSON nếu có detections và emitter được bật
            if emitter and detections:
                width = int(frame.shape[1])
                height = int(frame.shape[0])
                emitter.emit_detection(
                    schema_version="1.0",
                    pipeline_run_id=pipeline_run_id,
                    source={
                        "store_id": args.store_id,
                        "camera_id": args.camera_id,
                        "stream_id": args.stream_id,
                    },
                    frame_index=frame_index,
                    capture_ts=datetime.now(timezone.utc).isoformat(),
                    image_size=(width, height),
                    detections=[
                        {
                            "bbox": det.bbox,
                            "conf": det.conf,
                            "class_id": det.class_id,
                            "class_name": det.class_name,
                            "track_id": det.track_id,
                        }
                        for det in detections
                    ],
                )

            # Hiển thị preview window nếu được bật
            if args.display:
                preview = _draw_preview(frame, detections)
                cv2.imshow(window_name, preview)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):  # ESC hoặc 'q' để thoát
                    break

            # Log thống kê FPS định kỳ
            if args.fps_log and frame_index % args.fps_log == 0:
                elapsed = time.time() - started_at
                fps = frame_index / elapsed if elapsed else 0.0
                print(
                    f"[INFO] Frames={frame_index} | Res={frame.shape[1]}x{frame.shape[0]} | ~{fps:.1f} FPS "
                    f"| det={len(detections)} | tracks={len([t for t in tracks if t.track_id is not None])}"
                )

    except KeyboardInterrupt:
        print("[INFO] Dừng pipeline theo yêu cầu người dùng")
    finally:
        source.release()
        if emitter:
            emitter.close()
        if args.display:
            cv2.destroyAllWindows()


def main() -> None:
    run()


if __name__ == "__main__":
    main()

