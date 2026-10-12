import csv
import threading

_lock = threading.Lock()
_rows = []  # (name, call_type, url)
_seen = set()  # (name, call_type) already recorded


def record_call(name, call_type, call_id):
    if not call_id:
        return
    url = f"https://dialpadbeta.com/csr/call/{call_id}"
    with _lock:
        # the same entity can be exercised under two policies; keep both as separate groups
        group = 1
        while (name, group, call_type) in _seen:
            group += 1
        _seen.add((name, group, call_type))
        _rows.append((name if group == 1 else f"{name} (Group {group})", call_type, url))


def write_csv(path="call_summary.csv"):
    """One row per entity; its Inbound/Outbound/VM links share a single cell."""
    with _lock:
        rows = list(_rows)
    if not rows:
        return 0  # don't clobber the existing summary when no calls were made
    grouped = {}
    for name, call_type, url in rows:
        grouped.setdefault(name, []).append(f"{call_type}: {url}")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Calls"])
        for name, calls in grouped.items():
            writer.writerow([name, "\n".join(calls)])
    return len(grouped)
