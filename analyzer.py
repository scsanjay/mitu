import yfinance as yf
import pandas as pd
import ta
import numpy as np

# Scoring Thresholds
HOLD_THRESHOLD = 70
WARNING_THRESHOLD = 50

# Sector PE benchmarks
SECTOR_PE_BENCHMARKS = {
    "Technology":           28,
    "Financial Services":   18,
    "Banking":              14,
    "Energy":               14,
    "Consumer Defensive":   35,
    "Consumer Cyclical":    30,
    "Healthcare":           35,
    "Industrials":          25,
    "Basic Materials":      15,
    "Utilities":            16,
    "Real Estate":          30,
    "Communication":        22,
    "default":              22,
}

# Sector D/E benchmarks (as ratio, not %)
SECTOR_DE_BENCHMARKS = {
    "Technology":           0.3,
    "Financial Services":   8.0,
    "Banking":              8.0,
    "Energy":               0.8,
    "Consumer Defensive":   0.6,
    "Consumer Cyclical":    0.7,
    "Healthcare":           0.4,
    "Industrials":          0.8,
    "Basic Materials":      0.7,
    "Utilities":            1.2,
    "Real Estate":          1.5,
    "default":              0.8,
}

def calculate_predictive_trend_score(returns: dict, raw_returns: dict = None, weights: dict = None) -> dict:
    """
    Calculates a 0-100 trend score predicting performance over the next 2-3 months.
    raw_returns: the original returns dict BEFORE None->0 defaulting, used for confidence.
    """
    default_weights = {
        'short_momentum': 0.30,
        'acceleration':   0.25,
        'consistency':    0.25,
        'reversion':      0.20
    }
    w = weights if weights else default_weights

    if abs(sum(w.values()) - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {sum(w.values()):.3f}")

    # Track which periods had real data for confidence
    all_keys = ['3D', '1W', '2W', '1M', '2M', '3M', '6M', '1Y']
    important_keys = ['1M', '2M', '3M', '6M']  # critical for 3-6 month prediction
    raw = raw_returns if raw_returns else returns
    data_available = sum(1 for k in all_keys if raw.get(k) is not None)
    important_available = sum(1 for k in important_keys if raw.get(k) is not None)

    r = {k: returns.get(k, 0.0) for k in all_keys}
    
    # default to 0.0 if None
    for k in r:
        if r[k] is None:
            r[k] = 0.0

    # 1. Short-Term Momentum (30%)
    short_mom = (r['2W'] + r['1M'] + r['2M'] + r['3M']) / 4
    short_score = max(0, min(100, 50 + (short_mom * (50 / 15))))

    # 2. Momentum Acceleration (25%)
    med_avg = (r['2M'] + r['3M']) / 2
    acceleration = r['1M'] - med_avg
    accel_score = max(0, min(100, 50 + (acceleration * (50 / 20))))

    # 3. Trend Consistency (25%)
    periods = [r['3D'], r['1W'], r['2W'], r['1M'], r['2M'], r['3M'], r['6M'], r['1Y']]
    consistency_ratio = sum(1 for p in periods if p > 0) / len(periods)
    consist_score = consistency_ratio * 100

    # 4. Mean Reversion Potential (20%)
    long_drop = (r['6M'] + r['1Y']) / 2
    reversion_ratio = max(0, min(1, -long_drop / 30))
    reversion_score = reversion_ratio * 100

    raw_score = (
        short_score  * w['short_momentum'] +
        accel_score  * w['acceleration'] +
        consist_score * w['consistency'] +
        reversion_score * w['reversion']
    )

    final_score = max(0, min(100, round(raw_score, 1)))

    if final_score >= 75:   rating = "Strong Bullish 🟢"
    elif final_score >= 60: rating = "Moderately Bullish 🟢"
    elif final_score >= 40: rating = "Neutral / Mixed ⚪"
    elif final_score >= 25: rating = "Moderately Bearish 🟠"
    else:                   rating = "Strong Bearish 🔴"

    # Confidence: HIGH if >=6 periods available AND all 4 important ones present
    # MEDIUM if >=4 periods and >=2 important, LOW otherwise
    if data_available >= 6 and important_available >= 3:
        confidence = "HIGH"
    elif data_available >= 4 and important_available >= 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "score": final_score,
        "rating": rating,
        "confidence": confidence,
        "components": {
            "short_term_momentum":   round(short_score, 1),
            "momentum_acceleration": round(accel_score, 1),
            "trend_consistency":     round(consist_score, 1),
            "mean_reversion":        round(reversion_score, 1),
        },
        "inputs": r,
    }

