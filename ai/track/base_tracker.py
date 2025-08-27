# ai/track/base_tracker.py
from abc import ABC, abstractmethod
from typing import List, Tuple

BBox = Tuple[int, int, int, int, float, int, str]  # (x1,y1,x2,y2,conf,cls_id,cls_name)

class BaseTracker(ABC):
    @abstractmethod
    def update(self, detections: List[BBox]) -> List[Tuple[int, int, int, int, int, float, str]]:
        """
        Nhận list bbox từ detector, trả về list (x1,y1,x2,y2,track_id,conf,cls_name)
        """
        ...
