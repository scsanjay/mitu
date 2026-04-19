# MITU — Market Insights Tracking Utility

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-orange)
![Yahoo Finance](https://img.shields.io/badge/Data-Yahoo%20Finance-green)
![License](https://img.shields.io/badge/License-Apache--2.0-lightgrey)

MITU (Market Insights Tracking Utility) is a stock analysis tool designed for short- to medium-term decision support. It combines technical indicators, fundamental analysis, sentiment signals, and predictive trend insights to help you quickly understand a stock’s strength, momentum, and overall confidence.

MITU is free to use as it relies on Yahoo Finance for near real-time data. Because of this, it supports stock analysis across global markets.

It provides a concise yet detailed view of your holdings, breaking down each stock with clear scores, visual insights, and key metrics so you can quickly assess performance, risk, and potential opportunities.

---

## 📖 Overview

MITU provides a composite scoring model with a visual dashboard to evaluate stocks efficiently. It is built for investors who want a clear, practical view of whether a stock appears strong, weak, or uncertain in the near term.

The app supports:

* Manual ticker input
* Portfolio/holdings-based analysis
* Interactive charts and score breakdowns
* Zerodha Kite integration (free personal API)
* Reusable cached holdings data from Zerodha

For detailed scoring logic and formulas, see [`metrics.md`](./metrics.md).

---

## ✨ Features

* **Composite score** combining technical, fundamental, and sentiment factors
* **Predictive trend score** for short- to medium-term direction
* **Confidence score** indicating data completeness
* **Interactive charts** for price and indicator analysis
* **Sector-aware fundamental scoring** with benchmark comparisons
* **Current value per stock** based on latest market price
* **Global ticker support** via Yahoo Finance
* **Zerodha / Kite holdings integration**
* **Persistent local cache** to avoid repeated logins

---

## 📸 Demo

*Add a screenshot or GIF of the dashboard here.*

Example:

`![MITU dashboard](./assets/1.gif)`

---

## ⚙️ Getting Started

### Prerequisites

* Python installed locally
* `uv` for dependency management

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mitu

# Install dependencies
uv sync
```

### ▶️ Running the App

```bash
uv run streamlit run app.py
```

The app will open in your browser via Streamlit.

---

## 🧠 How It Works

### Scoring Architecture

MITU uses a multi-layer scoring model to generate a composite view of each stock.

#### Technical Score

Evaluates price action, trend structure, momentum, and indicator-based signals.

#### Fundamental Score

Analyzes valuation, financial health, growth, and sector benchmarks.

#### Sentiment Score

Incorporates signals such as analyst targets, promoter activity, and ownership trends.

#### Predictive Trend Score

Provides a directional bias for short- to medium-term movement.

#### Confidence Score

Reflects how complete and reliable the available data is.

➡️ For full formulas and scoring details, see [`metrics.md`](./metrics.md).

---

## 🔌 Zerodha / Kite Integration (Optional)

### Configuration

Create a `.env` file in the project root:

```env
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_REDIRECT_URL=http://localhost:8501
```

To obtain your API credentials, create an app in the Zerodha Kite Connect developer console. Ensure the redirect URL matches the one in your `.env` file.

Official guide:
[https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect)

### Connecting Your Account

1. Add credentials to `.env`
2. Register the redirect URL in Kite Connect
3. Launch the app and click **Login with Kite**
4. Approve access
5. Session tokens are stored locally for reuse

### Fetching Holdings

* Click **Fetch Kite Holdings** after login
* Data is cached locally and reused across sessions
* Re-login is only required if holdings change or the session expires

---

## 📂 Project Structure

```bash
.
├── app.py                  # Streamlit UI and entry point
├── analyzer.py             # Core analysis and scoring logic
├── metrics.md              # Scoring architecture and formulas
├── technical_metrics.md    # Technical scoring details
├── fundamental_metrics.md  # Fundamental scoring details
├── sentiment_metrics.md    # Sentiment scoring details
├── trend_metrics.md        # Predictive trend logic
├── Requirement.md          # Initial requirements
├── portfolio.txt           # Default ticker list
├── .env.example            # Environment variable template
├── pyproject.toml          # Project configuration
└── uv.lock                 # Dependency lock file
```

---

## 🌍 Supported Ticker Formats

MITU works with Yahoo Finance-style tickers and Kite holdings.

| Format          | Example               | Notes                                  |
| --------------- | --------------------- | -------------------------------------- |
| NSE             | `RELIANCE.NS`         | Standard NSE suffix                    |
| BSE             | `RELIANCE.BO`         | Standard BSE suffix                    |
| US              | `AAPL`                | Supported via Yahoo Finance            |
| Global          | `600519.SS`, `7203.T` | Supports global exchanges              |
| Mixed portfolio | `RELIANCE.NS, TCS.NS` | Comma-separated or one ticker per line |

When using Kite holdings, exchange mapping is handled automatically.

---

## ⚠️ Limitations & Disclaimer

* For informational and educational purposes only
* Not financial advice
* Data availability may vary by ticker and exchange
* Some metrics may have lower confidence due to missing data
* Best suited for liquid, actively traded stocks

---

## 🚀 Roadmap

Planned improvements:

* Enhanced portfolio analytics
* Additional chart overlays
* Exportable reports
* Backtesting capabilities
* Alerts and watchlist features

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test locally
5. Submit a pull request

---

## 👤 Author

Built by **Sanjay**.

---

## 📄 License

Licensed under the Apache-2.0 License. See [`LICENSE`](./LICENSE) for details.