def score_sentiment_v2(stock_data):
    signals = {}
    scored_checks = []
    data_found = 0

    # ─────────────────────────────────────────────────────────────
    # FIX 1: EPS TREND
    # Real format:
    #   index   → period labels: "0q", "+1q"
    #   columns → "current", "7daysAgo", "30daysAgo", "60daysAgo", "90daysAgo"
    #
    # RELIANCE: 0q current=15.6775, 60daysAgo=15.57086  → +0.7% (flat/ok)
    # TCS:      0q current=37.51, 60daysAgo=38.45       → -2.5% (slight cut)
    # ─────────────────────────────────────────────────────────────
    eps = stock_data.get("eps_trend")
    if eps is not None and isinstance(eps, pd.DataFrame) and not eps.empty:
        try:
            current_q_now = pd.to_numeric(eps.loc["0q", "current"],    errors="coerce")
            current_q_60d = pd.to_numeric(eps.loc["0q", "60daysAgo"],  errors="coerce")

            if pd.notna(current_q_now) and pd.notna(current_q_60d) and current_q_60d != 0:
                revision_pct = (current_q_now - current_q_60d) / abs(current_q_60d) * 100
                data_found += 1

                if revision_pct < -8:
                    check_score = 20
                    signals["EPS_Revision"] = f"❌ EPS cut {revision_pct:.1f}% in last 60 days"
                elif revision_pct < -2:
                    check_score = 45
                    signals["EPS_Revision"] = f"⚠️  Minor EPS cut ({revision_pct:.1f}% in 60d)"
                elif revision_pct > 5:
                    check_score = 90
                    signals["EPS_Revision"] = f"✅ EPS upgraded {revision_pct:.1f}% in 60 days"
                else:
                    check_score = 70
                    signals["EPS_Revision"] = f"✅ EPS estimates stable ({revision_pct:+.1f}% in 60d)"

                scored_checks.append((check_score, 30, "EPS Revision"))
        except KeyError as e:
            signals["EPS_Revision"] = f"⚠️  EPS key error: {e}"
        except Exception as e:
            signals["EPS_Revision"] = f"⚠️  EPS error: {e}"
    else:
        signals["EPS_Revision"] = "ℹ️  EPS trend not available"

    # ─────────────────────────────────────────────────────────────
    # FIX 2: PROMOTER / INSIDER HOLDING
    # Real format:
    #   index (Breakdown) → "insidersPercentHeld", "institutionsPercentHeld"
    #   column            → "Value"  (decimal: 0.51048 = 51%)
    #
    # RELIANCE: insidersPercentHeld = 0.51048 → 51% ✅ Strong
    # TCS:      insidersPercentHeld = 0.71789 → 71% ✅ Very strong (Tata group)
    # ─────────────────────────────────────────────────────────────
    major = stock_data.get("major_holders")
    if major is not None and isinstance(major, pd.DataFrame) and not major.empty:
        try:
            # Normalize index just in case casing differs
            major.index = major.index.str.strip()

            if "insidersPercentHeld" in major.index:
                promoter_pct = float(major.loc["insidersPercentHeld", "Value"]) * 100
                data_found += 1

                if promoter_pct < 25:
                    check_score = 40
                    signals["Promoter_Hold"] = f"⚠️  Low promoter/insider holding ({promoter_pct:.1f}%)"
                elif promoter_pct > 50:
                    check_score = 88
                    signals["Promoter_Hold"] = f"✅ Strong promoter holding ({promoter_pct:.1f}%)"
                else:
                    check_score = 65
                    signals["Promoter_Hold"] = f"✅ Moderate promoter holding ({promoter_pct:.1f}%)"

                scored_checks.append((check_score, 25, "Promoter Holding"))

            # Bonus: check institutional holding too
            if "institutionsPercentHeld" in major.index:
                inst_pct = float(major.loc["institutionsPercentHeld", "Value"]) * 100
                signals["Inst_Hold"] = f"ℹ️  Institutional holding: {inst_pct:.1f}%"

        except Exception as e:
            signals["Promoter_Hold"] = f"⚠️  Promoter parse error: {e}"
    else:
        signals["Promoter_Hold"] = "ℹ️  Major holders not available"

    # ─────────────────────────────────────────────────────────────
    # FIX 3: INSIDER TRANSACTIONS
    # Real format: columns include "Transaction" (not "Text"), "Value", "Shares"
    # Ownership = "D" means Direct holding
    #
    # RELIANCE has 5 rows — need to check "Transaction" column values
    # ─────────────────────────────────────────────────────────────
    insider = stock_data.get("insider_tx")
    if insider is not None and isinstance(insider, pd.DataFrame) and not insider.empty:
        try:
            # Use "Transaction" column (not "Text")
            if "Transaction" in insider.columns:
                tx_col = "Transaction"
            elif "Text" in insider.columns:
                tx_col = "Text"
            else:
                tx_col = None

            if tx_col:
                data_found += 1
                sell_mask = insider[tx_col].str.contains(
                    "Sale|Sold|Sell", case=False, na=False
                )
                buy_mask  = insider[tx_col].str.contains(
                    "Purchase|Buy|Acquisition", case=False, na=False
                )

                sell_rows = insider[sell_mask]
                buy_rows  = insider[buy_mask]

                # Weight by ₹ value if available
                if "Value" in insider.columns:
                    sell_val = pd.to_numeric(sell_rows["Value"], errors="coerce").sum()
                    buy_val  = pd.to_numeric(buy_rows["Value"],  errors="coerce").sum()

                    if sell_val > 0 or buy_val > 0:
                        if sell_val > buy_val * 3:
                            check_score = 25
                            signals["Insider"] = (
                                f"❌ Heavy insider selling "
                                f"(₹{sell_val/1e7:.1f}Cr sold vs ₹{buy_val/1e7:.1f}Cr bought)"
                            )
                        elif buy_val >= sell_val:
                            check_score = 80
                            signals["Insider"] = (
                                f"✅ Net insider buying "
                                f"(₹{buy_val/1e7:.1f}Cr bought)"
                            )
                        else:
                            check_score = 55
                            signals["Insider"] = (
                                f"⚠️  Mixed insider activity "
                                f"(sold ₹{sell_val/1e7:.1f}Cr, bought ₹{buy_val/1e7:.1f}Cr)"
                            )
                        scored_checks.append((check_score, 20, "Insider Tx"))
                else:
                    # No value col — use counts
                    if len(sell_rows) > len(buy_rows) * 2:
                        check_score = 30
                        signals["Insider"] = f"❌ More insider sells ({len(sell_rows)}) than buys ({len(buy_rows)})"
                    else:
                        check_score = 65
                        signals["Insider"] = f"⚠️  Insider activity: {len(buy_rows)} buys, {len(sell_rows)} sells"
                    scored_checks.append((check_score, 20, "Insider Tx"))
            else:
                signals["Insider"] = f"⚠️  No transaction column found. Cols: {insider.columns.tolist()}"
        except Exception as e:
            signals["Insider"] = f"⚠️  Insider parse error: {e}"
    else:
        signals["Insider"] = "ℹ️  No insider transactions found"

    # ─────────────────────────────────────────────────────────────
    # FIX 4: ANALYST TARGET — OVERBOUGHT FLAG ONLY
    # Dict keys: current, high, low, mean, median  ← confirmed working
    #
    # RELIANCE: current=1365, mean=1732  → 26.9% upside ✅
    # TCS:      current=2581, mean=2938  → 13.8% upside ✅
    # ─────────────────────────────────────────────────────────────
    targets = stock_data.get("price_targets")
    cp      = stock_data.get("current_price")

    if isinstance(targets, dict) and cp:
        try:
            mean_t = targets.get("mean")
            high_t = targets.get("high")

            if mean_t and mean_t > 0:
                data_found += 1
                upside_pct = (mean_t - cp) / cp * 100

                if high_t and cp > high_t * 1.05:
                    check_score = 20
                    signals["Analyst_Target"] = (
                        f"❌ CMP ₹{cp:.0f} above even highest analyst target ₹{high_t:.0f}"
                    )
                elif upside_pct < -10:
                    check_score = 30
                    signals["Analyst_Target"] = (
                        f"⚠️  CMP {abs(upside_pct):.1f}% above mean target ₹{mean_t:.0f}"
                    )
                elif upside_pct > 20:
                    check_score = 85
                    signals["Analyst_Target"] = (
                        f"✅ {upside_pct:.1f}% upside to mean target ₹{mean_t:.0f}"
                    )
                else:
                    check_score = 65
                    signals["Analyst_Target"] = (
                        f"✅ {upside_pct:.1f}% upside to mean target ₹{mean_t:.0f}"
                    )

                scored_checks.append((check_score, 15, "Analyst Target"))
        except Exception as e:
            signals["Analyst_Target"] = f"⚠️  Target error: {e}"
    else:
        signals["Analyst_Target"] = "ℹ️  Analyst targets not available"

    # ─────────────────────────────────────────────────────────────
    # FIX 5: GROWTH ESTIMATES
    # Real format:
    #   index   → "0q", "+1q", "0y", "+1y", "+5y"
    #   columns → "stockTrend", "indexTrend"
    #
    # RELIANCE: 0q=+9.33%, +1q=-15.39% (next Q looks weak — flag it)
    # TCS:      0q=+6.36%, +1q=+8.60% ✅
    # ─────────────────────────────────────────────────────────────
    growth = stock_data.get("growth_est")
    if growth is not None and isinstance(growth, pd.DataFrame) and not growth.empty:
        try:
            if "stockTrend" in growth.columns:
                data_found += 1
                results = []

                for period_label, display in [("0q", "curr Q"), ("+1q", "next Q"), ("+1y", "next yr")]:
                    if period_label in growth.index:
                        val = pd.to_numeric(growth.loc[period_label, "stockTrend"], errors="coerce")
                        if pd.notna(val):
                            results.append(f"{display}: {val*100:+.1f}%")

                if results:
                    # Score based on next year if available, else next quarter
                    score_period = "+1y" if "+1y" in growth.index else "+1q"
                    growth_val = pd.to_numeric(
                        growth.loc[score_period, "stockTrend"], errors="coerce"
                    )

                    if pd.notna(growth_val):
                        if growth_val < -0.10:
                            check_score = 25
                        elif growth_val < 0:
                            check_score = 45
                        elif growth_val > 0.15:
                            check_score = 85
                        else:
                            check_score = 65

                        signals["Growth_Est"] = (
                            f"{'✅' if growth_val >= 0 else '❌'} "
                            f"Growth estimates: {', '.join(results)}"
                        )
                        scored_checks.append((check_score, 10, "Growth Estimate"))
        except Exception as e:
            signals["Growth_Est"] = f"⚠️  Growth error: {e}"
    else:
        signals["Growth_Est"] = "ℹ️  Growth estimates not available"

    # ─────────────────────────────────────────────────────────────
    # FINAL COMPOSITE
    # ─────────────────────────────────────────────────────────────
    if not scored_checks:
        signals["_summary"] = "⚠️  No sentiment data available — returning neutral 50"
        return 50, signals, "LOW"

    total_weight = sum(w for _, w, _ in scored_checks)
    weighted_sum = sum(s * w for s, w, _ in scored_checks)
    final_score  = round(weighted_sum / total_weight)

    confidence   = "HIGH" if data_found >= 4 else "MEDIUM" if data_found >= 2 else "LOW"
    checks_used  = ", ".join(label for _, _, label in scored_checks)
    signals["_summary"] = (
        f"ℹ️  Scored on: {checks_used} | Confidence: {confidence}"
    )

    return final_score, signals, confidence

# ─────────────────────────────────────────────────────────────
# 52-WEEK RANGE HELPERS
# ─────────────────────────────────────────────────────────────
def score_52w(range_pos, pct_from_high):
    """Returns (0-100 score, signal string) based on position in 52W range."""
    if range_pos < 15:
        return 25, f"❌ Near 52W low — down {pct_from_high:.1f}% from peak"
    elif range_pos < 40:
        return 45, f"⚠️  Lower half of 52W range ({range_pos:.0f}%), down {pct_from_high:.1f}% from high"
    elif range_pos > 85:
        return 75, f"✅ Near 52W high ({range_pos:.0f}% of range)"
    else:
        return 65, f"✅ Mid-upper range ({range_pos:.0f}%), {pct_from_high:.1f}% below 52W high"


