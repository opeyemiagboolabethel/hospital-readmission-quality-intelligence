import json
import sqlite3
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.pipeline import ROOT, prepare, review_queue, select_scope, split_queries

class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pd.read_csv(ROOT / 'outputs/hospital_measures.csv.gz', dtype={'facility_id': str}, keep_default_na=False)
        for column in ['score', 'denominator', 'national_rate', 'gap_pp']:
            cls.data[column] = pd.to_numeric(cls.data[column], errors='coerce')
        cls.summary = json.loads((ROOT / 'outputs/summary.json').read_text())

    def test_integrity_and_missingness(self):
        d = self.data
        self.assertEqual(len(d), 28740)
        self.assertEqual(d.facility_id.nunique(), 4790)
        self.assertFalse(d.duplicated(['facility_id', 'measure_id', 'start_date', 'end_date']).any())
        self.assertTrue(d.facility_id.str.len().eq(6).all())
        self.assertIn('010001', set(d.facility_id))
        self.assertEqual(d.score.count(), self.summary['published_rates'])
        self.assertEqual(d.score.isna().sum(), self.summary['missing_rates'])
        self.assertTrue(d.score.dropna().between(0, 100).all())
        self.assertEqual(self.summary['published_intervals'], 0)

    def test_benchmark_and_gap(self):
        d = self.data
        self.assertEqual(d.groupby('measure_id').national_rate.nunique().max(), 1)
        delta = d.loc[d.score.notna(), 'gap_pp'] - (d.score - d.national_rate).dropna()
        self.assertLess(delta.abs().max(), 1e-6)
        self.assertTrue(d.loc[d.score.isna(), 'gap_pp'].isna().all())

    def test_sql_reconciles_processed_evidence(self):
        connection = sqlite3.connect(':memory:')
        self.data.to_sql('hospital_measure', connection, index=False)
        for name, query in split_queries((ROOT / 'analysis.sql').read_text()).items():
            computed = pd.read_sql_query(query, connection)
            saved = pd.read_csv(ROOT / f'outputs/{name}.csv', dtype={'facility_id': str, 'footnote': str, 'score_raw': str}, keep_default_na=False, na_values=[''])
            if 'facility_id' in computed:
                computed.facility_id = computed.facility_id.astype(str)
            # CSV round trip normalizes blank numeric cells.
            pd.testing.assert_frame_equal(computed.fillna(''), saved.fillna(''), check_dtype=False)
        connection.close()

    def test_filters_do_not_redefine_coverage(self):
        scope, available = select_scope(self.data, 'READM_30_HF', ['AL'], minimum_denominator=100)
        self.assertEqual(len(scope), len(self.data.loc[(self.data.measure_id == 'READM_30_HF') & (self.data.state == 'AL')]))
        self.assertTrue(available.denominator.ge(100).all())
        self.assertTrue(available.score.notna().all())
        q = review_queue(available, 1.0, 100)
        self.assertTrue(q.gap_pp.ge(1.0).all())
        self.assertTrue(q.denominator.ge(100).all())

    def test_rejects_misaligned_period_and_duplicates(self):
        # Use actual committed observations, rebuilding the original numeric-string fields.
        v = self.data.head(6).copy()
        for c in ['score', 'denominator']:
            v[c] = v[c + '_raw']
        v['lower_estimate'] = 'Not Available'
        v['higher_estimate'] = 'Not Available'
        n = v[['measure_id', 'start_date', 'end_date', 'national_rate']].copy()
        i = v[['facility_id', 'hospital_type', 'hospital_ownership']].drop_duplicates().copy()
        i['emergency_services'] = 'Yes'
        with self.assertRaises(ValueError):
            prepare(pd.concat([v, v.iloc[[0]]]), n, i)
        n['start_date'] = '01/01/1900'
        with self.assertRaises(ValueError):
            prepare(v, n, i)

    def test_app_and_filter_interactions(self):
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        app.sidebar.selectbox[0].select('READM_30_CABG')
        app.sidebar.multiselect[0].set_value(['AL'])
        app.sidebar.number_input[0].set_value(10000)
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('No numeric rates' in x.value for x in app.warning))
        app.sidebar.multiselect[0].set_value(['AL'])
        app.sidebar.number_input[0].set_value(0)
        app.run()
        self.assertFalse(app.exception)
        app.selectbox[0].select('010005')
        app.run()
        self.assertFalse(app.exception)

if __name__ == '__main__':
    unittest.main()
