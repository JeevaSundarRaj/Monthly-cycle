import csv
import re
import sys

LINE_PATTERN = re.compile(
    r"^(?:Inbound|Outbound|Missed and voicemail) Call id for '(?P<name>.+?)' "
    r"\(.*?\): (?P<call_type>Inbound|Outbound|VM):\s*(?P<url>\S+)$"
)


def parse_log(log_path):
    rows = []
    with open(log_path) as f:
        for line in f:
            match = LINE_PATTERN.match(line.strip())
            if match:
                rows.append((match["name"], f"{match['call_type']}: {match['url']}"))
    return rows


def write_table(rows, output_path):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Call"])
        writer.writerows(rows)


if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else "call.logs"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "call_summary.csv"

    rows = parse_log(log_path)
    write_table(rows, output_path)
    print(f"Wrote {len(rows)} call entries to {output_path}")
