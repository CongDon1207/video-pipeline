import argparse
import json
from collections import Counter, defaultdict


def analyze(path: str):
    ids = set()
    per_class_ids = defaultdict(set)
    frames = 0
    missing = 0
    cls_counter = Counter()
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            frames += 1
            obj = json.loads(line)
            for det in obj.get('detections', []):
                tid = det.get('track_id')
                cls = det.get('class')
                if cls is not None:
                    cls_counter[cls] += 1
                if tid is None:
                    missing += 1
                else:
                    ids.add(tid)
                    if cls is not None:
                        per_class_ids[cls].add(tid)

    print(f'frames: {frames}')
    print(f'unique_ids: {len(ids)} {sorted(list(ids))[:50]}')
    print(f'missing_track_ids: {missing}')
    print(f'class_counts: {dict(cls_counter)}')
    for c, s in per_class_ids.items():
        print(f'class_unique_ids[{c}]: {len(s)} {sorted(list(s))[:50]}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    args = ap.parse_args()
    analyze(args.path)

