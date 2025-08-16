
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

BASE_CCY = "ILS"

HEB_TO_EN = {
    "שם נייר": "Instrument Name",
    "מספר נייר": "Instrument Number",
    "שער אחרון": "Last Price",
    "כמות בתיק": "Quantity in Portfolio",
    "שווי אחזקה (₪)": "Holding Value (₪)",
    "שווי במטבע": "Holding Value (₪)",
    "שינוי יומי %": "Daily Change %",
    "שינוי יומי במטבע": "Daily Change in Currency",
    "שער עלות": "Cost Price",
    "שינוי מעלות %": "Change from Cost %",
    "שינוי מעלות במטבע": "Change from Cost in Currency",
    "שינוי מעלות (₪)": "Change from Cost (₪)",
    "נתח מהתיק": "Portfolio Share %",
    "כמות מושאלת": "Borrowed Quantity",
    "המלצת AI": "AI Recommendation",
    "דרוג AI": "AI Rating",
    "הערה אישית": "Personal Note",
}

NUMERIC_COLS = [
    "Last Price","Quantity in Portfolio","Holding Value (₪)","Holding Value (USD)",
    "Daily Change %","Daily Change in Currency","Cost Price",
    "Change from Cost %","Change from Cost (₪)","Change from Cost in Currency","Portfolio Share %"
]

def _first_sheet_name(xls: pd.ExcelFile) -> str:
    for name in xls.sheet_names:
        if re.search(r"portfolio|תיק|hold|positions", name, re.I):
            return name
    return xls.sheet_names[0]

def _find_header_row(df_like: pd.DataFrame, max_rows: int = 20) -> Optional[int]:
    target = set(HEB_TO_EN.keys())
    best, hits = None, -1
    for r in range(min(max_rows, len(df_like))):
        row_vals = [str(x).strip() for x in list(df_like.iloc[r].values)]
        h = sum(1 for v in row_vals if v in target)
        if h > hits and h >= 3:
            best, hits = r, h
    return best

def _translate_headers(headers_he):
    translated, seen = [], {}
    for h in headers_he:
        en = HEB_TO_EN.get(h, h)
        if en in seen:
            seen[en] += 1
            en = f"{en} ({seen[en]})"
        else:
            seen[en] = 0
        translated.append(en)
    return translated

def _coerce_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _detect_usd_ils(df: pd.DataFrame):
    hv_cols = [c for c in df.columns if c.startswith("Holding Value (₪)")]
    if len(hv_cols) >= 2:
        avgs = {c: pd.to_numeric(df[c], errors='coerce').dropna().mean() for c in hv_cols}
        ordered = sorted(avgs.items(), key=lambda kv: (np.nan_to_num(kv[1], nan=0.0)), reverse=True)
        if len(ordered) >= 2 and ordered[0][1] > 1.5 * max(ordered[1][1], 1e-9):
            usd_col = ordered[0][0]
            df.rename(columns={usd_col: "Holding Value (USD)"}, inplace=True)
            for c in hv_cols:
                if c != usd_col:
                    df.rename(columns={c: "Holding Value (₪)"}, inplace=True)
                    break
            for c in [c for c in hv_cols if c not in ["Holding Value (₪)","Holding Value (USD)"]]:
                df.drop(columns=[c], inplace=True)

def load_broker_excel(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sh = sheet or _first_sheet_name(xls)
    raw = pd.read_excel(path, sheet_name=sh, header=None)
    hdr = _find_header_row(raw) or 0
    he = [str(x).strip() for x in raw.iloc[hdr].tolist()]
    df = raw.iloc[hdr+1:].reset_index(drop=True).copy()
    df.columns = _translate_headers(he)
    for c in ["Borrowed Quantity","AI Recommendation","AI Rating","Personal Note"]:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)
    _detect_usd_ils(df)
    _coerce_numeric(df, NUMERIC_COLS + [c for c in df.columns if "Change from Cost" in c])
    non_name = [c for c in df.columns if c != "Instrument Name"]
    if non_name:
        df.dropna(how="all", subset=non_name, inplace=True)
    if "Holding Value (₪)" in df.columns:
        df = df.sort_values("Holding Value (₪)", ascending=False)
    elif "Holding Value (USD)" in df.columns:
        df = df.sort_values("Holding Value (USD)", ascending=False)
    return df

