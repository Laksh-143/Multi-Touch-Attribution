# Tableau Dashboard Guide: Step-by-Step

### Multi-Touch Attribution & Budget Reallocation Dashboard

---

## Data Sources

All CSV files are in `data/exports/`. Connect each one as a separate data source in Tableau Public:

| File | What It Contains |
|---|---|
| `model_comparison.csv` | 6-model attribution comparison (8 channels × 6 models) |
| `financial_reconciliation.csv` | Illustrative spend, CPA by Last-Click and Shapley |
| `budget_optimizer.csv` | Shapley-proportional budget reallocation deltas |

---

## Step 0: Download Tableau Public (Free)

1. Go to: https://public.tableau.com/en-us/s/download
2. Download and install Tableau Public Desktop.

---

## Sheet 1: Model Comparison (Grouped Bar Chart)
*Shows how conversion credit shifts across attribution models per channel.*

1. Select **`model_comparison`** as the data source.
2. The file is wide format. **Pivot** the 6 model columns (`First_Click` through `Shapley`):
   - In the Data Source tab, highlight all 6 model columns → Right-click → **Pivot**.
   - Rename `Pivot Field Names` to **`Attribution Model`** and `Pivot Field Values` to **`Attributed Conversions`**.
3. Drag **`Channel`** to **Rows**.
4. Drag **`Attributed Conversions`** to **Columns**.
5. Drag **`Attribution Model`** to **Color**.
6. **Filter:** Drag `Attribution Model` to Filters → select only `Last_Click`, `Markov`, `Shapley`.
7. Sort descending by conversions.

---

## Sheet 2: CPA Comparison (Side-by-Side Bars)
*Exposes true acquisition costs: Last-Click vs Shapley.*

1. New Sheet → select **`financial_reconciliation`** data source.
2. Drag **`Channel`** to **Rows**.
3. Drag **`Measure Names`** to **Columns** and **Filters** (select `Last_Click_CPA` and `Shapley_CPA`).
4. Drag **`Measure Values`** to **Columns** and **`Measure Names`** to **Color**.
5. **Filter out unpaid channels:** Drag `Illustrative_Spend` to Filters → set minimum to `1.00`.
6. Format: Right-click CPA values → Format → Currency.
7. **Add disclosure caption:** *"CPC values are illustrative estimates, not from a specific published benchmark."*

---

## Sheet 3: Budget Reallocation (Diverging Bar Chart)
*Shows recommended dollar deltas under Shapley-proportional constraints.*

1. New Sheet → select **`budget_optimizer`** data source.
2. Drag **`Channel`** to **Rows**.
3. Drag **`Spend_Delta`** to **Columns** and **Color**.
4. Edit Color: **Red-Green Diverging**, Center at `0`.
5. Add **`Spend_Delta`** to **Label** → Format as Currency.
6. Sort descending (positive additions at top).

---

## Dashboard Assembly

1. New Dashboard → Size: **1200 × 800**.
2. Layout:
   ```
   ┌──────────────────────────────────────────────────┐
   │  TITLE: Multi-Touch Attribution Dashboard         │
   ├─────────────────────────┬────────────────────────┤
   │  Model Comparison       │  CPA Comparison         │
   │  (65% width)            │  (35% width)            │
   ├─────────────────────────┴────────────────────────┤
   │  Budget Reallocation (full width)                 │
   ├──────────────────────────────────────────────────┤
   │  Disclosure: CPC values are illustrative          │
   │  estimates. GA4 data excludes real ad spend.      │
   └──────────────────────────────────────────────────┘
   ```
3. **File → Save to Tableau Public As...** to publish.
