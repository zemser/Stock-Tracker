
#!/usr/bin/env python3
import argparse, os
from portfolio_tools import load_broker_excel, portfolio_value, weights_from_holdings, hhi

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel")
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    df = load_broker_excel(args.excel)
    df.to_csv(os.path.join(args.outdir, "holdings_cleaned.csv"), index=False)

    vals = portfolio_value(df)
    w = weights_from_holdings(df, None)
    hhi_val, eff_n = hhi(w)

    print("Saved holdings_cleaned.csv")
    print("Value:", vals, "| HHI:", round(hhi_val,3), "| EffN:", round(eff_n,1))

if __name__ == "__main__":
    main()
