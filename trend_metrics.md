# Predictive Trend Score — Documentation

This document explains the **Predictive Trend Score** calculated by `calculate_predictive_trend_score()` in `analyzer.py`. It is a **separate, standalone signal** — it does not contribute to the Composite Score (which is Technical + Fundamental + Sentiment). Its purpose is to answer a distinct question:

> *"Based purely on how this stock has been moving, where is it likely headed over the next 2–3 months?"*

---

## 1. What Is the Predictive Trend Score?

The Predictive Trend Score is a **0–100 price-momentum indicator** that analyses a stock's trailing price returns across 8 timeframes and combines them into a single forward-looking rating.

### Key Differences vs Composite Score

| | **Composite Score** | **Predictive Trend Score** |
| :--- | :--- | :--- |
| Purpose | Overall stock health (hold/warn/sell) | Direction of momentum (next 2–3 months) |
| Inputs | Technicals + Fundamentals + Sentiment | Price returns only (8 timeframes) |
| Scale | 0–100 → mapped to 40+40+20 pts | 0–100 directly |
| Affects classification? | ✅ Yes | ❌ No |
| Displayed as | Composite score + label | Rating badge (Bullish / Bearish etc.) |

---

## 2. Input: Trailing Price Returns

Returns are computed from 1 year of daily closing price history (`hist['Close']`). Each period compares today's close against the close *N trading days ago*.

**Formula for each period:**
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

> [!NOTE]
> If the price history is shorter than the required lookback (e.g. a recently listed stock), that period returns `None` and defaults to `0.0` in the calculation. It does not cause an error.

---

## 3. Score Components

The final score is built from **4 weighted components**, each independently scored on a 0–100 scale.

### Weight Distribution

| # | Component | Weight | What It Asks |
| :--- | :--- | :---: | :--- |
| 1 | Short-Term Momentum | **40%** | Is the stock rising over the last month? |
| 2 | Momentum Acceleration | **30%** | Is it moving *faster* recently than before? |
| 3 | Trend Consistency | **20%** | Is it positive across most timeframes? |
| 4 | Mean Reversion Potential | **10%** | Could a big drop trigger a technical bounce? |

---

### Component 1 — Short-Term Momentum (40%)

**What it captures:** The average price performance over the very recent past (3D through 1M). A stock rising consistently over days to a month is likely still in momentum.

**Formula:**
```
short_mom   = (Return_3D + Return_1W + Return_2W + Return_1M) / 4

short_score = clamp(50 + (short_mom × 50/15), 0, 100)
```

**Calibration:**
- `+15%` average short-term return → score = **100**
- `0%` (flat) → score = **50**
- `−15%` average → score = **0**

**Interpretation table:**

| Average Short-Term Return | Approx Score | Meaning |
| :--- | :---: | :--- |
| > +15% | ~100 | Strong upward momentum |
| +8% to +15% | 75–100 | Healthy momentum |
| +2% to +8% | 55–75 | Mild positive drift |
| −2% to +2% | 43–57 | Essentially flat |
| −8% to −2% | 25–43 | Mild selling pressure |
| < −15% | ~0 | Strong downward momentum |

---

### Component 2 — Momentum Acceleration (30%)

**What it captures:** Whether the stock is *gaining speed* relative to its recent medium-term average. A stock up 5% in the last month but only 2% average over 2–3 months is *accelerating* — a bullish signal. The reverse (decelerating) warns of stalling.

**Formula:**
```
med_avg      = (Return_2M + Return_3M) / 2
acceleration = Return_1M − med_avg

accel_score  = clamp(50 + (acceleration × 50/20), 0, 100)
```

**Calibration:**
- Acceleration of `+20%` → score = **100** (1M massively outperforming 2–3M avg)
- Acceleration of `0%` → score = **50** (pace unchanged)
- Acceleration of `−20%` → score = **0** (sharply decelerating)

**Interpretation table:**

