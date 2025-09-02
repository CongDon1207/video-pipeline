from typing import List, Tuple

import numpy as np

# Kiểu bbox từ detector: (x1,y1,x2,y2,conf,cls_id,cls_name)
BBox = Tuple[int, int, int, int, float, int, str]


class DeepSortTracker:
    """
    Wrapper around deep-sort-realtime's DeepSort.

    Input detections: List[(x1, y1, x2, y2, conf, cls_id, cls_name)]
    Output: List[(x1, y1, x2, y2, track_id, conf, cls_name)]
    """

    def __init__(
        self,
        *,
        max_age: int = 30,
        n_init: int = 3,
        max_iou_distance: float = 0.7,
        nms_max_overlap: float = 1.0,
        embedder: str = "mobilenet",
        embedder_gpu: bool = False,
        half: bool = False,
    ) -> None:
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
        except Exception as e:
            raise RuntimeError(
                "deep-sort-realtime is required for DeepSortTracker. Install with 'pip install deep-sort-realtime'."
            ) from e

        # Lazily import to avoid hard dependency when not used
        self._DeepSort = DeepSort
        self.tracker = self._DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            nms_max_overlap=nms_max_overlap,
            embedder=embedder,
            embedder_gpu=embedder_gpu,
            half=half,
            bgr=True,
        )

    def update(self, detections: List[BBox], frame: np.ndarray | None = None) -> List[Tuple[int, int, int, int, int, float, str]]:
        # Convert xyxy to ltwh
        raw = []
        for x1, y1, x2, y2, conf, _cls_id, cls_name in detections:
            w = max(0, int(x2 - x1))
            h = max(0, int(y2 - y1))
            raw.append(([int(x1), int(y1), w, h], float(conf), str(cls_name)))

        tracks = self.tracker.update_tracks(raw, frame=frame)
        out: List[Tuple[int, int, int, int, int, float, str]] = []
        for t in tracks:
            # Some tracks may be unconfirmed; we keep only confirmed tracks with a bbox
            if hasattr(t, "is_confirmed") and not t.is_confirmed():
                continue
            if hasattr(t, "to_ltrb"):
                l, t_, r, b = t.to_ltrb()
            elif hasattr(t, "to_tlbr"):
                l, t_, r, b = t.to_tlbr()
            else:
                continue
            track_id = getattr(t, "track_id", -1)
            # DeepSORT does not retain original det confidence per track, set to 1.0 or best available
            conf = float(getattr(t, "det_confidence", 1.0) or 1.0)
            # Try to keep class name from first associated detection if available
            cls_name = getattr(t, "det_class", None) or "object"
            out.append((int(l), int(t_), int(r), int(b), int(track_id), conf, str(cls_name)))
        return out
