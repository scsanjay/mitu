# Sentiment Metrics Documentation

This document explains every sentiment metric used in MITU's sentiment scoring system — from the raw data sourced from Yahoo Finance, to the signal logic, and finally the weighted scoring formula used in `score_sentiment_v2()`. It also covers the **Predictive Trend Score**, which is a separate price-momentum indicator displayed alongside the sentiment score.

---

## 1. Base Data (from Yahoo Finance)

Sentiment data is fetched from multiple `yfinance` sub-objects beyond `stock.info`.

| Data Object | `yfinance` Attribute | Description |
| :--- | :--- | :--- |
| **EPS Trend** | `stock.eps_trend` | DataFrame of analyst EPS estimates across time windows (current, 7d ago, 30d ago, 60d ago, 90d ago) |
| **Major Holders** | `stock.major_holders` | DataFrame with insider/promoter and institutional holding percentages |
| **Insider Transactions** | `stock.insider_transactions` | DataFrame of recent buy/sell transactions by company insiders |
| **Price Targets** | `stock.info['targetMeanPrice']`, `targetHighPrice` | Analyst consensus mean and high price targets |
| **Growth Estimates** | `stock.growth_estimates` *(if available)* | Forward earnings growth estimates by period (current Q, next Q, next year) |
| **Recent News** | `stock.news` | Array of recent news articles with title, summary, date, and URL |

> [!NOTE]
> All sentiment data fetches are individually wrapped in `try/except`. If a sub-object fails or returns empty, that component is **skipped** — it does not contribute a score, and the final result is re-normalised over available components.

---

## 2. Sentiment Components

### Component Overview

| # | Component | Max Weight | Data Source |
| :--- | :--- | :---: | :--- |
| 1 | EPS Estimate Revision | **30%** | `stock.eps_trend` |
| 2 | Promoter / Insider Holding | **25%** | `stock.major_holders` |
| 3 | Insider Transactions | **20%** | `stock.insider_transactions` |
| 4 | Analyst Price Target | **15%** | `stock.info` targets |
| 5 | Forward Growth Estimates | **10%** | `stock.growth_estimates` |

---

### 1. EPS Estimate Revision (30%)

**What it measures:** Whether Wall Street / analysts have been upgrading or cutting their earnings expectations for the current quarter over the last 60 days.

**Data source:** `stock.eps_trend` — a DataFrame where:
- Index = period labels: `"0q"` (current quarter), `"+1q"` (next quarter)
- Columns = `"current"`, `"7daysAgo"`, `"30daysAgo"`, `"60daysAgo"`, `"90daysAgo"`

**Formula:**
```
Revision % = (EPS_0q_current - EPS_0q_60daysAgo) / |EPS_0q_60daysAgo| × 100
```

**Rationale:** Analysts revising EPS upward signals improving business momentum and forthcoming positive earnings surprises. Downward cuts are a leading warning of deteriorating fundamentals.

**Scoring Table:**

| Revision (60-day) | Score | Signal |
| :--- | :---: | :--- |
| < −8% (significant cut) | **20** | ❌ EPS cut — analysts losing confidence |
| −8% to −2% (minor cut) | **45** | ⚠️ Minor EPS cut — watch next quarter |
| −2% to +5% (stable or minor upgrade) | **70** | ✅ EPS estimates stable |
| > +5% (meaningful upgrade) | **90** | ✅ EPS upgrade — positive earnings catalyst |

---

### 2. Promoter / Insider Holding (25%)

**What it measures:** The percentage of shares held by promoters and company insiders. High promoter holding indicates confidence in the business and aligns insider interest with shareholders.

**Data source:** `stock.major_holders` — a DataFrame where:
- Index = `"insidersPercentHeld"`, `"institutionsPercentHeld"`, etc.
- Column = `"Value"` (decimal format: `0.51` = 51%)

**Formula:**
```
Promoter % = major_holders.loc["insidersPercentHeld", "Value"] × 100
```

**Scoring Table:**

| Promoter / Insider Holding | Score | Signal |
| :--- | :---: | :--- |
| > 50% | **88** | ✅ Strong promoter holding — high skin in the game |
| 25%–50% | **65** | ✅ Moderate holding |
| < 25% | **40** | ⚠️ Low promoter holding — reduced alignment |

**Bonus (Informational only — not scored):** Institutional holding % is also extracted and displayed as context. High institutional interest (> 40%) often validates the investment thesis.

---

### 3. Insider Transactions (20%)

