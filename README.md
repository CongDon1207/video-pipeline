# Video Metadata Pipeline for Retail

Dự án xây dựng pipeline thu thập và xử lý metadata từ camera chuỗi bán lẻ.

## Thành phần
- **frontend/**: Dashboard hiển thị chỉ số real-time
- **backend/**: API phục vụ dữ liệu (FastAPI)
- **ai/**: Module AI (YOLOv8, DeepSORT/ByteTrack)
- **infra/**: Hạ tầng (Kafka, Spark, MinIO, Docker)
- **docs/**: Tài liệu kỹ thuật & báo cáo

## Roadmap (tóm tắt)
1. Ingestion (RTSP → Kafka)
2. AI detection & tracking
3. Spark streaming processing
4. Lakehouse storage
5. API & Dashboard
