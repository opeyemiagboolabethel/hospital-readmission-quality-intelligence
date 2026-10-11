# Hospital Readmission & Quality Risk Intelligence

An end-to-end public-health analytics project by Opeyemi Agboola. The application turns official CMS hospital-level readmission reporting into a reproducible quality-review workspace: benchmark comparisons, reporting coverage, configurable review lists and individual hospital briefings.

## What the project answers

- Which published hospital rates sit above or below the matching national point benchmark?
- Where does missing reporting limit the comparison?
- How does a review list change when the rate-gap and denominator screens change?
- What evidence should a quality team inspect before choosing an intervention?

This is hospital-level descriptive intelligence. It is not a patient-level readmission prediction model. No new risk-adjustment model, clinical intervention effect or financial savings estimate is claimed.

## Evidence

The hospital-visits and national datasets were released on 30 September 2026; hospital characteristics were released on 13 August 2026. The six included readmission measures cover 1 July 2023–30 June 2025. A release date is not the period of care.

The snapshot contains 4,790 hospitals, 28,740 hospital-measure rows, and 14,701 numeric rates. All six measures lack published lower/upper estimates and CMS national-comparison categories in this release. Above/below benchmark labels therefore refer to point estimates only.

Data sources: [hospital visits](https://data.cms.gov/provider-data/dataset/632h-zaca), [national visits](https://data.cms.gov/provider-data/dataset/cvcs-xecj), [hospital information](https://data.cms.gov/provider-data/dataset/xubh-q36u), and [official dictionary](https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/hospital/HOSPITAL_Data_Dictionary.pdf).

No Kaggle or synthetic analysis data are used. No personal medical records are included. Public facility identifiers and names are retained for evidence tracing.

## Run the application

Use Python **3.12**. Committed processed data allow offline application use, without downloading the full raw files or setting API keys.

```sh
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Streamlit Community Cloud: repository `opeyemiagboolabethel/hospital-readmission-quality-intelligence`, branch `main`, entrypoint `streamlit_app.py`, Advanced settings → Python 3.12. No secrets required.

## Reproduce the analysis

```sh
python download_data.py
python src/pipeline.py
python -m unittest test_project.py
```

The download script uses the exact CSV URLs recorded in `data/source_manifest.json` and verifies source and parsed-data SHA-256 checksums. It refuses to overwrite existing raw files. If CMS retires a recorded URL, the committed processed snapshot still supports the app and evidence tests, but the raw pipeline will need the original source files. Raw files and the regenerated SQLite database are excluded from Git.

## Project structure

| File | Purpose |
| --- | --- |
| `download_data.py` | Source download, preserved text values and checksums |
| `src/pipeline.py` | Validated joins, numeric parsing, missingness preservation and report generation |
| `analysis.sql` | Executed SQLite queries for coverage, summaries, review lists and threshold sensitivity |
| `streamlit_app.py` | Interactive review workspace and briefing export |
| `outputs/hospital_measures.csv.gz` | Complete six-measure processed snapshot, including unavailable rates |
| `outputs/*.csv` | Reproducible analysis and audit tables |
| `outputs/summary.json` | Reconciled counts and findings |
| `test_project.py` | Evidence consistency, malformed joins, filters and application interactions |
| `RESULTS.md` | Findings, interpretation and limits |

## Analytical choices

Facility IDs remain six-character strings. National comparisons join on measure ID and both period dates, never only the condition name. The hospital-information join is many-to-one and preserves hospitals if enrichment is missing. Source values such as `Not Available` remain traceable next to parsed numeric values.

SQL means and displayed medians describe reporting hospitals with equal hospital weights; they are not pooled patient risks. The national rate is taken from CMS and never recomputed from the displayed hospitals. Coverage is calculated before denominator screening. The default review screen is a point-estimate gap of at least 1 percentage point and a reported denominator of at least 100; these are transparent user-selected review settings, not significance thresholds. A sensitivity report varies both settings.

Do not sum denominators across overlapping condition measures, infer preventable cases from gap × denominator, or calculate simple binomial uncertainty for the standardized rates. Absence of a rate does not establish poor care. The overall hospital star rating is not used as a prediction feature or independent quality outcome.

## Boundaries

This is one public release with historical performance windows, not a trend study. Case mix, social context and local process data require further investigation. Benchmark gaps do not identify causes or prove poor care. The U.S. measurement system has not been validated for Nigerian hospitals. The project demonstrates analytics and review workflow, not clinical deployment.