**What it measures:** Whether company insiders (directors, promoters, C-suite) have been net buyers or sellers of the stock recently. Insider buying is one of the strongest bullish signals; heavy selling is a red flag.

**Data source:** `stock.insider_transactions` — a DataFrame with columns:
- `"Transaction"` (or `"Text"`) — text like `"Sale"`, `"Purchase"`, `"Acquisition"`
- `"Value"` — transaction value in currency
- `"Shares"` — number of shares

**Classification logic:**
```
Sell keywords: "Sale", "Sold", "Sell"
Buy  keywords: "Purchase", "Buy", "Acquisition"
```

**Scoring — Value-weighted (preferred):**

| Condition | Score | Signal |
| :--- | :---: | :--- |
| Sell value > 3× Buy value | **25** | ❌ Heavy insider selling — insiders distributing |
| Buy value ≥ Sell value | **80** | ✅ Net insider buying — strong confidence signal |
| Mixed (some of both) | **55** | ⚠️ Mixed insider activity |

**Scoring — Count-based (fallback, when Value column is unavailable):**

| Condition | Score | Signal |
| :--- | :---: | :--- |
| Sell count > 2× Buy count | **30** | ❌ More sells than buys |
| Otherwise | **65** | ⚠️ Balanced or modest activity |

---

### 4. Analyst Price Target (15%)

**What it measures:** The gap between the current market price and the consensus analyst mean target. This signals whether analysts collectively believe the stock has room to run or is already overpriced.

**Data source:** `stock.info['targetMeanPrice']` and `stock.info['targetHighPrice']`

**Formula:**
```
Upside % = (Mean_Target - Current_Price) / Current_Price × 100
```

**Scoring Table:**

| Condition | Score | Signal |
| :--- | :---: | :--- |
| CMP > High Target × 1.05 (above even the bull case) | **20** | ❌ Trading above even highest analyst target |
| Upside < −10% (CMP well above mean) | **30** | ⚠️ Significantly above consensus — likely overvalued |
| Upside > 20% | **85** | ✅ Significant analyst upside |
| Upside 0%–20% | **65** | ✅ Reasonable upside to mean target |

> [!NOTE]
> In the **sentiment** scorer, analyst targets reflect how the market and analyst community perceive the stock — it is a *sentiment* signal, not a valuation score. The fundamental scorer (`score_fundamentals_v2`) also includes analyst targets independently for a valuation-adjusted view.

---

### 5. Forward Growth Estimates (10%)

**What it measures:** What analysts expect for EPS growth in the near future. This is forward-looking (unlike earnings growth in fundamentals, which is backward-looking historical data).

**Data source:** `stock.growth_estimates` — a DataFrame where:
- Index = `"0q"` (current Q), `"+1q"` (next Q), `"0y"` (current year), `"+1y"` (next year), `"+5y"` (5-year)
- Columns = `"stockTrend"`, `"indexTrend"`

**Scoring period priority:** Uses `+1y` (next year estimate) if available; falls back to `+1q`.

**Scoring Table:**

| Forward Growth Estimate | Score | Signal |
| :--- | :---: | :--- |
| > +15% | **85** | ✅ Strong growth expected |
| 0% to +15% | **65** | ✅ Positive growth outlook |
| −10% to 0% | **45** | ⚠️ Growth slowing — caution |
| < −10% | **25** | ❌ Earnings expected to decline |

---

## 3. Sentiment Score Formula

### Final Score Calculation

```
Sentiment_Score = Σ (component_score × component_weight) / Σ (component_weight_of_available_checks)
```

If **no component** has any data, a neutral score of **50** is returned with `LOW` confidence.

**Example (all 5 components present):**

```
Sentiment_Score = (EPS_Score×30 + Promoter_Score×25 + Insider_Score×20
                 + Target_Score×15 + Growth_Score×10) / 100
```

The result is rounded to the nearest integer (0–100).

### Confidence Level

Unlike the fundamental scorer (which uses data coverage %), sentiment confidence is based on the raw count of data sources that successfully returned data:

| Data Sources Found | Confidence |
| :--- | :--- |
| ≥ 4 | **HIGH** |
| 2–3 | **MEDIUM** |
| 0–1 | **LOW** |

---

### Composite Integration

The sentiment score is one of three pillars in the overall composite score:

| Pillar | Raw Scale | Scaled Max in Composite |
| :--- | :---: | :---: |
| **Technical** | 0–100 | **40 points** |
| **Fundamental** | 0–100 | **40 points** |
| **Sentiment** | 0–100 | **20 points** |

