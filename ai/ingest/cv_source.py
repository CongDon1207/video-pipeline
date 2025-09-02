import cv2
import numpy as np
from typing import Optional, Tuple


class CvSource:
    """
    OpenCV-based video source. Supports file path or RTSP URL.
    Produces BGR frames compatible with OpenCV/Ultralytics.
    """

    def __init__(self, path: str):
        self.path = path
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.path)
        return bool(self.cap and self.cap.isOpened())

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap:
            return False, None
        ok, frame = self.cap.read()
        if not ok:
            return False, None
        return True, frame

    def release(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None

