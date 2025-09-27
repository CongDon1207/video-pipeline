from __future__ import annotations

import json
import sys
from typing import Any, Dict, Iterable, Optional, TextIO, Tuple


# Dict chứa thông tin 1 detection: bbox, confidence, class_name, track_id, etc.
DetectionDict = Dict[str, Any]


class JsonEmitter:
    """Ghi metadata detection/tracking dạng NDJSON."""

    def __init__(self, out_path: str = "-") -> None:
        self.out_path = out_path
        self._handle: Optional[TextIO] = None
        self._open()

    def _open(self) -> None:
        """Mở file output hoặc dùng stdout"""
        if self.out_path in ("-", "", None):
            self._handle = sys.stdout
            return
        try:
            self._handle = open(self.out_path, "w", encoding="utf-8")
        except OSError as exc:
            print(f"[WARN] Không mở được {self.out_path}: {exc}; ghi ra stdout")
            self._handle = sys.stdout

    def emit_detection(
        self,
        *,
        schema_version: str,     # Version của JSON schema
        pipeline_run_id: str,   # ID của pipeline run
        source: Dict[str, str], # Metadata source (store_id, camera_id, etc.)
        frame_index: int,       # Số thứ tự frame
        capture_ts: str,        # Timestamp capture (ISO format)
        image_size: Tuple[int, int],  # (width, height) của frame
        detections: Iterable[DetectionDict],  # List detections trong frame
    ) -> None:
        """
        Xuất detection data của 1 frame dạng NDJSON
        """
        if not self._handle:
            return

        width, height = image_size
        frame_payload = []
        
        # Process từng detection trong frame
        for idx, det in enumerate(detections):
            x1, y1, x2, y2 = det.get("bbox", (0, 0, 0, 0))
            w = max(x2 - x1, 0)
            h = max(y2 - y1, 0)
            cx = x1 + w / 2.0  # Centroid X
            cy = y1 + h / 2.0  # Centroid Y
            
            # Helper function normalize coordinates [0,1]
            norm = lambda value, denom: value / denom if denom else 0.0

            # Tạo detection record với đầy đủ metadata
            frame_payload.append(
                {
                    "det_id": f"{frame_index}-{idx}",
                    "class": det.get("class_name"),
                    "class_id": det.get("class_id"),
                    "conf": round(float(det.get("conf", 0.0)), 4),
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "bbox_norm": {  # Normalized bbox [0,1]
                        "x": norm(x1, width),
                        "y": norm(y1, height),
                        "w": norm(w, width),
                        "h": norm(h, height),
                    },
                    "centroid": {"x": int(round(cx)), "y": int(round(cy))},
                    "centroid_norm": {"x": norm(cx, width), "y": norm(cy, height)},
                    "track_id": det.get("track_id"),  # Track ID từ DeepSORT (nếu có)
                }
            )

        # Tạo record JSON cho frame
        record = {
            "schema_version": schema_version,
            "pipeline_run_id": pipeline_run_id,
            "source": source,
            "frame_index": frame_index,
            "capture_ts": capture_ts,
            "image_size": {"width": width, "height": height},
            "detections": frame_payload,
        }

        # Ghi NDJSON (mỗi record 1 dòng)
        try:
            json.dump(record, self._handle, ensure_ascii=False)
            self._handle.write("\n")
            self._handle.flush()
        except OSError as exc:
            print(f"[WARN] Lỗi ghi JSON: {exc}")

    def close(self) -> None:
        """Đóng file output"""
        if self._handle and self._handle is not sys.stdout:
            self._handle.close()
        self._handle = None
