# Findings and interpretation

## A broad reporting universe is not the same as complete evidence

The source hospital-visits file contains 67,060 rows. Restricting to six condition/procedure readmission measures yields 28,740 rows for 4,790 hospitals. There are 14,701 published numeric rates and 14,039 unavailable rates (48.85% of included rows). Every hospital row matches a national benchmark on the exact measurement period; all facility IDs match the hospital-information snapshot.

| Measure | National point benchmark | Hospitals with a numeric rate | Coverage of 4,790 listed hospitals |
| --- | ---: | ---: | ---: |
| Heart attack | 14.4% | 1,971 | 41.15% |
| Coronary bypass | 11.0% | 938 | 19.58% |
| COPD | 20.0% | 3,086 | 64.43% |
| Heart failure | 21.3% | 3,253 | 67.91% |
| Hip/knee replacement | 5.8% | 1,695 | 35.39% |
| Pneumonia | 17.3% | 3,758 | 78.46% |

Measurement period: 1 July 2023–30 June 2025. Hospital/national visits release: 30 September 2026. Hospital-information release: 13 August 2026.

Coronary-bypass coverage is much lower than pneumonia coverage. This does not imply poorer bypass care: services offered, eligibility, volume, suppression and other source rules affect reporting. Keep unavailable records visible and inspect the original footnotes before interpreting absence.

## A transparent list for investigation

Using a gap of at least **1 percentage point above the national benchmark** and a reported denominator of at least **100** identifies **1,952 hospital-measure observations at 1,250 distinct hospitals**. The observations comprise 627 heart-failure, 601 pneumonia, 335 COPD, 219 heart-attack, 117 bypass and 53 hip/knee rows. A hospital can appear under multiple conditions.

These counts depend on the review settings. They are not statistically significant outliers, avoidable readmissions, preventable admissions or quantified intervention opportunities. `review_screen_sensitivity.csv` makes the threshold dependence inspectable.

## Uncertainty is a material constraint

The downloaded six-measure snapshot has **zero published comparison intervals**; all CMS national-comparison categories are `Not Available`. The application does not substitute guessed intervals or a simple binomial calculation from the denominators. A point gap can support a local question, but cannot establish a statistically different hospital result.

## How a quality team could use the output

1. Confirm the measure, hospital identity, period and reporting scope.
2. Review the selected hospital's published point rates alongside national references.
3. Check local case mix, follow-up processes and internal data completeness.
4. Decide which local process merits investigation using additional evidence.
5. Evaluate any implemented intervention with an appropriate prospective or quasi-experimental design.

The public data do not establish which discharge process caused a gap, which intervention would work, or how much money it would save.

## Reproducibility and practical limits

The SQL reports reconcile to the full committed processed snapshot. Source CSV URLs and SHA-256 checksums are recorded. Numeric missingness is retained rather than imputed. Descriptive means give each reporting hospital equal weight; they are not patient-weighted national or state rates. Condition denominators overlap and must not be summed.

One release cannot establish longitudinal deterioration or improvement. Overall hospital stars are omitted because they incorporate related quality information. There is no patient-level predictive model, live clinical feed or Nigerian validation.
