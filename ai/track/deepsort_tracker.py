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
        # Convert xyxy detections to DeepSORT expected ltwh
        raw = []
        for x1, y1, x2, y2, conf, _cls_id, cls_name in detections:
            w = max(0, int(x2 - x1))
            h = max(0, int(y2 - y1))
            raw.append(([int(x1), int(y1), w, h], float(conf), str(cls_name)))

        # Update the underlying DeepSort tracker
        tracks = self.tracker.update_tracks(raw, frame=frame)

        # Build an alignment from detections -> track_id by IoU with original det bboxes
        def iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            ix1 = max(ax1, bx1)
            iy1 = max(ay1, by1)
            ix2 = min(ax2, bx2)
            iy2 = min(ay2, by2)
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            inter = iw * ih
            if inter <= 0:
                return 0.0
            area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
            area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
            union = area_a + area_b - inter
            if union <= 0:
                return 0.0
            return inter / union

        det_xyxy = [
            (int(x1), int(y1), int(x2), int(y2)) for (x1, y1, x2, y2, _c, _id, _n) in detections
        ]

        # For current frame, many tracks may be unconfirmed; only consider confirmed tracks with an original bbox
        candidates: list[tuple[int, Tuple[int, int, int, int], str, float]] = []
        for t in tracks:
            if hasattr(t, "is_confirmed") and not t.is_confirmed():
                continue
            # Prefer original detection bbox for this frame to align back to dets
            orig = None
            if hasattr(t, "to_ltrb"):
                orig = t.to_ltrb(orig=True, orig_strict=True)
            if orig is None and hasattr(t, "to_tlbr"):
                orig = t.to_tlbr()
            if orig is None:
                continue
            l, t_, r, b = [int(v) for v in orig]
            tid = int(getattr(t, "track_id", -1))
            cls_name = str(getattr(t, "det_class", None) or "object")
            conf = float(getattr(t, "det_conf", 1.0) or 1.0)
            candidates.append((tid, (l, t_, r, b), cls_name, conf))

        # Map each detection to best matching track by IoU
        assigned = [-1] * len(det_xyxy)
        assigned_meta: list[tuple[str, float]] = [("object", 1.0)] * len(det_xyxy)
        for i, dbox in enumerate(det_xyxy):
            best_iou = 0.0
            best_tid = -1
            best_meta = ("object", 1.0)
            for tid, tbox, cname, cconf in candidates:
                v = iou(dbox, tbox)
                if v > best_iou:
                    best_iou = v
                    best_tid = tid
                    best_meta = (cname, cconf)
            # Consider a valid match only if IoU is reasonably high
            if best_iou >= 0.5 and best_tid > 0:
                assigned[i] = best_tid
                assigned_meta[i] = best_meta

        # Return list aligned with detections length for downstream emitter
        aligned: List[Tuple[int, int, int, int, int, float, str]] = []
        for (x1, y1, x2, y2, conf, _cls_id, cls_name), tid, meta in zip(detections, assigned, assigned_meta):
            cname, tconf = meta
            # Keep the original det class name if present
            out_name = cls_name or cname
            track_id = int(tid) if tid is not None else -1
            aligned.append((int(x1), int(y1), int(x2), int(y2), track_id, float(conf if conf is not None else tconf), str(out_name)))
        return aligned
