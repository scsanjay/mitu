# Fundamental Metrics Documentation

This document explains every fundamental metric used in MITU's fundamental scoring system — from the raw data sourced from Yahoo Finance, to computed intermediate metrics, and finally the weighted scoring formula used in `score_fundamentals_v2()`.

---

## 1. Base Metrics (from Yahoo Finance `stock.info`)

These are fetched directly from `yf.Ticker(ticker).info` — no calculation required.

| Metric | `info` Key | Description |
| :--- | :--- | :--- |
| **Trailing P/E** | `trailingPE` | Price divided by trailing twelve-month (TTM) earnings per share |
| **Price-to-Book** | `priceToBook` | Market price divided by book value per share |
| **Debt-to-Equity** | `debtToEquity` | Total debt as a percentage of equity (Yahoo returns this as %, e.g. `150` = 150%) |
| **Return on Equity** | `returnOnEquity` | Net income as a fraction of shareholders' equity (decimal, e.g. `0.20` = 20%) |
| **Revenue Growth** | `revenueGrowth` | YoY revenue growth as a decimal fraction (e.g. `0.12` = 12%) |
| **Earnings Growth** | `earningsGrowth` | TTM earnings growth as a decimal fraction (used as fallback) |
| **Mean Analyst Target** | `targetMeanPrice` | Consensus mean price target from covering analysts (₹) |
| **High Analyst Target** | `targetHighPrice` | The most optimistic analyst price target (₹) |
| **Sector** | `sector` | Yahoo's sector classification (e.g. `"Technology"`, `"Banking"`) |

---

## 2. Calculated Intermediate Metrics

These are computed inside `analyzer.py` using `yfinance` sub-objects beyond `stock.info`.

### EPS Growth (Year-over-Year)

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **EPS Growth (YoY)** | `stock.info.earningsGrowth` *(primary)* | Directly from Yahoo TTM earnings growth field |
| | `stock.earnings` DataFrame *(fallback)* | `(Latest_EPS − Prev_EPS) / |Prev_EPS|` — computed from annual earnings history |

**Logic:** If `earningsGrowth` is available in `info`, it is used as-is. Otherwise the function falls back to computing it from the annual earnings DataFrame sorted by date.

```
EPS Growth = (EPS_latest_year - EPS_prior_year) / |EPS_prior_year|
```

---

### PEG Ratio

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **PEG Ratio** | `stock.info.pegRatio` *(primary)* | Directly from Yahoo |
| | Computed *(fallback)* | `PE_Ratio / (EPS_Growth × 100)` |

**Condition:** PEG is only considered meaningful when both PE and EPS growth are positive. Negative PEG is excluded from scoring.

```
PEG = Trailing PE / (EPS Growth %)
```

*Example: PE = 25, EPS growth = 20% → PEG = 25 / 20 = 1.25*

---

### Earnings Growth (from Income Statement)

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **Net Profit Growth** | `stock.info.earningsGrowth` *(primary)* | TTM figure from Yahoo |
| | `stock.income_stmt` *(fallback)* | Computed from Net Income row in annual income statement |

```
Earnings Growth = (Net_Income_latest - Net_Income_prior) / |Net_Income_prior|
```

Additionally, a **multi-year trend history** is built (up to 3 years back) by comparing consecutive years in the income statement. This history feeds the trend consistency bonus/penalty in scoring.

---

## 3. Sector Benchmarks

The scoring system uses sector-specific reference values instead of absolute cutoffs. This prevents a bank stock (high leverage by nature) from being unfairly penalised, or a tech stock from being rated "cheap" at a PE of 30 when its sector average is 28.

### PE Benchmarks

| Sector | Reference PE |
| :--- | :---: |
| Technology | 28 |
| Healthcare | 35 |
| Consumer Defensive | 35 |
| Consumer Cyclical | 30 |
| Real Estate | 30 |
| Communication | 22 |
| Industrials | 25 |
| Financial Services | 18 |
| Banking | 14 |
| Energy | 14 |
| Utilities | 16 |
| Basic Materials | 15 |
| **Default** | **22** |

### Debt-to-Equity Benchmarks (as actual ratio, not %)

| Sector | Reference D/E |
| :--- | :---: |
| Technology | 0.3x |
| Healthcare | 0.4x |
| Consumer Defensive | 0.6x |
| Consumer Cyclical | 0.7x |
| Basic Materials | 0.7x |
| Energy | 0.8x |
| Industrials | 0.8x |
| Utilities | 1.2x |
| Real Estate | 1.5x |
| Financial Services | 8.0x *(banks borrow to lend)* |
| Banking | 8.0x *(banks borrow to lend)* |
| **Default** | **0.8x** |