| 1M vs Medium-Term | Approx Score | Meaning |
| :--- | :---: | :--- |
| 1M >> med avg (+20%) | ~100 | Sharply accelerating — breakout momentum |
| 1M > med avg (+10%) | ~75 | Gently accelerating |
| 1M ≈ med avg | ~50 | Cruise control — steady pace |
| 1M < med avg (−10%) | ~25 | Decelerating — losing steam |
| 1M << med avg (−20%) | ~0 | Sharp deceleration — trend reversal risk |

---

### Component 3 — Trend Consistency (20%)

**What it captures:** Whether the stock is positive across *most* timeframes, not just one. A stock up 2% today but down across every other timeframe is not in a trend — it's noise.

**Formula:**
```
positive_periods  = count of periods where Return > 0
consistency_ratio = positive_periods / 8

consist_score = consistency_ratio × 100
```

**Interpretation table:**

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

---

### Component 4 — Mean Reversion Potential (10%)

**What it captures:** Whether the stock has fallen so much over 6M and 1Y that a *technical bounce* is plausible. This is the only component that can score positively on a falling stock — it reflects the law of stretched rubber bands.

> [!IMPORTANT]
> This component is **one-directional**. It only adds points when a stock has fallen significantly. It does **not** penalise stocks in an uptrend; those simply score 0 on this component (no meaningful reversion expected upward from a new high).

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

**Interpretation table:**

| Avg 6M + 1Y Return | Score | Meaning |
| :--- | :---: | :--- |
| ≤ −30% | **100** | Deep in distress — high snap-back potential |
| −20% | **67** | Significant underperformance |
| −15% | **50** | Moderate correction territory |
| −5% | **17** | Minor pullback — small reversion potential |
| 0% or positive | **0** | No mean-reversion upside to exploit |

---

## 4. Final Score Calculation

```
Predictive_Trend_Score = (short_score  × 0.40)
                       + (accel_score  × 0.30)
                       + (consist_score × 0.20)
                       + (reversion_score × 0.10)
```

Result is clamped to **[0, 100]** and rounded to 1 decimal place.

---

## 5. Rating Thresholds

| Score Range | Rating | Colour in UI |
| :--- | :--- | :--- |
| ≥ 75 | **Strong Bullish 🟢** | Light green |
| 60–74 | **Moderately Bullish 🟢** | Light green |
| 40–59 | **Neutral / Mixed ⚪** | Light gray |
| 25–39 | **Moderately Bearish 🟠** | Orange |
| < 25 | **Strong Bearish 🔴** | Red |

---

## 6. Worked Example

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
short_mom   = (2.1 + 3.5 + 1.8 + 6.2) / 4 = 3.4%
short_score = clamp(50 + (3.4 × 50/15), 0, 100)
            = clamp(50 + 11.3, 0, 100)
            = 61.3
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
Score = (61.3 × 0.40) + (59.9 × 0.30) + (75 × 0.20) + (33.3 × 0.10)
      = 24.5 + 18.0 + 15.0 + 3.3
      = 60.8  →  Rating: Moderately Bullish 🟢
```

---

## 7. Design Philosophy & Limitations

### Why 4 components instead of just one return?

A single return figure is noisy and easily manipulated by one big day. The 4-component design ensures:
- **Short momentum** catches what's happening *now*
- **Acceleration** confirms whether the trend is strengthening (not fading)
- **Consistency** filters out one-day spikes from genuine sustained moves
- **Mean reversion** adds a contrarian safety valve for oversold stocks

### Known Limitations

| Limitation | Impact |
| :--- | :--- |
| Pure price-based — no fundamentals | A fundamentally broken company can still score "Bullish" if its price has bounced |
| Gap risk | Overnight gaps (earnings, news) can rapidly invalidate a trend score |
| Works best for liquid, large-cap stocks | Thinly traded stocks can produce misleading volume-driven returns |
| Looks backward | It predicts *continuation* of the trend, not reversal (except via reversion component) |

> [!TIP]
> Use the Predictive Trend Score **in conjunction with** the Composite Score. A stock with a high Composite Score (good fundamentals + technicals) AND a Strong Bullish trend is a stronger conviction hold than one with only one of the two signals.
