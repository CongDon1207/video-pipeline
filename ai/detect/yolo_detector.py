# ai/detect/yolo_detector.py
from typing import List, Tuple, Optional
import numpy as np
from ultralytics import YOLO

class YoloDetector:
    """
    Thin wrapper quanh Ultralytics YOLOv8 để detect theo lớp mong muốn.
    Kết quả trả về: list (x1, y1, x2, y2, conf, cls_id, cls_name)
    """
    def __init__(self, model_path: str = "yolov8n.pt", conf: float = 0.25, classes: Optional[List[str]] = None):
        self.model = YOLO(model_path)  # tự tải nếu chưa có
        self.conf = conf
        self.classes = set([c.lower() for c in classes]) if classes else None
        # map id -> name từ model
        self.id2name = self.model.model.names if hasattr(self.model.model, "names") else {}

    def infer(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, float, int, str]]:
        # Ultralytics nhận BGR hoặc RGB; tự xử lý nội bộ
        results = self.model.predict(frame_bgr, verbose=False, conf=self.conf, device="cpu")
        out = []
        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes.xyxy.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            clss = r.boxes.cls.cpu().numpy().astype(int)
            for (x1, y1, x2, y2), cf, ci in zip(boxes, confs, clss):
                name = str(self.id2name.get(int(ci), ci)).lower()
                if self.classes and name not in self.classes:
                    continue
                out.append((x1, y1, x2, y2, float(cf), int(ci), name))
        return out