def score_technicals_v2(df):
    """
    Redesigned technical score — 0-100 scale.
    Weighted scoring based on medium-term (6-12 month) holding logic.
    Components: MA Stack (30%), MACD (25%), RSI (20%), Volume (15%), 52W (10%)
    """
    latest    = df.iloc[-1]
    prev      = df.iloc[-2]
    prev5     = df.iloc[-5]   # 1 week ago
    signals   = {}
    checks    = []
    # Each check: (score 0-100, weight, label)

    price  = latest["Close"]
    ema20  = latest["EMA_20"]
    ema50  = latest["EMA_50"]
    sma100 = latest["SMA_100"]
    sma200 = latest["SMA_200"]

    # ──────────────────────────────────────────────────────────────
    # 1. MA STACK — 30% weight
    # Rewards full alignment, distinguishes gap size
    # ──────────────────────────────────────────────────────────────
    mas_above = sum([
        price > ema20,
        price > ema50,
        price > sma100,
        price > sma200
    ])

    # Stack order bonus — all aligned matters most
    stack_order_correct = ema20 > ema50 > sma100   # healthy alignment

    if mas_above == 4 and stack_order_correct:
        ma_score = 95
        signals["MA_Stack"] = "✅ Full bullish stack — price above all MAs, MAs aligned"
    elif mas_above == 4:
        ma_score = 80
        signals["MA_Stack"] = "✅ Price above all MAs (MAs not fully aligned yet)"
    elif mas_above == 3 and price > sma200:
        ma_score = 65
        signals["MA_Stack"] = "⚠️  Above SMA200 and 2 short-term MAs — mild pullback in uptrend"
    elif mas_above == 2 and price > sma200:
        ma_score = 50
        signals["MA_Stack"] = "⚠️  Holding above SMA200 — long-term trend intact but weakening"
    elif mas_above == 1 and price > sma200:
        ma_score = 35
        signals["MA_Stack"] = "⚠️  Barely above SMA200 — trend at risk, watch closely"
    elif mas_above == 0:
        # How far below SMA200?
        gap_pct = (sma200 - price) / sma200 * 100
        if gap_pct > 10:
            ma_score = 10
            signals["MA_Stack"] = f"❌ Price {gap_pct:.1f}% below SMA200 — deep downtrend"
        else:
            ma_score = 25
            signals["MA_Stack"] = f"❌ Below all MAs including SMA200 — bearish structure"
    else:
        ma_score = 30
        signals["MA_Stack"] = f"❌ Below SMA200 — long-term trend broken ({mas_above}/4 MAs above)"

    checks.append((ma_score, 30, "MA Stack"))

    # ──────────────────────────────────────────────────────────────
    # 2. MACD — 25% weight
    # 3-tier: position, crossover direction, histogram momentum
    # ──────────────────────────────────────────────────────────────
    macd_v      = latest["MACD"]
    signal_v    = latest["MACD_Signal"]
    hist_v      = latest["MACD_Hist"]
    prev_hist   = prev["MACD_Hist"]

    above_zero      = macd_v > 0 and signal_v > 0
    below_zero      = macd_v < 0 and signal_v < 0
    macd_bullish    = macd_v > signal_v
    hist_improving  = hist_v > prev_hist       # momentum accelerating
    hist_worsening  = hist_v < prev_hist

    if above_zero and macd_bullish and hist_improving:
        macd_score = 95
        signals["MACD"] = "✅ MACD bullish above zero and accelerating — strong momentum"
    elif above_zero and macd_bullish:
        macd_score = 80
        signals["MACD"] = "✅ MACD bullish above zero — positive momentum"
    elif above_zero and not macd_bullish and hist_worsening:
        macd_score = 45
        signals["MACD"] = "⚠️  MACD topping out above zero — momentum fading"
    elif below_zero and macd_bullish and hist_improving:
        macd_score = 55
        signals["MACD"] = "⚠️  MACD recovering below zero — early positive signal, not confirmed"
    elif below_zero and macd_bullish:
        macd_score = 45
        signals["MACD"] = "⚠️  MACD above signal but both negative — weak recovery attempt"
    elif below_zero and not macd_bullish and hist_worsening:
        macd_score = 10
        signals["MACD"] = "❌ MACD bearish below zero and accelerating down — strong sell signal"
    elif below_zero and not macd_bullish:
        macd_score = 20
        signals["MACD"] = "❌ MACD bearish below zero"
    else:
        macd_score = 40
        signals["MACD"] = "⚠️  MACD mixed signals"

    checks.append((macd_score, 25, "MACD"))

    # ──────────────────────────────────────────────────────────────
    # 3. RSI — 20% weight
    # Medium-term logic: reward momentum zone (50-65), not oversold
    # ──────────────────────────────────────────────────────────────
    rsi       = latest["RSI"]
    rsi_5d    = prev5["RSI"]
    rsi_trend = rsi - rsi_5d   # rising or falling

    if 55 <= rsi <= 70:
        rsi_score = 85
        signals["RSI"] = f"✅ RSI in momentum zone ({rsi:.1f}) — ideal for medium-term hold"
    elif 50 <= rsi < 55:
        rsi_score = 65
        signals["RSI"] = f"✅ RSI above 50 ({rsi:.1f}) — mild positive momentum"
    elif 70 < rsi <= 80:
        rsi_score = 55
        signals["RSI"] = f"⚠️  RSI overbought ({rsi:.1f}) — trim risk, watch for reversal"
    elif rsi > 80:
        rsi_score = 30
        signals["RSI"] = f"⚠️  RSI extremely overbought ({rsi:.1f}) — high reversal risk"
    elif 40 <= rsi < 50:
        # Below 50 but direction matters
        if rsi_trend > 3:
            rsi_score = 45
            signals["RSI"] = f"⚠️  RSI below 50 ({rsi:.1f}) but rising — watch for 50 crossover"
        else:
            rsi_score = 35
            signals["RSI"] = f"⚠️  RSI below 50 ({rsi:.1f}) — weak momentum"
    elif 30 <= rsi < 40:
        rsi_score = 25
        signals["RSI"] = f"❌ RSI weak ({rsi:.1f}) — downtrend momentum. Not a buy signal for medium term"
    else:
        rsi_score = 15
        signals["RSI"] = f"❌ RSI deeply oversold ({rsi:.1f}) — severe downtrend, avoid"

    checks.append((rsi_score, 20, "RSI"))

    # ──────────────────────────────────────────────────────────────
    # 4. VOLUME — 15% weight
    # ──────────────────────────────────────────────────────────────
    vol_ratio    = latest["Vol_Ratio"]
    price_up     = latest["Close"] > prev["Close"]

    if price_up and vol_ratio >= 1.5:
        vol_score = 90
        signals["Volume"] = f"✅ Rising on {vol_ratio:.1f}x avg volume — strong conviction buying"
    elif price_up and vol_ratio >= 1.0:
        vol_score = 70
        signals["Volume"] = f"✅ Rising on normal volume ({vol_ratio:.1f}x avg)"
    elif price_up and vol_ratio < 0.7:
        vol_score = 45
        signals["Volume"] = f"⚠️  Rising on low volume ({vol_ratio:.1f}x avg) — weak conviction"
    elif not price_up and vol_ratio >= 1.5:
        vol_score = 15
        signals["Volume"] = f"❌ Falling on {vol_ratio:.1f}x avg volume — distribution signal"
    elif not price_up and vol_ratio >= 1.0:
        vol_score = 35
        signals["Volume"] = f"⚠️  Falling on average volume — mild selling pressure"
    else:
        vol_score = 55
        signals["Volume"] = f"ℹ️  Low volume session ({vol_ratio:.1f}x) — inconclusive"

    checks.append((vol_score, 15, "Volume"))

    # ──────────────────────────────────────────────────────────────
    # 5. 52W POSITION — 10% weight
    # ──────────────────────────────────────────────────────────────
    pos_52w = latest["52W_Pos"]

    if pos_52w >= 75:
        w52_score = 85
        signals["52W"] = f"✅ Upper range ({pos_52w:.0f}%) — strong relative strength"
    elif pos_52w >= 50:
        w52_score = 65
        signals["52W"] = f"✅ Mid-upper range ({pos_52w:.0f}%)"
    elif pos_52w >= 30:
        w52_score = 40
        signals["52W"] = f"⚠️  Lower half of range ({pos_52w:.0f}%) — underperforming"
    else:
        w52_score = 20
        signals["52W"] = f"❌ Near 52W low ({pos_52w:.0f}%) — significant weakness"

    checks.append((w52_score, 10, "52W Position"))

    # ──────────────────────────────────────────────────────────────
    # FINAL SCORE
    # ──────────────────────────────────────────────────────────────
    total_weight = sum(w for _, w, _ in checks)
    weighted_sum = sum(s * w for s, w, _ in checks)
    raw_100  = weighted_sum / total_weight          # 0-100 internal
    final_score  = round(raw_100)                   # stay on 0-100 scale

    # ATR stop-loss suggestion (informational, doesn't affect score)
    atr = latest["ATR14"]
    signals["Stop_Loss"] = f"ℹ️  Suggested stop-loss: ₹{price - 2*atr:.1f} (2x ATR)"

    # Confidence: all 5 components (MA, MACD, RSI, Volume, 52W) are always present
    # from the DataFrame, so confidence is based on indicator quality
    num_checks = len(checks)
    # Check if key indicators have reasonable (non-NaN) values
    has_valid_sma200 = pd.notna(sma200)
    has_valid_rsi = pd.notna(latest["RSI"])
    has_valid_macd = pd.notna(latest["MACD"])

    if num_checks >= 5 and has_valid_sma200 and has_valid_rsi and has_valid_macd:
        confidence = "HIGH"
    elif num_checks >= 3 and (has_valid_sma200 or has_valid_rsi):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return final_score, signals, confidence



# ─────────────────────────────────────────────────────────────
# EPS GROWTH HELPERS
# ─────────────────────────────────────────────────────────────
def get_eps_growth(ticker_obj):
    """Compute YoY EPS growth. Falls back to annual earnings if info missing."""
    try:
        eg = ticker_obj.info.get("earningsGrowth")
        if eg is not None:
            return eg, "info"
        earnings = ticker_obj.earnings
        if earnings is None or earnings.empty:
            return None, "unavailable"
        earnings = earnings.sort_index(ascending=True)
        if "Earnings" in earnings.columns and len(earnings) >= 2:
            latest_eps = earnings["Earnings"].iloc[-1]
            prev_eps   = earnings["Earnings"].iloc[-2]
            if prev_eps and prev_eps != 0:
                yoy_growth = (latest_eps - prev_eps) / abs(prev_eps)
                return yoy_growth, "computed"
    except Exception:
        pass
    return None, "unavailable"


def score_eps_growth(eps_growth, source):
    if eps_growth is None:
        return None, "ℹ️  EPS growth not available"
    label = "computed YoY" if source == "computed" else "TTM"
    if eps_growth < -0.15:
        return 15, f"❌ EPS declining {eps_growth*100:.1f}% ({label})"
    elif eps_growth < 0:
        return 40, f"⚠️  EPS weakening {eps_growth*100:.1f}% ({label})"
    elif eps_growth < 0.08:
        return 60, f"⚠️  Slow EPS growth {eps_growth*100:.1f}% ({label})"
    elif eps_growth < 0.20:
        return 75, f"✅ Healthy EPS growth {eps_growth*100:.1f}% ({label})"
    else:
        return 90, f"✅ Strong EPS growth {eps_growth*100:.1f}% ({label})"


# ─────────────────────────────────────────────────────────────
# PEG RATIO HELPERS
# ─────────────────────────────────────────────────────────────
def get_peg_ratio(ticker_obj, pe, eps_growth):
    """PEG = PE / (EPS Growth %). Meaningful only for positive, growing earnings."""
    try:
        peg = ticker_obj.info.get("pegRatio")
        if peg is not None and peg > 0:
            return peg, "direct"
        if pe and eps_growth and eps_growth > 0:
            peg = pe / (eps_growth * 100)
            return peg, "computed"
    except Exception:
        pass
    return None, "unavailable"


