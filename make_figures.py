"""Render the case-study evidence figure from the SQL output table."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

root = Path(__file__).resolve().parent
data = pd.read_csv(root / 'outputs/measure_summary.csv').sort_values('coverage_pct')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
fig, ax = plt.subplots(figsize=(11, 5.5))
fig.patch.set_facecolor('#f7f7f2')
ax.set_facecolor('#f7f7f2')
ax.barh(data.condition, data.coverage_pct, color='#167e83', height=.58)
for y, row in enumerate(data.itertuples()):
    ax.text(row.coverage_pct + 1.5, y, f'{row.coverage_pct:.1f}%  ·  {row.published_rates:,} hospitals', va='center', fontsize=10, color='#183542')
ax.set_xlim(0, 108)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel('Share of 4,790 listed hospitals with a numeric rate (%)')
ax.grid(axis='x', alpha=.15)
ax.set_axisbelow(True)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(length=0)
fig.suptitle('Reporting coverage varies sharply by measure', fontsize=18, fontweight='bold', x=.03, ha='left', color='#132d3a')
fig.text(.03, .02, 'CMS September 2026 release · Measurement period July 2023–June 2025\nUnavailable rates are not zeros and do not establish poor care.', fontsize=10, color='#526b75')
fig.tight_layout(rect=[0, .08, 1, .94])
fig.savefig(root / 'outputs/reporting-coverage.svg')
