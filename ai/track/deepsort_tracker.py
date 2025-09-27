from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
except ImportError as exc:  # pragma: no cover - phụ thuộc môi trường
    raise ImportError("Cần cài: pip install deep-sort-realtime") from exc


# Format detection từ YOLO: (x1, y1, x2, y2, confidence, class_id, class_name)
DetectionTuple = Tuple[int, int, int, int, float, int, str]


@dataclass
class TrackResult:
    """Kết quả tracking cho 1 object"""
    x1: int
    y1: int
    x2: int
    y2: int
    track_id: int
    confidence: float
    class_name: str


class DeepSortTracker:
    """Wrapper gọn cho DeepSORT - multi-object tracking với appearance features"""

    def __init__(
        self,
        *,
        max_age: int = 30,           # Track tồn tại tối đa bao nhiêu frame khi mất detection
        n_init: int = 3,             # Số detection cần để confirm track mới
        max_iou_distance: float = 0.7,  # Ngưỡng IoU cho data association
        nms_max_overlap: float = 1.0,   # Ngưỡng NMS overlap
        embedder: str = "mobilenet",     # Model extract appearance features
        embedder_gpu: bool = False,      # Dùng GPU cho embedder
        half: bool = False,              # FP16 precision
    ) -> None:
        # Khởi tạo DeepSORT tracker với parameters
        self._tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            nms_max_overlap=nms_max_overlap,
            embedder=embedder,
            embedder_gpu=embedder_gpu,
            half=half,
        )

    def update(self, detections: Sequence[DetectionTuple], frame: np.ndarray) -> List[TrackResult]:
        """
        Update tracking với detections mới
        Args:
            detections: List detection từ YOLO
            frame: Frame hiện tại để extract appearance features
        Returns:
            List confirmed tracks với track_id
        """
        # Convert format YOLO sang DeepSORT (x,y,w,h)
        formatted = []
        for x1, y1, x2, y2, conf, _, cls_name in detections:
            width = max(0, x2 - x1)
            height = max(0, y2 - y1)
            if width <= 0 or height <= 0:
                continue  # Skip invalid boxes
            formatted.append(([x1, y1, width, height], conf, cls_name))
        
        # Update tracker với frame context
        tracks = self._tracker.update_tracks(formatted, frame=frame)

        # Convert output về format chuẩn
        results: List[TrackResult] = []
        for track in tracks:
            if not track.is_confirmed():
                continue  # Chỉ lấy confirmed tracks
            
            # Convert từ (left,top,width,height) về (x1,y1,x2,y2)
            left, top, width, height = track.to_ltwh()
            x1 = int(round(left))
            y1 = int(round(top))
            x2 = int(round(left + width))
            y2 = int(round(top + height))
            
            results.append(
                TrackResult(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    track_id=int(track.track_id),
                    confidence=float(track.get_det_conf() or 0.0),
                    class_name=str(track.get_det_class() or ""),
                )
            )
        return results


