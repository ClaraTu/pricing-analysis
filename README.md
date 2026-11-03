# Pricing Analysis — UCI Online Retail

**Business question:** where can we raise prices without losing volume,
and where are discounts costing money?

## Dataset

UCI Online Retail (UCI Machine Learning Repository, dataset 00352),
donated by Daqing Chen (2012). Real transactions from a UK online
giftware retailer, Dec 1, 2010 – Dec 9, 2011.

- 541,909 rows, 8 columns: InvoiceNo, StockCode, Description, Quantity,
  InvoiceDate, UnitPrice, CustomerID, Country
- Source: https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx

## Week 1 — verified numbers (2026-11-03)

Revenue bridge:

| stage | rows | revenue |
|---|---|---|
| raw | 541,909 | $9,747,747.93 |
| after R1–R3 | 530,104 | $10,666,684.54 |
| product lines only | 527,806 | $10,272,346.92 |

Cleaning audits:

| check | rows |
|---|---|
| cancelled invoices (InvoiceNo starts with 'C') | 9,288 |
| negative-quantity rows (returns/corrections) | 10,624 |
| zero/negative-price rows | 2,517 |
| null CustomerID (raw / after R1–R3) | 135,080 / 132,220 |

`daily_revenue`: 305 days, Dec 1, 2010 – Dec 9, 2011, $10,272,346.92.
Null-customer share of product revenue: 14.7%.

Note: revenue goes UP after cleaning. That is correct, not a bug:
returns (negative quantities) and negative prices were dragging the raw
total down.

## Cleaning rules (decided)

- R1: drop cancelled invoices (InvoiceNo starts with 'C').
- R2: drop returns/corrections (Quantity <= 0). They are not sales;
  a returns analysis is a different project.
- R3: drop zero/negative prices (UnitPrice <= 0). A sale cannot cost
  $0 or less, and the negative prices in this file are adjustments.

## Decisions (confirmed 2026-11-03)

- **A — NULL CustomerID rows stay** in `orders` and `daily_revenue`
  (132,220 rows, about 16% of clean revenue; dropping them would
  understate revenue by a sixth). They are excluded only from
  customer-level analysis in Week 2: filter on `has_customer_id = 1`.
- **B — non-product lines are flagged, not capped.** Lines with
  StockCode POST, DOT, AMAZONFEE, B, M, C2, D, or Description
  containing POSTAGE / AMAZON FEE / ADJUST BAD DEBT / MANUAL get
  `is_non_product = 1` and are excluded from `daily_revenue`. The
  five most expensive lines in the file are fees, not products:
  AMAZON FEE ($13,541.33), Adjust bad debt ($11,062.06), POSTAGE
  ($8,142.75), DOTCOM POSTAGE ($4,505.17), Manual ($4,287.63).
  UnitPrice over $100 is only 811 rows but 3.51% of revenue, so a
  blanket price cap would hide this; the flag removes the fees
  without touching real high-price products.

## Monthly revenue (product lines only)

| month | revenue | orders |
|---|---|---|
| 2010-12 | $778,023.36 | 1,551 |
| 2011-01 | $672,007.41 | 1,082 |
| 2011-02 | $508,952.87 | 1,093 |
| 2011-03 | $691,265.94 | 1,440 |
| 2011-04 | $516,354.79 | 1,237 |
| 2011-05 | $741,290.74 | 1,669 |
| 2011-06 | $738,876.88 | 1,525 |
| 2011-07 | $689,397.74 | 1,452 |
| 2011-08 | $725,605.16 | 1,339 |
| 2011-09 | $1,030,530.36 | 1,820 |
| 2011-10 | $1,106,749.54 | 2,008 |
| 2011-11 | $1,457,775.53 | 2,753 |
| 2011-12 | $615,516.60 | 817 |

Dec 2010 and Dec 2011 are partial months (data starts Dec 1, 2010 and
ends Dec 9, 2011).

## Top 10 SKUs by revenue (product lines only)

| StockCode | Description | revenue | units | orders |
|---|---|---|---|---|
| 22423 | REGENCY CAKESTAND 3 TIER | $174,484.74 | 13,879 | 1,988 |
| 23843 | PAPER CRAFT, LITTLE BIRDIE | $168,469.60 | 80,995 | 1 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | $104,340.29 | 37,599 | 2,189 |
| 47566 | PARTY BUNTING | $99,504.33 | 18,295 | 1,685 |
| 85099B | JUMBO BAG RED RETROSPOT | $94,340.05 | 48,474 | 2,089 |
| 23166 | MEDIUM CERAMIC TOP STORAGE JAR | $81,700.92 | 78,033 | 247 |
| 23084 | RABBIT NIGHT LIGHT | $66,964.99 | 30,788 | 994 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | $64,952.29 | 19,355 | 1,160 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | $59,094.93 | 36,461 | 1,455 |
| 79321 | CHILLI LIGHTS | $54,117.76 | 10,306 | 661 |

## How to run

- `python scripts/load_data.py` — loads `data/online_retail.xlsx`
  into `retail.db` as table `raw`.
- `python scripts/run_sql.py` — runs `sql/01_cleaning.sql`, builds
  `orders` and `daily_revenue`, prints all checks. Safe to re-run.
- Requires Python 3.15, pandas, openpyxl. SQLite is built into Python.

## Limitations (things a reviewer will ask)

- No discount or profit columns: this dataset has an explicit UnitPrice
  but no cost, so the analysis is about price variation across
  products and time, not margin. Elasticity is estimated from price
  and quantity variation, not from a discount field.
- UK giftware, 2010–2011: old, single-category retail; the findings
  show method, not current market pricing.
- 14.7% of product revenue has no CustomerID: customer-level analysis
  in Week 2 covers only the identifiable 85.3%.
- Dec 2010 and Dec 2011 are partial months; month comparisons should
  note this.
- Outlier: PAPER CRAFT, LITTLE BIRDIE — 80,995 units in a single
  order, $168,469.60, the #2 SKU by revenue. One bulk order, not a
  repeat pattern; Week 2 should check whether to keep it in
  elasticity estimates.
- Returns are excluded by design (R2); a returns analysis is a
  different project.