def score_peg(peg, source):
    if peg is None:
        return None, "ℹ️  PEG not available (negative/no earnings growth)"
    tag = f"(PEG {peg:.2f}, {source})"
    if peg <= 0:
        return None, f"ℹ️  PEG not meaningful (negative earnings) {tag}"
    elif peg < 0.5:
        return 70, f"⚠️  Very low PEG {tag} — cheap but verify earnings quality"
    elif peg < 1.0:
        return 85, f"✅ Attractive PEG {tag} — growth not fully priced in"
    elif peg < 2.0:
        return 65, f"✅ Fair PEG {tag} — reasonably valued"
    elif peg < 3.0:
        return 40, f"⚠️  Elevated PEG {tag} — paying premium for growth"
    else:
        return 20, f"❌ High PEG {tag} — expensive relative to growth"


# ─────────────────────────────────────────────────────────────
# EARNINGS GROWTH HELPERS
# ─────────────────────────────────────────────────────────────
def get_earnings_growth(ticker_obj):
    """Compute net profit growth from income statement with multi-year history."""
    try:
        eg = ticker_obj.info.get("earningsGrowth")
        if eg is not None:
            return {"growth": eg, "source": "TTM (info)", "history": None}
        stmt = ticker_obj.income_stmt
        if stmt is None or stmt.empty:
            stmt = ticker_obj.quarterly_income_stmt
            if stmt is None or stmt.empty:
                return {"growth": None, "source": "unavailable", "history": None}
        net_income_row = None
        for label in ["Net Income", "NetIncome", "Net Income Common Stockholders"]:
            if label in stmt.index:
                net_income_row = stmt.loc[label]
                break
        if net_income_row is None:
            return {"growth": None, "source": "row not found", "history": None}
        net_income_row = net_income_row.sort_index(ascending=True)
        values = pd.to_numeric(net_income_row, errors="coerce").dropna()
        if len(values) < 2:
            return {"growth": None, "source": "insufficient data", "history": None}
        latest = values.iloc[-1]
        prev   = values.iloc[-2]
        growth = (latest - prev) / abs(prev) if prev != 0 else None
        history = {}
        for i in range(1, min(4, len(values))):
            yr_label = values.index[-i].year if hasattr(values.index[-i], 'year') else f"Y-{i}"
            v_curr = values.iloc[-i]
            if i + 1 <= len(values):
                v_prev = values.iloc[-(i + 1)]
                if v_prev != 0:
                    history[str(yr_label)] = round((v_curr - v_prev) / abs(v_prev) * 100, 1)
        return {"growth": growth, "source": "computed (income_stmt)", "history": history}
    except Exception as e:
        return {"growth": None, "source": f"error: {e}", "history": None}


def score_earnings_growth(eg_data):
    growth  = eg_data.get("growth")
    history = eg_data.get("history")
    if growth is None:
        return None, f"ℹ️  Earnings growth not available ({eg_data.get('source')})"
    trend_note = ""
    if history and len(history) >= 2:
        vals = list(history.values())
        if all(v > 0 for v in vals):   trend_note = " | consistently growing ✅"
        elif all(v < 0 for v in vals): trend_note = " | consistently declining ❌"
        else:                           trend_note = " | inconsistent trend ⚠️"
    growth_pct = growth * 100
    history_str = ", ".join([f"{k}: {v:+.1f}%" for k, v in (history or {}).items()])
    suffix = f"{trend_note}" + (f" [{history_str}]" if history_str else "")
    if growth < -0.15:
        return 10,  f"❌ Net profit down {growth_pct:.1f}%{suffix}"
    elif growth < 0:
        return 35,  f"⚠️  Earnings declining {growth_pct:.1f}%{suffix}"
    elif growth < 0.08:
        return 55,  f"⚠️  Weak earnings growth {growth_pct:.1f}%{suffix}"
    elif growth < 0.20:
        return 75,  f"✅ Solid earnings growth {growth_pct:.1f}%{suffix}"
    else:
        return 92,  f"✅ Strong earnings growth {growth_pct:.1f}%{suffix}"


