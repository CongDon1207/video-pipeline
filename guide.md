# Hướng dẫn chạy Video Pipeline (Ingest → YOLOv8 → DeepSORT → Export)

Video pipeline thực hiện luồng xử lý video hoàn chỉnh: **Ingest video** → **Object Detection** → **Object Tracking** → **Export Metadata**

## 🎯 Tổng quan Pipeline

**Pipeline Components:**
- **Ingest**: Đọc video từ file MP4/RTSP qua GStreamer hoặc OpenCV
- **Detect**: Phát hiện đối tượng (người, xe, đồ vật) bằng YOLOv8 
- **Track**: Theo dõi đối tượng qua các frame bằng DeepSORT
- **Emit**: Xuất metadata detection/tracking dạng NDJSON

**Luồng xử lý**: `Video Frame` → `YOLO Detection` → `DeepSORT Tracking` → `JSON Metadata` → `Display/Export`

## 📁 Cấu trúc Core Files

```
ai/
├── ingest/
│   ├── __main__.py           # CLI chính điều phối pipeline
│   ├── gst_source.py         # GStreamer video source (RTSP/MP4)
│   └── cv_source.py          # OpenCV video source (fallback)
├── detect/
│   └── yolo_detector.py      # YOLOv8 object detection
├── track/
│   └── deepsort_tracker.py   # DeepSORT multi-object tracking
└── emit/
    └── json_emitter.py       # NDJSON metadata export
```

## 🔧 Cài đặt môi trường

**Python 3.12** (khuyến nghị trên Windows):

```bash
# Cài dependencies chính
py -3.12 -m pip install --upgrade pip wheel setuptools
py -3.12 -m pip install ultralytics opencv-python deep-sort-realtime

# Kiểm tra cài đặt
py -3.12 -m pip list | grep -E "(ultralytics|opencv|deep-sort)"
```

## 🚀 Cách chạy Pipeline từng bước

### Bước 1: Chuẩn bị video test

```bash
# Tạo video tổng hợp để test (nếu chưa có video thực)
py -3.12 scripts/make_synth_video.py
# → Tạo data/synth.avi

# Hoặc dùng video thực có sẵn
ls "data/videos/"
```

### Bước 2: Chạy Pipeline cơ bản (với display)

```bash
# Test với video thực - hiển thị cửa sổ preview
py -3.12 -m ai.ingest \
  --backend cv \
  --src "data/videos/Midtown corner store surveillance video 11-25-18.mp4" \
  --yolo 1 \
  --track 1 \
  --display 1
```

**Ý nghĩa từng tham số:**
- `--backend cv`: Dùng OpenCV để đọc video (ổn định, không cần GStreamer)
- `--src`: Đường dẫn file video input  
- `--yolo 1`: Bật YOLO detection (phát hiện người, xe, đồ vật)
- `--track 1`: Bật DeepSORT tracking (gán ID cho đối tượng qua frames)
- `--display 1`: **Hiển thị cửa sổ preview** để xem trực quan quá trình detect/track

### Bước 3: Chạy Pipeline với xuất NDJSON

```bash
# Chạy đầy đủ + export metadata
py -3.12 -m ai.ingest \
  --backend cv \
  --src "data/videos/Midtown corner store surveillance video 11-25-18.mp4" \
  --yolo 1 \
  --track 1 \
  --display 1 \
  --emit detection \
  --out detections_output.ndjson
```

**Tham số bổ sung:**
- `--emit detection`: Xuất detection metadata mỗi frame
- `--out detections_output.ndjson`: File output chứa metadata

### Bước 4: Kiểm tra kết quả

```bash
# Xem thông tin file output
ls -la detections_output.ndjson
wc -l detections_output.ndjson

# Xem sample output
head -2 detections_output.ndjson | jq .
```

## 📊 Đọc hiểu Log Output

```
[INFO] Frames=30 | Res=1280x720 | ~9.8 FPS | det_total=33 | active_tracks=0
```

**Giải thích:**
- `Frames=30`: Đã xử lý 30 frames
- `Res=1280x720`: Resolution video 
- `~9.8 FPS`: Tốc độ xử lý pipeline
- `det_total=33`: Tổng số detection từ đầu
- `active_tracks=0`: Số đối tượng đang được track

