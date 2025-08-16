
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from portfolio_tools import (
    load_broker_excel, load_prices_csv, load_benchmarks_csv, weights_from_holdings,
    hhi, portfolio_value, build_portfolio_series, rolling_vol, beta_alpha
)

st.set_page_config(page_title="Portfolio Dashboard (ILS-first)", layout="wide")
st.title("Portfolio Dashboard")

with st.sidebar:
    holdings_file = st.file_uploader("Broker Excel (.xlsx)", type=["xlsx"])
    prices_file = st.file_uploader("Prices CSV (date,ticker,close,currency)", type=["csv"])
    bench_file = st.file_uploader("Benchmarks CSV (date,symbol,close)", type=["csv"])

if holdings_file is not None:
    hold = load_broker_excel(holdings_file)
    vals = portfolio_value(hold)
    w = weights_from_holdings(hold, None)
    hhi_val, eff_n = hhi(w)

    c = st.columns(4)
    c[0].metric("Value (ILS)", f"{vals.get('ILS', 0):,.0f}")
    c[1].metric("Value (USD)", f"{vals.get('USD', 0):,.0f}")
    c[2].metric("Eff. Holdings", f"{eff_n:,.1f}")
    c[3].metric("HHI", f"{hhi_val:.3f}")

    st.subheader("Allocation (Top 20)")
    st.bar_chart(w.sort_values(ascending=False).head(20))

    st.subheader("Performance")
    if prices_file is not None:
        pr = load_prices_csv(prices_file)
        series = build_portfolio_series(hold, pr, None)
        if not series.empty:
            fig = plt.figure()
            plt.plot(series["date"], series["cum_index"])
            plt.title("Cumulative Index (static positions)")
            plt.xticks(rotation=45)
            st.pyplot(fig, clear_figure=True)

            if bench_file is not None:
                bench = load_benchmarks_csv(bench_file)
                sym = bench["symbol"].iloc[0]
                bret = bench[bench["symbol"] == sym].set_index("date")["close"].pct_change()
                merged = series.set_index("date")[["ret_d"]].join(bret.rename("bench_ret"), how="inner").dropna()
                if not merged.empty:
                    beta, alpha = beta_alpha(merged["ret_d"], merged["bench_ret"])
                    vol30 = rolling_vol(merged["ret_d"], 30)
                    vol90 = rolling_vol(merged["ret_d"], 90)
                    st.caption(f"β={beta:.2f} | α(ann)={alpha:.2f}% | σ30={vol30:.2%} | σ90={vol90:.2%}")
else:
    st.info("Upload your broker Excel to start.")