> [!NOTE]
> Yahoo Finance returns `debtToEquity` as a percentage (e.g. `45.6` means 45.6%). Internally, the scorer divides by 100 to convert to a ratio before comparing with the sector benchmark.

---

## 4. Fundamental Score Formula

The fundamental score is calculated on a **0–100 scale** using up to **6 weighted components**. Each component is independently scored 0–100, then combined using a weighted average of **only the components for which data was available**.

### Component Weight Distribution

| # | Component | Max Weight | What It Measures |
| :--- | :--- | :---: | :--- |
| 1 | PE Ratio | **15%** | Sector-relative valuation |
| 2 | PB Ratio | **10%** | Asset-based valuation |
| 3 | Debt/Equity | **15%** | Balance sheet health (sector-aware) |
| 4 | ROE | **10%** | Capital efficiency |
| 5 | Revenue Growth | **10%** | Top-line expansion |
| 6 | Earnings Growth | **15%** | Bottom-line quality + trend consistency |
| 7 | PEG Ratio | **10%** | Growth-adjusted valuation |
| 8 | Analyst Target | **10%** | Market consensus upside |
| 9 | Position P&L *(optional)* | **5%** | Your entry price vs current price |
| | **Total (all present)** | **100%** | |

> [!IMPORTANT]
> If a metric is unavailable (e.g. Yahoo returns `None`), its check is **skipped entirely** — no score, no weight. The final score is re-normalised over the weights of checks that actually ran. This means missing data never artificially punishes or rewards a stock.

---

### Component Scoring Tables

#### 1. PE Ratio (15%)

Scored relative to the sector PE benchmark. `pe_ratio = Stock_PE / Sector_PE_Benchmark`.

| Relative PE | Score | Signal |
| :--- | :---: | :--- |
| pe_ratio < 0.70 (≥30% discount to sector) | **90** | ✅ Undervalued vs peers |
| 0.70 ≤ pe_ratio < 0.90 | **75** | ✅ Slightly below sector avg — fair value |
| 0.90 ≤ pe_ratio < 1.10 (±10% of sector) | **60** | ⚠️ In line with sector avg |
| 1.10 ≤ pe_ratio < 1.40 | **40** | ⚠️ Premium valuation |
| pe_ratio ≥ 1.40 (≥40% premium to sector) | **15** | ❌ Significantly overvalued vs peers |

#### 2. PB Ratio (10%)

Absolute thresholds — sector context is noted in commentary but not used for scoring.

| P/B | Score | Signal |
| :--- | :---: | :--- |
| PB < 1.0x | **85** | ✅ Trading near/below book value |
| 1.0x ≤ PB < 2.5x | **75** | ✅ Reasonable |
| 2.5x ≤ PB < 4.0x | **55** | ⚠️ Premium to book, needs strong ROE |
| 4.0x ≤ PB < 6.0x | **35** | ⚠️ Expensive on asset basis |
| PB ≥ 6.0x | **15** | ❌ Very expensive vs assets |

#### 3. Debt/Equity (15%)

Scored relative to sector D/E benchmark. `de_rel = (D/E ratio) / Sector_DE_Benchmark`.

> For **Banking / Financial Services**: D/E interpretation is entirely different (banks are inherently leveraged). These sectors receive a neutral score of **65** and commentary explaining the exception.

| Relative D/E | Score | Signal |
| :--- | :---: | :--- |
| de_rel < 0.50 (half the sector norm) | **90** | ✅ Very low leverage — strong balance sheet |
| 0.50 ≤ de_rel < 0.90 | **75** | ✅ Conservative leverage |
| 0.90 ≤ de_rel < 1.30 | **55** | ⚠️ Average for sector |
| 1.30 ≤ de_rel < 2.00 | **30** | ⚠️ Above-average leverage — watch interest coverage |
| de_rel ≥ 2.00 | **10** | ❌ High leverage vs sector |
| Banking / Fin. Services (any D/E) | **65** | ℹ️ Neutral — high leverage is structural |

#### 4. ROE — Return on Equity (10%)

| ROE | Score | Signal |
| :--- | :---: | :--- |
| ROE > 25% | **95** | ✅ Exceptional — world-class capital efficiency |
| 18% < ROE ≤ 25% | **80** | ✅ Strong |
| 12% < ROE ≤ 18% | **65** | ✅ Decent |
| 8% < ROE ≤ 12% | **45** | ⚠️ Weak — capital not deployed efficiently |
| 0% < ROE ≤ 8% | **25** | ❌ Very low |
| ROE ≤ 0% | **5** | ❌ Negative — destroying shareholder value |

