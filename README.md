---
title: AI Stock Analyzer 360°
sdk: docker
port: 8501
emoji: 🤖📈
colorFrom: blue
colorTo: green
pinned: false
---

# 🤖 AI Stock Analyzer 360°

Welcome to the AI Stock Analyzer 360°, a comprehensive web application designed for a dual-perspective analysis of Indian stocks listed on the National Stock Exchange (NSE). This tool integrates short-term technical indicators with long-term fundamental analysis to provide a holistic "360-degree" view of any company.

The application is powered by a robust data pipeline that automates the fetching and processing of financial data, making sophisticated analysis accessible with a single click.

---

## 🚀 Key Features

*   **Dual-Pronged Analysis**: Get the best of both worlds:
    *   **📈 Short-Term Technical View**: Utilizes key indicators like Moving Averages (MA), Average True Range (ATR), and Pivot Points to generate actionable short-term signals (Uptrend/Downtrend, Support/Resistance).
    *   **🏦 Long-Term Fundamental View**: Scores companies based on a weighted model of Valuation, Profitability & Growth, and Financial Health, providing a clear recommendation (Buy/Hold/Sell).
*   **Automated Data Pipeline**: Leverages `Playwright` to scrape detailed financial statements from [Screener.in](https://www.screener.in/) and `yfinance` to fetch live and historical market data.
*   **Interactive & User-Friendly UI**: Built with Streamlit, the interface allows for easy searching of stocks by ticker or company name. Analysis results are presented in a clean, digestible format with metrics, charts, and clear conclusions.
*   **Customizable Fundamental Scoring**: Tailor the analysis to your investment philosophy. The sidebar allows you to adjust the weights assigned to Valuation, Growth, and Health to see how your priorities impact the final score.
*   **Robust & Decoupled Architecture**: The data-scraping process runs in a separate, isolated subprocess, preventing conflicts and ensuring the Streamlit application remains responsive and stable.

---

## 🛠️ How It Works

The application follows a simple yet powerful workflow when you request an analysis for a stock:

1.  **Ticker Resolution**: Your input (e.g., "RELIANCE" or "RIL") is mapped to a valid NSE ticker symbol using a comprehensive list of stocks.
2.  **Data Fetching**:
    *   **Fundamental Data**: A background process logs into Screener.in, navigates to the company's page, and downloads the last 10 years of financial data as an Excel file.
    *   **Market Data**: The `yfinance` library is called to get the latest stock price, market cap, and 5 years of historical price data.
3.  **Data Processing & Analysis**:
    *   The raw Excel data is cleaned, parsed, and transformed into a structured DataFrame.
    *   Key financial ratios (like Debt-to-Equity and Sales Growth CAGR) are calculated from historical data.
    *   Technical indicators (MAs, ATR, Volume SMA) are calculated on the price history.
4.  **Scoring & Recommendation**:
    *   The calculated fundamental and live market ratios are fed into the customizable scoring model.
    *   The technical indicators are analyzed to produce a short-term trend signal and key price levels.
5.  **Visualization**: The final analysis, scores, charts, and recommendations are presented on the dashboard.

---

## 📋 How to Use the Application

1.  **Launch the App**: The application is hosted and ready to use.
2.  **Enter a Stock**: In the main input bar at the top, type the **NSE Ticker Symbol** (e.g., `TCS`, `HDFCBANK`) or the **Company Name** (e.g., `Tata Consultancy`, `Vip Industries`).
3.  **Adjust Weights (Optional)**: Open the sidebar on the left to customize the importance of Valuation, Profitability, and Financial Health in the fundamental score.
4.  **Click "Analyze Stock"**: The analysis will run, and the results will be displayed on the page.

---

## ⚙️ Technology Stack

*   **Frontend**: [Streamlit](https://streamlit.io/)
*   **Data Scraping**: [Playwright](https://playwright.dev/)
*   **Data Analysis**: [Pandas](https://pandas.pydata.org/), [yfinance](https://pypi.org/project/yfinance/), [pandas-ta](https://github.com/twopirllc/pandas-ta)
*   **Visualization**: [Plotly](https://plotly.com/)
*    [yfinance](https://pypi.org/project/yfinance/), [pandas-ta](https://github.com/twopirllc/pandas-ta)
*   **Visualization**: [Plotly](https://plotly.com/)
*   **Core Language**: Python 3.10+

## React + FastAPI interface

The original Streamlit application remains available through `run_app.py`. A new React interface uses the same Python market-analysis direction through a FastAPI backend.

Start the backend in one terminal:

```bash
source .venv/bin/activate
pip install -r requirements-api.txt
uvicorn api:app --reload --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.