from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

# Import GStreamer với error handling
try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)  # Khởi tạo GStreamer
    GST_READY = True
    GST_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - phụ thuộc máy
    GST_READY = False
    GST_ERROR = exc
    Gst = None  # type: ignore


class GstSource:
    """Nguồn video dựa trên GStreamer (file hoặc RTSP)."""

    def __init__(self, uri: str) -> None:
        if not GST_READY:
            raise RuntimeError(f"GStreamer chưa sẵn sàng: {GST_ERROR}")
        self._uri = uri
        self._pipeline: Optional[Gst.Pipeline] = None
        self._sink = None

    def _build_description(self) -> str:
        """Tạo GStreamer pipeline description tùy theo loại source"""
        if self._uri.startswith(("rtsp://", "rtsps://")):
            # Pipeline cho RTSP stream
            return (
                f"rtspsrc location={self._uri} latency=200 ! "
                "rtph264depay ! h264parse ! avdec_h264 ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink name=sink emit-signals=false sync=false max-buffers=1 drop=true"
            )
        # Pipeline cho file video
        return (
            f"filesrc location={self._uri} ! "
            "decodebin ! videoconvert ! video/x-raw,format=BGR ! "
            "appsink name=sink emit-signals=false sync=false max-buffers=1 drop=true"
        )

    def open(self) -> bool:
        """Mở và khởi tạo GStreamer pipeline"""
        description = self._build_description()
        try:
            # Tạo pipeline từ description string
            self._pipeline = Gst.parse_launch(description)
            self._sink = self._pipeline.get_by_name("sink")
            if not self._sink:
                return False
            
            # Start pipeline
            self._pipeline.set_state(Gst.State.PLAYING)
            
            # Kiểm tra lỗi trong 3 giây đầu
            bus = self._pipeline.get_bus()
            msg = bus.timed_pop_filtered(3 * Gst.SECOND, Gst.MessageType.ERROR)
            if msg is not None:
                self.release()
                return False
            return True
        except Exception:
            self.release()
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Đọc frame tiếp theo từ pipeline"""
        if not self._sink:
            return False, None
        try:
            # Pull sample từ appsink
            sample = self._sink.emit("pull-sample")
            if not sample:
                return False, None
            
            # Lấy buffer từ sample
            buffer = sample.get_buffer()
            if not buffer:
                return False, None
            
            # Map buffer memory để đọc data
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return False, None
            try:
                # Lấy thông tin kích thước frame từ caps
                caps = sample.get_caps()
                structure = caps.get_structure(0)
                width = int(structure.get_value("width"))
                height = int(structure.get_value("height"))
                
                # Convert buffer data thành numpy array
                data = np.frombuffer(map_info.data, dtype=np.uint8)
                frame = data.reshape((height, width, 3)).copy()
                return True, frame
            finally:
                buffer.unmap(map_info)  # Luôn unmap buffer
        except Exception:
            return False, None

    def release(self) -> None:
        """Giải phóng tài nguyên GStreamer"""
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        self._sink = None

    def __del__(self) -> None:  # pragma: no cover - đảm bảo giải phóng
        self.release()
