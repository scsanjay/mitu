import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from analyzer import analyze_stock
from streamlit_cookies_manager import CookieManager

st.set_page_config(page_title="MITU - Stock Analysis", layout="wide")

# Initialize Cookie Manager
cookies = CookieManager()
if not cookies.ready():
    st.stop() # Wait for the cookies manager to initialize

# Initialize Session State for results
if 'results' not in st.session_state:
    st.session_state.results = None

# Inject CSS for uppercase text area and layout styling
st.markdown("""
<style>
textarea {
    text-transform: uppercase;
}
/* Flashy Analyze Button - Frosted Glass & Gradient Border */
.stButton > button[kind="primary"] {
    background: linear-gradient(rgba(43, 49, 62, 0.7), rgba(43, 49, 62, 0.7)) padding-box,
                linear-gradient(45deg, #ff7e67, #E75480) border-box !important;
    border: 3px solid transparent !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    padding: 12px 32px !important;
    border-radius: 14px !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 0 14px 0 rgba(231, 84, 128, 0.2) !important;
    width: 220px;
}
.stButton > button[kind="primary"] * {
    color: white !important;
    font-size: 20px !important;
    font-weight: bold !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 20px rgba(231, 84, 128, 0.6) !important;
}
/* Dimmed Multi-select Tags */
span[data-baseweb="tag"] {
    background-color: #475569 !important; /* Dark Grayish blue */
    color: white !important;
}
span[data-baseweb="tag"] svg {
    fill: white !important;
}
</style>
<h1 style='color: #E75480; text-align: center;' >MITU — Manage Investment Terminal Utility</h1>
""", unsafe_allow_html=True)
# st.markdown("Analyze medium-term stock outlooks.")

