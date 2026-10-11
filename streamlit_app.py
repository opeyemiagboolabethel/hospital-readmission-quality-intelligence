"""Hospital quality review workspace, backed by a frozen official CMS snapshot."""
import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.pipeline import LABELS, review_queue, select_scope

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Hospital Quality Intelligence | Opeyemi Agboola', page_icon='🏥', layout='wide')
st.markdown('''<style>
.stApp {background:#f7f7f2;color:#132d3a}
.block-container {max-width:1440px;padding-top:2.5rem;padding-bottom:3rem}
.hero {background:linear-gradient(120deg,#0b2838,#146d73);padding:2.8rem;border-radius:22px;color:#fff;margin-bottom:1.3rem}
.hero p {color:#c9e4e3;font-size:1.05rem;max-width:840px}
.hero h1 {font-size:clamp(2rem,3vw,3.5rem);line-height:1.1;color:white;margin:1rem 0}
.hero .label {font-size:.8rem;letter-spacing:.12em;text-transform:uppercase}
[data-testid="stMetric"] {background:white;border:1px solid #d6e3e2;padding:1.2rem;border-radius:16px}
button[data-baseweb="tab"] {font-size:1rem}
div[data-testid="stSidebar"] {background:#eef3f0}
</style>''', unsafe_allow_html=True)
st.markdown('''<div class="hero"><div class="label">Opeyemi Agboola · Health Data Analytics</div><h1>Hospital Readmission<br>& Quality Intelligence</h1><p>Turn public performance data into a focused quality-review conversation. Compare published rates, inspect reporting gaps, and prepare a hospital-specific briefing.</p></div>''', unsafe_allow_html=True)

@st.cache_data
def load_data():
    frame = pd.read_csv(ROOT / 'outputs/hospital_measures.csv.gz', dtype={'facility_id': str, 'footnote': str, 'score_raw': str, 'denominator_raw': str}, keep_default_na=False)
    for c in ['score', 'denominator', 'national_rate', 'gap_pp', 'lower_estimate', 'higher_estimate']:
        frame[c] = pd.to_numeric(frame[c], errors='coerce')
    for c in ['rate_available', 'interval_available']:
        frame[c] = frame[c].astype(str).str.lower().eq('true')
    return frame, json.loads((ROOT / 'outputs/summary.json').read_text())

data, summary = load_data()
with st.sidebar:
    st.subheader('Set the review scope')
    measure = st.selectbox('Readmission measure', list(LABELS), format_func=LABELS.get)
    states = st.multiselect('States / territories', sorted(data.state.unique()), help='Leave blank for all reporting locations.')
    owners = st.multiselect('Hospital ownership', sorted(data.hospital_ownership.unique()), help='Leave blank for all ownership types. Unmatched hospitals retain a blank ownership value.')
    minimum = st.number_input('Minimum reported denominator', 0, 10000, 0, 25, help='Optional review screen. It does not determine statistical reliability.')
    st.caption('Snapshot retrieved October 2026. Each rate retains its CMS measurement period. The app makes no live API calls.')

scope, available = select_scope(data, measure, states, owners, minimum)
reference = data.loc[data.measure_id == measure].iloc[0]
benchmark = float(reference.national_rate)
st.caption(f"{LABELS[measure]} · {reference.start_date}–{reference.end_date} · U.S. hospital-level public reporting")
st.info('This release has no published comparison intervals for the six included measures. Above/below refers only to point estimates; it does not establish a statistically different result or explain its cause.')

def style(fig):
    fig.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'family': 'Arial', 'color': '#183542'}, margin={'l': 15, 'r': 15, 't': 40, 'b': 35}, legend_title_text='')
    return fig

def csv(table):
    return table.to_csv(index=False).encode('utf-8')

