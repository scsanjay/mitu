# Technical Metrics Documentation

This document explains every technical metric used in MITU's technical scoring system — from the raw data sourced from Yahoo Finance, to the calculated indicators, and finally the weighted scoring formula.

---

## 1. Base Metrics (from Yahoo Finance)

These are fetched directly via `yfinance` using 1 year of daily OHLCV history.

| Metric | Source | Description |
| :--- | :--- | :--- |
| **Close** | `hist['Close']` | Daily closing price |
| **High** | `hist['High']` | Daily high price |
| **Low** | `hist['Low']` | Daily low price |
| **Volume** | `hist['Volume']` | Number of shares traded in the session |

---

## 2. Calculated Technical Indicators

All indicators are computed from the base OHLCV data using the `ta` (Technical Analysis) library.

### Moving Averages

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **EMA 20** | Exponential Moving Average, 20-day window | Short-term trend. Reacts quickly to price changes. |
| **EMA 50** | Exponential Moving Average, 50-day window | Medium-term trend direction. |
| **SMA 100** | Simple Moving Average, 100-day window | India-specific mid-term anchor. Smooths out 2-3 month noise. |
| **SMA 200** | Simple Moving Average, 200-day window | Long-term trend baseline. The most important support/resistance level for medium-term holders. |

**Stack Order Check:** A "healthy" market structure has `EMA20 > EMA50 > SMA100`. When all MAs are aligned in this order AND price is above all of them, the trend is strongly bullish.

### MACD (Moving Average Convergence Divergence)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **MACD Line** | EMA(12) − EMA(26) of Close | Measures the gap between fast and slow EMAs. Positive = bullish momentum. |
| **Signal Line** | EMA(9) of the MACD Line | Smoothed version of MACD. Crossovers generate buy/sell signals. |
| **MACD Histogram** | MACD Line − Signal Line | Visualizes momentum acceleration. Increasing histogram = strengthening momentum. |

**Key states:**
- **MACD > Signal, both > 0** → Strong bullish momentum
- **MACD > Signal, both < 0** → Early recovery, not confirmed
- **MACD < Signal, both < 0, histogram worsening** → Strong bearish, accelerating sell-off

### RSI (Relative Strength Index)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **RSI (14)** | 14-period RSI of Close | Momentum oscillator (0-100). Measures speed and change of price movements. |
| **RSI 5-day Trend** | `RSI_today − RSI_5_days_ago` | Direction of momentum — is RSI rising or falling over the past week? |

**Interpretation for medium-term holding (differs from day-trading):**
- **55–70**: Momentum sweet zone — ideal for medium-term hold
- **50–55**: Mild positive, bulls slightly in control
- **40–50**: Weak zone. RSI trend direction matters here — rising RSI gets slightly more credit
- **30–40**: Downtrend momentum dominant. Not a buy signal for medium-term
- **< 30**: Deep oversold — severe weakness, avoid catching the falling knife
- **70–80**: Overbought. Consider trimming
- **> 80**: Extremely overbought — high reversal risk

### Volume Analysis

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

### 52-Week Range Position

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **52W High** | Rolling 252-day max of High | Highest price in the past year |
| **52W Low** | Rolling 252-day min of Low | Lowest price in the past year |
| **52W Position** | `(Close − 52W_Low) / (52W_High − 52W_Low) × 100` | Where the stock sits in its annual range (0% = at low, 100% = at high) |
| **% from 52W High** | `(52W_High − Close) / 52W_High × 100` | How far the stock has fallen from its peak |

### ATR (Average True Range)

| Indicator | Calculation | Purpose |
| :--- | :--- | :--- |
| **ATR (14)** | 14-period ATR of High, Low, Close | Measures daily volatility. Used for stop-loss placement, not for scoring. |

**Stop-loss suggestion:** `Current Price − (2 × ATR)` — gives the stock room to breathe while protecting against sharp drops.

---

## 3. Technical Score Formula

The technical score is calculated on a **0–100 scale** using 5 weighted components. Each component is independently scored 0–100, then combined using a weighted average.

### Weight Distribution

| # | Component | Weight | What It Captures |
| :--- | :--- | :--- | :--- |
| 1 | MA Stack | **30%** | Trend structure and alignment |
| 2 | MACD | **25%** | Momentum direction and acceleration |
| 3 | RSI | **20%** | Momentum strength and zone |
| 4 | Volume | **15%** | Conviction behind price moves |
| 5 | 52W Position | **10%** | Relative strength within the annual range |

### Component Scoring Tables

#### 1. MA Stack (30%)

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

#### 2. MACD (25%)

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

#### 3. RSI (20%)

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

#### 4. Volume (15%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Price ↑, Volume ≥ 1.5x avg | **90** | ✅ Strong conviction buying |
| Price ↑, Volume ≥ 1.0x avg | **70** | ✅ Normal bullish volume |
| Price ↑, Volume < 0.7x avg | **45** | ⚠️ Weak conviction rally |
| Price ↓, Volume ≥ 1.5x avg | **15** | ❌ Distribution |
| Price ↓, Volume ≥ 1.0x avg | **35** | ⚠️ Mild selling pressure |
| Price ↓, Volume < 0.7x avg | **55** | ℹ️ Inconclusive |

#### 5. 52-Week Position (10%)

| Condition | Score | Signal |
| :--- | :--- | :--- |
| Position ≥ 75% | **85** | ✅ Strong relative strength |
| Position ≥ 50% | **65** | ✅ Mid-upper range |
| Position ≥ 30% | **40** | ⚠️ Underperforming |
| Position < 30% | **20** | ❌ Near 52W low |

### Final Score Calculation

```
Technical Score = Σ (component_score × component_weight) / Σ (component_weight)
```

Expanded:

```
Tech Score = (MA_Score × 30 + MACD_Score × 25 + RSI_Score × 20 + Vol_Score × 15 + 52W_Score × 10) / 100
```

The result is a value between **0 and 100**, rounded to the nearest integer.

### Composite Integration

The technical score is one of three pillars in the overall composite score:

| Pillar | Raw Scale | Weight in Composite | Scaled Max |
| :--- | :--- | :--- | :--- |
| **Technical** | 0–100 | 40% | 40 points |
| **Fundamental** | 0–40 | 40% | 40 points |
| **Sentiment** | 0–100 (scaled) | 20% | 20 points |

```
Composite Score = (Tech_Raw / 100 × 40) + Fund_Score + (Sent_Raw / 100 × 20)
```

### Classification Thresholds

| Composite Score | Classification |
| :--- | :--- |
| ≥ 65 | **Hold** ✅ |
| 45–64 | **Warning** ⚠️ |
| < 45 | **Sell** ❌ |

### Stop-Loss (Informational Only)

The ATR-based stop-loss is provided as a suggestion and does **not** affect the score:

```
Suggested Stop-Loss = Current Price − (2 × ATR14)
```

This gives the stock 2× its average daily volatility as breathing room — wide enough to avoid getting stopped out by normal fluctuations, tight enough to limit downside.
