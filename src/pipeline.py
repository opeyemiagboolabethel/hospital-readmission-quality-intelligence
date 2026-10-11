"""Reproducible hospital-level benchmarking. No patient prediction or re-risk-adjustment."""
import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'READM_30_HF': 'Heart failure', 'READM_30_PN': 'Pneumonia', 'READM_30_COPD': 'COPD', 'READM_30_AMI': 'Heart attack', 'READM_30_CABG': 'Coronary bypass', 'READM_30_HIP_KNEE': 'Hip / knee replacement'}
KEYS = ['facility_id', 'measure_id', 'start_date', 'end_date']

def prepare(visits, national, information):
    data = visits.loc[visits.measure_id.isin(LABELS)].copy()
    if data.duplicated(KEYS).any() or information.facility_id.duplicated().any():
        raise ValueError('Duplicate hospital-measure-period or hospital ID')
    if not data.facility_id.str.fullmatch(r'[A-Z0-9]{6}').all():
        raise ValueError('Facility identifiers were damaged')
    for field in ['score', 'denominator', 'lower_estimate', 'higher_estimate']:
        data[field + '_raw'] = data[field]
        data[field] = pd.to_numeric(data[field], errors='coerce')
    if not data.score.dropna().between(0, 100).all():
        raise ValueError('Rate outside percentage scale')
    if (data.denominator.dropna() <= 0).any():
        raise ValueError('Invalid denominator')
    reference = national.loc[national.measure_id.isin(LABELS), ['measure_id', 'start_date', 'end_date', 'national_rate']].copy()
    reference.national_rate = pd.to_numeric(reference.national_rate, errors='raise')
    if reference.duplicated(KEYS[1:]).any():
        raise ValueError('Duplicate reference')
    data = data.merge(reference, on=KEYS[1:], how='left', validate='many_to_one', indicator='reference_match')
    if (data.reference_match != 'both').any():
        raise ValueError('Missing national benchmark for exact measure and period')
    cols = ['facility_id', 'hospital_type', 'hospital_ownership', 'emergency_services']
    data = data.merge(information[cols], on='facility_id', how='left', validate='many_to_one', indicator='information_match')
    data['condition'] = data.measure_id.map(LABELS)
    data['gap_pp'] = (data.score - data.national_rate).round(6)
    data['rate_available'] = data.score.notna()
    data['interval_available'] = data.lower_estimate.notna() & data.higher_estimate.notna()
    data['point_comparison'] = np.select([data.score.isna(), data.gap_pp > 0, data.gap_pp < 0], ['Unavailable', 'Above benchmark', 'Below benchmark'], default='At benchmark')
    return data

def select_scope(data, measure_id, states=None, ownership=None, minimum_denominator=0):
    out = data.loc[data.measure_id == measure_id].copy()
    if states:
        out = out.loc[out.state.isin(states)]
    if ownership:
        out = out.loc[out.hospital_ownership.isin(ownership)]
    # Coverage is evaluated BEFORE a numeric-score / denominator screen.
    available = out.loc[out.rate_available & out.denominator.ge(minimum_denominator)].copy()
    return out, available

def review_queue(data, minimum_gap=1.0, minimum_denominator=100):
    """User-set descriptive review threshold; not clinical/statistical significance."""
    return data.loc[data.rate_available & data.gap_pp.ge(minimum_gap) & data.denominator.ge(minimum_denominator)].sort_values(['gap_pp', 'denominator'], ascending=False)

def main():
    manifest = json.loads((ROOT / 'data/source_manifest.json').read_text())
    frames = {}
    for entry in manifest:
        path = ROOT / 'data/raw' / (entry['name'] + '.json')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Snapshot checksum failed')
        frames[entry['name']] = pd.DataFrame(json.loads(path.read_text()))
        if len(frames[entry['name']]) != entry['rows']:
            raise ValueError('Snapshot row count mismatch')
    data = prepare(frames['hospital_visits'], frames['national_visits'], frames['hospital_information'])
    output = ROOT / 'outputs'
    output.mkdir(exist_ok=True)
    columns = ['facility_id', 'facility_name', 'state', 'citytown', 'measure_id', 'condition', 'score', 'denominator', 'national_rate', 'gap_pp', 'point_comparison', 'rate_available', 'interval_available', 'lower_estimate', 'higher_estimate', 'compared_to_national', 'footnote', 'start_date', 'end_date', 'hospital_type', 'hospital_ownership', 'information_match', 'score_raw', 'denominator_raw']
    data[columns].to_csv(output / 'hospital_measures.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    connection = sqlite3.connect(output / 'hospital_quality.sqlite')
    data[columns].to_sql('hospital_measure', connection, if_exists='replace', index=False)
    reports = {}
    for name, query in split_queries((ROOT / 'analysis.sql').read_text()).items():
        table = pd.read_sql_query(query, connection)
        table.to_csv(output / f'{name}.csv', index=False)
        reports[name] = table
    connection.close()
    summary = {'hospital_source_rows': len(frames['hospital_visits']), 'information_hospitals': len(frames['hospital_information']), 'included_hospitals': int(data.facility_id.nunique()), 'readmission_rows': len(data), 'published_rates': int(data.rate_available.sum()), 'missing_rates': int((~data.rate_available).sum()), 'published_intervals': int(data.interval_available.sum()), 'unmatched_information_rows': int((data.information_match != 'both').sum()), 'measures': reports['measure_summary'].to_dict('records'), 'source_released': {x['name']: x['released'] for x in manifest}}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary, indent=2))

def split_queries(text):
    queries = {}
    for block in text.split('-- report: ')[1:]:
        name, query = block.split('\n', 1)
        queries[name.strip()] = query.strip().rstrip(';')
    return queries

if __name__ == '__main__':
    main()