overview, hospitals, coverage, methods = st.tabs(['Performance overview', 'Hospital briefing', 'Reporting coverage', 'Methods & evidence'])
with overview:
    columns = st.columns(4)
    columns[0].metric('Hospitals in scope', f'{len(scope):,}')
    columns[1].metric('Published rates', f'{scope.rate_available.sum():,}')
    columns[2].metric('National benchmark', f'{benchmark:.1f}%')
    columns[3].metric('Median after screening', f'{available.score.median():.1f}%' if len(available) else '—')
    st.caption(f'{len(available):,} hospitals remain after the denominator screen. The national benchmark stays fixed; it is not recalculated from your filters.')
    if available.empty:
        st.warning('No numeric rates meet this scope. Lower the denominator screen or widen the filters.')
    else:
        left, right = st.columns([1.15, 1])
        with left:
            st.subheader('Where the published rates sit')
            fig = px.histogram(available, x='score', nbins=35, color_discrete_sequence=['#167e83'], labels={'score': 'Published readmission rate (%)'})
            fig.add_vline(x=benchmark, line_dash='dash', line_color='#b77729', annotation_text=f'National {benchmark:.1f}%')
            fig.update_yaxes(title='Hospitals')
            st.plotly_chart(style(fig), width='stretch')
        with right:
            st.subheader('Volume and benchmark gap')
            st.plotly_chart(style(px.scatter(available, x='denominator', y='gap_pp', opacity=.4, color_discrete_sequence=['#167e83'], hover_name='facility_name', hover_data=['facility_id', 'state', 'score'], labels={'denominator': 'Reported denominator', 'gap_pp': 'Gap from national (percentage points)'}).add_hline(y=0, line_dash='dash')), width='stretch')
            st.caption('Published risk-standardized rates are not simple binomial proportions. No funnel limits or confidence intervals are invented from denominators.')
        st.subheader('Build a focused review list')
        gap = st.slider('Minimum gap above benchmark (percentage points)', 0.0, 5.0, 1.0, .1)
        volume = st.number_input('Review-list minimum denominator', 0, 10000, max(100, int(minimum)), 25)
        queue = review_queue(available, gap, volume)
        fields = ['facility_id', 'facility_name', 'state', 'score', 'national_rate', 'gap_pp', 'denominator']
        st.caption(f'{len(queue):,} hospitals meet these user-set review thresholds. This is an investigation list, not a verdict or an estimate of preventable readmissions.')
        st.dataframe(queue[fields], hide_index=True, width='stretch')
        st.download_button('Download review list', csv(queue[fields + ['measure_id', 'start_date', 'end_date']]), 'hospital_review_list.csv', 'text/csv')

with hospitals:
    st.subheader('One hospital. Six distinct measures.')
    options = scope[['facility_id', 'facility_name', 'state']].drop_duplicates().sort_values(['facility_name', 'facility_id'])
    if options.empty:
        st.warning('No hospitals match the current location and ownership scope.')
    else:
        names = {r.facility_id: f'{r.facility_name} · {r.state} · {r.facility_id}' for r in options.itertuples()}
        selected = st.selectbox('Find a hospital', list(names), format_func=names.get)
        hospital = data.loc[data.facility_id == selected].copy()
        st.caption('The hospital briefing includes all six measures; the sidebar denominator screen applies to the overview only.')
        record = hospital.iloc[0]
        st.markdown(f'**{record.facility_name}** · {record.citytown}, {record.state}')
        st.write(f'{record.hospital_type or "Type unavailable"} · {record.hospital_ownership or "Ownership unavailable"}')
        numeric = hospital.loc[hospital.rate_available]
        if len(numeric):
            chart = go.Figure()
            chart.add_trace(go.Scatter(x=numeric.score, y=numeric.condition, mode='markers', name='Hospital point estimate', marker={'color': '#167e83', 'size': 12}))
            chart.add_trace(go.Scatter(x=numeric.national_rate, y=numeric.condition, mode='markers', name='National benchmark', marker={'color': '#b77729', 'symbol': 'diamond', 'size': 11}))
            chart.update_xaxes(title='Readmission rate (%)')
            st.plotly_chart(style(chart), width='stretch')
        fields = ['condition', 'score', 'national_rate', 'gap_pp', 'denominator', 'point_comparison', 'footnote', 'start_date', 'end_date']
        st.dataframe(hospital[fields], hide_index=True, width='stretch')
        st.caption('Blank rates are unavailable, never zero. Source footnote codes are preserved; consult the CMS dictionary for their meaning.')
        lines = [f'# Quality review briefing: {record.facility_name}', f'Facility ID: {selected} | {record.state}', '', 'CMS September 2026 hospital-visits release. Hospital-level descriptive benchmarking.', '']
        for r in hospital.itertuples():
            text = f'{r.score:.1f}% versus national {r.national_rate:.1f}% ({r.gap_pp:+.1f} pp); denominator {r.denominator:g}' if r.rate_available else f'Rate unavailable; source footnote {r.footnote or "not supplied"}'
            lines.append(f'- {r.condition}: {text}. Period {r.start_date}–{r.end_date}.')
        lines.extend(['', 'Review questions: validate the measurement period and reporting scope; examine local discharge and follow-up processes; check internal case mix and data completeness before choosing an intervention.', '', 'No published comparison intervals are available in this snapshot. Gaps do not establish statistical significance, causality, avoidable cases, or financial savings. This is not a patient-level prediction system.'])
        st.download_button('Download hospital briefing', '\n'.join(lines), f'hospital_{selected}_briefing.md', 'text/markdown')

