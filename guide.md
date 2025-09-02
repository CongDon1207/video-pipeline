# Hướng dẫn chạy pipeline tối giản (GStreamer → YOLOv8 → DeepSORT)

Mục tiêu: ingest video (file/RTSP) bằng GStreamer hoặc OpenCV, detect bằng YOLOv8 (Ultralytics), track bằng DeepSORT, và xuất metadata NDJSON.

Repo đã được tinh gọn, chỉ giữ các file cần thiết để chạy và test nhanh.

## 1) Cấu trúc thư mục (tối giản)

- `ai/ingest/__main__.py`: CLI điều phối ingest → detect → track → emit
- `ai/ingest/gst_source.py`: Nguồn video qua GStreamer (ưu tiên nếu có)
- `ai/ingest/cv_source.py`: Nguồn video qua OpenCV (fallback khi thiếu GStreamer)
- `ai/detect/yolo_detector.py`: YOLOv8 (Ultralytics)
- `ai/track/deepsort_tracker.py`: DeepSORT (deep-sort-realtime)
- `ai/emit/json_emitter.py`: Xuất NDJSON (1 dòng mỗi frame)
- `scripts/make_synth_video.py`: Tạo video mẫu để test
- `ai/ingest/__init__.py`: đánh dấu package
- `guide.md`: file hướng dẫn này

## 2) Yêu cầu môi trường

Khuyến nghị Python 3.12 trên Windows (dùng launcher `py`).

Các package Python bắt buộc:
- `ultralytics` (YOLOv8)
- `opencv-python` (OpenCV, dùng cả hiển thị và fallback ingest)
- `deep-sort-realtime` (DeepSORT)

Tùy chọn để dùng GStreamer backend (ưu tiên):
- Windows: cài GStreamer + PyGObject (`gi`). Cách nhanh nhất là theo MSYS2/GStreamer/PyGObject (không bắt buộc nếu dùng OpenCV backend). Nếu thiếu `gi`, chương trình sẽ tự fallback sang OpenCV.

## 3) Cài đặt nhanh (Windows, dùng OpenCV backend)

1. Cài các dependency Python (CPU):
   - `py -3.12 -m pip install --upgrade pip wheel setuptools`
   - `py -3.12 -m pip install ultralytics opencv-python deep-sort-realtime`

2. Tạo video mẫu để test:
   - `py -3.12 scripts\make_synth_video.py`
   - Kết quả: `data/synth.avi`

3. Chạy pipeline (OpenCV backend):
   - `py -3.12 -m ai.ingest --backend cv --src data/synth.avi --yolo 1 --track 1 --display 0`

4. Xuất NDJSON (tùy chọn):
   - `py -3.12 -m ai.ingest --backend cv --src data/synth.avi --yolo 1 --track 1 --display 0 --emit detection --out detections.ndjson`

Ghi chú: Video mẫu không có đối tượng người/vật thực nên YOLO có thể không phát hiện gì (detections rỗng) — mục đích chính là smoke test toàn bộ luồng.

## 4) Dùng GStreamer backend (tùy chọn, ưu tiên cho RTSP)

Khi `gi` (PyGObject) sẵn sàng, bạn có thể chạy backend GStreamer để ingest ổn định RTSP/H.264.

Ví dụ lệnh chạy:
- File MP4/H.264: `py -3.12 -m ai.ingest --backend gst --src "path/to/video.mp4" --yolo 1 --track 1`
- RTSP/H.264: `py -3.12 -m ai.ingest --backend gst --src "rtsp://user:pass@host/stream" --yolo 1 --track 1`

Nếu import `gi` thất bại, CLI sẽ tự in cảnh báo và chuyển sang `--backend cv`.

Tóm tắt chuẩn bị GStreamer (Windows, tham khảo nhanh):
- Cài MSYS2, mở "MSYS2 MinGW 64-bit"
- Cài gói: `pacman -Syu` rồi `pacman -S mingw-w64-x86_64-python mingw-w64-x86_64-gstreamer mingw-w64-x86_64-gst-plugins-{base,good,bad,ugly} mingw-w64-x86_64-gst-libav mingw-w64-x86_64-gobject-introspection mingw-w64-x86_64-python-gobject`
- Tạo venv kiểu `--system-site-packages` để Python nhìn thấy `gi`

Lưu ý: Thiết lập MSYS2/PyGObject/GStreamer trên Windows có thể yêu cầu dùng Python trong MSYS2. Nếu chưa quen, hãy chạy nhanh bằng OpenCV backend trước.

## 5) Đối số CLI quan trọng

- `--src`: đường dẫn file hoặc RTSP URL (bắt buộc)
- `--backend {gst,cv}`: chọn backend ingest (mặc định: `gst`, tự fallback `cv` nếu thiếu `gi`)
- `--yolo {0|1}`: bật/tắt YOLO detect (mặc định 1)
- `--track {0|1}`: bật/tắt DeepSORT tracking (mặc định 1)
- `--display {0|1}`: hiển thị preview bằng OpenCV (mặc định 1)
- `--fps_log N`: chu kỳ log FPS (mặc định 30)
- `--emit {none|detection}` + `--out PATH`: xuất NDJSON theo frame
- Metadata nguồn: `--store_id`, `--camera_id`, `--stream_id`, `--run_id`

## 6) Định dạng NDJSON

Mỗi dòng là một JSON với các trường: `schema_version`, `pipeline_run_id`, `source{store_id,camera_id,stream_id}`, `frame_index`, `capture_ts`, `detections[]`.

Mỗi detection: `class`, `class_id`, `conf`, `bbox{x1,y1,x2,y2}`, `bbox_norm{x,y,w,h}`, `centroid{x,y}`, `track_id|null`.

## 7) Gợi ý hiệu năng & GPU

- YOLOv8 có thể dùng GPU nếu PyTorch/CUDA sẵn sàng; mặc định chạy CPU để đơn giản.
- DeepSORT embedder mặc định ‘mobilenet’, chạy CPU (chúng tôi bật `embedder_gpu=False`).

## 8) Khắc phục sự cố nhanh

- Lỗi import `ultralytics/opencv-python/deep_sort_realtime`: kiểm tra đã cài đúng Python phiên bản đang chạy (`py -3.12 -m pip list`).
- Lỗi `gi` không có: backend GStreamer sẽ fallback sang OpenCV; nếu muốn dùng GStreamer, xem mục 4.
- Không thấy detection trên video mẫu: bình thường. Hãy chạy với video thực tế có người/vật.
- RTSP lag: thử GStreamer backend (`--backend gst`) sẽ ổn định hơn OpenCV cho H.264/RTSP.

---

Hết. Cần mình bổ sung Dockerfile hoặc cấu hình GPU/CUDA cho YOLO/DeepSORT không?