```
Composite Score = (Tech_Raw / 100 × 40) + (Fund_Raw / 100 × 40) + (Sent_Raw / 100 × 20)
```

---

## 4. Predictive Trend Score (separate indicator)

The **Predictive Trend Score** is an additional analysis that is **not part of the composite score**. It uses historical price returns across multiple timeframes to estimate where the stock is likely headed over the next 2–3 months.

### Trailing Return Periods

Returns are computed from closing price history:

| Period Label | Trading Days Used | Formula |
| :--- | :---: | :--- |
| **3 Days** | 3 | `(Price_today - Price_3d_ago) / Price_3d_ago × 100` |
| **1 Week** | 5 | Same pattern |
| **2 Weeks** | 10 | Same pattern |
| **1 Month** | 21 | Same pattern |
| **2 Months** | 42 | Same pattern |
| **3 Months** | 63 | Same pattern |
| **6 Months** | 126 | Same pattern |
| **1 Year** | Up to 252 | Same pattern |

If price history is shorter than the required lookback, that period returns `None` and defaults to `0.0` in scoring.

---

### Predictive Trend Components

| # | Component | Weight | What It Captures |
| :--- | :--- | :---: | :--- |
| 1 | Short-Term Momentum | **40%** | Performance over the last 1 month (avg of 3D, 1W, 2W, 1M) |
| 2 | Momentum Acceleration | **30%** | Whether recent (1M) is outperforming medium-term (2M + 3M avg) |
| 3 | Trend Consistency | **20%** | What fraction of the 8 periods are positive |
| 4 | Mean Reversion Potential | **10%** | Whether a long-term drop might fuel a snapback |

---

### Component Formulas

#### 1. Short-Term Momentum Score (40%)

```
short_mom   = (Return_3D + Return_1W + Return_2W + Return_1M) / 4
short_score = clamp(50 + (short_mom × 50/15), 0, 100)
```

*Interpretation: A 15% average short-term return maps to a score of 100. A −15% maps to 0. Neutral (0%) maps to 50.*

#### 2. Momentum Acceleration Score (30%)

```
med_avg      = (Return_2M + Return_3M) / 2
acceleration = Return_1M - med_avg
accel_score  = clamp(50 + (acceleration × 50/20), 0, 100)
```

*Interpretation: Positive acceleration (1M > 2–3M avg) scores above 50 — the stock is gathering speed. A +20% acceleration differential maps to 100.*

#### 3. Trend Consistency Score (20%)

```
consistency_ratio = count_of_positive_periods / 8
consist_score     = consistency_ratio × 100
```

*Interpretation: If 6 of 8 periods are positive, score = 75. All 8 positive = 100. All 8 negative = 0.*

#### 4. Mean Reversion Potential Score (10%)

```
long_drop       = (Return_6M + Return_1Y) / 2
reversion_ratio = clamp(-long_drop / 30, 0, 1)
reversion_score = reversion_ratio × 100
```

*Interpretation: A stock that has dropped 30%+ over 6M–1Y scores 100 on this component (maximum reversion potential). This component only contributes positively when the stock has fallen significantly — it is never a penalty.*

---

### Final Predictive Trend Score

```
Predictive_Trend = (short_score × 0.40) + (accel_score × 0.30)
                 + (consist_score × 0.20) + (reversion_score × 0.10)
```

Clamped to **0–100**, rounded to 1 decimal place.

### Predictive Trend Rating

| Score | Rating |
| :--- | :--- |
| ≥ 75 | **Strong Bullish 🟢** |
| 60–74 | **Moderately Bullish 🟢** |
| 40–59 | **Neutral / Mixed ⚪** |
| 25–39 | **Moderately Bearish 🟠** |
| < 25 | **Strong Bearish 🔴** |

> [!IMPORTANT]
> The Predictive Trend Score is a **pure price-momentum signal** — it tells you the direction the stock has been moving and whether that momentum is accelerating. It does **not** factor in fundamentals or valuation.

---

## 5. News Feed (Informational)

**Source:** `stock.news` — Yahoo Finance news array

**Filtering:** Only articles published within the **last 10 days** are included, sorted from newest to oldest.

**Fields extracted per article:**
- `title` — headline
- `summary` — brief description
- `url` — direct link to the article
- `date` — formatted as `"Apr 18, 2026"`

News is displayed in the UI as contextual information only. It does **not** affect any score.