# Helper to load/save portfolio
def load_portfolio():
    try:
        if os.path.exists("portfolio.txt"):
            with open("portfolio.txt", "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return "RELIANCE.NS\nTCS.NS"


# Priority-based ticker loading (1. URL, 2. Cookie, 3. Txt file)
if "tickers_input_state" not in st.session_state:
    url_params = st.query_params.get("tickers")
    cookie_tickers = cookies.get("saved_tickers")
    
    if url_params:
        initial_val = url_params.replace(',', '\n')
    elif cookie_tickers:
        initial_val = cookie_tickers
    else:
        initial_val = load_portfolio()
    st.session_state.tickers_input_state = initial_val

st.markdown("##### Enter Stock Tickers (comma or newline separated):")
tickers_input = st.text_area("Tickers", key="tickers_input_state", label_visibility="collapsed", height=150)

if st.button("Analyze 📊", type="primary"):
    # Clear previous results immediately to avoid showing stale data
    st.session_state.results = None
    
    # Save the input to cookies and query parameters
    if cookies.get("saved_tickers") != tickers_input:
        cookies["saved_tickers"] = tickers_input
        cookies.save()
        st.query_params["tickers"] = tickers_input.replace('\n', ',')
        
    # Parse tickers
    raw_tickers = tickers_input.replace(',', '\n').split('\n')
    tickers = [t.strip().upper() for t in raw_tickers if t.strip()]
    
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        with st.status("Initializing Analysis...", expanded=True) as status:
            results = []
            for ticker in tickers:
                status.update(label=f"Analyzing {ticker}...", state="running")
                st.write(f"🔍 Fetching data for {ticker}...")
                
                res = analyze_stock(ticker)
                
                # Check for errors
                if res.get("error"):
                    st.write(f"❌ Failed to analyze {ticker}")
                    results.append({"ticker": ticker, "error": res['error']})
                    continue
                
                st.write(f"📈 Computing technical, fundamental, & sentiment indicators...")
                st.write(f"✅ Successfully analyzed {ticker}")
                
                results.append({"ticker": ticker, **res})
                
            status.update(label="Analysis complete!", state="complete", expanded=False)
            st.session_state.results = results
                

# --- Display Results Section (Persists via Session State) ---
if st.session_state.results:
    results = st.session_state.results
    
    # --- Sidebar Filters ---
    st.sidebar.header("Filter Results")
    
    # Classification Filter
    filter_class = st.sidebar.multiselect(
        "Composite Classification",
        options=["Hold", "Warning", "Sell"],
        default=["Hold", "Warning", "Sell"],
        key="filter_class_key",
        help="Filter by the 100-point composite score category."
    )
    
    # Predictive Trend Filter
    trend_options = [
        "Strong Bullish 🟢",
        "Moderately Bullish 🟢",
        "Neutral / Mixed ⚪",
        "Moderately Bearish 🟠",
        "Strong Bearish 🔴"
    ]
    filter_trend = st.sidebar.multiselect(
        "Predictive Trend",
        options=trend_options,
        default=trend_options,
        key="filter_trend_key",
        help="Filter by the 2-3 month predictive momentum rating."
    )
    
    def reset_filters():
        st.session_state["filter_class_key"] = ["Hold", "Warning", "Sell"]
        st.session_state["filter_trend_key"] = trend_options

    st.sidebar.button("Reset Filters", on_click=reset_filters)

    # Apply Filters
    filtered_results = [
        res for res in results 
        if "classification" in res # Skip rows that are just error markers
        and res["classification"] in filter_class 
        and res.get("predictive_trend", {}).get("rating") in filter_trend
    ]

    # Sort filtered results by severity (Sell first)
    filtered_results.sort(key=lambda x: x["severity"])
    
    if not filtered_results:
        st.info("No stocks match the selected filters. Try adjusting your selections in the sidebar.")
        # Still show failures even if no successful results match filters
        errors = [r for r in results if r.get("error")]
        if errors:
            st.subheader("Analysis Failures")
            for err in errors:
                st.error(f"⚠️ **{err['ticker']}**: Could not analyze. Reason: {err['error']}")
    else:
        st.subheader(f"Analysis Results ({len(filtered_results)} matching)")
        
        # Show failures at the top
        errors = [r for r in results if r.get("error")]
        for err in errors:
            st.error(f"⚠️ **{err['ticker']}**: Could not analyze. Reason: {err['error']}")
        
        for res in filtered_results:
            if res.get("error"): continue # Skip processed error objects in this loop
            ticker = res["ticker"]
            classification = res["classification"]
            
            if classification == "Sell":
                color_emoji = "🔴"
                composite_color = "red"
            elif classification == "Warning":
                color_emoji = "🟠"
                composite_color = "orange"
            else:
                color_emoji = "🟢"
                composite_color = "lightgreen"
                
            pred_rating = res.get('predictive_trend', {}).get('rating', '')
            
            if "Strong Bullish" in pred_rating or "Moderately Bullish" in pred_rating:
                predictive_color = "lightgreen"
            elif "Neutral" in pred_rating:
                predictive_color = "lightgray"
            elif "Moderately Bearish" in pred_rating:
                predictive_color = "orange"
            elif "Strong Bearish" in pred_rating:
                predictive_color = "red"
            else:
                predictive_color = "white"
            
            heading_html = f"""
            <div style='margin-bottom: 20px;'>
                <h3 style='margin-bottom: 12px; margin-top: 0px;'>{ticker}</h3>
                <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px;'>
                    <span style='background-color: #2b313e; color: {composite_color}; border: 1px solid #475569; border-radius: 14px; padding: 8px 18px; font-size: 16px; font-weight: 600;'>
                        Composite Score: {res['score']} ({classification}) {color_emoji} — [Tech: {res['tech_score']}, Fund: {res['fund_score']}, Sent: {res['sent_score']}]
                    </span>
                    <span style='background-color: #2b313e; color: {predictive_color}; border: 1px solid #475569; border-radius: 14px; padding: 8px 18px; font-size: 16px; font-weight: 600;'>
                        Predictive Trend: {pred_rating}
                    </span>
                </div>
            </div>
            """
            st.markdown(heading_html, unsafe_allow_html=True)
            
            # Trailing Returns
            trailing = res.get('trailing_returns', {})
            if trailing:
                cols = st.columns(len(trailing))
                for idx, (label, pct) in enumerate(trailing.items()):
                    with cols[idx]:
                        if pct is not None:
                            color = "green" if pct >= 0 else "red"
                            st.markdown(f"<div style='text-align: center; margin-bottom: 15px'><b>{label}</b><br/><span style='color:{color}'>{pct:+.2f}%</span></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='text-align: center; margin-bottom: 15px'><b>{label}</b><br/>N/A</div>", unsafe_allow_html=True)
                            
            with st.expander(f"View Detailed Analysis for {ticker}", expanded=False):
                # Display sub-scores
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Technical Score", f"{res['tech_score']} / 40")
                sc2.metric("Fundamental Score", f"{res['fund_score']} / 40")
                sc3.metric("Sentiment Score", f"{res['sent_score']} / 20")
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("### Technicals")
                    tc = res.get("tech_commentary", {})

                    st.write(f"**Current Price:** \u20b9{res['price']:.2f}")
                    if "price" in tc:
                        st.caption(f":{tc['price']['color']}[{tc['price']['text']}]")

                    st.write(f"**EMA 20:** \u20b9{res['ema_20']:.2f}")
                    if "ema20" in tc:
                        st.caption(f":{tc['ema20']['color']}[{tc['ema20']['text']}]")

                    st.write(f"**EMA 50:** \u20b9{res['ema_50']:.2f}")
                    if "ema50" in tc:
                        st.caption(f":{tc['ema50']['color']}[{tc['ema50']['text']}]")

                    st.write(f"**SMA 100:** \u20b9{res['sma_100']:.2f}")
                    if "sma100" in tc:
                        st.caption(f":{tc['sma100']['color']}[{tc['sma100']['text']}]")

                    st.write(f"**SMA 200:** \u20b9{res['sma_200']:.2f}")
                    if "sma200" in tc:
                        st.caption(f":{tc['sma200']['color']}[{tc['sma200']['text']}]")

                    st.write(f"**RSI (14):** {res['rsi']:.2f}")
                    if "rsi" in tc:
                        st.caption(f":{tc['rsi']['color']}[{tc['rsi']['text']}]")

                    macd_v = res.get('macd')
                    macd_sig = res.get('macd_signal')
                    macd_h = res.get('macd_hist')
                    if macd_v is not None:
                        macd_text = f"**MACD:** {macd_v:.2f} (Signal: {macd_sig:.2f}"
                        if macd_h is not None:
                            macd_text += f", Hist: {macd_h:.2f})"
                        else:
                            macd_text += ")"
                        st.write(macd_text)
                    else:
                        st.write("**MACD:** N/A")
                    if "macd" in tc:
                        st.caption(f":{tc['macd']['color']}[{tc['macd']['text']}]")

                    # Volume Analysis
                    vr = res.get('vol_ratio')
                    if vr is not None:
                        st.write(f"**Volume Ratio:** {vr:.2f}x (vs 20d avg)")

                    # ATR
                    atr_val = res.get('atr')
                    if atr_val is not None:
                        st.write(f"**ATR (14):** \u20b9{atr_val:.2f}")

                    # 52W High / Low
                    h52 = res.get('high_52w')
                    l52 = res.get('low_52w')
                    pos = res.get('range_52w_pos')
                    pfh = res.get('pct_from_high_52w')
                    if h52 is not None and l52 is not None:
                        st.write(f"**52W High:** \u20b9{h52:.2f}")
                        st.write(f"**52W Low:** \u20b9{l52:.2f}")
                    if pos is not None:
                        pos_color = "green" if pos >= 60 else ("orange" if pos >= 30 else "red")
                        st.markdown(
                            f"**52W Range Position:** "
                            f"<span style='color:{pos_color};font-weight:600'>{pos:.1f}%</span> of range",
                            unsafe_allow_html=True
                        )
                    if pfh is not None:
                        st.write(f"**Distance from 52W High:** {pfh:.1f}% below peak")
                    if "52w" in tc:
                        st.caption(f":{tc['52w']['color']}[{tc['52w']['text']}]")

                with col2:
                    st.write("### Fundamentals")
                    fc = res.get("fund_commentary", {})

                    pe = res.get('pe_ratio')
                    st.write(f"**P/E Ratio:** {pe if pe is not None else 'N/A'}")
                    if "pe" in fc:
                        st.caption(f":{fc['pe']['color']}[{fc['pe']['text']}]")

                    pb = res.get('pb_ratio')
                    st.write(f"**P/B Ratio:** {pb if pb is not None else 'N/A'}")
                    if "pb" in fc:
                        st.caption(f":{fc['pb']['color']}[{fc['pb']['text']}]")

                    dte = res.get('debt_to_equity')
                    st.write(f"**Debt to Equity:** {dte if dte is not None else 'N/A'}")
                    if "de" in fc:
                        st.caption(f":{fc['de']['color']}[{fc['de']['text']}]")

                    roe = res.get('roe')
                    if roe is not None:
                        st.write(f"**Return on Equity:** {roe * 100:.1f}%")
                    else:
                        st.write(f"**Return on Equity:** N/A")
                    if "roe" in fc:
                        st.caption(f":{fc['roe']['color']}[{fc['roe']['text']}]")

                    rev = res.get('rev_growth')
                    if rev is not None:
                        st.write(f"**Revenue Growth:** {rev * 100:.1f}%")
                    if "rev_growth" in fc:
                        st.caption(f":{fc['rev_growth']['color']}[{fc['rev_growth']['text']}]")

                    tm = res.get('target_mean')
                    st.write(f"**Analyst Mean Target Price:** {tm if tm is not None else 'N/A'}")
                    if "target" in fc:
                        st.caption(f":{fc['target']['color']}[{fc['target']['text']}]")

                    # --- EPS Growth (YoY) ---
                    eps_growth = res.get('eps_growth')
                    eps_signal = res.get('eps_signal', '')
                    if eps_growth is not None:
                        st.write(f"**EPS Growth (YoY):** {eps_growth * 100:.1f}%")
                    else:
                        st.write(f"**EPS Growth (YoY):** N/A")
                    if "eps_growth" in fc:
                        st.caption(f":{fc['eps_growth']['color']}[{fc['eps_growth']['text']}]")

                    # --- PEG Ratio ---
                    peg = res.get('peg')
                    peg_signal = res.get('peg_signal', '')
                    if peg is not None:
                        st.write(f"**PEG Ratio:** {peg:.2f}")
                    else:
                        st.write(f"**PEG Ratio:** N/A")
                    if "peg" in fc:
                        st.caption(f":{fc['peg']['color']}[{fc['peg']['text']}]")

                    # --- Earnings Growth ---
                    eg_data = res.get('earnings_growth_data', {})
                    eg_signal = res.get('eg_signal', '')
                    eg_growth = eg_data.get('growth') if eg_data else None
                    eg_history = eg_data.get('history') if eg_data else None
                    if eg_growth is not None:
                        st.write(f"**Earnings Growth:** {eg_growth * 100:.1f}%")
                    else:
                        st.write(f"**Earnings Growth:** N/A")
                    if "earn_growth" in fc:
                        st.caption(f":{fc['earn_growth']['color']}[{fc['earn_growth']['text']}]")


                    
                # Chart
                hist = res['history']
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['Close'], 
                    mode='lines', name='Price',
                    line=dict(color='#89F336'),
                    hovertemplate='Price: ₹%{y:,.2f}<extra></extra>'
                ))
                colors = ['#00d4ff', '#ff8c00', '#ffd700', '#ff4500'] # Cyan, DarkOrange, Gold, OrangeRed
                
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['EMA_20'], 
                    mode='lines', name='EMA 20', 
                    line=dict(color=colors[0], width=1.5),
                    hovertemplate='EMA 20: ₹%{y:,.2f}<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['EMA_50'], 
                    mode='lines', name='EMA 50', 
                    line=dict(color=colors[1], width=1.5),
                    hovertemplate='EMA 50: ₹%{y:,.2f}<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['SMA_100'], 
                    mode='lines', name='SMA 100', 
                    line=dict(color=colors[2], width=1.5),
                    hovertemplate='SMA 100: ₹%{y:,.2f}<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['SMA_200'], 
                    mode='lines', name='SMA 200', 
                    line=dict(color=colors[3], width=1.5),
                    hovertemplate='SMA 200: ₹%{y:,.2f}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f"{ticker} - 1 Year Price Chart",
                    xaxis_title="Date",
                    yaxis_title="Price",
                    height=450,
                    hovermode='x unified',
                    hoverlabel=dict(
                        bgcolor="rgba(43, 49, 62, 0.9)",
                        font_size=13,
                        font_family="Inter, sans-serif"
                    ),
                    margin=dict(l=0, r=0, t=50, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                
                # Bottom Section: Recommendations | News
                bot_col1, bot_col2 = st.columns(2)
                
                with bot_col1:
                    recoms = res.get('recommendations')
                    if recoms is not None and not recoms.empty:
                        st.write("### Analyst Recommendations")
                        st.dataframe(recoms, hide_index=True)
                    else:
                        st.write("### Analyst Recommendations")
                        st.info("No recent recommendations available.")
                        
                with bot_col2:
                    recent_news = res.get('recent_news', [])
                    if recent_news:
                        st.write("### Recent News (Last 10 Days)")
                        for news_item in recent_news:
                            st.markdown(f"**[{news_item['title']}]({news_item['url']})** — {news_item['date']}")
                            st.write(f"_{news_item['summary']}_")
                            st.markdown("---")
                    else:
                        st.write("### Recent News (Last 10 Days)")
                        st.info("No recent news found.")
                        
            # Thematic bold separator between different stocks
            st.markdown("<br><hr style='border: 1px solid #475569; margin-top: 10px; margin-bottom: 40px;'><br>", unsafe_allow_html=True)



@st.dialog("Metrics Documentation", width="large")
def show_metrics_docs():
    try:
        with open("metrics.md", "r") as f:
            docs = f.read()
        st.markdown(docs)
    except FileNotFoundError:
        st.error("Documentation file not found.")

# Documentation Button at the end (Popup)
st.markdown("---")
if st.button("📖 View Metrics Documentation"):
    show_metrics_docs()
