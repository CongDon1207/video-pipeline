# ai/ingest/video_source.py
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np

class VideoSource(ABC):
    @abstractmethod
    def open(self) -> bool: ...
    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]: ...
    @abstractmethod
    def release(self) -> None: ...
