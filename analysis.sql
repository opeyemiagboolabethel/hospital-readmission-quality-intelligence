-- Each hospital contributes one row per measure-period. No pooled patient rate.
-- report: measure_summary
SELECT measure_id, condition, start_date, end_date, national_rate,
 COUNT(*) AS hospitals, COUNT(score) AS published_rates,
 COUNT(*) - COUNT(score) AS unavailable_rates,
 ROUND(100.0 * COUNT(score) / COUNT(*), 2) AS coverage_pct,
 ROUND(AVG(score), 3) AS unweighted_hospital_mean,
 SUM(CASE WHEN gap_pp > 0 THEN 1 ELSE 0 END) AS above_point_benchmark,
 SUM(CASE WHEN gap_pp = 0 THEN 1 ELSE 0 END) AS at_point_benchmark,
 SUM(CASE WHEN gap_pp < 0 THEN 1 ELSE 0 END) AS below_point_benchmark
FROM hospital_measure
GROUP BY measure_id, condition, start_date, end_date, national_rate
ORDER BY measure_id;

-- report: state_coverage
SELECT measure_id, condition, state, COUNT(*) AS hospitals,
 COUNT(score) AS published_rates,
 ROUND(100.0 * COUNT(score) / COUNT(*), 2) AS coverage_pct,
 ROUND(AVG(score), 3) AS unweighted_hospital_mean,
 ROUND(AVG(gap_pp), 3) AS unweighted_mean_gap_pp
FROM hospital_measure
GROUP BY measure_id, condition, state
ORDER BY measure_id, state;

-- report: ownership_coverage
SELECT measure_id, hospital_ownership, COUNT(*) AS hospitals,
 COUNT(score) AS published_rates,
 ROUND(100.0 * COUNT(score) / COUNT(*), 2) AS coverage_pct,
 ROUND(AVG(score), 3) AS unweighted_hospital_mean
FROM hospital_measure
GROUP BY measure_id, hospital_ownership
ORDER BY measure_id, hospital_ownership;

-- report: unavailable_footnotes
SELECT measure_id, footnote, score_raw, COUNT(*) AS hospital_rows
FROM hospital_measure WHERE score IS NULL
GROUP BY measure_id, footnote, score_raw
ORDER BY measure_id, hospital_rows DESC;

-- report: default_review_queue
SELECT facility_id, facility_name, state, measure_id, condition,
 score, national_rate, gap_pp, denominator, start_date, end_date
FROM hospital_measure WHERE score IS NOT NULL AND gap_pp >= 1.0 AND denominator >= 100
ORDER BY gap_pp DESC, denominator DESC;

-- report: review_screen_sensitivity
WITH gaps(value) AS (VALUES (0.5),(1.0),(2.0)),
volumes(value) AS (VALUES (25),(100),(250))
SELECT gaps.value AS minimum_gap_pp, volumes.value AS minimum_denominator,
 COUNT(h.facility_id) AS hospital_measure_rows,
 COUNT(DISTINCT h.facility_id) AS distinct_hospitals
FROM gaps CROSS JOIN volumes
LEFT JOIN hospital_measure h ON h.score IS NOT NULL
 AND h.gap_pp >= gaps.value AND h.denominator >= volumes.value
GROUP BY gaps.value, volumes.value
ORDER BY gaps.value, volumes.value;
