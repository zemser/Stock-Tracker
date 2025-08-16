
# Portfolio Dashboard Toolkit (ILS-first)

## Run the dashboard
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_dashboard.py
```

## CLI
```
python portfolio_cli.py "/path/to/export.xlsx" --outdir out
```

Upload optional prices and benchmark CSVs to unlock performance/risk stats.
