# Schneider ESG Scoring Dashboard

Streamlit dashboard for comparing Schneider Electric ESG scores across MSCI, Sustainalytics, CDP, and S&P CSA.

The dashboard reads `data/schneider_esg_scores_from_tables.csv`, generated from the Schneider ESG workbook CSV exports. Provider-native scales are normalized to 0-100 for comparison.

The methodology, data coverage, and weighting explanations are marked as analyst interpretation based on public methodology. Each row includes a provider methodology source name and URL.

## What It Shows

- Aggregated provider scores normalized to a 0-100 scale
- Provider divergence for a selected year
- Reasons scores differ across methodology, data coverage, and weighting
- Schneider Electric score history over time
- CSV upload for updated provider data
- Conversion script for rebuilding the dashboard dataset from the exported provider CSV files

## Run

```powershell
python -m pip install -r requirements.txt
python scripts/build_dashboard_scores.py
python -m streamlit run app.py
```

If `python` opens the Microsoft Store on Windows, use a real Python install or the bundled runtime path shown by Codex.

## Input CSV Columns

Required columns:

- `company`
- `year`
- `provider`
- `raw_score`
- `normalized_score`
- `environment_score`
- `social_score`
- `governance_score`
- `confidence`
- `ranking`
- `keywords`
- `interpretation_basis`
- `methodology_source`
- `methodology_url`
- `methodology_gap`
- `data_gap`
- `weighting_difference`

`normalized_score` should be oriented so 100 means stronger ESG performance or lower ESG risk.

## Rebuild From Provider CSV Exports

Put the four provider CSV files in `csv_exports/`, then run:

```powershell
python scripts/build_dashboard_scores.py
```

This creates `data/schneider_esg_scores_from_tables.csv`, which is the default dashboard input.
