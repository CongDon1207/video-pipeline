# ai/ingest/gst_source.py
import os
import gi
import numpy as np

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp

# Khởi tạo GStreamer
Gst.init(None)


def _to_file_uri(path: str) -> str:
    """Chuyển đường dẫn Windows sang file:// URI an toàn."""
    abs_path = os.path.abspath(path)
    # thay \ thành / để GStreamer hiểu
    abs_path = abs_path.replace("\\", "/")
    return f"file:///{abs_path}"


class GstSource:
    """
    Nguồn video dựa trên GStreamer, đọc frame (BGR) qua appsink.

    - File MP4 H.264: filesrc ! qtdemux ! h264parse ! avdec_h264 ! videoconvert ! appsink
    - RTSP H.264    : rtspsrc ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink
    """

    def __init__(self, path: str):
        self.path = path
        self.pipeline: Gst.Pipeline | None = None
        self.appsink: GstApp.AppSink | None = None
        self.bus: Gst.Bus | None = None

    def _build_pipeline_desc(self) -> str:
        if self.path.startswith("rtsp://"):
            # Pipeline RTSP (H.264)
            return (
                f'rtspsrc location="{self.path}" latency=200 drop-on-late=true ! '
                'rtph264depay ! h264parse ! avdec_h264 ! '
                'videoconvert ! video/x-raw,format=BGR ! '
                'appsink name=sink sync=false drop=true max-buffers=1 emit-signals=false'
            )
        else:
            # Pipeline file MP4 (H.264)
            if not os.path.exists(self.path):
                # Không phải RTSP cũng không phải file có sẵn
                return ""

            # Dùng demux tường minh để chỉ lấy nhánh video_0
            file_uri = _to_file_uri(self.path)
            # filesrc cần 'location' (không phải uri). Ta vẫn dùng location trực tiếp.
            # qtdemux tạo pad động video_0 → link tường minh
            return (
                f'filesrc location="{self.path}" ! qtdemux name=d '
                'd.video_0 ! queue ! h264parse ! avdec_h264 ! '
                'videoconvert ! video/x-raw,format=BGR ! '
                'appsink name=sink sync=false drop=true max-buffers=1 emit-signals=false'
            )

    def open(self) -> bool:
        desc = self._build_pipeline_desc()
        if not desc:
            return False

        self.pipeline = Gst.parse_launch(desc)
        if not isinstance(self.pipeline, Gst.Pipeline):
            return False

        # Lấy appsink và cast đúng type
        sink = self.pipeline.get_by_name("sink")
        if sink is None:
            return False
        self.appsink = GstApp.AppSink.cast(sink)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()

        # Start
        self.pipeline.set_state(Gst.State.PLAYING)

        # Đợi trạng thái sẵn sàng/ báo lỗi sớm (tối đa ~5s)
        msg = self.bus.timed_pop_filtered(
            5 * Gst.SECOND,
            Gst.MessageType.ERROR | Gst.MessageType.STATE_CHANGED | Gst.MessageType.EOS,
        )
        if msg and msg.type == Gst.MessageType.ERROR:
            return False
        if msg and msg.type == Gst.MessageType.EOS:
            return False
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        """
        Đọc 1 frame.
        Trả về: (ok: bool, frame_bgr: np.ndarray | None)
        """
        if not self.pipeline or not self.appsink or not self.bus:
            return False, None

        # Kiểm tra lỗi/EOS nhanh
        msg = self.bus.timed_pop_filtered(
            0, Gst.MessageType.ERROR | Gst.MessageType.EOS
        )
        if msg:
            return False, None

        # Lấy sample từ appsink. Ưu tiên try_pull_sample (non-blocking timeout).
        sample = None
        if hasattr(self.appsink, "try_pull_sample"):
            sample = self.appsink.try_pull_sample(2 * Gst.SECOND)
            while sample is None:
                # giữa các lần chờ, kiểm tra EOS/ERROR
                msg = self.bus.timed_pop_filtered(
                    0, Gst.MessageType.ERROR | Gst.MessageType.EOS
                )
                if msg:
                    return False, None
                sample = self.appsink.try_pull_sample(2 * Gst.SECOND)
        else:
            # Fallback: pull_sample() (blocking) – kiểm tra nhanh EOS trước khi block
            msg = self.bus.timed_pop_filtered(
                0, Gst.MessageType.ERROR | Gst.MessageType.EOS
            )
            if msg:
                return False, None
            sample = self.appsink.pull_sample()
            if sample is None:
                return False, None

        # Map buffer thành BGR array
        buf = sample.get_buffer()
        caps = sample.get_caps()
        s = caps.get_structure(0)
        w = int(s.get_value("width"))
        h = int(s.get_value("height"))

        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return False, None
        try:
            frame = np.frombuffer(mapinfo.data, dtype=np.uint8).reshape(h, w, 3)  # BGR
            # Trả về bản copy nếu bạn sợ buffer bị reuse: frame = frame.copy()
        finally:
            buf.unmap(mapinfo)

        return True, frame

    def release(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.appsink = None
        self.bus = None


if __name__ == "__main__":
    # Test nhanh: đọc vài frame rồi thoát
    test_path = os.path.join(
        "data", "videos", "Midtown corner store surveillance video 11-25-18.mp4"
    )
    src = GstSource(test_path)
    if not src.open():
        print("[ERROR] Không mở được nguồn")
        raise SystemExit(2)
    cnt = 0
    while True:
        ok, frame = src.read()
        if not ok or frame is None:
            break
        cnt += 1
        if cnt % 30 == 0:
            print("Frame:", frame.shape, "Count:", cnt)
        if cnt >= 120:
            break
    src.release()
    print("[INFO] Done.")
