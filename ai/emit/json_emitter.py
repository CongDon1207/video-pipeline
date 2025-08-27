# ai/emit/json_emitter.py
import sys, json, uuid
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

Det = Tuple[int,int,int,int,float,int,str]       # (x1,y1,x2,y2,conf,cls_id,cls_name)
Tracked = Tuple[int,int,int,int,int,float,str]   # (x1,y1,x2,y2,track_id,conf,cls_name)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class JsonEmitter:
    def __init__(self, out_path: Optional[str] = None):
        """
        out_path: đường dẫn file NDJSON. Nếu None hoặc "-", ghi ra stdout.
        """
        self.out_path = out_path
        self._fh = None
        if out_path and out_path != "-":
            self._fh = open(out_path, "a", encoding="utf-8")

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None

    def _write_line(self, obj: Dict):
        line = json.dumps(obj, ensure_ascii=False)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()
        else:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

    def emit_detection(
        self,
        *,
        schema_version: str,
        pipeline_run_id: str,
        source: Dict,                     # {"store_id":..., "camera_id":..., "stream_id":...}
        frame_index: int,
        capture_ts: Optional[str],
        image_size: Tuple[int,int],       # (w,h)
        dets: List[Det],
        tracked: Optional[List[Tracked]] = None
    ):
        """
        Ghi 1 bản ghi detection cho 1 frame. Nếu có 'tracked', sẽ điền track_id tương ứng.
        """
        w, h = image_size
        ts = capture_ts or _utc_now_iso()

        detections = []
        if tracked is not None and len(tracked) == len(dets):
            # giả định output của tracker giữ thứ tự theo detections
            for i, (d, t) in enumerate(zip(dets, tracked)):
                x1, y1, x2, y2, conf, cls_id, cls_name = d
                _, _, _, _, track_id, _, _ = t
                detections.append({
                    "det_id": f"{frame_index}-{i}",
                    "class": cls_name,
                    "class_id": int(cls_id),
                    "conf": float(conf),
                    "bbox": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                    "bbox_norm": {
                        "x": float(x1)/max(1,w),
                        "y": float(y1)/max(1,h),
                        "w": float(x2 - x1)/max(1,w),
                        "h": float(y2 - y1)/max(1,h),
                    },
                    "centroid": {"x": int((x1 + x2)//2), "y": int((y1 + y2)//2)},
                    "track_id": int(track_id)
                })
        else:
            for i, (x1, y1, x2, y2, conf, cls_id, cls_name) in enumerate(dets):
                detections.append({
                    "det_id": f"{frame_index}-{i}",
                    "class": cls_name,
                    "class_id": int(cls_id),
                    "conf": float(conf),
                    "bbox": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                    "bbox_norm": {
                        "x": float(x1)/max(1,w),
                        "y": float(y1)/max(1,h),
                        "w": float(x2 - x1)/max(1,w),
                        "h": float(y2 - y1)/max(1,h),
                    },
                    "centroid": {"x": int((x1 + x2)//2), "y": int((y1 + y2)//2)},
                    "track_id": None
                })

        record = {
            "schema_version": schema_version,
            "pipeline_run_id": pipeline_run_id,
            "source": source,
            "frame_index": int(frame_index),
            "capture_ts": ts,
            "detections": detections
        }
        self._write_line(record)
