# ai/ingest/ffmpeg_source.py
import cv2
from typing import Optional, Tuple
import numpy as np

from .video_source import VideoSource  # ✅ chỉ import interface, không import chính mình

class FFmpegSource(VideoSource):
    def __init__(self, src: str):
        self.src = src
        self.cap = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.src)
        return bool(self.cap and self.cap.isOpened())

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.cap:
            return False, None
        ok, frame = self.cap.read()
        return ok, frame if ok else None

    def release(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
