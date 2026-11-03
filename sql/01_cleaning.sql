-- Week 1: Clean and model (SQL) -- UCI Online Retail, Dec 2010 - Dec 2011
-- Starter file prepared 2026-11-01. Run it, read the sanity-check output,
-- then make the two flagged decisions (A and B) your own before Week 2.
--
-- HOW TO RUN
--   1. Load data/online_retail.xlsx into a table called `raw` with columns
--      InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice,
--      CustomerID, Country (e.g. pandas read_excel -> to_sql, or DuckDB).
--   2. Run this file top to bottom. It only reads `raw` and creates two
--      new tables: `orders` and `daily_revenue`. It never modifies `raw`.
--   3. Standard SQL; tested logic against DuckDB/SQLite-style syntax.
--
-- VERIFIED COUNTS (checked against the actual file on 2026-11-01, not the brief)
--   Raw rows: 541,909. Raw revenue (Quantity * UnitPrice): $9,747,747.93
--   Cancelled invoices (InvoiceNo starts with 'C'): 9,288 rows
--   Negative-quantity rows (returns/corrections): 10,624 rows
--   Zero or negative-price rows: 2,517 rows
--   Rows with no CustomerID: 135,080 raw / 132,220 after the rules below
--   After the three decided rules: 530,104 rows, revenue $10,666,684.54
--   NOTE: revenue goes UP after cleaning. That is correct, not a bug:
--   returns (negative quantities) and negative prices were dragging the
--   raw total down. Write this down in the README; a reviewer will ask.

-- ---------------------------------------------------------------------------
-- Step 1: Audit the raw table. Each query should return the verified count
-- in the comment. If one does not match, stop: the load is wrong.
-- ---------------------------------------------------------------------------

-- Expect 541,909 rows, revenue $9,747,747.93
SELECT COUNT(*) AS raw_rows,
       ROUND(SUM(Quantity * UnitPrice), 2) AS raw_revenue
FROM raw;

-- Expect 9,288
SELECT COUNT(*) AS cancelled_rows
FROM raw
WHERE InvoiceNo LIKE 'C%';

-- Expect 10,624
SELECT COUNT(*) AS negative_qty_rows
FROM raw
WHERE Quantity < 0;

-- Expect 2,517
SELECT COUNT(*) AS nonpositive_price_rows
FROM raw
WHERE UnitPrice <= 0;

-- Expect 135,080
SELECT COUNT(*) AS null_customer_rows
FROM raw
WHERE CustomerID IS NULL;

-- ---------------------------------------------------------------------------
-- Step 2: Build `orders` -- one row per cleaned invoice line.
-- DECIDED RULES (already in the project brief, implemented here):
--   R1: drop cancelled invoices (InvoiceNo starts with 'C').
--   R2: drop returns/corrections (Quantity <= 0). They are not sales;
--       a returns analysis is a different project.
--   R3: drop zero/negative prices (UnitPrice <= 0). A sale cannot cost $0
--       or less, and the negative prices in this file are adjustments.
-- ---------------------------------------------------------------------------

CREATE TABLE orders AS
SELECT
    InvoiceNo,
    StockCode,
    Description,
    Quantity,
    DATE(InvoiceDate) AS invoice_date,
    UnitPrice,
    CustomerID,
    Country,
    Quantity * UnitPrice AS line_revenue,
    CASE WHEN CustomerID IS NULL THEN 0 ELSE 1 END AS has_customer_id,
    -- Decision B flag, see below. 1 = fee / postage / manual adjustment,
    -- not a product sale. daily_revenue excludes these lines (see Step 3).
    CASE
        WHEN StockCode IN ('POST', 'DOT', 'AMAZONFEE', 'B', 'M', 'C2', 'D')
          OR UPPER(COALESCE(Description, '')) LIKE '%POSTAGE%'
          OR UPPER(COALESCE(Description, '')) LIKE '%AMAZON FEE%'
          OR UPPER(COALESCE(Description, '')) LIKE '%ADJUST BAD DEBT%'
          OR UPPER(COALESCE(Description, '')) LIKE '%MANUAL%'
        THEN 1 ELSE 0
    END AS is_non_product
FROM raw
WHERE InvoiceNo NOT LIKE 'C%'
  AND Quantity > 0
  AND UnitPrice > 0;

