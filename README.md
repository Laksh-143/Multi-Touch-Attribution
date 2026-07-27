# Multi-Touch Attribution & Algorithmic Budget Optimizer
### A SQL-First E-Commerce Marketing Analytics Pipeline using Cooperative Game Theory & Markov Chains

[![Live Interactive Dashboard](https://img.shields.io/badge/🚀_Live_Demo-Interactive_Web_Dashboard-6366f1?style=for-the-badge)](https://laksh-143.github.io/Multi-Touch-Attribution/dashboard.html)
[![Tableau Dashboard](https://img.shields.io/badge/📊_Tableau_Public-Executive_Portfolio-e17055?style=for-the-badge)](tableau_guide.md)
[![Python & SQL Stack](https://img.shields.io/badge/Stack-SQLite_%7C_Python_%7C_Chart.js-38bdf8?style=for-the-badge)](#system-architecture)

> **Live Interactive Web Dashboard:** *[Click here to view the live standalone interactive web dashboard](https://laksh-143.github.io/Multi-Touch-Attribution/dashboard.html)*

---

## 1. Executive Summary & Problem Statement

### The Broken Mechanics of Last-Click Attribution
In modern multi-channel marketing, a customer rarely purchases on their first interaction with a brand. A typical e-commerce journey spans multiple touchpoints: an initial organic search discovery, a retargeting display ad, a social media engagement, and finally a direct visit to complete the purchase. 

Traditional **Last-Click Attribution** credits 100% of the conversion and revenue to the final touchpoint before purchase. This creates a severe analytical bias:
1. **Systematic Starvation of Top-of-Funnel Channels:** Discovery channels (like Paid Search and Non-Brand Organic) bear the acquisition cost of introducing new users but receive zero conversion credit if another channel closes the sale.
2. **Over-Valuation of Bottom-Funnel Closing Channels:** Saturated closing channels (such as Brand Search, Retargeting Display, and Direct) take full credit for conversions that were initiated and nurtured by upstream investments.
3. **Misallocated Capital:** When marketing budgets are allocated based on last-click CPA/ROAS, companies continuously cut budget from top-of-funnel discovery channels until new customer acquisition collapses.

### Project Objective
This project builds an end-to-end, reproducible analytics engine that evaluates **319,982 e-commerce sessions** across **258,650 unique visitors** from the Google Merchandise Store. We compare traditional heuristic baselines against advanced algorithmic models — **Absorbing Markov Chain Removal Effects** and **Cooperative Game Theory (Shapley Value)** — to uncover true channel contributions and mathematically reallocate a fixed marketing budget for maximum portfolio ROI.

---

## 2. System Architecture & Data Pipeline

A foundational engineering requirement of this project is that **SQL performs the core relational modeling and aggregation work**, rather than delegating heavy data manipulation to Python memory.

```
+---------------------------------------------------------------------------------------------------+
|                                      1. EXTRACTION LAYER                                          |
|  Google BigQuery Public Dataset (google_analytics_sample.ga_sessions_*)                           |
|  --> Decoupled via scripts/00_extract_bigquery.py --> Stored as data/raw/staging_sessions.csv     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                    2. SQL WAREHOUSE LAYER (SQLite)                                |
|  Executed via scripts/01_build_warehouse.py into data/warehouse.db                               |
|                                                                                                   |
|  [dim_channel]                [fact_sessions]               [fact_conversions]                    |
|  8 Reference Channels         319,982 Sequenced Rows        3,719 Converting Sessions             |
|                               ROW_NUMBER() Sequencing       Real Revenue & Transactions ($522k)   |
|                                                                                                   |
|  [fact_channel_transitions]   [journey_paths]                                                     |
|  574,856 Markov Edges         258,650 Visitor Path Strings                                        |
|  Computed via UNION ALL       Pre-sorted GROUP_CONCAT Aggregation                                 |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 3. ALGORITHMIC STATISTICAL LAYER                                  |
|  Executed via scripts/02_run_attribution_models.py (Python / Pandas / NumPy / NetworkX)           |
|                                                                                                   |
|  * Heuristic Baselines: First-Click, Last-Click, Linear, Time-Decay                               |
|  * Analytical Markov Chain: Closed-form (I - Q)^-1 fundamental matrix inversion                   |
|  * Exact Shapley Value: Vectorized 2^8 = 256 coalition game theory enumeration                    |
|  * Financial Reconciliation & Shapley-Proportional Budget Optimizer                               |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 4. PRESENTATION & DELIVERABLES                                    |
|  * Standalone Interactive Web Dashboard (dashboard.html via Chart.js & Glassmorphism UI)          |
|  * Clean Jupyter Research Notebooks (notebooks/01_*.ipynb and 02_*.ipynb)                         |
|  * Tableau Executive Portfolio Guide (tableau_guide.md)                                           |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Algorithmic Methodology & Architectural Decisions

### Why SQL-First Modeling?
In production analytics engineering, extracting raw logs directly into Pandas leads to memory bottlenecks and unversioned transformations. We architected a relational star-schema in ANSI SQL (`sql/01_dim_channel.sql` through `sql/05_journey_paths.sql`) executed inside SQLite:
* **Session Sequencing:** Used `ROW_NUMBER() OVER (PARTITION BY full_visitor_id ORDER BY visit_id)` to establish chronological touchpoint order.
* **Pre-Conversion Scoping:** Built a `scoped_sessions` CTE that joins against `MIN(visit_id)` from `fact_conversions`, strictly truncating user histories at the moment of first purchase. Post-conversion browsing is cleanly excluded from attribution logic.
* **In-SQL Markov Transition Matrix:** In `04_fact_channel_transitions.sql`, the transition matrix is constructed entirely in SQL using three `UNION ALL` blocks combining `Start` edges, `LAG()` mid-path step edges, and `Conversion`/`Null` absorption edges.

### Why Analytical Closed-Form Markov Chains?
Rather than simulating thousands of random walks (which introduces stochastic noise and run-time latency), we solve the absorbing Markov chain **deterministically** using linear algebra.
1. The transition matrix is partitioned into transient states ($Q$, marketing channels) and absorbing states ($R$, Conversion and Drop-off/Null).
2. The fundamental matrix $N = (I - Q)^{-1}$ yields the exact expected number of visits to each state before absorption.
3. The absorption probability matrix is computed as $B = N \cdot R$.
4. **Removal Effect Methodology:** To compute the contribution of channel $i$, we remove state $i$ from the transition matrix and re-route all inbound transitions directly to the drop-off state (`Null`). The percentage drop in overall system absorption probability represents channel $i$'s removal effect, which is normalized across all channels to distribute conversions.

### Why Exact Shapley Value Enumeration?
Shapley Value (derived from cooperative game theory) assigns each marketing channel its average marginal contribution across all possible touchpoint permutations. 
* In environments with dozens of channels, Shapley requires Monte Carlo approximation. However, with our taxonomy of 8 marketing channels ($N=8$), the power set of coalitions contains exactly $2^8 = 256$ subsets.
* We perform **exact, full-dataset enumeration** across all 258,650 visitors without subsampling approximation error. By defining the characteristic game function $v(S)$ as the total conversion volume achieved by coalition $S$, marginal contributions are strictly non-negative and sum to exactly 100% of realized conversions.

---

## 4. Key Strategic Findings & Budget Reallocation

### Attribution Model Shifts (Shapley vs. Last-Click)
Comparing traditional Last-Click credit against algorithmic Shapley contribution reveals significant credit shifts across the 3,341 converting visitor paths:

| Marketing Channel | Last-Click Conversions | Shapley Conversions | Conversion Delta | Credit Shift (%) | Role in Customer Journey |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Direct** | 562.0 | **629.17** | +67.17 | **+11.9%** | Strong closing & brand recall; undervalued by heuristics. |
| **Paid Search** | 162.0 | **169.50** | +7.50 | **+4.6%** | High-intent discovery & upper-funnel acquisition. |
| **Display** | 54.0 | **56.50** | +2.50 | **+4.6%** | Top-of-funnel brand awareness and retargeting assist. |
| **Organic Search** | 1,022.0 | **1,033.00** | +11.00 | **+1.1%** | Core educational research and product discovery. |
| **Social** | 31.0 | **31.17** | +0.17 | **+0.5%** | Mid-funnel engagement and community touchpoint. |
| **Referral** | 1,509.0 | **1,420.67** | -88.33 | **-5.9%** | Heavily over-credited by Last-Click due to third-party domains. |

### Shapley-Proportional Budget Reallocation
Under a fixed paid marketing budget constraint ($148,694.70 illustrative spend across Paid Search, Display, Social, and Affiliates), reallocating capital proportional to Shapley algorithmic contribution weights produces an optimized investment strategy:
* 🟢 **Paid Search (+$71,464.63 / +273% addition):** Currently starved by last-click CPA metrics; generates 65.7% of paid algorithmic conversion value.
* 🟢 **Display (+$30,980.34 / +1,984% addition):** Highly efficient upper-funnel discovery assist channel (21.9% Shapley weight).
* 🔴 **Social (-$95,963.43 / -84% cut):** Absorbs massive raw click volume in current spend but yields low closing efficiency (12.1% Shapley weight).
* 🔴 **Affiliates (-$6,481.54 / -92% cut):** Low incremental contribution weight (0.4%); budget reallocated to discovery channels.

---

## 5. Honest Analytical Disclosures & Known Limitations

To maintain strict engineering and analytical credibility, the following data realities are transparently disclosed across all notebooks, scripts, and dashboard interfaces:
1. **Illustrative Advertising Spend:** Google Analytics 360 sample datasets do not contain financial cost or advertising spend metrics. The CPC figures used in this project ($2.50 Paid Search, $0.60 Display, $1.20 Social, $1.50 Affiliates) are plausible order-of-magnitude assumptions by channel type, used solely to demonstrate the financial reconciliation and budget optimization methodology. If real ad spend were available, it would act as a drop-in replacement.
2. **Real Average Order Value (AOV = $135.70):** Unlike spend, transaction revenue is real. AOV is computed directly from actual transaction data (`SUM(revenue) / SUM(transactions)` = $522,574.73 / 3,851 transactions) in `fact_conversions.csv`.
3. **Linear "What-If" Scaling:** The interactive scenario simulator assumes constant marginal returns. In production environments, advertising channels experience diminishing returns at scale; linear scaling serves as directional strategic guidance.
4. **Left-Censoring Window:** The 4-month extraction window (Nov 2016 – Feb 2017) means visitors converting in early November may have had awareness touchpoints in October that fall outside the extraction boundary.

---

## 6. Repository Structure & Local Execution

### Project Directory
```
multi_touch_attribution/
├── dashboard.html                       # Standalone interactive web dashboard (Double-click to open!)
├── sql/
│   ├── 01_dim_channel.sql               # Reference channel taxonomy
│   ├── 02_fact_sessions.sql             # Chronological session sequencing
│   ├── 03_fact_conversions.sql          # Converting sessions & revenue
│   ├── 04_fact_channel_transitions.sql  # In-SQL Markov transition matrix
│   └── 05_journey_paths.sql             # Ordered journey path strings
├── scripts/
│   ├── 00_extract_bigquery.py           # BigQuery extraction (requires GCP auth)
│   ├── 01_build_warehouse.py            # SQLite warehouse builder & checkpoint validator
│   ├── 02_run_attribution_models.py     # Markov, Shapley & budget optimization engine
│   └── 04_build_html_dashboard.py       # Standalone HTML dashboard generator
├── notebooks/
│   ├── 01_sql_warehouse_and_attribution.ipynb     # Phase 1 & 2 research notebook
│   └── 02_budget_optimization_and_simulation.ipynb # Phase 3 strategy & visualization notebook
├── data/
│   ├── raw/staging_sessions.csv         # Extracted raw session data (319k rows)
│   └── exports/                         # Clean CSV exports feeding Tableau and HTML dashboard
└── tableau_guide.md                     # Click-by-click Tableau Public dashboard blueprint
```

### How to Run Locally

**1. Environment Setup:**
```powershell
# Clone repository and enter directory
git clone https://github.com/Laksh-143/Multi-Touch-Attribution.git
cd Multi-Touch-Attribution

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate           # Windows PowerShell
# source venv/bin/activate      # macOS / Linux

# Install required analytical dependencies
pip install pandas numpy matplotlib networkx
```

**2. Execute the Analytics Pipeline:**
```powershell
# Step 1: Build SQL warehouse and verify all 5 row-count checkpoints
python scripts/01_build_warehouse.py

# Step 2: Run Algorithmic Attribution Models & Budget Optimizer
python scripts/02_run_attribution_models.py

# Step 3 (Optional): Update the standalone HTML web dashboard
python scripts/04_build_html_dashboard.py
```

**3. View Interactive Deliverables:**
* **Web Dashboard:** Double-click `dashboard.html` in Windows Explorer to open the interactive UI in any browser.
* **Jupyter Notebooks:** Open `notebooks/01_*.ipynb` and `notebooks/02_*.ipynb` in VS Code or Jupyter Lab, select the `venv` kernel, and run all cells.

---
*Built as an advanced analytical portfolio project demonstrating rigorous SQL data warehousing, algorithmic game theory, and executive financial presentation.*
