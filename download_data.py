"""Snapshot official CMS API responses; never silently replace an existing snapshot."""
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASETS = {'hospital_visits': '632h-zaca', 'national_visits': 'cvcs-xecj', 'hospital_information': 'xubh-q36u'}

def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt + 1)

def download(item):
    name, identifier = item
    path = ROOT / 'data' / 'raw' / f'{name}.json'
    url = f'https://data.cms.gov/provider-data/api/1/datastore/query/{identifier}/0'
    if path.exists():
        raise FileExistsError(f'{path}: preserve snapshot; move it before refreshing')
    manifest_path = ROOT / 'data/source_manifest.json'
    recorded = next((e for e in json.loads(manifest_path.read_text()) if e['name'] == name), None) if manifest_path.exists() else None
    metadata = fetch(f'https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{identifier}') if recorded is None else {}
    csv_url = recorded['download_url'] if recorded else metadata['distribution'][0]['downloadURL']
    with urllib.request.urlopen(csv_url, timeout=180) as response:
        csv_bytes = response.read()
    if recorded and hashlib.sha256(csv_bytes).hexdigest() != recorded['source_csv_sha256']:
        raise ValueError('Published source has changed; cannot reproduce the pinned snapshot')
    import csv, io
    records = list(csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'))))
    # Match CMS API field names, keeping every source value as text.
    def field_name(key):
        return key.lower().replace(' ', '_').replace('/', '')
    rows = [{field_name(k): v for k, v in r.items()} for r in records]
    count = len(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, separators=(',', ':')), encoding='utf-8')
    print(name, count, flush=True)
    if recorded:
        if hashlib.sha256(path.read_bytes()).hexdigest() != recorded['sha256'] or count != recorded['rows']:
            raise ValueError('Parsed snapshot differs from recorded evidence')
        return recorded
    return {'name': name, 'identifier': identifier, 'api_url': url, 'download_url': csv_url, 'released': metadata.get('released'), 'modified': metadata.get('modified'), 'source_csv_sha256': hashlib.sha256(csv_bytes).hexdigest(), 'catalog_url': f'https://data.cms.gov/provider-data/dataset/{identifier}', 'rows': count, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__ == '__main__':
    with ThreadPoolExecutor(3) as pool:
        manifest = list(pool.map(download, DATASETS.items()))
    (ROOT / 'data' / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
