# Setup: Python + SQL on a work computer (Windows)

You need exactly two things: Python, and two small libraries. There is
no database to install: SQLite is built into Python. Nothing here needs
admin rights.

## Step 1: Install Python (pick one)

**Option A — Microsoft Store (easiest, no admin).**
Open the Microsoft Store app, search "Python 3.12", click Install.

**Option B — python.org.**
Go to https://www.python.org/downloads/, download the Windows
installer (64-bit), run it. On the first screen, tick
"Add python.exe to PATH", then click Install. If it asks about admin,
choose "Install for current user only".

Check it worked. Open Command Prompt or PowerShell (press Win+R, type
`cmd`, Enter) and run:
```
python --version
```
It should print something like `Python 3.12.x`. If it says "not
recognized", close the terminal, open a new one, and try again. If it
still fails, reinstall with the PATH box ticked.

## Step 2: Install the two libraries

In the same terminal:
```
pip install pandas openpyxl
```
Check it worked:
```
python -c "import pandas; print(pandas.__version__)"
```
It should print a version number like `2.2.3`. If pip complains about
permissions, try `pip install --user pandas openpyxl` instead.

## Step 3: Editor (optional but recommended)

VS Code, https://code.visualstudio.com — download the **User Installer**
for Windows (no admin). After installing, open VS Code, go to
Extensions, and install the **Python** extension by Microsoft. You can
open the whole project folder in VS Code and run the scripts from its
built-in terminal.

## Step 4: Get the project files

Download the project zip (link from Muse), unzip it somewhere easy,
for example `Documents\pricing-analysis`. It contains:
- `PROJECT_BRIEF.md` — the full plan
- `SETUP.md` — this file
- `data/online_retail.xlsx` — the dataset
- `sql/01_cleaning.sql` — the Week 1 SQL
- `scripts/load_data.py` — loads the xlsx into a SQLite database
- `scripts/run_sql.py` — runs the SQL file and prints the results

## Step 5: Run Week 1

In the terminal, go into the project folder:
```
cd Documents\pricing-analysis
```
Then:
```
python scripts/load_data.py
python scripts/run_sql.py
```
`load_data.py` should print `wrote table raw: 541,909 rows, revenue
$9,747,747.93`. `run_sql.py` prints the audit counts and builds two
tables, `orders` (expect 530,104 rows, $10,666,684.54) and
`daily_revenue` (expect 305 rows, $10,272,346.92). If a number does not
match, stop and paste the output to Muse in the project chat.

## If IT blocks installs entirely

Fallback, no install at all: Google Colab (colab.research.google.com).
Upload `data/online_retail.xlsx` to Google Drive, open a new notebook,
and run the same pandas code there. Ask Muse in the project chat and
it will rewrite the two scripts for Colab.

## Not needed yet

- Tableau: Week 3 only.
- GitHub account / Git: Week 4 only.