-- Expect 530,104 rows, revenue $10,666,684.54 (includes non-product lines;
-- see the non-product split in the Step 4 checks before quoting a number).
SELECT COUNT(*) AS orders_rows,
       ROUND(SUM(line_revenue), 2) AS orders_revenue
FROM orders;

-- ---------------------------------------------------------------------------
-- DECISION A (left open in the brief -- recommended answer, change if you
-- disagree): NULL CustomerID rows. There are 132,220 of them in `orders`,
-- worth $1,755,276.64, about 16% of clean revenue. Dropping them would
-- understate revenue by a sixth, so they STAY in `orders` and in
-- `daily_revenue`. They are excluded only from customer-level analysis in
-- Week 2: filter on has_customer_id = 1 there. No action needed here.
--
-- DECISION B (left open in the brief -- recommended answer, change if you
-- disagree): EXTREME PRICES ARE MOSTLY NOT PRODUCTS. The five most
-- expensive lines in the file are AMAZON FEE ($13,541.33), Adjust bad debt
-- ($11,062.06), POSTAGE ($8,142.75), DOTCOM POSTAGE ($4,505.17) and Manual
-- ($4,287.63). UnitPrice over $100 is only 811 rows but 3.51% of revenue.
-- A blanket price cap would hide this; a StockCode/Description flag
-- removes the fees without touching real high-price products. The flag
-- above (is_non_product) does that, and daily_revenue below excludes
-- flagged lines. If you would rather keep them, change Step 3 to drop
-- the `AND is_non_product = 0` line and note the choice in the README.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Step 3: Build `daily_revenue` -- one row per day, product sales only.
-- ---------------------------------------------------------------------------

CREATE TABLE daily_revenue AS
SELECT
    invoice_date AS date,
    ROUND(SUM(line_revenue), 2) AS revenue,
    SUM(Quantity) AS units,
    COUNT(DISTINCT InvoiceNo) AS orders
FROM orders
WHERE is_non_product = 0
GROUP BY invoice_date
ORDER BY invoice_date;

-- Expect 305 rows (only days with sales, Dec 1, 2010 - Dec 9, 2011),
-- product-only revenue $10,272,346.92, no NULL dates.
SELECT COUNT(*) AS daily_rows,
       MIN(date) AS first_day,
       MAX(date) AS last_day,
       ROUND(SUM(revenue), 2) AS total_revenue
FROM daily_revenue;

-- ---------------------------------------------------------------------------
-- Step 4: Sanity checks. Record all four numbers in the README.
-- ---------------------------------------------------------------------------

-- 1. Revenue bridge: raw -> after R1-R3 -> after removing non-product lines.
SELECT 'raw' AS stage, COUNT(*) AS rows,
       ROUND(SUM(Quantity * UnitPrice), 2) AS revenue FROM raw
UNION ALL
SELECT 'after R1-R3', COUNT(*), ROUND(SUM(line_revenue), 2) FROM orders
UNION ALL
SELECT 'product lines only', COUNT(*), ROUND(SUM(line_revenue), 2)
FROM orders WHERE is_non_product = 0;

-- 2. Revenue by month (spot the Dec 2010 / Dec 2011 partial months).
SELECT CAST(strftime('%Y-%m', invoice_date) AS TEXT) AS month,
       ROUND(SUM(line_revenue), 2) AS revenue,
       COUNT(DISTINCT InvoiceNo) AS orders
FROM orders
WHERE is_non_product = 0
GROUP BY month
ORDER BY month;

-- 3. Top 10 SKUs by revenue, product lines only (Week 2 starts here).
SELECT StockCode, Description,
       ROUND(SUM(line_revenue), 2) AS revenue,
       SUM(Quantity) AS units,
       COUNT(DISTINCT InvoiceNo) AS orders
FROM orders
WHERE is_non_product = 0
GROUP BY StockCode, Description
ORDER BY revenue DESC
LIMIT 10;

-- 4. Null-CustomerID share of product-line revenue, for the README
-- limitations section. Expect about 14.7% ($1,511,115.27 of product
-- revenue; $1,755,276.64, 16.5%, of all cleaned-line revenue).
SELECT ROUND(100.0 * SUM(CASE WHEN has_customer_id = 0 THEN line_revenue ELSE 0 END)
             / SUM(line_revenue), 1) AS pct_revenue_no_customer_id
FROM orders
WHERE is_non_product = 0;
