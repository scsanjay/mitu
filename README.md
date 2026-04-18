# MITU Stock Analysis Engine

MITU (Manage Investment Terminal Utility) is a comprehensive stock analysis tool designed to provide data-driven insights into stock health, momentum, and sentiment. It leverages technical indicators, fundamental data, and market sentiment to help investors make informed decisions.

## Features

- **Composite Scoring**: A 100-point scoring model based on Technicals (40%), Fundamentals (40%), and Sentiment (20%).
- **Predictive Trend Analysis**: An independent momentum signal that estimates price direction over the next 2–3 months.
- **Sector-Aware Fundamentals**: Compares valuation and health metrics against industry-specific benchmarks.
- **Interactive Dashboard**: Built with Streamlit for a seamless and responsive user experience.
- **Real-time Data**: Fetches data directly from Yahoo Finance.
- **Technical Indicator Visualizations**: Includes MACD, RSI, Moving Averages, and Volume analysis.
- **Sentiment Tracking**: Monitors analyst EPS revisions, promoter holdings, and insider transactions.

## Installation

This project uses `uv` for dependency management. If you don't have `uv` installed, you can install it via:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Steps to set up:

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Stock_Analysis
   ```

2. **Sync dependencies**:
   ```bash
   uv sync
   ```

## Running the Application

To start the Streamlit dashboard, run the following command:

```bash
uv run streamlit run app.py
```

The application will be available at `http://localhost:8501`.

## Metrics and Scoring

For detailed information on how scores are calculated, please refer to:
- [Metrics Documentation (metrics.md)](./metrics.md)

Specific documentation for each pillar:
- [Technical Metrics](./technical_metrics.md)
- [Fundamental Metrics](./fundamental_metrics.md)
- [Sentiment Metrics](./sentiment_metrics.md)
- [Trend Metrics](./trend_metrics.md)

## Documentation Structure

- `app.py`: The Streamlit dashboard interface.
- `analyzer.py`: The core analysis engine containing all scoring logic (`score_technicals_v2`, `score_fundamentals_v2`, `score_sentiment_v2`, `calculate_predictive_trend_score`).
- `metrics.md`: Consolidated documentation for the scoring system.
- `Requirement.md`: Original project requirements and scope.

---
*Disclaimer: This tool is for educational and informational purposes only. It is not financial advice. Always perform your own due diligence before making investment decisions.*