## 🎛️ Tuỳ chỉnh Pipeline

### Chỉ Detection (không Tracking)
```bash
py -3.12 -m ai.ingest --backend cv --src video.mp4 --yolo 1 --track 0 --display 1
```

### Thay đổi model YOLO
```bash
py -3.12 -m ai.ingest --backend cv --src video.mp4 --model yolov8s.pt --conf 0.5 --display 1
```

### Lọc chỉ detect người
```bash
py -3.12 -m ai.ingest --backend cv --src video.mp4 --classes person --display 1
```

### Điều chỉnh metadata nguồn
```bash
py -3.12 -m ai.ingest \
  --src video.mp4 \
  --store_id "store_downtown" \
  --camera_id "cam_entrance" \
  --stream_id "main_feed" \
  --display 1
```

## 🔍 GStreamer Backend (Advanced)

**Khi nào dùng GStreamer:**
- Xử lý RTSP streams từ IP cameras
- Cần hiệu năng tốt với H.264 decoding
- Xử lý nhiều stream đồng thời

```bash
# Thử GStreamer (sẽ fallback OpenCV nếu thiếu 'gi')
py -3.12 -m ai.ingest --backend gst --src video.mp4 --display 1

# RTSP stream (khi có GStreamer)
py -3.12 -m ai.ingest --backend gst --src "rtsp://user:pass@192.168.1.100/stream" --display 1
```

## 📄 Format NDJSON Output

Mỗi dòng là JSON của 1 frame:

```json
{
  "schema_version": "1.0",
  "pipeline_run_id": "unique-run-id", 
  "source": {
    "store_id": "store_01",
    "camera_id": "cam_01", 
    "stream_id": "stream_01"
  },
  "frame_index": 1,
  "capture_ts": "2025-09-02T03:00:13.891188+00:00",
  "detections": [
    {
      "det_id": "1-0",
      "class": "person",
      "class_id": 0, 
      "conf": 0.823,
      "bbox": {"x1": 344, "y1": 58, "x2": 438, "y2": 430},
      "bbox_norm": {"x": 0.269, "y": 0.081, "w": 0.073, "h": 0.517},
      "centroid": {"x": 391, "y": 244},
      "track_id": null
    }
  ]
}
```

## ⚠️ Troubleshooting

### Lỗi thiếu dependencies
```bash
# Kiểm tra packages
py -3.12 -m pip list | grep -E "(ultralytics|opencv|deep-sort)"

# Cài lại nếu thiếu
py -3.12 -m pip install ultralytics opencv-python deep-sort-realtime
```

### Video không load được
```bash
# Kiểm tra file tồn tại
ls -la "data/videos/"

# Test với video đơn giản
py -3.12 scripts/make_synth_video.py
py -3.12 -m ai.ingest --backend cv --src data/synth.avi --display 1
```

### GStreamer fallback
```
[WARN] GStreamer backend không sẵn sàng (thiếu gi). Tự động chuyển sang OpenCV.
```
**→ Bình thường**, pipeline vẫn hoạt động với OpenCV backend.

### Không thấy detection
- Video tổng hợp (`synth.avi`) có thể không có đối tượng thực → bình thường
- Dùng video surveillance có người/xe để thấy detection
- Giảm `--conf` (mặc định 0.25) để detection nhạy hơn

## 🎯 Use Cases thực tế

**Retail Surveillance:**
```bash
py -3.12 -m ai.ingest \
  --src "rtsp://camera-ip/stream" \
  --classes "person,bag,bottle" \
  --store_id "walmart_downtown" \
  --camera_id "checkout_cam_03" \
  --emit detection \
  --out retail_detections.ndjson \
  --display 1
```

**Traffic Monitoring:**
```bash  
py -3.12 -m ai.ingest \
  --src traffic_video.mp4 \
  --classes "car,truck,bus,motorcycle" \
  --track 1 \
  --emit detection \
  --out traffic_analysis.ndjson \
  --display 1
```

---

**💡 Tip**: Luôn dùng `--display 1` khi test để theo dõi trực quan pipeline hoạt động!

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