# ─────────────────────────────────────────────────────────────
# FUNDAMENTAL SCORING V2
# ─────────────────────────────────────────────────────────────
def score_fundamentals_v2(stock_data, buy_price=None, risk="MEDIUM"):
    """
    Redesigned fundamental score — 100 point scale.
    6 components with sector-aware thresholds.
    Returns (score 0-100, signals dict, confidence str).
    """
    checks  = []   # (score 0-100, weight, label)
    signals = {}
    sector  = stock_data.get("sector", "default") or "default"

    pe          = stock_data.get("pe")
    pb          = stock_data.get("pb")
    de          = stock_data.get("debt_equity")          # yfinance % format
    roe         = stock_data.get("roe")
    rev_growth  = stock_data.get("revenue_growth")
    earn_data   = stock_data.get("earn_growth_data") or {}
    earn_growth = earn_data.get("growth") if isinstance(earn_data, dict) else None
    earn_hist   = earn_data.get("history") or {}
    eps_raw     = stock_data.get("eps_growth_data")
    if isinstance(eps_raw, tuple):
        eps_growth = eps_raw[0]  # (value, source) tuple
    elif isinstance(eps_raw, dict):
        eps_growth = eps_raw.get("growth")
    else:
        eps_growth = eps_raw
    peg         = stock_data.get("peg")
    cp          = stock_data.get("current_price")
    targets     = stock_data.get("price_targets", {})
    div_yield   = stock_data.get("div_yield")

    # ──────────────────────────────────────────────────────────────
    # 1. VALUATION — 25% weight
    # ──────────────────────────────────────────────────────────────
    if pe is not None:
        try:
            pe = float(pe)
            sector_pe = SECTOR_PE_BENCHMARKS.get(sector, SECTOR_PE_BENCHMARKS["default"])
            pe_ratio  = pe / sector_pe

            if pe_ratio < 0.7:
                pe_score = 90
                signals["PE"] = (
                    f"✅ PE {pe:.1f}x is {(1-pe_ratio)*100:.0f}% below sector avg "
                    f"({sector_pe}x) — undervalued vs peers"
                )
            elif pe_ratio < 0.9:
                pe_score = 75
                signals["PE"] = (
                    f"✅ PE {pe:.1f}x slightly below sector avg ({sector_pe}x) — fair value"
                )
            elif pe_ratio < 1.1:
                pe_score = 60
                signals["PE"] = (
                    f"⚠️  PE {pe:.1f}x in line with sector avg ({sector_pe}x)"
                )
            elif pe_ratio < 1.4:
                pe_score = 40
                signals["PE"] = (
                    f"⚠️  PE {pe:.1f}x is {(pe_ratio-1)*100:.0f}% above sector avg "
                    f"({sector_pe}x) — premium valuation"
                )
            else:
                pe_score = 15
                signals["PE"] = (
                    f"❌ PE {pe:.1f}x is {(pe_ratio-1)*100:.0f}% above sector avg "
                    f"({sector_pe}x) — significantly overvalued vs peers"
                )
            checks.append((pe_score, 15, "PE Ratio"))
        except (TypeError, ValueError):
            pass

    if pb is not None:
        try:
            pb = float(pb)
            if pb < 1.0:
                pb_score = 85
                signals["PB"] = f"✅ PB {pb:.2f}x — trading near/below book value"
            elif pb < 2.5:
                pb_score = 75
                signals["PB"] = f"✅ PB {pb:.2f}x — reasonable"
            elif pb < 4.0:
                pb_score = 55
                signals["PB"] = f"⚠️  PB {pb:.2f}x — premium to book, needs strong ROE"
            elif pb < 6.0:
                pb_score = 35
                signals["PB"] = f"⚠️  PB {pb:.2f}x — expensive on asset basis"
            else:
                pb_score = 15
                signals["PB"] = f"❌ PB {pb:.2f}x — very expensive vs assets"
            checks.append((pb_score, 10, "PB Ratio"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # 2. FINANCIAL HEALTH — 25% weight
    # ──────────────────────────────────────────────────────────────
    if de is not None:
        try:
            de_ratio  = float(de) / 100
            sector_de = SECTOR_DE_BENCHMARKS.get(sector, SECTOR_DE_BENCHMARKS["default"])
            de_rel    = de_ratio / sector_de if sector_de > 0 else 1.0

            if sector in ("Banking", "Financial Services"):
                signals["DE"] = (
                    f"ℹ️  D/E {de_ratio:.1f}x — banking sector, high leverage is normal"
                )
                de_score = 65
            elif de_rel < 0.5:
                de_score = 90
                signals["DE"] = (
                    f"✅ Very low leverage (D/E {de_ratio:.2f}x vs sector norm {sector_de}x) "
                    "— strong balance sheet"
                )
            elif de_rel < 0.9:
                de_score = 75
                signals["DE"] = f"✅ Conservative leverage (D/E {de_ratio:.2f}x)"
            elif de_rel < 1.3:
                de_score = 55
                signals["DE"] = f"⚠️  Average leverage for sector (D/E {de_ratio:.2f}x)"
            elif de_rel < 2.0:
                de_score = 30
                signals["DE"] = (
                    f"⚠️  Above-average leverage (D/E {de_ratio:.2f}x vs sector "
                    f"{sector_de}x) — watch interest coverage"
                )
            else:
                de_score = 10
                signals["DE"] = (
                    f"❌ High leverage vs sector (D/E {de_ratio:.2f}x vs norm {sector_de}x)"
                )
            checks.append((de_score, 15, "Debt/Equity"))
        except (TypeError, ValueError):
            pass

    if roe is not None:
        try:
            roe_pct = float(roe) * 100
            if roe_pct > 25:
                roe_score = 95
                signals["ROE"] = f"✅ Exceptional ROE {roe_pct:.1f}% — world class capital efficiency"
            elif roe_pct > 18:
                roe_score = 80
                signals["ROE"] = f"✅ Strong ROE {roe_pct:.1f}%"
            elif roe_pct > 12:
                roe_score = 65
                signals["ROE"] = f"✅ Decent ROE {roe_pct:.1f}%"
            elif roe_pct > 8:
                roe_score = 45
                signals["ROE"] = f"⚠️  Weak ROE {roe_pct:.1f}% — capital not deployed efficiently"
            elif roe_pct > 0:
                roe_score = 25
                signals["ROE"] = f"❌ Very low ROE {roe_pct:.1f}%"
            else:
                roe_score = 5
                signals["ROE"] = f"❌ Negative ROE {roe_pct:.1f}% — destroying shareholder value"
            checks.append((roe_score, 10, "ROE"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # 3. GROWTH QUALITY — 25% weight
    # ──────────────────────────────────────────────────────────────
    if rev_growth is not None:
        try:
            rv = float(rev_growth) * 100
            if rv > 20:
                rev_score = 90
                signals["Rev_Growth"] = f"✅ Strong revenue growth {rv:.1f}%"
            elif rv > 12:
                rev_score = 75
                signals["Rev_Growth"] = f"✅ Healthy revenue growth {rv:.1f}%"
            elif rv > 5:
                rev_score = 60
                signals["Rev_Growth"] = f"⚠️  Moderate revenue growth {rv:.1f}%"
            elif rv > 0:
                rev_score = 40
                signals["Rev_Growth"] = f"⚠️  Sluggish revenue growth {rv:.1f}%"
            else:
                rev_score = 15
                signals["Rev_Growth"] = f"❌ Revenue declining {rv:.1f}%"
            checks.append((rev_score, 10, "Revenue Growth"))
        except (TypeError, ValueError):
            pass

    if earn_growth is not None:
        try:
            eg = float(earn_growth) * 100
            trend_adj  = 0
            trend_note = ""
            if earn_hist and len(earn_hist) >= 2:
                vals = list(earn_hist.values())
                if all(v > 5 for v in vals):
                    trend_adj  = +10
                    trend_note = " | 3yr consistent growth ✅"
                elif all(v < 0 for v in vals):
                    trend_adj  = -10
                    trend_note = " | 3yr consistent decline ❌"
                elif vals[-1] > vals[0]:
                    trend_adj  = +5
                    trend_note = " | trend improving"
                else:
                    trend_note = " | inconsistent"

            if eg > 20:
                base_score = 90
                signals["Earn_Growth"] = f"✅ Strong earnings growth {eg:.1f}%{trend_note}"
            elif eg > 10:
                base_score = 75
                signals["Earn_Growth"] = f"✅ Healthy earnings growth {eg:.1f}%{trend_note}"
            elif eg > 0:
                base_score = 50
                signals["Earn_Growth"] = f"⚠️  Weak earnings growth {eg:.1f}%{trend_note}"
            else:
                base_score = 15
                signals["Earn_Growth"] = f"❌ Earnings declining {eg:.1f}%{trend_note}"

            final_eg_score = max(0, min(100, base_score + trend_adj))
            checks.append((final_eg_score, 15, "Earnings Growth"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # 4. PEG RATIO — 10% weight
    # ──────────────────────────────────────────────────────────────
    if peg is not None:
        try:
            peg = float(peg)
            if peg > 0:
                if peg < 0.5:
                    peg_score = 70
                    signals["PEG"] = f"⚠️  Very low PEG {peg:.2f} — verify earnings estimates"
                elif peg < 1.0:
                    peg_score = 88
                    signals["PEG"] = f"✅ Attractive PEG {peg:.2f} — undervalued vs growth"
                elif peg < 1.5:
                    peg_score = 70
                    signals["PEG"] = f"✅ Fair PEG {peg:.2f}"
                elif peg < 2.5:
                    peg_score = 45
                    signals["PEG"] = f"⚠️  Elevated PEG {peg:.2f} — growth premium priced in"
                else:
                    peg_score = 20
                    signals["PEG"] = f"❌ High PEG {peg:.2f} — expensive vs growth"
                checks.append((peg_score, 10, "PEG Ratio"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # 5. ANALYST TARGET UPSIDE — 10% weight
    # ──────────────────────────────────────────────────────────────
    if isinstance(targets, dict) and cp:
        try:
            mean_t = targets.get("mean")
            high_t = targets.get("high")
            if mean_t and float(mean_t) > 0:
                cp_f    = float(cp)
                mean_t  = float(mean_t)
                upside  = (mean_t - cp_f) / cp_f * 100
                if high_t and cp_f > float(high_t):
                    tgt_score = 15
                    signals["Target"] = f"❌ CMP above even highest target ₹{high_t:.0f}"
                elif upside > 25:
                    tgt_score = 90
                    signals["Target"] = f"✅ {upside:.1f}% upside to mean target ₹{mean_t:.0f}"
                elif upside > 10:
                    tgt_score = 70
                    signals["Target"] = f"✅ {upside:.1f}% upside to mean target ₹{mean_t:.0f}"
                elif upside > 0:
                    tgt_score = 50
                    signals["Target"] = f"⚠️  Limited upside {upside:.1f}% to mean target ₹{mean_t:.0f}"
                else:
                    tgt_score = 25
                    signals["Target"] = f"⚠️  CMP {abs(upside):.1f}% above mean target ₹{mean_t:.0f}"
                checks.append((tgt_score, 10, "Analyst Target"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # 6. P&L ON POSITION — 5% weight
    # ──────────────────────────────────────────────────────────────
    if cp and buy_price:
        try:
            pnl = (float(cp) - float(buy_price)) / float(buy_price) * 100
            if pnl > 20:
                pnl_score = 85
                signals["PnL"] = f"✅ Up {pnl:.1f}% from buy price ₹{buy_price}"
            elif pnl > 0:
                pnl_score = 65
                signals["PnL"] = f"✅ Up {pnl:.1f}% from buy price ₹{buy_price}"
            elif pnl > -10:
                pnl_score = 45
                signals["PnL"] = f"⚠️  Down {abs(pnl):.1f}% from buy price ₹{buy_price}"
            elif pnl > -20:
                pnl_score = 25
                signals["PnL"] = f"⚠️  Down {abs(pnl):.1f}% — approaching stop-loss territory"
            else:
                pnl_score = 10
                signals["PnL"] = f"❌ Down {abs(pnl):.1f}% — significant loss, review thesis"
            checks.append((pnl_score, 5, "Position P&L"))
        except (TypeError, ValueError):
            pass

    # ──────────────────────────────────────────────────────────────
    # FINAL SCORE — weighted average of available checks only
    # ──────────────────────────────────────────────────────────────
    if not checks:
        signals["_summary"] = "⚠️  No fundamental data available"
        return 50, signals, "LOW"

    total_weight  = sum(w for _, w, _ in checks)
    weighted_sum  = sum(s * w for s, w, _ in checks)
    final_score   = round(weighted_sum / total_weight)

    max_weight    = 100  # if all checks present
    data_coverage = total_weight / max_weight * 100
    confidence    = (
        "HIGH"   if data_coverage >= 75 else
        "MEDIUM" if data_coverage >= 50 else
        "LOW"
    )

    checks_used = ", ".join(label for _, _, label in checks)
    signals["_summary"] = (
        f"ℹ️  Scored on: {checks_used} | "
        f"Coverage: {data_coverage:.0f}% | Confidence: {confidence}"
    )

    return final_score, signals, confidence


# ─────────────────────────────────────────────────────────────
# TECHNICAL COMMENTARY
# ─────────────────────────────────────────────────────────────
def get_technical_commentary(data: dict) -> dict:
    commentary = {}
    price  = data["current_price"]
    ema20  = data["ema20"]
    ema50  = data["ema50"]
    sma100 = data["sma100"]
    sma200 = data["sma200"]
    rsi    = data["rsi"]
    macd   = data["macd"]
    macd_s = data["macd_signal"]
    hi52   = data["52w_high"]
    lo52   = data["52w_low"]
    pos52  = data["52w_pos"]
    dist52 = data["dist_from_high"]

    # ── Current Price vs MAs ──────────────────────────────────────
    above_emas = price > ema20 and price > ema50
    below_emas = price < ema20 and price < ema50
    above_long = price > sma100 and price > sma200

    if above_emas and above_long:
        commentary["price"] = {
            "text": "Price is above all key moving averages — bullish structure intact.",
            "color": "green"
        }
    elif price > ema20 and price < ema50:
        commentary["price"] = {
            "text": "Price above EMA20 but below EMA50 — short-term recovery, medium-term still weak.",
            "color": "orange"
        }
    elif price < ema20 and price < ema50 and price < sma200:
        commentary["price"] = {
            "text": "Price below all moving averages — stock in a confirmed downtrend.",
            "color": "red"
        }
    elif price < ema50 and price > sma200:
        commentary["price"] = {
            "text": "Price below short-term MAs but above SMA200 — medium-term trend intact, "
                    "short-term pullback. Watch EMA50 recovery.",
            "color": "orange"
        }
    else:
        commentary["price"] = {
            "text": "Mixed MA signals — no clear directional bias.",
            "color": "orange"
        }

    # ── EMA 20 ────────────────────────────────────────────────────
    ema20_gap = (price - ema20) / ema20 * 100
    if price > ema20:
        commentary["ema20"] = {
            "text": f"Price {ema20_gap:.1f}% above EMA20 — short-term momentum positive.",
            "color": "green"
        }
    elif abs(ema20_gap) < 0.5:
        commentary["ema20"] = {
            "text": "Price hugging EMA20 — at a decision point, watch next 2-3 sessions.",
            "color": "orange"
        }
    else:
        commentary["ema20"] = {
            "text": f"Price {abs(ema20_gap):.1f}% below EMA20 — short-term trend negative.",
            "color": "red"
        }

    # ── EMA 50 ────────────────────────────────────────────────────
    ema50_gap = (price - ema50) / ema50 * 100
    if price > ema50:
        commentary["ema50"] = {
            "text": "Holding above EMA50 — medium-term trend supportive.",
            "color": "green"
        }
    elif abs(ema50_gap) < 1.5:
        commentary["ema50"] = {
            "text": f"Just {abs(ema50_gap):.1f}% below EMA50 — critical support level. "
                    f"A close above \u20b9{ema50:.0f} needed to confirm recovery.",
            "color": "orange"
        }
    else:
        commentary["ema50"] = {
            "text": f"Price {abs(ema50_gap):.1f}% below EMA50 — medium-term momentum lost. "
                    "EMA50 now acts as resistance.",
            "color": "red"
        }

    # ── SMA 100 ───────────────────────────────────────────────────
    sma100_gap = (price - sma100) / sma100 * 100
    if price > sma100:
        commentary["sma100"] = {
            "text": "Above SMA100 — trend structure healthy for medium-term hold.",
            "color": "green"
        }
    elif abs(sma100_gap) < 3:
        commentary["sma100"] = {
            "text": f"Just below SMA100 (\u20b9{sma100:.0f}) — key medium-term level. "
                    "Failure to reclaim this is a warning sign.",
            "color": "orange"
        }
    else:
        commentary["sma100"] = {
            "text": f"Price {abs(sma100_gap):.1f}% below SMA100 — medium-term trend broken. "
                    "This level is now resistance.",
            "color": "red"
        }

    # ── SMA 200 ───────────────────────────────────────────────────
    sma200_gap = (price - sma200) / sma200 * 100
    if price > sma200:
        commentary["sma200"] = {
            "text": "Above SMA200 — long-term bull trend intact. "
                    "This is the most important support level to hold.",
            "color": "green"
        }
    elif abs(sma200_gap) < 3:
        commentary["sma200"] = {
            "text": f"Dangerously close to SMA200 (\u20b9{sma200:.0f}). "
                    "A weekly close below this triggers a long-term trend reversal alert.",
            "color": "orange"
        }
    else:
        commentary["sma200"] = {
            "text": "Below SMA200 — long-term trend broken. High risk for medium-term holders.",
            "color": "red"
        }

    # ── RSI ───────────────────────────────────────────────────────
    if rsi >= 70:
        commentary["rsi"] = {
            "text": f"Overbought ({rsi:.1f}). High risk of short-term pullback. "
                    "Consider booking partial profits.",
            "color": "red"
        }
    elif rsi >= 60:
        commentary["rsi"] = {
            "text": f"Strong momentum ({rsi:.1f}) — not yet overbought. Trend has room to continue.",
            "color": "green"
        }
    elif rsi >= 50:
        commentary["rsi"] = {
            "text": f"Neutral momentum ({rsi:.1f}). Bulls and bears are evenly matched. "
                    "A move above 55 would signal recovery.",
            "color": "orange"
        }
    elif rsi >= 40:
        commentary["rsi"] = {
            "text": f"Weak momentum ({rsi:.1f}). Selling pressure dominant but not extreme. "
                    "Watch for divergence with price.",
            "color": "orange"
        }
    elif rsi >= 30:
        commentary["rsi"] = {
            "text": f"Approaching oversold ({rsi:.1f}). Short-term bounce likely but "
                    "doesn't confirm trend reversal.",
            "color": "orange"
        }
    else:
        commentary["rsi"] = {
            "text": f"Oversold ({rsi:.1f}). Technically due for a bounce. "
                    "Only buy if fundamentals support it.",
            "color": "red"
        }

    # ── MACD ─────────────────────────────────────────────────────
    macd_above_signal = macd > macd_s
    both_negative     = macd < 0 and macd_s < 0
    both_positive     = macd > 0 and macd_s > 0

    if both_positive and macd_above_signal:
        commentary["macd"] = {
            "text": "MACD above signal and both positive — strong bullish momentum confirmed.",
            "color": "green"
        }
    elif macd_above_signal and both_negative:
        commentary["macd"] = {
            "text": "MACD crossing above signal line — early recovery signal. "
                    "However both lines are still negative, so not confirmed bullish yet. "
                    "Watch for a zero-line crossover.",
            "color": "orange"
        }
    elif not macd_above_signal and both_negative:
        commentary["macd"] = {
            "text": "MACD below signal and both negative — bearish momentum active. "
                    "No recovery signal yet.",
            "color": "red"
        }
    elif not macd_above_signal and both_positive:
        commentary["macd"] = {
            "text": "MACD crossing below signal — momentum fading. "
                    "Watch for continuation — possible short-term top.",
            "color": "orange"
        }
    else:
        commentary["macd"] = {
            "text": "MACD at crossover point — direction change imminent.",
            "color": "orange"
        }

    # ── 52W Range ─────────────────────────────────────────────────
    if pos52 is None or dist52 is None:
        commentary["52w"] = {"text": "52-week range data not available.", "color": "grey"}
    elif pos52 >= 80:
        commentary["52w"] = {
            "text": f"Near 52W high — strong stock. Momentum favors continuation "
                    "but risk of profit-booking at resistance.",
            "color": "green"
        }
    elif pos52 >= 50:
        commentary["52w"] = {
            "text": f"Upper half of 52W range ({pos52:.1f}%) — stock holding up well "
                    f"despite {dist52:.1f}% correction from peak.",
            "color": "green"
        }
    elif pos52 >= 30:
        commentary["52w"] = {
            "text": f"Lower half of 52W range ({pos52:.1f}%) and {dist52:.1f}% off peak. "
                    "Stock has corrected meaningfully. Potential value zone IF fundamentals hold.",
            "color": "orange"
        }
    elif pos52 >= 15:
        commentary["52w"] = {
            "text": f"Near the lower end of 52W range ({pos52:.1f}%) — "
                    "significant underperformance. High risk, review fundamentals carefully.",
            "color": "red"
        }
    else:
        commentary["52w"] = {
            "text": f"At/near 52W low ({pos52:.1f}%) — stock in distress. "
                    "Strong sell unless there is a specific recovery catalyst.",
            "color": "red"
        }

    return commentary


# ─────────────────────────────────────────────────────────────
# FUNDAMENTAL COMMENTARY
# ─────────────────────────────────────────────────────────────
def get_fundamental_commentary(data: dict) -> dict:
    commentary = {}

    pe          = data.get("pe")
    pb          = data.get("pb")
    de          = data.get("de")
    roe         = data.get("roe")
    rev_growth  = data.get("rev_growth")
    target      = data.get("mean_target")
    price       = data.get("current_price")
    eps_growth  = data.get("eps_growth")
    peg         = data.get("peg")
    earn_growth = data.get("earn_growth")

    # ── PE Ratio ──────────────────────────────────────────────────
    if pe is None:
        commentary["pe"] = {"text": "PE not available.", "color": "grey"}
    elif pe < 10:
        commentary["pe"] = {
            "text": f"PE of {pe:.1f}x is low — potentially undervalued. "
                    "Verify that earnings haven't fallen sharply.",
            "color": "green"
        }
    elif pe < 20:
        commentary["pe"] = {
            "text": f"PE of {pe:.1f}x is reasonable. "
                    "Fair valuation for a large-cap — not cheap, not expensive.",
            "color": "green"
        }
    elif pe < 30:
        commentary["pe"] = {
            "text": f"PE of {pe:.1f}x is moderate. Acceptable if earnings growth "
                    "is 15%+. Check PEG ratio to confirm.",
            "color": "orange"
        }
    elif pe < 50:
        commentary["pe"] = {
            "text": f"PE of {pe:.1f}x is elevated. Market is pricing in strong "
                    "future growth. Any earnings miss could cause sharp correction.",
            "color": "orange"
        }
    else:
        commentary["pe"] = {
            "text": f"PE of {pe:.1f}x is very high. Significant growth already "
                    "priced in. High valuation risk.",
            "color": "red"
        }

    # ── PB Ratio ──────────────────────────────────────────────────
    if pb is None:
        commentary["pb"] = {"text": "P/B not available.", "color": "grey"}
    elif pb < 1.0:
        commentary["pb"] = {
            "text": f"P/B of {pb:.2f}x — trading below book value. "
                    "Either a hidden gem or the market expects asset write-downs.",
            "color": "green"
        }
    elif pb < 2.5:
        commentary["pb"] = {
            "text": f"P/B of {pb:.2f}x — reasonable for a profitable large-cap.",
            "color": "green"
        }
    elif pb < 5.0:
        commentary["pb"] = {
            "text": f"P/B of {pb:.2f}x — premium valuation. "
                    "Justified only if ROE is consistently high (>20%).",
            "color": "orange"
        }
    else:
        commentary["pb"] = {
            "text": f"P/B of {pb:.2f}x — expensive on an asset basis. "
                    "Company must justify this with strong earnings quality.",
            "color": "red"
        }

    # ── Debt to Equity ────────────────────────────────────────────
    if de is None:
        commentary["de"] = {"text": "D/E not available.", "color": "grey"}
    else:
        de_ratio = de / 100
        if de_ratio < 0.3:
            commentary["de"] = {
                "text": f"Very low leverage (D/E: {de_ratio:.2f}x) — "
                        "strong balance sheet, no debt risk.",
                "color": "green"
            }
        elif de_ratio < 0.8:
            commentary["de"] = {
                "text": f"Manageable debt (D/E: {de_ratio:.2f}x) — "
                        "healthy capital structure.",
                "color": "green"
            }
        elif de_ratio < 1.5:
            commentary["de"] = {
                "text": f"Moderate leverage (D/E: {de_ratio:.2f}x) — "
                        "watch interest coverage, especially if rates stay high.",
                "color": "orange"
            }
        elif de_ratio < 2.5:
            commentary["de"] = {
                "text": f"High leverage (D/E: {de_ratio:.2f}x) — "
                        "earnings vulnerable to rate hikes and economic slowdown.",
                "color": "red"
            }
        else:
            commentary["de"] = {
                "text": f"Very high leverage (D/E: {de_ratio:.2f}x) — "
                        "significant financial risk. Review debt repayment schedule.",
                "color": "red"
            }

    # ── ROE ───────────────────────────────────────────────────────
    if roe is None:
        commentary["roe"] = {
            "text": "ROE not available — may indicate recent restructuring or data gap.",
            "color": "grey"
        }
    elif roe < 0:
        commentary["roe"] = {
            "text": f"Negative ROE ({roe*100:.1f}%) — company destroying shareholder value. Red flag.",
            "color": "red"
        }
    elif roe < 0.10:
        commentary["roe"] = {
            "text": f"Low ROE ({roe*100:.1f}%) — poor capital efficiency. "
                    "Management not generating adequate returns.",
            "color": "orange"
        }
    elif roe < 0.20:
        commentary["roe"] = {
            "text": f"Decent ROE ({roe*100:.1f}%) — adequate returns on equity.",
            "color": "green"
        }
    else:
        commentary["roe"] = {
            "text": f"Strong ROE ({roe*100:.1f}%) — excellent capital efficiency. "
                    "Management creating real value.",
            "color": "green"
        }

    # ── Revenue Growth ────────────────────────────────────────────
    if rev_growth is None:
        commentary["rev_growth"] = {"text": "Revenue growth not available.", "color": "grey"}
    elif rev_growth < -0.05:
        commentary["rev_growth"] = {
            "text": f"Revenue declining {rev_growth*100:.1f}% — top-line under pressure. "
                    "Serious concern for medium-term outlook.",
            "color": "red"
        }
    elif rev_growth < 0.05:
        commentary["rev_growth"] = {
            "text": f"Flat revenue growth ({rev_growth*100:.1f}%) — "
                    "business not growing. Margin expansion needed to justify hold.",
            "color": "orange"
        }
    elif rev_growth < 0.12:
        commentary["rev_growth"] = {
            "text": f"Moderate revenue growth ({rev_growth*100:.1f}%) — "
                    "steady but not exceptional. In line with large-cap expectations.",
            "color": "green"
        }
    elif rev_growth < 0.25:
        commentary["rev_growth"] = {
            "text": f"Strong revenue growth ({rev_growth*100:.1f}%) — "
                    "business scaling well. Positive for medium-term.",
            "color": "green"
        }
    else:
        commentary["rev_growth"] = {
            "text": f"Exceptional revenue growth ({rev_growth*100:.1f}%) — "
                    "high growth but verify margins are not being sacrificed.",
            "color": "green"
        }

    # ── Analyst Mean Target ───────────────────────────────────────
    if target and price:
        upside = (target - price) / price * 100
        if upside > 25:
            commentary["target"] = {
                "text": f"Significant analyst upside of {upside:.1f}% to mean target \u20b9{target:.0f}. "
                        "Strong consensus for appreciation — but verify recency of estimates.",
                "color": "green"
            }
        elif upside > 10:
            commentary["target"] = {
                "text": f"Reasonable upside of {upside:.1f}% to mean target \u20b9{target:.0f}. "
                        "Analysts see value at current price.",
                "color": "green"
            }
        elif upside > 0:
            commentary["target"] = {
                "text": f"Limited upside of {upside:.1f}% to mean target \u20b9{target:.0f}. "
                        "Most of the value may already be priced in.",
                "color": "orange"
            }
        elif upside > -10:
            commentary["target"] = {
                "text": f"CMP is {abs(upside):.1f}% above mean analyst target \u20b9{target:.0f}. "
                        "Stock running ahead of analyst expectations.",
                "color": "orange"
            }
        else:
            commentary["target"] = {
                "text": f"CMP is {abs(upside):.1f}% above even mean analyst target. "
                        "Technically overvalued vs analyst consensus — high exit risk.",
                "color": "red"
            }

    # ── EPS Growth ────────────────────────────────────────────────
    if eps_growth is None:
        commentary["eps_growth"] = {"text": "EPS growth not available.", "color": "grey"}
    elif eps_growth < -0.10:
        commentary["eps_growth"] = {
            "text": f"EPS declining {eps_growth*100:.1f}% — earnings deteriorating. "
                    "High risk for medium-term holders.",
            "color": "red"
        }
    elif eps_growth < 0:
        commentary["eps_growth"] = {
            "text": f"Slight EPS decline ({eps_growth*100:.1f}%) — watch next quarter "
                    "for confirmation of trend.",
            "color": "orange"
        }
    elif eps_growth < 0.05:
        commentary["eps_growth"] = {
            "text": f"EPS growth nearly flat ({eps_growth*100:.1f}%) — earnings stagnating. "
                    "Revenue growth not converting to profit growth. "
                    "Margin compression likely.",
            "color": "orange"
        }
    elif eps_growth < 0.15:
        commentary["eps_growth"] = {
            "text": f"Moderate EPS growth ({eps_growth*100:.1f}%) — "
                    "earnings growing but slowly. Acceptable for a large conglomerate.",
            "color": "green"
        }
    else:
        commentary["eps_growth"] = {
            "text": f"Strong EPS growth ({eps_growth*100:.1f}%) — "
                    "earnings momentum healthy. Supports current valuation.",
            "color": "green"
        }

    # ── PEG Ratio ─────────────────────────────────────────────────
    if peg is None:
        commentary["peg"] = {"text": "PEG not available.", "color": "grey"}
    elif peg <= 0:
        commentary["peg"] = {
            "text": "PEG not meaningful — negative or zero earnings growth.",
            "color": "grey"
        }
    elif peg < 0.5:
        commentary["peg"] = {
            "text": f"Very low PEG ({peg:.2f}) — either deeply undervalued "
                    "or earnings growth estimates are too optimistic. Verify.",
            "color": "orange"
        }
    elif peg < 1.0:
        commentary["peg"] = {
            "text": f"Attractive PEG of {peg:.2f} — stock is undervalued relative "
                    "to its earnings growth. Classic value zone for medium-term entry.",
            "color": "green"
        }
    elif peg < 2.0:
        commentary["peg"] = {
            "text": f"Fair PEG of {peg:.2f} — reasonably priced for the growth on offer.",
            "color": "green"
        }
    elif peg < 3.0:
        commentary["peg"] = {
            "text": f"Elevated PEG of {peg:.2f} — paying a premium for growth. "
                    "Only hold if growth visibility is high.",
            "color": "orange"
        }
    else:
        commentary["peg"] = {
            "text": f"High PEG of {peg:.2f} — significantly overpriced vs growth. "
                    "Valuation risk is high.",
            "color": "red"
        }

    # ── Earnings Growth ───────────────────────────────────────────
    if earn_growth is not None and eps_growth is not None:
        divergence = abs(earn_growth - eps_growth)
        if divergence > 0.10:
            commentary["earn_growth"] = {
                "text": f"Net profit growth ({earn_growth*100:.1f}%) diverges from EPS growth "
                        f"({eps_growth*100:.1f}%) — likely due to share buybacks or dilution. "
                        "Investigate further.",
                "color": "orange"
            }
        else:
            # Reuse eps_growth commentary text but prefix with earnings growth figure
            base = commentary.get("eps_growth", {}).get("text", "")
            base_color = commentary.get("eps_growth", {}).get("color", "grey")
            commentary["earn_growth"] = {
                "text": f"Earnings growth ({earn_growth*100:.1f}%) in line with EPS trend. " + base,
                "color": base_color
            }
    elif earn_growth is not None:
        commentary["earn_growth"] = {"text": "Earnings growth data available but EPS growth missing for comparison.", "color": "grey"}

    return commentary


def analyze_stock(ticker: str) -> dict:
    """
    Analyzes a given stock ticker and returns its classification 
    ("HOLD", "WARNING", "SELL") along with relevant fundamentals and indicator data,
    based on a 100-point composite score (Tech/40 + Fund/40 + Sent/20).
    """
    try:
        stock = yf.Ticker(ticker)
        # Get 1 year of daily history
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 200:
            return {"error": "Not enough historical data (need at least 200 days)."}
        
        info = stock.info
        
        # --- 1. Technical Analysis (Max 40 points) ---
        # Compute all technical indicators
        hist['EMA_20'] = ta.trend.ema_indicator(hist['Close'], window=20)
        hist['EMA_50'] = ta.trend.ema_indicator(hist['Close'], window=50)
        hist['SMA_100'] = ta.trend.sma_indicator(hist['Close'], window=100)
        hist['SMA_200'] = ta.trend.sma_indicator(hist['Close'], window=200)
        hist['RSI'] = ta.momentum.rsi(hist['Close'], window=14)
        macd_ind = ta.trend.MACD(hist['Close'])
        hist['MACD'] = macd_ind.macd()
        hist['MACD_Signal'] = macd_ind.macd_signal()
        hist['MACD_Hist'] = macd_ind.macd_diff()
        hist['Vol_Ratio'] = hist['Volume'] / hist['Volume'].rolling(20).mean()
        hist['ATR14'] = ta.volatility.average_true_range(
            hist['High'], hist['Low'], hist['Close'], window=14
        )

        latest = hist.iloc[-1]
        ema_20 = latest['EMA_20']
        ema_50 = latest['EMA_50']
        sma_100 = latest['SMA_100']
        sma_200 = latest['SMA_200']
        rsi = latest['RSI']
        macd_val = latest['MACD']
        macd_signal = latest['MACD_Signal']
        current_price = latest['Close']

        # 52-Week High/Low from price history
        rolling_high = hist['High'].rolling(252, min_periods=200).max()
        rolling_low  = hist['Low'].rolling(252, min_periods=200).min()
        high_52w = rolling_high.iloc[-1]
        low_52w  = rolling_low.iloc[-1]
        range_52w_pos    = None
        pct_from_high_52w = None
        pct_from_low_52w  = None
        if pd.notna(high_52w) and pd.notna(low_52w) and (high_52w - low_52w) > 0:
            range_52w_pos     = (current_price - low_52w) / (high_52w - low_52w) * 100
            pct_from_high_52w = (high_52w - current_price) / high_52w * 100
            pct_from_low_52w  = (current_price - low_52w)  / low_52w  * 100

        # Add 52W position as a column for score_technicals_v2
        range_span = rolling_high - rolling_low
        hist['52W_Pos'] = np.where(range_span > 0, (hist['Close'] - rolling_low) / range_span * 100, 50)

        # Score technicals using v2 weighted scoring (returns 0-100)
        tech_score, tech_signals, tech_confidence = score_technicals_v2(hist)

        # --- 2. Fundamental Analysis (Max 40 points via score_fundamentals_v2) ---
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        debt_to_equity = info.get('debtToEquity')
        roe = info.get('returnOnEquity')
        rev_growth = info.get('revenueGrowth')
        earn_growth_info = info.get('earningsGrowth')

        # Fetch enhanced metrics (still needed for commentary + output)
        eps_growth_val, eps_growth_src = get_eps_growth(stock)
        peg_val, peg_src = get_peg_ratio(stock, pe_ratio, eps_growth_val)
        _, peg_signal = score_peg(peg_val, peg_src)
        _, eps_signal = score_eps_growth(eps_growth_val, eps_growth_src)
        eg_data = get_earnings_growth(stock)
        _, eg_signal = score_earnings_growth(eg_data)

        fund_stock_data = {
            "sector":          info.get("sector", "default"),
            "pe":              pe_ratio,
            "pb":              pb_ratio,
            "debt_equity":     debt_to_equity,
            "roe":             roe,
            "revenue_growth":  rev_growth,
            "earn_growth_data": eg_data,
            "eps_growth_data": (eps_growth_val, eps_growth_src),
            "peg":             peg_val,
            "current_price":   current_price,
            "price_targets": {
                "high": info.get("targetHighPrice"),
                "mean": info.get("targetMeanPrice"),
            },
        }

        raw_fund_score, fund_signals, fund_confidence = score_fundamentals_v2(
            fund_stock_data, buy_price=None
        )
        # Keep on 0-100 scale
        fund_score = raw_fund_score

        # --- 3. Sentiment Analysis (Max 20 points) ---
        sent_score = 0
        sent_points_available = 0
        
        try:
            recoms = stock.recommendations
        except Exception:
            recoms = None
            
        # Parse recent news (last 10 days)
        recent_news = []
        try:
            news_raw = stock.news
            if news_raw:
                from datetime import datetime, timedelta, timezone
                now = datetime.now(timezone.utc)
                ten_days_ago = now - timedelta(days=10)
                for item in news_raw:
                    content = item.get('content', item)
                    pubDate_str = content.get('pubDate')
                    if pubDate_str:
                        try:
                            # e.g. "2026-03-24T10:06:43Z"
                            pub_date = datetime.strptime(pubDate_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            if pub_date >= ten_days_ago:
                                url = content.get('canonicalUrl', {}).get('url', '') if isinstance(content.get('canonicalUrl'), dict) else ''
                                recent_news.append({
                                    "title": content.get('title', ''),
                                    "summary": content.get('summary', ''),
                                    "url": url,
                                    "date": pub_date.strftime("%b %d, %Y"),
                                    "timestamp": pub_date.timestamp()
                                })
                        except Exception:
                            pass
                # Sort from latest to oldest
                recent_news.sort(key=lambda x: x['timestamp'], reverse=True)
        except Exception:
            pass
            
        # Calculate Trailing Returns
        trailing_returns = {}
        if len(hist) > 0:
            periods = {
                '3 Days': 3,
                '1 Week': 5,
                '2 Weeks': 10,
                '1 Month': 21,
                '2 Months': 42,
                '3 Months': 63,
                '6 Months': 126,
                '1 Year': min(252, len(hist)-1)
            }
            for label, days in periods.items():
                if len(hist) > days:
                    past_price = hist['Close'].iloc[-(days+1)]
                    pct_change = ((current_price - past_price) / past_price) * 100
                    trailing_returns[label] = pct_change
                else:
                    trailing_returns[label] = None
                    
        # Calculate Predictive Trend
        pred_map = {
            '3D': trailing_returns.get('3 Days'),
            '1W': trailing_returns.get('1 Week'),
            '2W': trailing_returns.get('2 Weeks'),
            '1M': trailing_returns.get('1 Month'),
            '2M': trailing_returns.get('2 Months'),
            '3M': trailing_returns.get('3 Months'),
            '6M': trailing_returns.get('6 Months'),
            '1Y': trailing_returns.get('1 Year'),
        }
        predictive_trend = calculate_predictive_trend_score(pred_map, raw_returns=pred_map)
            
        # Collect data for v2 sentiment score
        target_mean = info.get('targetMeanPrice')
        
        try:
            eps_trend = stock.eps_trend
        except Exception:
            eps_trend = None
            
        try:
            major_holders = stock.major_holders
        except Exception:
            major_holders = None
            
        try:
            insider_tx = stock.insider_transactions
        except Exception:
            insider_tx = None

        stock_data = {
            "eps_trend": eps_trend,
            "major_holders": major_holders,
            "insider_tx": insider_tx,
            "price_targets": {
                "high": info.get("targetHighPrice"),
                "mean": target_mean,
            },
            "current_price": current_price
        }

        raw_sent_score, sentiment_signals, confidence = score_sentiment_v2(stock_data)
        # Keep on 0-100 scale
        sent_score = raw_sent_score
            
        # --- Final Scoring (Tech 50% + Fund 35% + Sent 15%) ---
        total_score = round(tech_score * 0.50 + fund_score * 0.35 + sent_score * 0.15)
        
        if total_score >= HOLD_THRESHOLD:
            classification = "Hold"
        elif total_score >= WARNING_THRESHOLD:
            classification = "Warning"
        else:
            classification = "Sell"
            
        severity_map = {"Sell": 1, "Warning": 2, "Hold": 3}
        severity = severity_map[classification]
        
        # ── Build Commentary ──────────────────────────────────────
        tech_commentary = get_technical_commentary({
            "current_price": current_price,
            "ema20": ema_20,
            "ema50": ema_50,
            "sma100": sma_100,
            "sma200": sma_200,
            "rsi": rsi,
            "macd": macd_val if pd.notna(macd_val) else 0.0,
            "macd_signal": macd_signal if pd.notna(macd_signal) else 0.0,
            "52w_high": high_52w,
            "52w_low": low_52w,
            "52w_pos": range_52w_pos,
            "dist_from_high": pct_from_high_52w,
        })

        eg_growth_val = eg_data.get("growth") if eg_data else None
        fund_commentary = get_fundamental_commentary({
            "pe": float(pe_ratio) if pe_ratio is not None else None,
            "pb": float(pb_ratio) if pb_ratio is not None else None,
            "de": float(debt_to_equity) if debt_to_equity is not None else None,
            "roe": roe,
            "rev_growth": rev_growth,
            "mean_target": target_mean,
            "current_price": current_price,
            "eps_growth": eps_growth_val,
            "peg": peg_val,
            "earn_growth": eg_growth_val,
        })

        return {
            "error": None,
            "classification": classification,
            "severity": severity,
            "score": int(total_score),
            "tech_score": int(round(tech_score)),
            "fund_score": int(round(fund_score)),
            "sent_score": int(round(sent_score)),
            "tech_confidence": tech_confidence,
            "fund_confidence": fund_confidence,
            "sentiment_confidence": confidence,
            "trend_confidence": predictive_trend.get("confidence", "LOW"),
            "price": current_price,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "sma_100": sma_100,
            "sma_200": sma_200,
            "rsi": rsi,
            "macd": macd_val,
            "macd_signal": macd_signal,
            "macd_hist": latest['MACD_Hist'],
            "vol_ratio": latest['Vol_Ratio'],
            "atr": latest['ATR14'],
            "high_52w": high_52w,
            "low_52w": low_52w,
            "range_52w_pos": range_52w_pos,
            "pct_from_high_52w": pct_from_high_52w,
            "pct_from_low_52w": pct_from_low_52w,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "debt_to_equity": debt_to_equity,
            "roe": roe,
            "rev_growth": rev_growth,
            "target_mean": target_mean,
            "eps_growth": eps_growth_val,
            "eps_growth_src": eps_growth_src,
            "eps_signal": eps_signal,
            "peg": peg_val,
            "peg_src": peg_src,
            "peg_signal": peg_signal,
            "earnings_growth_data": eg_data,
            "eg_signal": eg_signal,
            "recommendations": recoms,
            "recent_news": recent_news,
            "trailing_returns": trailing_returns,
            "predictive_trend": predictive_trend,
            "sentiment_signals": sentiment_signals,
            "tech_signals": tech_signals,
            "fund_signals": fund_signals,
            "tech_commentary": tech_commentary,
            "fund_commentary": fund_commentary,
            "history": hist
        }

    except Exception as e:
        return {"error": str(e)}
