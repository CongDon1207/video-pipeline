import inspect

try:
    import deep_sort_realtime.deepsort_tracker as d
except Exception as e:
    print("deep_sort_realtime not importable:", e)
    raise SystemExit(1)

DeepSort = getattr(d, "DeepSort")
print("Signature:", inspect.signature(DeepSort.__init__))

src = inspect.getsource(DeepSort.__init__).splitlines()
print("\nFirst 60 lines of __init__:\n")
for i, line in enumerate(src[:60], start=1):
    print(f"{i:02d}:", line.rstrip())

