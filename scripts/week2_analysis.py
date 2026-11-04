"""Pricing analysis (pandas, numpy) -- UCI Online Retail.

Reads the cleaned `orders` table built in Week 1 (retail.db) and does
the four analyses in PROJECT_BRIEF.md, Week 2:

  1. Revenue structure: by month, country, and price band.
  2. Price elasticity: log-log OLS of weekly quantity on weekly price
     for the top 25 SKUs by revenue, with calendar-month dummies and a
     linear trend. Two price measures are reported, because they answer
     different questions and disagree for a reason:
       - avg price (weekly revenue / weekly units): the price actually
         paid. It is well identified, but it is biased toward large
         negative elasticities: weeks with heavy discounting have a low
         average price AND high volume, so the estimate mixes the
         response to discounts with promotion / demand timing.
       - modal price (the week's most common UnitPrice): the list price
         actually charged that week. Cleaner, but most SKUs barely
         changed their list price all year (often 1-5 distinct values),
         so it is frequently not identified. Where it is identified it
         clusters near -1, far smaller in magnitude than the avg-price
         estimates. Trust the modal column where it exists; treat the
         avg-price column as an upper bound on responsiveness, not as
         a causal elasticity.
     Outlier rule (elasticity only): a SKU-week whose average price is
     more than 3x that SKU's median weekly average price is dropped
     (e.g. StockCode 22502, one week at $649.50 driven by two mis-keyed
     lines on 2011-06-10). The dropped-week count is reported.
  3. Discount check: for each top-25 SKU, lines sold below the SKU's
     modal (most common) price vs lines at the modal price. The dataset
     has no discount/promotion field, so "discounted" here means sold
     below the modal price. It is a proxy, not a labelled promotion.
  4. Customer segments: identifiable customers only
     (has_customer_id = 1) split into spend quartiles; per tier, spend
     share, orders, recency, and share of spend on below-modal lines.

SKU = StockCode. Descriptions vary within a StockCode in this file
(e.g. 22197 is both "POPCORN HOLDER" and "SMALL POPCORN HOLDER"), so
every table groups by StockCode and labels it with its most frequent
description. Do not group by (StockCode, Description): that splits one
SKU into two rows and double-counts weeks in the elasticity regression.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DB = HERE / "retail.db"
OUT = HERE / "outputs"
TOP_N = 25
MIN_WEEKS = 30          # elasticity: need enough weekly observations
MIN_DISTINCT_PRICES = 5
MIN_PRICE_CV = 0.02      # elasticity (avg price): need real price variation

PRICE_BANDS = [0, 1, 2, 5, 10, float("inf")]
PRICE_LABELS = ["<= $1", "$1-2", "$2-5", "$5-10", "> $10"]


def ols_loglog(y, X):
    """OLS via numpy. Returns beta, standard errors, R^2, n, k, or None."""
    n, k = X.shape
    if n - k <= 0:
        return None
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - k
    sigma2 = float(resid @ resid / dof)
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None
    se = np.sqrt(np.diag(cov))
    if not np.all(np.isfinite(se)):
        return None
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    return beta, se, r2, n, k


def _design(g, price_col):
    """Design matrix: intercept, log price, trend, calendar-month dummies."""
    months = pd.get_dummies(g["cal_month"], prefix="m",
                            drop_first=True, dtype=float)
    return np.column_stack([
        np.ones(len(g)),
        np.log(g[price_col].to_numpy(dtype=float)),
        g["week_num"].to_numpy(dtype=float),
        months.to_numpy(dtype=float),
    ])


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"{DB.name} not found. Run Week 1 first: "
                         "python scripts/load_data.py, then "
                         "python scripts/run_sql.py")
    OUT.mkdir(exist_ok=True)
    with sqlite3.connect(DB) as conn:
        orders = pd.read_sql("SELECT * FROM orders", conn,
                             parse_dates=["invoice_date"])
    prod = orders[orders["is_non_product"] == 0].copy()
    print(f"product lines: {len(prod):,} rows, "
          f"revenue ${prod['line_revenue'].sum():,.2f}")
    print("expected: 527,806 rows, revenue $10,272,346.92")
    print()

    # ---- Top SKUs (by StockCode; label = most frequent description) -----
    canon_desc = (prod.groupby("StockCode")["Description"]
                  .agg(lambda s: s.mode().iloc[0]))
    top = (prod.groupby("StockCode", as_index=False)
           .agg(revenue=("line_revenue", "sum"), units=("Quantity", "sum"),
                orders=("InvoiceNo", "nunique"))
           .sort_values("revenue", ascending=False)
           .head(TOP_N))
    top["Description"] = top["StockCode"].map(canon_desc)
    top = top[["StockCode", "Description", "revenue", "units", "orders"]]
    top.to_csv(OUT / "top25_skus.csv", index=False)
    print(f"Top {TOP_N} SKUs: ${top['revenue'].sum():,.2f} revenue, "
          f"{100 * top['revenue'].sum() / prod['line_revenue'].sum():.1f}% "
          "of product revenue")
    print("Note: 23843 PAPER CRAFT, LITTLE BIRDIE is one single bulk order "
          "(80,995 units, $168,469.60), not a repeat pattern. It is in the "
          "top 25 by revenue but cannot have an elasticity estimated.")
    # Extreme-price warning: a line priced at >=10x its SKU's modal price
    # is almost certainly a mis-key. 22502 is the case that matters: two
    # lines at $649.50 on 2011-06-10 are $39,619.50 of its $51,426.62
    # "revenue", so its top-25 ranking is an artifact of that error.
    _modal_all = (prod.groupby("StockCode")["UnitPrice"]
                  .agg(lambda s: s.mode().iloc[0]))
    _prod2 = prod.copy()
    _prod2["modal_price"] = _prod2["StockCode"].map(_modal_all)
    _extreme = _prod2[_prod2["UnitPrice"] >= 10 * _prod2["modal_price"]]
    _ext = (_extreme.groupby("StockCode", as_index=False)
            .agg(extreme_revenue=("line_revenue", "sum"),
                 extreme_lines=("line_revenue", "size")))
    _ext = _ext.merge(top[["StockCode", "revenue"]], on="StockCode",
                      how="inner")
    _ext["extreme_rev_pct"] = 100 * _ext["extreme_revenue"] / _ext["revenue"]
    extreme_rev_pct = dict(zip(_ext["StockCode"], _ext["extreme_rev_pct"]))
    for _, r in _ext.iterrows():
        print(f"WARNING: {r['StockCode']} has {int(r['extreme_lines'])} "
              f"line(s) priced >=10x its modal price, worth "
              f"${r['extreme_revenue']:,.2f} ({r['extreme_rev_pct']:.1f}% of "
              "its revenue). Treat its revenue ranking and any "
              "recommendation on it with suspicion.")
    print()

    # ---- 1. Revenue structure ------------------------------------------
    prod["month"] = prod["invoice_date"].dt.to_period("M").astype(str)
    by_month = (prod.groupby("month", as_index=False)
                .agg(revenue=("line_revenue", "sum"),
                     units=("Quantity", "sum"),
                     orders=("InvoiceNo", "nunique")))
    by_month["revenue_share_pct"] = (
        100 * by_month["revenue"] / by_month["revenue"].sum())
    by_month.to_csv(OUT / "revenue_by_month.csv", index=False)

    by_country = (prod.groupby("Country", as_index=False)
                  .agg(revenue=("line_revenue", "sum"),
                       units=("Quantity", "sum"),
                       orders=("InvoiceNo", "nunique"))
                  .sort_values("revenue", ascending=False))
    by_country["revenue_share_pct"] = (
        100 * by_country["revenue"] / by_country["revenue"].sum())
    by_country.to_csv(OUT / "revenue_by_country.csv", index=False)

    prod["price_band"] = pd.cut(prod["UnitPrice"], bins=PRICE_BANDS,
                                labels=PRICE_LABELS)
    by_band = (prod.groupby("price_band", observed=True, as_index=False)
               .agg(revenue=("line_revenue", "sum"),
                    units=("Quantity", "sum"),
                    lines=("line_revenue", "size")))
    by_band["revenue_share_pct"] = (
        100 * by_band["revenue"] / by_band["revenue"].sum())
    by_band["units_share_pct"] = (
        100 * by_band["units"] / by_band["units"].sum())
    by_band["avg_price"] = by_band["revenue"] / by_band["units"]
    by_band.to_csv(OUT / "revenue_by_price_band.csv", index=False)

    print("== 1. Revenue structure ==")
    print("By price band (revenue vs volume):")
    print(by_band.to_string(index=False))
    print()
    print("Top 5 countries by revenue:")
    print(by_country.head(5).to_string(index=False))
    print()

    # ---- 2. Price elasticity (weekly, log-log OLS) ----------------------
    # Weekly aggregation: 13 monthly observations per SKU cannot carry
    # 11 month dummies + trend + price, so use ~53 weekly observations.
    prod["week"] = prod["invoice_date"].dt.to_period("W").dt.start_time

    def _modal(s):
        return s.mode().iloc[0]

    weekly = (prod.groupby(["StockCode", "week"], as_index=False)
              .agg(qty=("Quantity", "sum"),
                   revenue=("line_revenue", "sum"),
                   modal_price=("UnitPrice", _modal)))
    weekly["avg_price"] = weekly["revenue"] / weekly["qty"]
    weekly = weekly[weekly["qty"] > 0].copy()
    weekly["week_num"] = ((weekly["week"] - weekly["week"].min())
                          .dt.days // 7)
    weekly["cal_month"] = weekly["week"].dt.month

    rows = []
    for code, g in weekly.groupby("StockCode"):
        if code not in set(top["StockCode"]):
            continue
        desc = canon_desc[code]
        rev = float(g["revenue"].sum())
        med = g["avg_price"].median()
        outlier_weeks = g[g["avg_price"] > 3 * med]
        g = g[g["avg_price"] <= 3 * med]
        n_weeks = len(g)
        cv = g["avg_price"].std() / g["avg_price"].mean() if n_weeks > 1 else 0.0
        base = {"StockCode": code, "Description": desc, "weeks": n_weeks,
                "outlier_weeks_dropped": int(len(outlier_weeks)),
                "revenue": round(rev, 2),
                "avg_price_cv": round(float(cv), 3),
                "modal_distinct_prices": int(g["modal_price"].nunique())}
        if (n_weeks < MIN_WEEKS
                or g["avg_price"].nunique() < MIN_DISTINCT_PRICES
                or cv < MIN_PRICE_CV):
            rows.append({**base, "elasticity_avg_price": None,
                         "ci_low": None, "ci_high": None,
                         "elasticity_modal_price": None,
                         "modal_se": None, "r2": None,
                         "note": "excluded: too few weeks / too little "
                                 "price variation to estimate"})
            continue
        y = np.log(g["qty"].to_numpy(dtype=float))
        res = ols_loglog(y, _design(g, "avg_price"))
        if res is None:
            rows.append({**base, "elasticity_avg_price": None,
                         "ci_low": None, "ci_high": None,
                         "elasticity_modal_price": None,
                         "modal_se": None, "r2": None,
                         "note": "excluded: regression did not solve"})
            continue
        beta, se, r2, n, k = res
        e, e_se = float(beta[1]), float(se[1])
        # Modal-price elasticity, where the list price moved enough.
        modal_e, modal_se = None, None
        if g["modal_price"].nunique() >= 3:
            res_m = ols_loglog(y, _design(g, "modal_price"))
            if res_m is not None and np.isfinite(res_m[1][1]) \
                    and res_m[1][1] < 5:
                modal_e, modal_se = float(res_m[0][1]), float(res_m[1][1])
        if modal_e is not None and modal_e >= 0:
            note = ("FLAG modal: positive elasticity, list-price rises "
                    "coincide with higher quantity; do not use")
        elif modal_e is not None and modal_e > -1:
            note = "modal: inelastic (|e| < 1)"
        elif modal_e is not None:
            note = "modal: elastic (|e| > 1)"
        elif e > -1:
            note = "avg-price only: inelastic, but list price barely moved"
        else:
            note = ("avg-price only: elastic; list price barely moved, so "
                    "no clean modal estimate exists")
        rows.append({**base,
                     "elasticity_avg_price": round(e, 3),
                     "ci_low": round(e - 1.96 * e_se, 3),
                     "ci_high": round(e + 1.96 * e_se, 3),
                     "elasticity_modal_price":
                         round(modal_e, 3) if modal_e is not None else None,
                     "modal_se":
                         round(modal_se, 3) if modal_se is not None else None,
                     "r2": round(float(r2), 3),
                     "note": note})
    elas = pd.DataFrame(rows).sort_values("revenue", ascending=False)
    elas.to_csv(OUT / "elasticity_top25.csv", index=False)
    print("== 2. Price elasticity (top 25 SKUs, weekly log-log OLS) ==")
    print(elas.to_string(index=False))
    print()
    print("Read it as: elasticity -1.0 means a 1% price rise is associated "
          "with a 1% quantity fall, holding month and trend fixed. "
          "The modal-price column is the cleaner estimate; the avg-price "
          "column is systematically more negative because discount weeks "
          "are also high-volume weeks. Both are observational: association, "
          "not a controlled experiment. Do not quote an avg-price "
          "elasticity of -4 as if a 5% rise would lose 20% of volume.")
    print()

    # ---- 3. Discount check (modal price = full price proxy) ------------
    modal = (prod.groupby("StockCode")["UnitPrice"]
             .agg(lambda s: s.mode().iloc[0]).rename("modal_price"))
    top_prod = prod[prod["StockCode"].isin(top["StockCode"])].copy()
    top_prod["modal_price"] = top_prod["StockCode"].map(modal)
    top_prod["price_class"] = np.where(
        top_prod["UnitPrice"] < top_prod["modal_price"], "below_modal",
        np.where(top_prod["UnitPrice"] == top_prod["modal_price"],
                 "at_modal", "above_modal"))
    disc = (top_prod.groupby(["StockCode", "price_class"], as_index=False)
            .agg(lines=("line_revenue", "size"),
                 units=("Quantity", "sum"),
                 revenue=("line_revenue", "sum")))
    disc["Description"] = disc["StockCode"].map(canon_desc)
    disc["rev_per_unit"] = disc["revenue"] / disc["units"]
    disc.to_csv(OUT / "discount_check_top25.csv", index=False)
    piv = disc.pivot_table(index=["StockCode", "Description"],
                           columns="price_class", values="units",
                           aggfunc="sum", fill_value=0)
    print("== 3. Discount check (units below vs at modal price) ==")
    print("Below-modal = sold under the SKU's most common price. "
          "No labelled discount field exists in this dataset.")
    print(piv.to_string())
    print()
    # Money given away: (modal - below-modal avg price) * below-modal units,
    # per SKU. A what-if upper bound, not a claim: it assumes the same
    # units would have sold at the modal price.
    below = disc[disc["price_class"] == "below_modal"].copy()
    below["modal_price"] = below["StockCode"].map(modal)
    below["given_away"] = ((below["modal_price"] - below["rev_per_unit"])
                           * below["units"])
    print(f"Total below-modal discount cost across top 25 SKUs "
          f"(what-if upper bound): ${below['given_away'].sum():,.0f}")
    print()

    # ---- 4. Customer segments (identifiable customers only) ------------
    cust = prod[prod["has_customer_id"] == 1].copy()
    max_date = prod["invoice_date"].max()
    per_cust = (cust.groupby("CustomerID", as_index=False)
                .agg(spend=("line_revenue", "sum"),
                     orders=("InvoiceNo", "nunique"),
                     units=("Quantity", "sum"),
                     last_date=("invoice_date", "max")))
    per_cust["recency_days"] = (max_date - per_cust["last_date"]).dt.days
    q = per_cust["spend"].quantile([0.25, 0.5, 0.75]).to_dict()
    labels = ["Q1 lowest spend", "Q2", "Q3", "Q4 highest spend"]
    per_cust["tier"] = pd.cut(per_cust["spend"],
                              bins=[-float("inf"), q[0.25], q[0.5], q[0.75],
                                    float("inf")], labels=labels)
    # share of each customer's spend on below-modal lines (price sensitivity proxy)
    cust["modal_price"] = cust["StockCode"].map(modal)
    cust["below_modal"] = cust["UnitPrice"] < cust["modal_price"]
    below_rev = (cust.assign(below_rev=np.where(
        cust["below_modal"], cust["line_revenue"], 0.0))
        .groupby("CustomerID")["below_rev"].sum())
    total_rev = cust.groupby("CustomerID")["line_revenue"].sum()
    below_share = (below_rev / total_rev).rename("below_modal_spend_share")
    per_cust = per_cust.merge(below_share, on="CustomerID", how="left")
    tiers = (per_cust.groupby("tier", observed=True, as_index=False)
             .agg(customers=("CustomerID", "size"),
                  spend=("spend", "sum"),
                  avg_orders=("orders", "mean"),
                  avg_recency_days=("recency_days", "mean"),
                  avg_below_modal_share=("below_modal_spend_share", "mean")))
    tiers["spend_share_pct"] = 100 * tiers["spend"] / tiers["spend"].sum()
    tiers.to_csv(OUT / "customer_tiers.csv", index=False)
    print("== 4. Customer segments (identifiable customers only, "
          f"n={len(per_cust):,}) ==")
    print(tiers.to_string(index=False))
    print()
    print(f"Spend quartile cutoffs: ${q[0.25]:,.0f} / ${q[0.5]:,.0f} / "
          f"${q[0.75]:,.0f}. Identifiable customers cover "
          f"{100 * cust['line_revenue'].sum() / prod['line_revenue'].sum():.1f}% "
          "of product revenue; the rest has no CustomerID (Week 1, decision A).")
    print()

    # ---- Draft recommendation -------------------------------------------
    usable = elas.dropna(subset=["elasticity_modal_price"])
    inelastic = usable[(usable["elasticity_modal_price"] < 0)
                       & (usable["elasticity_modal_price"] > -1)]
    print("== Draft recommendation (check the numbers before quoting) ==")
    print("The modal-price elasticities that could be estimated cluster "
          "around -1 (roughly unit-elastic), and none is precisely "
          "estimated enough to prove inelasticity. A blanket 5% price "
          "rise is NOT supported by this data. The defensible write-up is:")
    print("- Do not claim a priced-in revenue gain from the avg-price "
          "elasticities; they overstate responsiveness.")
    if len(inelastic):
        for _, r in inelastic.iterrows():
            if extreme_rev_pct.get(r["StockCode"], 0) > 10:
                print(f"- {r['StockCode']} {r['Description']}: modal e="
                      f"{r['elasticity_modal_price']}, but "
                      f"{extreme_rev_pct[r['StockCode']]:.0f}% of its revenue "
                      "is mis-keyed extreme-price lines (see warning "
                      "above). Excluded from the test list until that is "
                      "cleaned.")
                continue
            gain = (1.05 * (1 + r["elasticity_modal_price"] * 0.05) - 1.0) \
                * r["revenue"]
            print(f"- {r['StockCode']} {r['Description']}: modal e="
                  f"{r['elasticity_modal_price']} (se {r['modal_se']}), "
                  f"revenue ${r['revenue']:,.0f}. A 5% rise is worth roughly "
                  f"${gain:,.0f} on that year's volume IF the modal "
                  "elasticity is taken at face value, before any "
                  "second-order volume loss. Present it as a test, not a "
                  "forecast: raise price 5% on these SKUs and measure.")
    print("- The stronger Week 2 finding may be discount discipline "
          "(Part 3): quantify the below-modal cost per SKU and ask which "
          "discounts bought volume and which just gave money away.")
    print()
    print("Wrote outputs/ : top25_skus, revenue_by_month, "
          "revenue_by_country, revenue_by_price_band, elasticity_top25, "
          "discount_check_top25, customer_tiers.")
    print("Next: pick ONE recommendation from above, write it up with its "
          "math and caveats, and carry the elasticity chart into Week 3 "
          "(Tableau).")


if __name__ == "__main__":
    main()
