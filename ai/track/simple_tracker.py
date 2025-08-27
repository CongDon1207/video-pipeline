# ai/track/simple_tracker.py
from typing import List, Tuple, Dict
from .base_tracker import BaseTracker, BBox

def iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, inter_x2 - inter_x1), max(0, inter_y2 - inter_y1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / max(1.0, union)

class SimpleTracker(BaseTracker):
    def __init__(self, iou_thresh: float = 0.3, max_ttl: int = 30):
        self.iou_thresh = iou_thresh
        self.max_ttl = max_ttl
        self._next_id = 1
        # track_id -> {"bbox":(x1,y1,x2,y2), "ttl":k, "cls":name, "conf":conf}
        self.tracks: Dict[int, Dict] = {}

    def update(self, detections: List[BBox]) -> List[Tuple[int,int,int,int,int,float,str]]:
        # Giảm TTL, xoá track hết hạn
        for tid in list(self.tracks.keys()):
            self.tracks[tid]["ttl"] -= 1
            if self.tracks[tid]["ttl"] <= 0:
                del self.tracks[tid]

        assigned = set()
        results = []

        # Matching greedy theo IOU
        for det in detections:
            x1,y1,x2,y2,conf,_,cls_name = det
            best_iou, best_id = 0.0, None
            for tid, t in self.tracks.items():
                i = iou((x1,y1,x2,y2), t["bbox"])
                if i > best_iou:
                    best_iou, best_id = i, tid

            if best_id is not None and best_iou >= self.iou_thresh and best_id not in assigned:
                # cập nhật track
                self.tracks[best_id]["bbox"] = (x1,y1,x2,y2)
                self.tracks[best_id]["ttl"] = self.max_ttl
                self.tracks[best_id]["conf"] = conf
                self.tracks[best_id]["cls"] = cls_name
                assigned.add(best_id)
                results.append((x1,y1,x2,y2,best_id,conf,cls_name))
            else:
                # tạo track mới
                tid = self._next_id
                self._next_id += 1
                self.tracks[tid] = {"bbox":(x1,y1,x2,y2), "ttl":self.max_ttl, "conf":conf, "cls":cls_name}
                assigned.add(tid)
                results.append((x1,y1,x2,y2,tid,conf,cls_name))

        return results