#### 5. Revenue Growth (10%)

| YoY Revenue Growth | Score | Signal |
| :--- | :---: | :--- |
| > 20% | **90** | ✅ Strong |
| 12%–20% | **75** | ✅ Healthy |
| 5%–12% | **60** | ⚠️ Moderate |
| 0%–5% | **40** | ⚠️ Sluggish |
| < 0% | **15** | ❌ Declining |

#### 6. Earnings Growth (15%) — with Trend Adjustment

Base score is set by the latest YoY earnings growth, then a **trend adjustment** is applied based on the multi-year earnings history:

**Step 1 — Base Score:**

| YoY Earnings Growth | Base Score |
| :--- | :---: |
| > 20% | **90** |
| 10%–20% | **75** |
| 0%–10% | **50** |
| < 0% | **15** |

**Step 2 — Trend Adjustment** (applied to base score, capped at 0–100):

| Multi-Year History (≥ 2 years available) | Adjustment |
| :--- | :---: |
| All years consistently > 5% growth | **+10** |
| All years consistently declining (< 0%) | **−10** |
| Most recent year better than oldest | **+5** |
| Inconsistent / mixed | **0** |

```
Final_Earnings_Score = clamp(Base_Score + Trend_Adjustment, 0, 100)
```

#### 7. PEG Ratio (10%)

Only scored when PEG > 0 (i.e. both PE and earnings growth are positive).

| PEG | Score | Signal |
| :--- | :---: | :--- |
| 0 < PEG < 0.5 *(suspiciously low)* | **70** | ⚠️ Very low — verify earnings estimates |
| 0.5 ≤ PEG < 1.0 | **88** | ✅ Attractive — undervalued vs growth |
| 1.0 ≤ PEG < 1.5 | **70** | ✅ Fair |
| 1.5 ≤ PEG < 2.5 | **45** | ⚠️ Elevated — growth premium priced in |
| PEG ≥ 2.5 | **20** | ❌ Expensive vs growth |

#### 8. Analyst Target Upside (10%)

| Condition | Score | Signal |
| :--- | :---: | :--- |
| CMP > Highest analyst target | **15** | ❌ Above even the most optimistic target |
| Upside > 25% to mean target | **90** | ✅ Strong upside |
| 10%–25% upside | **70** | ✅ Reasonable upside |
| 0%–10% upside | **50** | ⚠️ Limited upside |
| CMP above mean target (downside) | **25** | ⚠️ Trading above consensus |

#### 9. Position P&L — optional (5%)

Only computed when a `buy_price` is passed to the function. Not scored in the default `analyze_stock()` flow.

| P&L from Buy Price | Score | Signal |
| :--- | :---: | :--- |
| > +20% | **85** | ✅ Strong gain |
| 0%–+20% | **65** | ✅ In profit |
| 0% to −10% | **45** | ⚠️ Small loss |
| −10% to −20% | **25** | ⚠️ Approaching stop-loss territory |
| < −20% | **10** | ❌ Significant loss — review thesis |

---

### Final Score Calculation

```
Fund_Score = Σ (component_score × component_weight) / Σ (component_weight_of_available_checks)
```

Expanded example (all components present):

```
Fund_Score = (PE_Score×15 + PB_Score×10 + DE_Score×15 + ROE_Score×10
            + Rev_Score×10 + Earn_Score×15 + PEG_Score×10 + Target_Score×10
            + PnL_Score×5) / 100
```

The result is a value between **0 and 100**, rounded to the nearest integer.

**Confidence Level** is derived from how much of the maximum possible weight (100) was actually covered:

| Data Coverage | Confidence |
| :--- | :--- |
| ≥ 75% | **HIGH** |
| 50%–74% | **MEDIUM** |
| < 50% | **LOW** |

---

### Composite Integration

The fundamental score is one of three pillars in the overall composite score:

| Pillar | Raw Scale | Scaled Max in Composite |
| :--- | :---: | :---: |
| **Technical** | 0–100 | **40 points** |
| **Fundamental** | 0–100 | **40 points** |
| **Sentiment** | 0–100 | **20 points** |

```
Composite Score = (Tech_Raw / 100 × 40) + (Fund_Raw / 100 × 40) + (Sent_Raw / 100 × 20)
```

### Classification Thresholds

| Composite Score | Classification |
| :--- | :--- |
| ≥ 65 | **Hold** ✅ |
| 45–64 | **Warning** ⚠️ |
| < 45 | **Sell** ❌ |
