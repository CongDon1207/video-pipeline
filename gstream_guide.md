# GStreamer + Python (Windows/MSYS2) — Hướng dẫn nhanh cho team

> Mục tiêu: Cài **GStreamer** chạy với **Python** trên Windows thông qua **MSYS2**, kiểm tra bằng script, và gợi ý tích hợp vào dự án AI/video-pipeline.

---

## 0) TL;DR (copy–paste nhanh)

```bash
# 1) Cài MSYS2 từ https://www.msys2.org/ rồi mở **MSYS2 MinGW 64-bit** (không dùng Git Bash)
pacman -Syu   # nếu được nhắc thì đóng/mở lại terminal, sau đó:
pacman -Su

# 2) Cài Python + GStreamer + PyGObject + plugin + OpenCV (tuỳ chọn)
pacman -S \
  mingw-w64-x86_64-python \
  mingw-w64-x86_64-gstreamer \
  mingw-w64-x86_64-gst-plugins-base \
  mingw-w64-x86_64-gst-plugins-good \
  mingw-w64-x86_64-gst-plugins-bad \
  mingw-w64-x86_64-gst-plugins-ugly \
  mingw-w64-x86_64-gst-libav \
  mingw-w64-x86_64-gobject-introspection \
  mingw-w64-x86_64-python-gobject \
  mingw-w64-x86_64-python-numpy \
  mingw-w64-x86_64-python-opencv

# 3) (Khuyên dùng) Tạo venv dùng system site-packages
python -m venv .venv_msys --system-site-packages
source .venv_msys/bin/activate

# 4) Kiểm tra
python -c "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; Gst.init(None); print(Gst.version_string())"
# kỳ vọng: GStreamer x.y.z

# (tuỳ chọn) kiểm tra plugin
gst-inspect-1.0 qtdemux avdec_h264 h264parse mp4mux aacparse avenc_aac
```

---

## 1) Vì sao dùng MSYS2?

- Có \*\*trình quản lý gói \*\*`` cài được Python, GStreamer, PyGObject, OpenCV trên Windows đồng bộ với nhau.
- Tránh xung đột giữa Python cài từ python.org và các DLL/typelib của GStreamer.
- Giảm công build/thiếu wheel (đặc biệt với PyGObject).

> **Lưu ý:** Đừng dùng **Git Bash** cho bước cài → `pacman: command not found`. Phải mở **Start Menu → MSYS2 MinGW 64-bit**.

---

## 2) Cài đặt chi tiết

1. Tải MSYS2 từ [https://www.msys2.org/](https://www.msys2.org/) và cài đặt.
2. Mở **MSYS2 MinGW 64-bit**.
3. Cập nhật hệ thống:
   ```bash
   pacman -Syu
   # (nếu được yêu cầu) đóng terminal, mở lại **MSYS2 MinGW 64-bit**, rồi:
   pacman -Su
   ```
4. Cài các gói cần thiết:
   ```bash
   pacman -S \
     mingw-w64-x86_64-python \
     mingw-w64-x86_64-gstreamer \
     mingw-w64-x86_64-gst-plugins-base \
     mingw-w64-x86_64-gst-plugins-good \
     mingw-w64-x86_64-gst-plugins-bad \
     mingw-w64-x86_64-gst-plugins-ugly \
     mingw-w64-x86_64-gst-libav \
     mingw-w64-x86_64-gobject-introspection \
     mingw-w64-x86_64-python-gobject \
     mingw-w64-x86_64-python-numpy \
     mingw-w64-x86_64-python-opencv
   ```

---

## 3) (Khuyến nghị) Tạo virtualenv dùng system site-packages

Mục đích: venv dự án nhìn thấy các package cài bằng `pacman`.

```bash
python -m venv .venv_msys --system-site-packages
source .venv_msys/bin/activate
python -c "import cv2, gi; from gi.repository import Gst; print('OpenCV OK'); Gst.init(None); print(Gst.version_string())"
```

> Nếu bạn tạo venv **không** có `--system-site-packages`, các package cài bằng pacman (cv2/gi) sẽ **không thấy**.

---

