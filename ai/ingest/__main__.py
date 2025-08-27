# ai/ingest/__main__.py
import os
import time
import uuid
import argparse
from datetime import datetime, timezone

import cv2
from .gst_source import GstSource


def _maybe_init_detector(args):
    if not args.yolo:
        return None
    from ai.detect.yolo_detector import YoloDetector
    classes = [c.strip() for c in args.classes.split(",")] if args.classes else None
    return YoloDetector(model_path=args.model, conf=args.conf, classes=classes)


def main():
    ap = argparse.ArgumentParser()
    # Ingest & hiển thị
    ap.add_argument("--src", required=True, help="Đường dẫn file hoặc RTSP URL")
    ap.add_argument("--display", type=int, default=int(os.getenv("DISPLAY", "1")), help="Hiển thị preview (1/0)")
    ap.add_argument("--fps_log", type=int, default=int(os.getenv("FPS_LOG_INTERVAL", "30")), help="Chu kỳ log FPS")

    # YOLO (detect)
    ap.add_argument("--yolo", type=int, default=0, help="Bật YOLO detect (1/0)")
    ap.add_argument("--model", type=str, default=os.getenv("YOLO_MODEL", "yolov8n.pt"), help="Model YOLOv8")
    ap.add_argument("--conf", type=float, default=float(os.getenv("YOLO_CONF", "0.25")), help="Ngưỡng confidence")
    ap.add_argument("--classes", type=str, default=os.getenv("YOLO_CLASSES", "person"),
                    help="Lọc class, ví dụ: 'person,bag'")

    # Tracking
    ap.add_argument("--track", type=int, default=0, help="Bật tracking (1/0). Bước sau có thể đổi sang ByteTrack.")
    ap.add_argument("--iou", type=float, default=float(os.getenv("TRACK_IOU", "0.3")),
                    help="Ngưỡng IOU cho SimpleTracker")
    ap.add_argument("--ttl", type=int, default=int(os.getenv("TRACK_TTL", "30")),
                    help="Số khung giữ track nếu mất mục tiêu")

    # Emit NDJSON (detection per-frame) & metadata nguồn
    ap.add_argument("--emit", type=str, default="none", choices=["none", "detection"],
                    help="Kiểu dữ liệu xuất NDJSON")
    ap.add_argument("--out", type=str, default="-",
                    help="Đường dẫn file NDJSON (mặc định '-' = stdout)")
    ap.add_argument("--store_id", type=str, default=os.getenv("STORE_ID", "store_01"))
    ap.add_argument("--camera_id", type=str, default=os.getenv("CAMERA_ID", "cam_01"))
    ap.add_argument("--stream_id", type=str, default=os.getenv("STREAM_ID", "stream_01"))
    ap.add_argument("--run_id", type=str, default=os.getenv("PIPELINE_RUN_ID", ""))

    args = ap.parse_args()

    # Detector & Tracker
    det = _maybe_init_detector(args)
    tracker = None
    if args.track:
        from ai.track.simple_tracker import SimpleTracker
        tracker = SimpleTracker(iou_thresh=args.iou, max_ttl=args.ttl)

    # Emitter NDJSON
    emitter = None
    if args.emit != "none":
        from ai.emit.json_emitter import JsonEmitter  # yêu cầu file ai/emit/json_emitter.py
        emitter = JsonEmitter(out_path=args.out)

    pipeline_run_id = args.run_id if args.run_id else uuid.uuid4().hex
    source_info = {"store_id": args.store_id, "camera_id": args.camera_id, "stream_id": args.stream_id}

    # Mở nguồn video
    src = GstSource(args.src)
    if not src.open():
        print(f"[ERROR] Không mở được nguồn: {args.src}")
        raise SystemExit(2)

    t0 = time.time()
    frames = 0
    det_total = 0
    win = "Ingestion Preview (q=quit)"

    try:
        while True:
            ok, frame = src.read()
            if not ok or frame is None:
                print("[INFO] End of stream or read error.")
                break
            frames += 1

            tracked = None
            dets = []
            # Detect + Track
            if det is not None:
                dets = det.infer(frame)  # [(x1,y1,x2,y2,conf,cls_id,cls_name)]
                det_total += len(dets)

                if tracker:
                    tracked = tracker.update(dets)  # [(x1,y1,x2,y2,tid,conf,cls)]
                else:
                    tracked = [(x1, y1, x2, y2, -1, conf, cls) for (x1, y1, x2, y2, conf, _, cls) in dets]

                # Vẽ bbox + ID (nếu bật display)
                if args.display:
                    for x1, y1, x2, y2, tid, cf, name in tracked:
                        color = (0, 255, 0) if tid > 0 else (255, 0, 0)
                        label = f"{'ID'+str(tid)+':' if tid>0 else ''}{name}:{cf:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, max(0, y1 - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

            # Emit NDJSON (detection per-frame)
            if emitter and det is not None:
                h, w = frame.shape[:2]
                capture_ts = datetime.now(timezone.utc).isoformat()
                emitter.emit_detection(
                    schema_version="1.0",
                    pipeline_run_id=pipeline_run_id,
                    source=source_info,
                    frame_index=frames,
                    capture_ts=capture_ts,
                    image_size=(w, h),
                    dets=dets,
                    tracked=tracked if tracker else None
                )

            # Hiển thị
            if args.display:
                cv2.imshow(win, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] Quit by user.")
                    break

            # Log
            if frames % args.fps_log == 0:
                fps = frames / (time.time() - t0)
                h, w = frame.shape[:2]
                extra = ""
                if det is not None:
                    active_tracks = len(tracker.tracks) if tracker else 0
                    extra = f" | det_total={det_total}" + (f" | active_tracks={active_tracks}" if tracker else "")
                print(f"[INFO] Frames={frames} | Res={w}x{h} | ~{fps:.1f} FPS{extra}")

    finally:
        src.release()
        if emitter:
            emitter.close()
        if args.display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
