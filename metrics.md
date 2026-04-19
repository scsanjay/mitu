# MITU Stock Analysis — Metrics Documentation

This document is a **comprehensive reference guide** for every metric, indicator, and scoring methodology used in the MITU Stock Analysis engine. It consolidates the Technical, Fundamental, Sentiment, and Predictive Trend scoring systems into a single document.

---

## Table of Contents

1. [Scoring Architecture](#1-scoring-architecture)
2. [Technical Metrics (50%)](#2-technical-metrics-weight-50)
3. [Fundamental Metrics (35%)](#3-fundamental-metrics-weight-35)
4. [Sentiment Metrics (15%)](#4-sentiment-metrics-weight-15)
5. [Predictive Trend Score (Independent)](#5-predictive-trend-score-independent)
6. [News Feed (Informational)](#6-news-feed-informational)
7. [Design Philosophy & Limitations](#7-design-philosophy--limitations)

---

## 1. Scoring Architecture

MITU uses a multi-layered scoring system to provide a holistic view of a stock's health and momentum. The primary indicator is the **Composite Score**, which is supported by three core pillars and one independent momentum signal.

### Composite Score Calculation

The Composite Score is a weighted average of three raw scores, each independently scored on a 0–100 scale, then normalised into a 100-point composite:

| Pillar | Raw Scale | Weight in Composite | Contribution |
| :--- | :--- | :--- | :--- |
| **Technical** | 0–100 | **50%** | 50 points |
| **Fundamental** | 0–100 | **35%** | 35 points |
| **Sentiment** | 0–100 | **15%** | 15 points |
| **Total** | | **100%** | **100 points** |

**Formula:**
```
Composite Score = (Tech_Raw × 0.50) + (Fund_Raw × 0.35) + (Sent_Raw × 0.15)
```

### Classification Thresholds

Based on the Composite Score, stocks are classified as follows:

| Composite Score | Classification |
| :--- | :--- |
| ≥ 70 | **Hold** ✅ |
| 50–69 | **Warning** ⚠️ |
| < 50 | **Sell** ❌ |

### Missing Data Handling

All three scorers (Technical, Fundamental, Sentiment) handle missing data gracefully:
- If a metric is unavailable (Yahoo returns `None` or API fails), that component is **skipped entirely** — no score, no weight.
- The final score is **re-normalised** over the weights of checks that actually ran.
- Missing data never artificially punishes or rewards a stock.

---

## 2. Technical Metrics (Weight: 50%)

The technical score assesses trend structure, momentum, and volume conviction using 1 year of daily OHLCV history from Yahoo Finance.

### 2.1 Base Data (from Yahoo Finance)

| Metric | Source | Description |
| :--- | :--- | :--- |
| **Close** | `hist['Close']` | Daily closing price |
| **High** | `hist['High']` | Daily high price |
| **Low** | `hist['Low']` | Daily low price |
| **Volume** | `hist['Volume']` | Number of shares traded in the session |

### 2.2 Calculated Technical Indicators

All indicators are computed from the base OHLCV data using the `ta` (Technical Analysis) library.

#### Moving Averages

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **EMA 20** | Exponential Moving Average, 20-day window | Short-term trend. Reacts quickly to price changes. |
| **EMA 50** | Exponential Moving Average, 50-day window | Medium-term trend direction. |
| **SMA 100** | Simple Moving Average, 100-day window | India-specific mid-term anchor. Smooths out 2–3 month noise. |
| **SMA 200** | Simple Moving Average, 200-day window | Long-term trend baseline. The most important support/resistance level for medium-term holders. |

**Stack Order Check:** A "healthy" market structure has `EMA20 > EMA50 > SMA100`. When all MAs are aligned in this order AND price is above all of them, the trend is strongly bullish.

#### MACD (Moving Average Convergence Divergence)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **MACD Line** | EMA(12) − EMA(26) of Close | Measures the gap between fast and slow EMAs. Positive = bullish momentum. |
| **Signal Line** | EMA(9) of the MACD Line | Smoothed version of MACD. Crossovers generate buy/sell signals. |
| **MACD Histogram** | MACD Line − Signal Line | Visualizes momentum acceleration. Increasing histogram = strengthening momentum. |

**Key states:**
- **MACD > Signal, both > 0** → Strong bullish momentum
- **MACD > Signal, both < 0** → Early recovery, not confirmed
- **MACD < Signal, both < 0, histogram worsening** → Strong bearish, accelerating sell-off

#### RSI (Relative Strength Index)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **RSI (14)** | 14-period RSI of Close | Momentum oscillator (0–100). Measures speed and change of price movements. |
| **RSI 5-day Trend** | `RSI_today − RSI_5_days_ago` | Direction of momentum — is RSI rising or falling over the past week? |

**Interpretation (medium-term holding, differs from day-trading):**
- **55–70**: Momentum sweet zone — ideal for medium-term hold
- **50–55**: Mild positive, bulls slightly in control
- **40–50**: Weak zone. RSI trend direction matters — rising RSI gets slightly more credit
- **30–40**: Downtrend momentum dominant. Not a buy signal for medium-term
- **< 30**: Deep oversold — severe weakness, avoid catching the falling knife
- **70–80**: Overbought. Consider trimming
- **> 80**: Extremely overbought — high reversal risk

#### Volume Analysis

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **Volume Ratio** | `Today's Volume / 20-day Average Volume` | Measures if today's volume is above or below normal. Confirms conviction behind price moves. |

**Interpretation (combined with price direction):**
- Price ↑ + Vol ≥ 1.5x → Strong conviction buying
- Price ↑ + Vol ≥ 1.0x → Normal bullish session
- Price ↑ + Vol < 0.7x → Weak conviction rally (suspicious)
- Price ↓ + Vol ≥ 1.5x → Distribution / heavy sell-off
- Price ↓ + Vol ≥ 1.0x → Mild selling pressure
- Price ↓ + Vol < 0.7x → Low volume dip, inconclusive

#### 52-Week Range Position

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **52W High** | Rolling 252-day max of High | Highest price in the past year |
| **52W Low** | Rolling 252-day min of Low | Lowest price in the past year |
| **52W Position** | `(Close − 52W_Low) / (52W_High − 52W_Low) × 100` | Where the stock sits in its annual range (0% = at low, 100% = at high) |
| **% from 52W High** | `(52W_High − Close) / 52W_High × 100` | How far the stock has fallen from its peak |

#### ATR (Average True Range)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **ATR (14)** | 14-period ATR of High, Low, Close | Measures daily volatility. Used for stop-loss placement, not for scoring. |

**Stop-loss suggestion:** `Current Price − (2 × ATR)` — gives the stock room to breathe while protecting against sharp drops.

### 2.3 Technical Score Formula

The technical score is calculated on a **0–100 scale** using 5 weighted components. Each component is independently scored 0–100, then combined.

#### Component Weight Distribution

| # | Component | Weight | What It Captures |
| :--- | :--- | :---: | :--- |
| 1 | MA Stack | **30%** | Trend structure and alignment |
| 2 | MACD | **25%** | Momentum direction and acceleration |
| 3 | RSI | **20%** | Momentum strength and zone |
| 4 | Volume | **15%** | Conviction behind price moves |
| 5 | 52W Position | **10%** | Relative strength within the annual range |

#### 1. MA Stack Scoring (30%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Price > all 4 MAs AND EMA20 > EMA50 > SMA100 | **95** | ✅ Full bullish stack — MAs aligned |
| Price > all 4 MAs (MAs not aligned) | **80** | ✅ Above all MAs |
| Price > 3 MAs including SMA200 | **65** | ⚠️ Mild pullback in uptrend |
| Price > 2 MAs including SMA200 | **50** | ⚠️ Trend intact but weakening |
| Price > 1 MA including SMA200 | **35** | ⚠️ At risk, watch closely |
| Price below all MAs, ≤ 10% gap from SMA200 | **25** | ❌ Bearish structure |
| Price below all MAs, > 10% gap from SMA200 | **10** | ❌ Deep downtrend |
| Below SMA200 (other combos) | **30** | ❌ Long-term trend broken |

#### 2. MACD Scoring (25%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Both > 0, MACD > Signal, histogram improving | **95** | ✅ Strong accelerating momentum |
| Both > 0, MACD > Signal | **80** | ✅ Positive momentum |
| Both > 0, MACD < Signal, histogram worsening | **45** | ⚠️ Momentum fading |
| Both < 0, MACD > Signal, histogram improving | **55** | ⚠️ Early recovery signal |
| Both < 0, MACD > Signal | **45** | ⚠️ Weak recovery attempt |
| Both < 0, MACD < Signal | **20** | ❌ Bearish |
| Both < 0, MACD < Signal, histogram worsening | **10** | ❌ Strong sell signal |
| Mixed / other | **40** | ⚠️ Mixed signals |

#### 3. RSI Scoring (20%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| 55 ≤ RSI ≤ 70 | **85** | ✅ Momentum sweet zone |
| 50 ≤ RSI < 55 | **65** | ✅ Mild positive |
| 70 < RSI ≤ 80 | **55** | ⚠️ Overbought |
| RSI > 80 | **30** | ⚠️ Extremely overbought |
| 40 ≤ RSI < 50, rising (+3 in 5d) | **45** | ⚠️ Below 50 but recovering |
| 40 ≤ RSI < 50, flat/falling | **35** | ⚠️ Weak momentum |
| 30 ≤ RSI < 40 | **25** | ❌ Downtrend momentum |
| RSI < 30 | **15** | ❌ Deeply oversold, avoid |

#### 4. Volume Scoring (15%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Price ↑, Volume ≥ 1.5x avg | **90** | ✅ Strong conviction buying |
| Price ↑, Volume ≥ 1.0x avg | **70** | ✅ Normal bullish volume |
| Price ↑, Volume < 0.7x avg | **45** | ⚠️ Weak conviction rally |
| Price ↓, Volume ≥ 1.5x avg | **15** | ❌ Distribution |
| Price ↓, Volume ≥ 1.0x avg | **35** | ⚠️ Mild selling pressure |
| Price ↓, Volume < 0.7x avg | **55** | ℹ️ Inconclusive |

#### 5. 52-Week Position Scoring (10%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Position ≥ 75% | **85** | ✅ Strong relative strength |
| Position ≥ 50% | **65** | ✅ Mid-upper range |
| Position ≥ 30% | **40** | ⚠️ Underperforming |
| Position < 30% | **20** | ❌ Near 52W low |

#### Final Technical Score Calculation

```
Tech Score = (MA_Score × 30 + MACD_Score × 25 + RSI_Score × 20 + Vol_Score × 15 + 52W_Score × 10) / 100
```

The result is a value between **0 and 100**, rounded to the nearest integer.

---

## 3. Fundamental Metrics (Weight: 35%)

The fundamental score evaluates valuation, financial health, and growth quality. It is **sector-aware**, comparing metrics against specific industry benchmarks.

### 3.1 Base Data (from Yahoo Finance `stock.info`)

| Metric | `info` Key | Description |
| :--- | :--- | :--- |
| **Trailing P/E** | `trailingPE` | Price divided by trailing twelve-month (TTM) earnings per share |
| **Price-to-Book** | `priceToBook` | Market price divided by book value per share |
| **Debt-to-Equity** | `debtToEquity` | Total debt as a percentage of equity (Yahoo returns as %, e.g. `150` = 150%) |
| **Return on Equity** | `returnOnEquity` | Net income as a fraction of shareholders' equity (decimal, e.g. `0.20` = 20%) |
| **Revenue Growth** | `revenueGrowth` | YoY revenue growth as a decimal fraction (e.g. `0.12` = 12%) |
| **Earnings Growth** | `earningsGrowth` | TTM earnings growth as a decimal fraction (used as fallback) |
| **Mean Analyst Target** | `targetMeanPrice` | Consensus mean price target from covering analysts (₹) |
| **High Analyst Target** | `targetHighPrice` | The most optimistic analyst price target (₹) |
| **Sector** | `sector` | Yahoo's sector classification (e.g. `"Technology"`, `"Banking"`) |

### 3.2 Calculated Intermediate Metrics

#### EPS Growth (Year-over-Year)

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **EPS Growth (YoY)** | `stock.info.earningsGrowth` *(primary)* | Directly from Yahoo TTM earnings growth field |
| | `stock.earnings` DataFrame *(fallback)* | `(Latest_EPS − Prev_EPS) / |Prev_EPS|` — computed from annual earnings history |

**Logic:** If `earningsGrowth` is available in `info`, it is used as-is. Otherwise the function falls back to computing it from the annual earnings DataFrame sorted by date.

```
EPS Growth = (EPS_latest_year - EPS_prior_year) / |EPS_prior_year|
```

#### PEG Ratio

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **PEG Ratio** | `stock.info.pegRatio` *(primary)* | Directly from Yahoo |
| | Computed *(fallback)* | `PE_Ratio / (EPS_Growth × 100)` |

**Condition:** PEG is only considered meaningful when both PE and EPS growth are positive. Negative PEG is excluded from scoring.

```
PEG = Trailing PE / (EPS Growth %)
```

*Example: PE = 25, EPS growth = 20% → PEG = 25 / 20 = 1.25*

#### Earnings Growth (from Income Statement)

| Metric | Source | Formula |
| :--- | :--- | :--- |
| **Net Profit Growth** | `stock.info.earningsGrowth` *(primary)* | TTM figure from Yahoo |
| | `stock.income_stmt` *(fallback)* | Computed from Net Income row in annual income statement |

```
Earnings Growth = (Net_Income_latest - Net_Income_prior) / |Net_Income_prior|
```

Additionally, a **multi-year trend history** is built (up to 3 years back) by comparing consecutive years in the income statement. This history feeds the trend consistency bonus/penalty in scoring.

### 3.3 Sector Benchmarks

The scoring system uses sector-specific reference values instead of absolute cutoffs. This prevents a bank stock (high leverage by nature) from being unfairly penalised, or a tech stock from being rated "cheap" at a PE of 30 when its sector average is 28.

#### PE Benchmarks

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

#### Debt-to-Equity Benchmarks (as actual ratio, not %)

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

> **Note:** Yahoo Finance returns `debtToEquity` as a percentage (e.g. `45.6` means 45.6%). Internally, the scorer divides by 100 to convert to a ratio before comparing with the sector benchmark.

### 3.4 Fundamental Score Formula

The fundamental score is calculated on a **0–100 scale** using up to **9 weighted components**. Each component is independently scored 0–100, then combined using a weighted average of **only the components for which data was available**.

#### Component Weight Distribution

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

> **Important:** If a metric is unavailable (e.g. Yahoo returns `None`), its check is **skipped entirely** — no score, no weight. The final score is re-normalised over the weights of checks that actually ran. This means missing data never artificially punishes or rewards a stock.

#### Component Scoring Tables

##### 1. PE Ratio (15%)

Scored relative to the sector PE benchmark. `pe_ratio = Stock_PE / Sector_PE_Benchmark`.

| Relative PE | Score | Signal |
| :--- | :---: | :--- |
| pe_ratio < 0.70 (≥30% discount to sector) | **90** | ✅ Undervalued vs peers |
| 0.70 ≤ pe_ratio < 0.90 | **75** | ✅ Slightly below sector avg — fair value |
| 0.90 ≤ pe_ratio < 1.10 (±10% of sector) | **60** | ⚠️ In line with sector avg |
| 1.10 ≤ pe_ratio < 1.40 | **40** | ⚠️ Premium valuation |
| pe_ratio ≥ 1.40 (≥40% premium to sector) | **15** | ❌ Significantly overvalued vs peers |

##### 2. PB Ratio (10%)

Absolute thresholds — sector context is noted in commentary but not used for scoring.

| P/B | Score | Signal |
| :--- | :---: | :--- |
| PB < 1.0x | **85** | ✅ Trading near/below book value |
| 1.0x ≤ PB < 2.5x | **75** | ✅ Reasonable |
| 2.5x ≤ PB < 4.0x | **55** | ⚠️ Premium to book, needs strong ROE |
| 4.0x ≤ PB < 6.0x | **35** | ⚠️ Expensive on asset basis |
| PB ≥ 6.0x | **15** | ❌ Very expensive vs assets |

##### 3. Debt/Equity (15%)

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

##### 4. ROE — Return on Equity (10%)

| ROE | Score | Signal |
| :--- | :---: | :--- |
| ROE > 25% | **95** | ✅ Exceptional — world-class capital efficiency |
| 18% < ROE ≤ 25% | **80** | ✅ Strong |
| 12% < ROE ≤ 18% | **65** | ✅ Decent |
| 8% < ROE ≤ 12% | **45** | ⚠️ Weak — capital not deployed efficiently |
| 0% < ROE ≤ 8% | **25** | ❌ Very low |
| ROE ≤ 0% | **5** | ❌ Negative — destroying shareholder value |

##### 5. Revenue Growth (10%)

| YoY Revenue Growth | Score | Signal |
| :--- | :---: | :--- |
| > 20% | **90** | ✅ Strong |
| 12%–20% | **75** | ✅ Healthy |
| 5%–12% | **60** | ⚠️ Moderate |
| 0%–5% | **40** | ⚠️ Sluggish |
| < 0% | **15** | ❌ Declining |

##### 6. Earnings Growth (15%) — with Trend Adjustment

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

##### 7. PEG Ratio (10%)

Only scored when PEG > 0 (i.e. both PE and earnings growth are positive).

| PEG | Score | Signal |
| :--- | :---: | :--- |
| 0 < PEG < 0.5 *(suspiciously low)* | **70** | ⚠️ Very low — verify earnings estimates |
| 0.5 ≤ PEG < 1.0 | **88** | ✅ Attractive — undervalued vs growth |
| 1.0 ≤ PEG < 1.5 | **70** | ✅ Fair |
| 1.5 ≤ PEG < 2.5 | **45** | ⚠️ Elevated — growth premium priced in |
| PEG ≥ 2.5 | **20** | ❌ Expensive vs growth |

##### 8. Analyst Target Upside (10%)

| Condition | Score | Signal |
| :--- | :---: | :--- |
| CMP > Highest analyst target | **15** | ❌ Above even the most optimistic target |
| Upside > 25% to mean target | **90** | ✅ Strong upside |
| 10%–25% upside | **70** | ✅ Reasonable upside |
| 0%–10% upside | **50** | ⚠️ Limited upside |
| CMP above mean target (downside) | **25** | ⚠️ Trading above consensus |

##### 9. Position P&L — optional (5%)

Only computed when a `buy_price` is passed to the function. Not scored in the default `analyze_stock()` flow.

| P&L from Buy Price | Score | Signal |
| :--- | :---: | :--- |
| > +20% | **85** | ✅ Strong gain |
| 0%–+20% | **65** | ✅ In profit |
| 0% to −10% | **45** | ⚠️ Small loss |
| −10% to −20% | **25** | ⚠️ Approaching stop-loss territory |
| < −20% | **10** | ❌ Significant loss — review thesis |

#### Final Fundamental Score Calculation

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

#### Confidence Level

Confidence is derived from how much of the maximum possible weight (100) was actually covered:

| Data Coverage | Confidence |
| :--- | :--- |
| ≥ 75% | **HIGH** |
| 50%–74% | **MEDIUM** |
| < 50% | **LOW** |

---

## 4. Sentiment Metrics (Weight: 15%)

Sentiment captures lead indicators from analysts, insiders, and institutional players.

### 4.1 Base Data (from Yahoo Finance)

| Data Object | `yfinance` Attribute | Description |
| :--- | :--- | :--- |
| **EPS Trend** | `stock.eps_trend` | DataFrame of analyst EPS estimates across time windows (current, 7d ago, 30d ago, 60d ago, 90d ago) |
| **Major Holders** | `stock.major_holders` | DataFrame with insider/promoter and institutional holding percentages |
| **Insider Transactions** | `stock.insider_transactions` | DataFrame of recent buy/sell transactions by company insiders |
| **Price Targets** | `stock.info['targetMeanPrice']`, `targetHighPrice` | Analyst consensus mean and high price targets |
| **Growth Estimates** | `stock.growth_estimates` *(if available)* | Forward earnings growth estimates by period (current Q, next Q, next year) |
| **Recent News** | `stock.news` | Array of recent news articles with title, summary, date, and URL |

> **Note:** All sentiment data fetches are individually wrapped in `try/except`. If a sub-object fails or returns empty, that component is **skipped** — it does not contribute a score, and the final result is re-normalised over available components.

### 4.2 Sentiment Components

#### Component Overview

| # | Component | Max Weight | Data Source |
| :--- | :--- | :---: | :--- |
| 1 | EPS Estimate Revision | **30%** | `stock.eps_trend` |
| 2 | Promoter / Insider Holding | **25%** | `stock.major_holders` |
| 3 | Insider Transactions | **20%** | `stock.insider_transactions` |
| 4 | Analyst Price Target | **15%** | `stock.info` targets |
| 5 | Forward Growth Estimates | **10%** | `stock.growth_estimates` |

##### 1. EPS Estimate Revision (30%)

**What it measures:** Whether analysts have been upgrading or cutting their earnings expectations for the current quarter over the last 60 days.

**Data source:** `stock.eps_trend` — a DataFrame where:
- Index = period labels: `"0q"` (current quarter), `"+1q"` (next quarter)
- Columns = `"current"`, `"7daysAgo"`, `"30daysAgo"`, `"60daysAgo"`, `"90daysAgo"`

**Formula:**
```
Revision % = (EPS_0q_current - EPS_0q_60daysAgo) / |EPS_0q_60daysAgo| × 100
```

**Rationale:** Analysts revising EPS upward signals improving business momentum. Downward cuts are a leading warning of deteriorating fundamentals.

**Scoring:**

| Revision (60-day) | Score | Signal |
| :--- | :---: | :--- |
| < −8% (significant cut) | **20** | ❌ EPS cut — analysts losing confidence |
| −8% to −2% (minor cut) | **45** | ⚠️ Minor EPS cut — watch next quarter |
| −2% to +5% (stable or minor upgrade) | **70** | ✅ EPS estimates stable |
| > +5% (meaningful upgrade) | **90** | ✅ EPS upgrade — positive earnings catalyst |

##### 2. Promoter / Insider Holding (25%)

**What it measures:** The percentage of shares held by promoters and company insiders. High promoter holding indicates confidence in the business and aligns insider interest with shareholders.

**Data source:** `stock.major_holders` where `insidersPercentHeld` value is in decimal format (e.g. `0.51` = 51%).

**Scoring:**

| Promoter / Insider Holding | Score | Signal |
| :--- | :---: | :--- |
| > 50% | **88** | ✅ Strong promoter holding — high skin in the game |
| 25%–50% | **65** | ✅ Moderate holding |
| < 25% | **40** | ⚠️ Low promoter holding — reduced alignment |

**Bonus (Informational only — not scored):** Institutional holding % is also extracted and displayed as context.

##### 3. Insider Transactions (20%)

**What it measures:** Whether company insiders have been net buyers or sellers of the stock recently.

**Data source:** `stock.insider_transactions` — DataFrame with `"Transaction"` (or `"Text"`) and `"Value"` columns.

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

##### 4. Analyst Price Target (15%)

**What it measures:** The gap between the current market price and the consensus analyst mean target.

**Formula:**
```
Upside % = (Mean_Target - Current_Price) / Current_Price × 100
```

**Scoring:**

| Condition | Score | Signal |
| :--- | :---: | :--- |
| CMP > High Target × 1.05 (above even the bull case) | **20** | ❌ Trading above even highest analyst target |
| Upside < −10% (CMP well above mean) | **30** | ⚠️ Significantly above consensus — likely overvalued |
| Upside > 20% | **85** | ✅ Significant analyst upside |
| Upside 0%–20% | **65** | ✅ Reasonable upside to mean target |

> **Note:** In the **sentiment** scorer, analyst targets reflect how the market and analyst community perceive the stock — it is a *sentiment* signal, not a valuation score. The fundamental scorer also includes analyst targets independently for a valuation-adjusted view.

##### 5. Forward Growth Estimates (10%)

**What it measures:** What analysts expect for EPS growth in the near future (forward-looking, unlike earnings growth in fundamentals which is backward-looking).

**Data source:** `stock.growth_estimates` where index = `"0q"`, `"+1q"`, `"0y"`, `"+1y"`, `"+5y"` and columns = `"stockTrend"`, `"indexTrend"`.

**Scoring period priority:** Uses `+1y` (next year estimate) if available; falls back to `+1q`.

**Scoring:**

| Forward Growth Estimate | Score | Signal |
| :--- | :---: | :--- |
| > +15% | **85** | ✅ Strong growth expected |
| 0% to +15% | **65** | ✅ Positive growth outlook |
| −10% to 0% | **45** | ⚠️ Growth slowing — caution |
| < −10% | **25** | ❌ Earnings expected to decline |

### 4.3 Sentiment Score Formula

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

#### Confidence Level

Unlike the fundamental scorer (which uses data coverage %), sentiment confidence is based on the raw count of data sources that successfully returned data:

| Data Sources Found | Confidence |
| :--- | :--- |
| ≥ 4 | **HIGH** |
| 2–3 | **MEDIUM** |
| 0–1 | **LOW** |

---

## 5. Predictive Trend Score (Independent)

The **Predictive Trend Score** is a **separate, standalone signal** — it does **not** contribute to the Composite Score. Its purpose is to answer:

> *"Based purely on how this stock has been moving, where is it likely headed over the next 2–3 months?"*

### Key Differences vs Composite Score

| | **Composite Score** | **Predictive Trend Score** |
| :--- | :--- | :--- |
| Purpose | Overall stock health (hold/warn/sell) | Direction of momentum (next 2–3 months) |
| Inputs | Technicals + Fundamentals + Sentiment | Price returns only (8 timeframes) |
| Scale | 0–100 → weighted 50+35+15 pts | 0–100 directly |
| Affects classification? | ✅ Yes | ❌ No |
| Displayed as | Composite score + label | Rating badge (Bullish / Bearish etc.) |

### 5.1 Input: Trailing Price Returns

Returns are computed from 1 year of daily closing price history. Each period compares today's close against the close *N trading days ago*.

**Formula:**
```
Return(period) = (Close_today - Close_N_days_ago) / Close_N_days_ago × 100
```

| Period Label | Trading Days (N) | Approx Calendar Time |
| :--- | :---: | :--- |
| `3D` | 3 | ~3 trading days |
| `1W` | 5 | 1 week |
| `2W` | 10 | 2 weeks |
| `1M` | 21 | 1 month |
| `2M` | 42 | 2 months |
| `3M` | 63 | 3 months |
| `6M` | 126 | 6 months |
| `1Y` | up to 252 | 1 year |

> **Note:** If price history is shorter than the required lookback (e.g. a recently listed stock), that period returns `None` and defaults to `0.0` in the calculation.

### 5.2 Score Components

The final score is built from **4 weighted components**, each independently scored 0–100.

#### Weight Distribution

| # | Component | Weight | What It Asks |
| :--- | :--- | :---: | :--- |
| 1 | Short-Term Momentum | **30%** | Is the stock rising over the last 3 months? |
| 2 | Momentum Acceleration | **25%** | Is it moving *faster* recently than before? |
| 3 | Trend Consistency | **25%** | Is it positive across most timeframes? |
| 4 | Mean Reversion Potential | **20%** | Could a big drop trigger a technical bounce? |

#### Component 1 — Short-Term Momentum (30%)

**What it captures:** Average price performance over the recent past (2W through 3M). A stock rising consistently over weeks to months is likely still in momentum.

**Formula:**
```
short_mom   = (Return_2W + Return_1M + Return_2M + Return_3M) / 4
short_score = clamp(50 + (short_mom × 50/15), 0, 100)
```

**Calibration:**
- `+15%` average short-term return → score = **100**
- `0%` (flat) → score = **50**
- `−15%` average → score = **0**

| Average Short-Term Return | Approx Score | Meaning |
| :--- | :---: | :--- |
| > +15% | ~100 | Strong upward momentum |
| +8% to +15% | 75–100 | Healthy momentum |
| +2% to +8% | 55–75 | Mild positive drift |
| −2% to +2% | 43–57 | Essentially flat |
| −8% to −2% | 25–43 | Mild selling pressure |
| < −15% | ~0 | Strong downward momentum |

#### Component 2 — Momentum Acceleration (25%)

**What it captures:** Whether the stock is *gaining speed* relative to its medium-term average. A stock up 5% in the last month but only 2% average over 2–3 months is *accelerating*.

**Formula:**
```
med_avg      = (Return_2M + Return_3M) / 2
acceleration = Return_1M − med_avg
accel_score  = clamp(50 + (acceleration × 50/20), 0, 100)
```

**Calibration:**
- Acceleration of `+20%` → score = **100**
- Acceleration of `0%` → score = **50**
- Acceleration of `−20%` → score = **0**

| 1M vs Medium-Term | Approx Score | Meaning |
| :--- | :---: | :--- |
| 1M >> med avg (+20%) | ~100 | Sharply accelerating — breakout momentum |
| 1M > med avg (+10%) | ~75 | Gently accelerating |
| 1M ≈ med avg | ~50 | Cruise control — steady pace |
| 1M < med avg (−10%) | ~25 | Decelerating — losing steam |
| 1M << med avg (−20%) | ~0 | Sharp deceleration — trend reversal risk |

#### Component 3 — Trend Consistency (25%)

**What it captures:** Whether the stock is positive across *most* timeframes, not just one.

**Formula:**
```
positive_periods  = count of periods where Return > 0
consistency_ratio = positive_periods / 8
consist_score     = consistency_ratio × 100
```

| Positive Periods (out of 8) | Score | Meaning |
| :--- | :---: | :--- |
| 8 / 8 | **100** | Rising across every timeframe |
| 7 / 8 | **87** | Strongly consistent uptrend |
| 6 / 8 | **75** | Broadly positive |
| 5 / 8 | **62** | Mild positive bias |
| 4 / 8 | **50** | Neutral — equally positive and negative |
| 3 / 8 | **37** | More negative than positive |
| 2 / 8 | **25** | Broadly weak |
| 1 / 8 | **12** | Almost universally falling |
| 0 / 8 | **0** | All timeframes negative — strong downtrend |

#### Component 4 — Mean Reversion Potential (20%)

**What it captures:** Whether the stock has fallen so much over 6M and 1Y that a *technical bounce* is plausible.

> **Important:** This component is **one-directional**. It only adds points when a stock has fallen significantly. It does **not** penalise stocks in an uptrend — those simply score 0 on this component.

**Formula:**
```
long_drop       = (Return_6M + Return_1Y) / 2
reversion_ratio = clamp(−long_drop / 30, 0, 1)
reversion_score = reversion_ratio × 100
```

**Calibration:**
- Average 6M + 1Y drop of `−30%` or more → score = **100** (maximum rebound potential)
- Drop of `−15%` → score = **50**
- Drop of `0%` or gain → score = **0** (no reversion expected)

| Avg 6M + 1Y Return | Score | Meaning |
| :--- | :---: | :--- |
| ≤ −30% | **100** | Deep in distress — high snap-back potential |
| −20% | **67** | Significant underperformance |
| −15% | **50** | Moderate correction territory |
| −5% | **17** | Minor pullback — small reversion potential |
| 0% or positive | **0** | No mean-reversion upside to exploit |

### 5.3 Final Predictive Trend Score

```
Predictive_Trend_Score = (short_score × 0.30) + (accel_score × 0.25)
                       + (consist_score × 0.25) + (reversion_score × 0.20)
```

Clamped to **[0, 100]**, rounded to 1 decimal place.

### 5.4 Trend Ratings

| Score Range | Rating | Colour in UI |
| :--- | :--- | :--- |
| ≥ 75 | **Strong Bullish 🟢** | Light green |
| 60–74 | **Moderately Bullish 🟢** | Light green |
| 40–59 | **Neutral / Mixed ⚪** | Light gray |
| 25–39 | **Moderately Bearish 🟠** | Orange |
| < 25 | **Strong Bearish 🔴** | Red |

### 5.5 Worked Example

Assume the following trailing returns for a stock:

| Period | Return |
| :--- | ---: |
| 3D | +2.1% |
| 1W | +3.5% |
| 2W | +1.8% |
| 1M | +6.2% |
| 2M | +3.0% |
| 3M | +1.5% |
| 6M | −8.0% |
| 1Y | −12.0% |

**Step 1 — Short-Term Momentum:**
```
short_mom   = (1.8 + 6.2 + 3.0 + 1.5) / 4 = 3.125%
short_score = clamp(50 + (3.125 × 50/15), 0, 100)
            = clamp(50 + 10.4, 0, 100)
            = 60.4
```

**Step 2 — Momentum Acceleration:**
```
med_avg      = (3.0 + 1.5) / 2 = 2.25%
acceleration = 6.2 − 2.25 = +3.95%
accel_score  = clamp(50 + (3.95 × 50/20), 0, 100)
             = clamp(50 + 9.9, 0, 100)
             = 59.9
```

**Step 3 — Trend Consistency:**
```
Positive periods: 3D✅, 1W✅, 2W✅, 1M✅, 2M✅, 3M✅ — 6/8 positive
consist_score = 6/8 × 100 = 75
```

**Step 4 — Mean Reversion:**
```
long_drop       = (−8.0 + −12.0) / 2 = −10.0%
reversion_ratio = clamp(−(−10) / 30, 0, 1) = 0.333
reversion_score = 0.333 × 100 = 33.3
```

**Final Score:**
```
Score = (60.4 × 0.30) + (59.9 × 0.25) + (75 × 0.25) + (33.3 × 0.20)
      = 18.1 + 15.0 + 18.8 + 6.7
      = 58.6  →  Rating: Neutral / Mixed ⚪
```

---

## 6. News Feed (Informational)

**Source:** `stock.news` — Yahoo Finance news array

**Filtering:** Only articles published within the **last 10 days** are included, sorted from newest to oldest.

**Fields extracted per article:**
- `title` — headline
- `summary` — brief description
- `url` — direct link to the article
- `date` — formatted as `"Apr 18, 2026"`

News is displayed in the UI as contextual information only. It does **not** affect any score.

---

## 7. Design Philosophy & Limitations

### Why Multiple Score Types?

| Score | Purpose | Use Case |
| :--- | :--- | :--- |
| **Composite Score** | Holistic health check | Should I hold or sell this stock? |
| **Predictive Trend** | Momentum direction | Where is this stock headed in 2–3 months? |

Using both in conjunction provides stronger conviction — a stock with a high Composite Score AND a Strong Bullish trend is a much stronger hold than one with only one signal.

### Why 4 Trend Components Instead of Just One Return?

A single return figure is noisy and easily manipulated by one big day. The 4-component design ensures:
- **Short momentum** catches what's happening *now*
- **Acceleration** confirms whether the trend is strengthening (not fading)
- **Consistency** filters out one-day spikes from genuine sustained moves
- **Mean reversion** adds a contrarian safety valve for oversold stocks

### Known Limitations

| Limitation | Impact |
| :--- | :--- |
| Predictive Trend is pure price-based — no fundamentals | A fundamentally broken company can still score "Bullish" if its price has bounced |
| Gap risk | Overnight gaps (earnings, news) can rapidly invalidate a trend score |
| Works best for liquid, large-cap stocks | Thinly traded stocks can produce misleading volume-driven returns |
| Trend looks backward | It predicts *continuation*, not reversal (except via reversion component) |
| Yahoo Finance data availability | Some Indian stocks may have missing or inconsistent data for certain metrics |
| Sector benchmarks are static | Industry benchmarks may need periodic updating to reflect market conditions |

> **Tip:** Use the Predictive Trend Score **in conjunction with** the Composite Score. A stock with a high Composite Score (good fundamentals + technicals) AND a Strong Bullish trend is a stronger conviction hold than one with only one of the two signals.