def load_prices_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

def load_fx_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

def load_benchmarks_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

def weights_from_holdings(df: pd.DataFrame, use_col: Optional[str] = None) -> pd.Series:
    col = use_col
    if col is None:
        if "Holding Value (₪)" in df.columns:
            col = "Holding Value (₪)"
        elif "Holding Value (USD)" in df.columns:
            col = "Holding Value (USD)"
        else:
            return pd.Series(dtype=float)
    vals = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    s = vals / max(vals.sum(), 1e-9)
    s.index = df["Instrument Name"]
    return s

def hhi(weights: pd.Series):
    w = weights.fillna(0.0).values
    h = float(np.sum(np.square(w)))
    eff_n = float(1.0 / max(h, 1e-12))
    return h, eff_n

def weighted_ter(weights: pd.Series, metadata: Optional[pd.DataFrame]):
    return None

def portfolio_value(df: pd.DataFrame):
    vals = {}
    if "Holding Value (₪)" in df.columns:
        vals["ILS"] = float(pd.to_numeric(df["Holding Value (₪)"], errors="coerce").sum())
    if "Holding Value (USD)" in df.columns:
        vals["USD"] = float(pd.to_numeric(df["Holding Value (USD)"], errors="coerce").sum())
    return vals

def build_portfolio_series(static_positions: pd.DataFrame, prices: pd.DataFrame, fx: Optional[pd.DataFrame]):
    if static_positions is None or static_positions.empty or prices is None or prices.empty:
        return pd.DataFrame()
    pos = static_positions.copy()
    pos["qty"] = pd.to_numeric(pos.get("Quantity in Portfolio", 0), errors="coerce").fillna(0.0)
    pos["name"] = pos["Instrument Name"].astype(str)
    pr = prices.copy()
    pr["date"] = pd.to_datetime(pr["date"]).dt.date
    all_dates = sorted(pr["date"].unique())
    vals = []
    for d in all_dates:
        day = pr[pr["date"] == d]
        total_ils = 0.0
        for _, r in pos.iterrows():
            tk = r["name"]
            match = day[day["ticker"] == tk]
            if match.empty:
                continue
            close = float(match.iloc[0]["close"])
            ccy = str(match.iloc[0].get("currency", "USD"))
            value_native = r["qty"] * close
            if ccy == "ILS":
                total_ils += value_native
            else:
                pair = f"{ccy}ILS"
                rate = 1.0
                if fx is not None and not fx.empty:
                    row = fx[(fx["date"] == d) & (fx["pair"] == pair)]
                    if not row.empty:
                        rate = float(row.iloc[0]["rate"])
                total_ils += value_native * rate
        vals.append({"date": d, "value_ILS": total_ils})
    out = pd.DataFrame(vals).sort_values("date")
    out["ret_d"] = out["value_ILS"].pct_change()
    out["cum_index"] = (1 + out["ret_d"].fillna(0)).cumprod()
    return out

def rolling_vol(returns: pd.Series, window: int):
    if len(returns) < max(window, 2):
        return np.nan
    d = returns.rolling(window).std().dropna()
    if d.empty:
        return np.nan
    return float(d.iloc[-1] * np.sqrt(252))

def compute_drawdown(series: pd.Series):
    roll_max = series.cummax()
    dd = (series / roll_max) - 1.0
    return float(dd.min()) if len(dd) else np.nan

def beta_alpha(port_ret: pd.Series, bench_ret: pd.Series):
    df = pd.concat([port_ret, bench_ret], axis=1).dropna()
    if df.shape[0] < 5:
        return (np.nan, np.nan)
    cov = np.cov(df.iloc[:,0], df.iloc[:,1])
    var_b = cov[1,1]
    if var_b == 0:
        return (np.nan, np.nan)
    beta = cov[0,1] / var_b
    alpha = (df.iloc[:,0] - beta * df.iloc[:,1]).mean() * 252
    return float(beta), float(alpha)