with coverage:
    st.subheader('What can—and cannot—be compared')
    table = pd.DataFrame(summary['measures'])
    st.dataframe(table[['condition', 'hospitals', 'published_rates', 'unavailable_rates', 'coverage_pct', 'national_rate']], hide_index=True, width='stretch')
    st.caption('All-location coverage before sidebar filters. Reporting availability differs by procedure, hospital services and source suppression rules; missingness is not evidence of poor care.')
    if len(scope):
        state = scope.groupby('state').agg(hospitals=('facility_id', 'size'), published_rates=('rate_available', 'sum')).reset_index()
        state['coverage_pct'] = 100 * state.published_rates / state.hospitals
        st.plotly_chart(style(px.bar(state, x='state', y='coverage_pct', color_discrete_sequence=['#167e83'], hover_data=['hospitals', 'published_rates'], labels={'coverage_pct': 'Published-rate coverage (%)', 'state': 'State / territory'}).update_yaxes(range=[0, 100])), width='stretch')
        st.caption('Current measure, location and ownership scope. Denominator filtering does not alter coverage calculations.')
        missing = scope.loc[~scope.rate_available].groupby(['footnote', 'score_raw'], dropna=False).size().reset_index(name='hospital_rows')
        st.dataframe(missing, hide_index=True, width='stretch')
    st.download_button('Download complete coverage summary', csv(table), 'readmission_coverage_summary.csv', 'text/csv')

with methods:
    st.subheader('Evidence trail')
    st.write(f"{summary['hospital_source_rows']:,} source visit rows → {summary['readmission_rows']:,} hospital-measure rows → {summary['published_rates']:,} numeric rates across {summary['included_hospitals']:,} hospitals.")
    st.markdown('''The analysis joins hospital and national records on **measure ID + start date + end date**, then enriches hospital characteristics using the six-character facility ID. Missing rates stay missing. The national benchmark comes from CMS, not a hospital average.

The overview separates coverage from the optional denominator screen. A median or mean describes **reporting hospitals**, not patients or state populations. Condition measures may overlap in patients and must not be added together. Rates are already CMS standardized measures; this project does not estimate a new adjustment model.

The current snapshot lacks readmission comparison intervals and CMS comparison categories. It therefore supports descriptive review only. Do not turn rate gaps × denominators into avoided cases, create binomial funnel limits, or infer intervention effects. Hospital overall star ratings are deliberately excluded from prediction because they partly incorporate related quality measures.

This is one release with historical measurement windows, not a longitudinal trend or a live monitoring feed. U.S. measures do not establish performance or transferability in Nigeria. No personal health records are used or collected.''')
    for entry in json.loads((ROOT / 'data/source_manifest.json').read_text()):
        st.markdown(f"[{entry['name'].replace('_', ' ').title()}]({entry['catalog_url']}) · released {entry['released']} · {entry['rows']:,} rows")
    st.markdown('[CMS data dictionary](https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/hospital/HOSPITAL_Data_Dictionary.pdf) · [Reproducible source code](https://github.com/opeyemiagboolabethel/hospital-readmission-quality-intelligence)')
    st.download_button('Download source manifest', (ROOT / 'data/source_manifest.json').read_bytes(), 'source_manifest.json', 'application/json')

st.caption('Prepared by Opeyemi Agboola · Python, SQL and public health analytics · Research and quality-review portfolio project')
