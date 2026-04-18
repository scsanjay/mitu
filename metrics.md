# MITU Stock Analysis — Metrics Documentation

This document provides a comprehensive breakdown of all metrics, scoring methodologies, and trend indicators used in the MITU Stock Analysis engine.

---

## 1. Scoring Architecture

MITU uses a multi-layered scoring system to provide a holistic view of a stock's health and momentum. The primary indicator is the **Composite Score**, which is supported by three core pillars and one independent momentum signal.

### Composite Score Calculation
The Composite Score is a weighted average of three raw scores, normalized to a 100-point scale:

| Pillar | Raw Scale | Weight in Composite | Contribution |
| :--- | :--- | :--- | :--- |
| **Technical** | 0–100 | **40%** | 40 points |
| **Fundamental** | 0–100 | **40%** | 40 points |
| **Sentiment** | 0–100 | **20%** | 20 points |
| **Total** | | **100%** | **100 points** |

**Formula:**
```
Composite Score = (Tech_Raw / 100 × 40) + (Fund_Raw / 100 × 40) + (Sent_Raw / 100 × 20)
```

### Classification Thresholds
Based on the Composite Score, stocks are classified as follows:
- **Hold ✅**: ≥ 65 (Strong fundamentals and technicals)
- **Warning ⚠️**: 45–64 (Mixed signals or weakening trend)
- **Sell ❌**: < 45 (Poor score across multiple pillars)

---

## 2. Technical Metrics (Weight: 40%)

The technical score assesses trend structure, momentum, and volume conviction.

### Component Weights
| Component | Weight | Key Indicator |
| :--- | :--- | :--- |
| **MA Stack** | 30% | Price relative to EMA20, EMA50, SMA100, SMA200 |
| **MACD** | 25% | Momentum direction and acceleration |
| **RSI** | 20% | Momentum strength and overbought/oversold levels |
| **Volume Conviction** | 15% | Volume ratio relative to 20-day average |
| **52-Week Position**| 10% | Relative strength within the annual range |

### Key Technical States
- **Bullish Stack**: `Price > EMA20 > EMA50 > SMA100 > SMA200`.
- **Momentum Sweet Zone**: RSI between 55 and 70.
- **Conviction Buying**: Price increase accompanied by Volume ≥ 1.5x average.

---

## 3. Fundamental Metrics (Weight: 40%)

The fundamental score evaluates valuation, financial health, and growth quality. It is **sector-aware**, comparing metrics against specific industry benchmarks.

### Key Fundamental Indicators
- **Valuation**: Trailing P/E and P/B (Scored relative to sector benchmarks).
- **Financial Health**: Debt-to-Equity (sector-aware) and ROE.
- **Growth**: YoY Revenue Growth and YoY EPS Growth.
- **Value/Growth Balance**: PEG Ratio (Price/Earnings to Growth).
- **Market Consensus**: Analyst Target Upside (Upside to mean target).

### Sector Benchmarks (Examples)
| Sector | Reference PE | Reference D/E |
| :--- | :---: | :---: |
| Technology | 28 | 0.3x |
| Banking | 14 | 8.0x |
| Utilities | 16 | 1.2x |

---

## 4. Sentiment Metrics (Weight: 20%)

Sentiment captures lead indicators from analysts, insiders, and institutional players.

### Component Weights
| Component | Weight | Source |
| :--- | :--- | :--- |
| **EPS Revisions** | 30% | 60-day change in analyst EPS estimates |
| **Promoter Holding** | 25% | Percentage of insider ownership |
| **Insider Activity** | 20% | Recent buy/sell transactions by management |
| **Price Target Sentiment**| 15% | Analyst upside expectations |
| **Forward Growth** | 10% | Future earnings estimates |

---

## 5. Predictive Trend Score (Independent)

The **Predictive Trend Score** is a standalone 0–100 signal based purely on price action. It estimates the likely direction of the stock over the next 2–3 months.

### Trailing Returns Calculation
The system computes price returns across 8 distinct timeframes:
- **Short-Term**: 3 Days, 1 Week, 2 Weeks, 1 Month.
- **Medium-Term**: 2 Months, 3 Months.
- **Long-Term**: 6 Months, 1 Year.

**Formula:**
```
Return % = ((Current Price - Historical Price) / Historical Price) * 100
```

### Predictive Trend Components
| Component | Weight | Logic |
| :--- | :--- | :--- |
| **Short-Term Momentum** | 40% | Average of 3D, 1W, 2W, 1M returns |
| **Momentum Acceleration**| 30% | 1M performance vs (2M+3M) average |
| **Trend Consistency** | 20% | Percentage of the 8 timeframes that are positive |
| **Mean Reversion** | 10% | Bounce potential if 6M/1Y drop is significant |

### Trend Ratings
- **Strong Bullish 🟢**: ≥ 75
- **Moderately Bullish 🟢**: 60–74
- **Neutral / Mixed ⚪**: 40–59
- **Moderately Bearish 🟠**: 25–39
- **Strong Bearish 🔴**: < 25
