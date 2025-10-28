import sys
from pathlib import Path
import json


def extract_metrics(path: Path) -> None:
    lines = path.read_text().splitlines()
    points = []

    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get('type') == 'Point' and record.get('metric') == 'http_req_duration':
            points.append(record['data']['value'])

    if not points:
        print('No http_req_duration data found.')
        return

    points.sort()
    p95_index = int(len(points) * 0.95) - 1
    p95_value = points[max(p95_index, 0)]

    print(f'Observed samples: {len(points)}')
    print(f'Computed p95: {p95_value:.2f} ms')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python scripts/perf/summarize_p95.py <k6-json-output>')
        sys.exit(1)
    extract_metrics(Path(sys.argv[1]))
