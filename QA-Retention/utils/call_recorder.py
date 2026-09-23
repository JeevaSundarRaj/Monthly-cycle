import csv
import threading

_lock = threading.Lock()
_rows = []


def record_call(name, call_type, call_id):
    if not call_id:
        return
    url = f"https://dialpadbeta.com/csr/call/{call_id}"
    with _lock:
        _rows.append((name, f"{call_type}: {url}"))


def write_csv(path="call_summary.csv"):
    with _lock:
        rows = list(_rows)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Call"])
        writer.writerows(rows)
    return len(rows)
