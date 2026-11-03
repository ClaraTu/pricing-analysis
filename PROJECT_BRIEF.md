# Side Project: Pricing & Revenue Analytics Case Study

**Status:** picked by Nehita on 2026-11-01 (over the data-pipeline and Ergomotion case-study options)
**Dataset (decided 2026-11-02):** UCI Online Retail. US Superstore and Airbnb NYC were evaluated and set aside; their files remain in data/ for reference.
**Project chat:** 86390552-22c3-4fac-b57b-134c70657e00 ("定价分析 side project", created 2026-11-02) — progress and questions go there, not the main chat.
**Time budget:** 3-4 hours/week for 4 weeks. Must not eat into French study time.
**Stack:** SQL + Python (pandas, numpy, stats) + Tableau. GitHub repo + 1-page write-up at the end.

## The business question

You are the pricing analyst for a UK online retailer. Management wants to know: **where can we raise prices without losing volume, and where are discounts actually costing us money?**

Answer it with data, not opinion. The deliverable is a short analysis a hiring manager can read in 5 minutes, backed by a repo they can open.

## The dataset (verified 2026-11-01)

**UCI Online Retail** (classic UCI ML Repository dataset 00352), a real UK online retailer's transactions.
Source: https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
Local copy: `data/online_retail.xlsx` (23.7 MB)

Verified profile:
- **541,909 rows**, 8 columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country
- Date range: **Dec 1, 2010 to Dec 9, 2011** (about 1 year)
- 4,070 products, 4,372 customers, 25,900 invoices, 38 countries (UK is 495,478 rows, ~91%)
- Median unit price $2.08 (this is a low-price giftware retailer, say so honestly)

Known data-quality quirks (these are part of the project, document every decision):
- 9,288 cancelled invoices (InvoiceNo starts with "C")
- 10,624 negative-quantity rows (returns/corrections)
- 2,517 zero or negative-price rows
- 135,080 rows with no CustomerID
- Extreme outliers: UnitPrice from -11,062 to 38,970; Quantity from -80,995 to 80,995 (almost certainly data-entry errors; decide an explicit rule, e.g. exclude or winsorize, and write it down)

## The plan

### Week 1: Clean and model (SQL)
- Load into SQLite/DuckDB or just pandas; either is fine, but do the cleaning in SQL so the repo shows SQL.
- Documented cleaning rules: drop cancelled invoices, handle returns and zero/negative prices, decide the null-CustomerID rule, decide the outlier rule.
- Build two clean tables: `orders` (one row per invoice line, cleaned) and `daily_revenue` (date, revenue, units, orders).
- Sanity checks: total revenue before vs after cleaning, row counts at each step.

### Week 2: Analysis (pandas, numpy, stats)
Pick the top 20-30 SKUs by revenue and do these four:
1. **Revenue structure:** revenue and units by month, country, and price band. Which bands drive revenue vs volume?
2. **Price elasticity:** for SKUs whose price changed during the year, estimate elasticity with a log-log regression of quantity on price (control for month/seasonality). Report the elasticity and its confidence interval; do not overclaim, this is observational data.
3. **Discount check:** compare revenue per unit on discounted vs full-price lines for the same SKU. Where does discounting buy volume, and where does it just give money away?
4. **Customer segments:** split customers into spend tiers (or RFM) and check which tiers are price-sensitive.
- End the week with **one pricing recommendation** in numbers, e.g. "raising price 5% on the 10 most inelastic SKUs is worth roughly $X/year at current volume, before any volume loss." Show the math and the caveats.

### Week 3: Dashboard (Tableau)
- One dashboard, four views: revenue trend, price-band mix, elasticity scatter (elasticity vs revenue by SKU), top SKUs table.
- Publish to Tableau Public so the resume can link to it.

### Week 4: Write-up and ship
- GitHub repo: `README.md` (business question, data, methods, findings, limitations), `sql/`, `notebooks/` or `src/`, and a link to the Tableau Public dashboard.
- One-page PDF write-up: question, 3 findings, 1 recommendation, limitations. This is the artifact a recruiter actually reads.
- Resume line (draft, to finalize when it ships): "Built an end-to-end pricing analysis on 542K retail transactions (SQL, Python, Tableau): estimated price elasticity for top SKUs and identified a 5% price increase opportunity on inelastic items." Adjust the numbers to what the analysis actually finds.

## Honest limitations (write these in the README)

- Data is from 2010-2011. Say so; it does not change the methods, but do not present it as current.
- No cost data, so margin is proxied by price, not true profit.
- Observational data only: elasticity estimates show association, not a controlled experiment. A real pricing test would be an A/B test.
- One retailer, mostly UK, low-price giftware. Findings do not generalize to all retail.

## What this is for

- A public, verifiable artifact that shows SQL + pandas + Tableau together, plus pricing-domain thinking, which is the exact cluster of roles she applies to most (pricing, revenue, BI, FP&A-adjacent).
- It does not fix ATS years-of-experience filters or sponsorship screens. Its value is at the human-review stage and in referrals/networking.
