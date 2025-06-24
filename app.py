# app.py (Final - with Secrets Management, Corrected Search, and Integrated AI Prediction)

import streamlit as st
from pathlib import Path
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import time
import re
import math
from typing import Dict, Any, Optional

# --- IMPORTS for AI Prediction ---
import joblib
from predictor import make_prediction
from run_training import get_or_update_data_and_model
# ---

# The import for data_manager has been removed as it is no longer used directly.
from config import MODELS_DIR

# 1. Page config must be the first Streamlit command
st.set_page_config(
    layout="wide",
    page_title="AI Stock Analyzer 360°",
    initial_sidebar_state="collapsed"
)

# 2. Other commands, like custom CSS, can come after
st.markdown("""
<style>
    button[data-testid="stFormSubmitButton"], button[data-testid="stButton"] {
        background-color: #4A90E2;
        color: white;
        border: 1px solid #4A90E2;
    }
    button[data-testid="stFormSubmitButton"]:hover, button[data-testid="stButton"]:hover {
        background-color: #357ABD;
        border: 1px solid #357ABD;
        color: white;
    }
    button[data-testid="stFormSubmitButton"]:active, button[data-testid="stButton"]:active {
        background-color: #285A8C;
        border: 1px solid #285A8C;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_ticker_data() -> Optional[pd.DataFrame]:
    csv_path = Path("EQUITY_L.csv")
    if not csv_path.exists():
        st.error(f"Fatal Error: Ticker file not found at {csv_path}. Please create EQUITY_L.csv.")
        return None
    try:
        df = pd.read_csv(csv_path)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error loading ticker CSV file: {e}")
        return None

@st.cache_data(ttl=300)
def get_stock_data(stock_ticker: str) -> Dict[str, Any]:
    try:
        ticker_obj = yf.Ticker(f"{stock_ticker.upper()}.NS")
        info = ticker_obj.info
        if 'symbol' not in info or not info.get('regularMarketPrice'):
             return {"info": {}, "history": pd.DataFrame()}
        history = ticker_obj.history(period="5y")
        if not history.empty:
            history = history[history['Volume'] > 0]
        if not history.empty and all(col in history.columns for col in ['High', 'Low', 'Close']):
            history.ta.sma(length=20, append=True)
            history.ta.sma(length=50, append=True)
            history.ta.sma(length=20, volume=history['Volume'], append=True, col_names=('VOL_SMA_20',))
            history.ta.atr(length=14, append=True)
        return {"info": info, "history": history}
    except Exception as e:
        st.error(f"Could not fetch price history for '{stock_ticker}'. Please check if the ticker is correct.")
        return {"info": {}, "history": pd.DataFrame()}

def format_value(value, format_type="float"):
    if value is None or not isinstance(value, (int, float)): return "N/A"
    if format_type == "float": return f"{value:.2f}"
    if format_type == "percent": return f"{(value * 100):.2f}%"
    if format_type == "large_number":
        if value >= 1_000_000_000_000: return f"{value / 1_000_000_000_000:.2f} T"
        if value >= 1_000_000_000: return f"{value / 1_000_000_000:.2f} B"
        if value >= 1_000_000: return f"{value / 1_000_000:.2f} M"
        return f"{value:,.0f}"
    return value

def calculate_cagr(series: pd.Series, years: int):
    if len(series) < years + 1: return None
    end_value = series.iloc[-1]; start_value = series.iloc[-(years + 1)]
    if pd.isna(start_value) or start_value <= 0 or pd.isna(end_value): return None
    return ((end_value / start_value) ** (1 / years)) - 1

def calculate_historical_ratios(df: pd.DataFrame) -> Dict[str, float]:
    ratios = {};
    if df.empty: return ratios
    df.index = df.index.str.lower().str.strip().str.replace(r'[^a-z0-9]', '', regex=True)
    try:
        borrowings_row = df[df.index.str.contains('borrowings')].sum()
        share_capital_row = df[df.index.str.contains('sharecapital', na=False)].iloc[0]
        reserves_row = df[df.index.str.contains('reserves', na=False)].iloc[0]
        equity_row = share_capital_row + reserves_row
        latest_equity = equity_row.iloc[-1]; latest_borrowings = borrowings_row.iloc[-1]
        ratios['Debt to Equity'] = latest_borrowings / latest_equity if latest_equity > 0 else None
    except (IndexError, KeyError): ratios['Debt to Equity'] = None
    try:
        sales_row = df[df.index.str.contains('sales', na=False)].iloc[0].dropna()
        ratios['Sales Growth 3Yr'] = calculate_cagr(sales_row, 3)
    except (IndexError, KeyError): ratios['Sales Growth 3Yr'] = None
    return ratios

def calculate_fundamental_score(live_data, historical_data, weights):
    scores = {"Valuation": {"score": 0}, "Profitability & Growth": {"score": 0}, "Health": {"score": 0}}
    def normalize_score(value, good_range, bad_range, high_is_good=True):
        if value is None: return 5
        good_min, good_max = good_range; bad_min, bad_max = bad_range
        if high_is_good:
            if value >= good_max: return 10
            if value <= bad_min: return 0
            if value >= good_min: return 5 + 5 * ((value - good_min) / (good_max - good_min))
            return 5 * ((value - bad_min) / (good_min - bad_min))
        else:
            if value <= good_max: return 10
            if value >= bad_min: return 0
            if value > good_max: return 5 + 5 * ((good_min - value) / (good_min - good_max))
            return 5 * ((bad_min - value) / (bad_min - good_min))
    pe_score = normalize_score(live_data.get('trailingPE'), (5, 15), (30, 50), False)
    pb_score = normalize_score(live_data.get('priceToBook'), (0, 1.5), (3, 5), False)
    scores["Valuation"]["score"] = (pe_score + pb_score) / 2
    roe_score = normalize_score(live_data.get('returnOnEquity'), (0.15, 0.25), (0.05, 0), True)
    growth_score = normalize_score(historical_data.get('Sales Growth 3Yr'), (0.10, 0.20), (0.05, 0), True)
    scores["Profitability & Growth"]["score"] = (roe_score + growth_score) / 2
    de_score = normalize_score(historical_data.get('Debt to Equity'), (0, 0.5), (1.5, 2.5), False)
    cr_score = normalize_score(live_data.get('currentRatio'), (2, 3), (1, 0.5), True)
    scores["Health"]["score"] = (de_score + cr_score) / 2
    final_score = (scores["Valuation"]["score"] * weights["Valuation"] + scores["Profitability & Growth"]["score"] * weights["Profitability & Growth"] + scores["Health"]["score"] * weights["Health"]) / 100
    if final_score >= 7.5: recommendation = "Strong Buy"
    elif final_score >= 6.0: recommendation = "Buy"
    elif final_score >= 5.0: recommendation = "Hold / Accumulate on Dips"
    elif final_score >= 4.0: recommendation = "Hold / Reduce on Rallies"
    else: recommendation = "Sell"
    return final_score, recommendation, scores

def generate_conclusion(scores: dict) -> str:
    GREEN, YELLOW, RED = "#1E8449", "#F39C12", "#E74C3C"
    valuation_score = scores['Valuation']['score']
    if valuation_score >= 7: valuation_text = f"<span style='color: {GREEN}; font-weight: bold;'>attractively valued</span>"
    elif valuation_score >= 4: valuation_text = f"<span style='color: {YELLOW}; font-weight: bold;'>fairly valued</span>"
    else: valuation_text = f"<span style='color: {RED}; font-weight: bold;'>expensive</span>"
    profit_score = scores['Profitability & Growth']['score']
    if profit_score >= 7: profit_text = f"shows <span style='color: {GREEN}; font-weight: bold;'>strong profitability and growth</span>"
    elif profit_score >= 4: profit_text = f"shows <span style='color: {YELLOW}; font-weight: bold;'>decent profitability and growth</span>"
    else: profit_text = f"shows <span style='color: {RED}; font-weight: bold;'>weaker profitability or growth</span>"
    health_score = scores['Health']['score']
    if health_score >= 7: health_text = f"a <span style='color: {GREEN}; font-weight: bold;'>strong financial position</span>"
    elif health_score >= 4: health_text = f"an <span style='color: {YELLOW}; font-weight: bold;'>acceptable financial position</span>"
    else: health_text = f"some <span style='color: {RED}; font-weight: bold;'>potential financial risks</span>"
    return f"This company {profit_text}. From a valuation perspective, it appears {valuation_text}. The analysis also indicates {health_text}."

def get_technical_analysis(df_history: pd.DataFrame):
    required_cols = ['ATRr_14', 'SMA_20', 'SMA_50', 'VOL_SMA_20']
    if df_history.empty or len(df_history) < 50: return {"error": "Could not fetch sufficient price history for advanced analysis (needs at least 50 trading days)."}
    if not all(col in df_history.columns for col in required_cols): return {"error": "Technical indicator data is missing. Cannot perform analysis."}

    prev_day = df_history.iloc[-2]; high, low, close = prev_day['High'], prev_day['Low'], prev_day['Close']
    pivot = (high + low + close) / 3; r1, s1 = (2 * pivot) - low, (2 * pivot) - high
    latest = df_history.iloc[-1]; current_price = latest['Close']; atr = latest['ATRr_14']
    
    confirmation_score = 0; confirmations = []
    if current_price > pivot:
        trend = "Up"; confirmation_score += 1; confirmations.append("✅ Price is above the daily pivot point.")
    else:
        trend = "Down"; confirmations.append("❌ Price is below the daily pivot point.")
    if latest['SMA_20'] > latest['SMA_50']:
        confirmation_score += 1; confirmations.append("✅ 20-day MA is above the 50-day MA (Golden Cross).")
    else:
        confirmations.append("❌ 20-day MA is below the 50-day MA (Death Cross).")
    if latest['Volume'] > latest['VOL_SMA_20']:
        confirmation_score += 1; confirmations.append(f"✅ Today's volume is above the 20-day average.")
    else:
        confirmations.append(f"❌ Today's volume is below the 20-day average.")
    
    strategy_base = f"**Confirmation Score: {confirmation_score}/3**"
    if trend == "Up":
        strategy = f"**Uptrend Signal.** {strategy_base}"; target, stop_loss = r1, s1
    else:
        strategy = f"**Downtrend Signal.** {strategy_base}"; target, stop_loss = s1, r1

    trend_projection_text = ""
    if atr and atr > 0:
        if trend == "Up" and r1 > current_price: days_to_target = math.ceil(abs(r1 - current_price) / atr); trend_projection_text = f"The current **uptrend** may test resistance at {r1:.2f} in approx. **{days_to_target} day(s)**."
        elif trend == "Down" and s1 < current_price: days_to_target = math.ceil(abs(s1 - current_price) / atr); trend_projection_text = f"The current **downtrend** may test support at {s1:.2f} in approx. **{days_to_target} day(s)**."

    visible_df = df_history.iloc[-90:]
    fig = go.Figure(data=[go.Candlestick(x=visible_df.index, open=visible_df['Open'], high=visible_df['High'], low=visible_df['Low'], close=visible_df['Close'], name='Candlesticks')])
    fig.add_trace(go.Scatter(x=visible_df.index, y=visible_df['SMA_20'], mode='lines', name='20-Day MA', line=dict(color='orange', width=1.5)))
    fig.add_trace(go.Scatter(x=visible_df.index, y=visible_df['SMA_50'], mode='lines', name='50-Day MA', line=dict(color='cyan', width=1.5)))
    fig.add_hline(y=r1, line_dash="dash", line_color="red", annotation_text=f"Resistance: {r1:.2f}", annotation_position="top left")
    fig.add_hline(y=pivot, line_dash="dot", line_color="blue", annotation_text=f"Pivot: {pivot:.2f}", annotation_position="bottom left")
    fig.add_hline(y=s1, line_dash="dash", line_color="green", annotation_text=f"Support: {s1:.2f}", annotation_position="bottom left")
    padding = (visible_df['High'].max() - visible_df['Low'].min()) * 0.05
    fig.update_layout(title='Price Chart with Key Levels & MAs', yaxis_title='Price', xaxis_rangeslider_visible=False, height=400, template='plotly_dark', margin=dict(l=20, r=20, t=40, b=20), yaxis_range=[visible_df['Low'].min() - padding, visible_df['High'].max() + padding], xaxis_rangebreaks=[dict(bounds=["sat", "mon"])])
    
    return {"current_price": current_price, "strategy": strategy, "support": s1, "resistance": r1, "target": target, "stop_loss": stop_loss, "figure": fig, "trend_projection": trend_projection_text, "confirmations": confirmations, "confidence_score": confirmation_score, "trend": trend}

ticker_df = load_ticker_data()

if 'analysis_run' not in st.session_state: st.session_state.analysis_run = False
if 'stock_ticker_input' not in st.session_state: st.session_state.stock_ticker_input = ""

with st.sidebar:
    st.header("⚙️ Customize Fundamental Scoring")
    weight_valuation = st.slider("Valuation Weight (%)", 0, 100, 30, help="Prioritize cheap stocks.")
    weight_profitability = st.slider("Profitability & Growth (%)", 0, 100, 45, help="Prioritize profitable, growing companies.")
    weight_health = st.slider("Financial Health Weight (%)", 0, 100, 25, help="Prioritize stable companies.")
    total_weight = weight_valuation + weight_profitability + weight_health
    if total_weight != 100: st.warning(f"Total weight should be 100%, currently {total_weight}%.")
    user_weights = {"Valuation": weight_valuation, "Profitability & Growth": weight_profitability, "Health": weight_health}
    st.markdown("---")
    force_refresh_checkbox = st.checkbox("Force refresh data from Screener.in", help="This will be slower and will re-train the model.")

# --- START OF CORRECTED SECTION ---

# Define a callback function to set the state for analysis
def run_analysis():
    # Get the current value from the text_input widget and update the main state variable
    if "stock_ticker_input_widget" in st.session_state and st.session_state.stock_ticker_input_widget:
        st.session_state.stock_ticker_input = st.session_state.stock_ticker_input_widget.upper()
        # Set the flag to run the analysis block
        st.session_state.analysis_run = True
    else: # Handle case where button is clicked with empty input
        st.session_state.analysis_run = False


header_col1, header_col2 = st.columns([1, 2])
with header_col1: st.title("🤖 AI Stock Analyzer 360°")
with header_col2:
    form_col1, form_col2 = st.columns([2, 1])
    with form_col1:
        # Use a unique 'key' for the widget to keep its state separate
        st.text_input(
            "Enter NSE Ticker or Company Name",
            key="stock_ticker_input_widget", # This is the widget's unique key
            label_visibility="collapsed",
            placeholder="e.g., INFY or VIP INDUSTRIES",
            on_change=run_analysis # Optional: Run analysis on pressing Enter
        )
    with form_col2:
        # The button's on_click now triggers the state update via the callback
        st.button(
            "Analyze Stock",
            on_click=run_analysis,
            use_container_width=True,
            type="primary"
        )

# --- END OF CORRECTED SECTION ---


if st.session_state.analysis_run and st.session_state.stock_ticker_input:
    found_ticker = None
    if ticker_df is not None:
        user_input = st.session_state.stock_ticker_input.strip()
        if user_input in ticker_df['symbol'].values:
            found_ticker = user_input
        else:
            matches = ticker_df[ticker_df['name_of_company'].str.contains(user_input, case=False, na=False)]
            if not matches.empty:
                found_ticker = matches.iloc[0]['symbol']
    
    if not found_ticker:
        st.error(f"Could not find a valid ticker for '{st.session_state.stock_ticker_input}'. Please check the name or symbol.")
        st.session_state.analysis_run = False
    elif total_weight != 100:
        st.warning("Cannot analyze. Please adjust weights in the sidebar to sum to 100%."); st.session_state.analysis_run = False
    else:
        display_ticker = screener_ticker = yfinance_ticker = found_ticker
        st.header(f"Analysis for: {display_ticker}", divider='rainbow')
        if display_ticker != st.session_state.stock_ticker_input:
            st.info(f"Note: Your input '{st.session_state.stock_ticker_input}' was resolved to '{display_ticker}'.")

        col1, col2 = st.columns(2)
        with col1:
            tech_timer_placeholder = st.empty()
            tech_start_time = time.perf_counter()
            st.header("📉 Short-Term (Technical)")
            stock_data = get_stock_data(yfinance_ticker)
            df_history = stock_data["history"]
            if df_history.empty: pass 
            else:
                tech_results = get_technical_analysis(df_history)
                if "error" in tech_results: st.error(tech_results["error"])
                else:
                    st.subheader("Trifecta Signal")
                    if tech_results['trend'] == "Up": st.success(tech_results['strategy'])
                    else: st.error(tech_results['strategy'])
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Price", f"₹{tech_results['current_price']:.2f}")
                    c2.metric("Target Price", f"₹{tech_results['target']:.2f}")
                    c3.metric("Stop Loss", f"₹{tech_results['stop_loss']:.2f}")
                    support_level = f"₹{tech_results['support']:.2f}"; resistance_level = f"₹{tech_results['resistance']:.2f}"
                    st.markdown(f"""<div style="text-align: center; font-size: 0.9em; opacity: 0.8; margin-top: -10px;"><span style="color: #28a745;">Support: {support_level}</span>   |   <span style="color: #dc3545;">Resistance: {resistance_level}</span></div>""", unsafe_allow_html=True)
                    st.markdown("---")
                    with st.expander("Show Confirmation Checklist", expanded=False):
                        for item in tech_results['confirmations']: st.markdown(item)
                    with st.expander("Show Price Chart & Projections", expanded=False):
                        st.plotly_chart(tech_results["figure"], use_container_width=True)
                        if tech_results['trend_projection']: st.info(tech_results['trend_projection'], icon="⏳")
            tech_duration = time.perf_counter() - tech_start_time
            tech_timer_placeholder.caption(f"Analysis took: {tech_duration:.2f} seconds (Data Source: Yahoo Finance)")

        with col2:
            funda_timer_placeholder = st.empty()
            funda_start_time = time.perf_counter()
            st.header("📈 Long-Term (Fundamental)")
            with st.spinner("Running fundamental analysis & AI forecast..."):
                try:
                    model_path, data_path = get_or_update_data_and_model(
                        stock_ticker=screener_ticker,
                        force_refresh=force_refresh_checkbox
                    )

                    live_data = get_stock_data(yfinance_ticker)["info"]
                    if not live_data: st.error(f"Could not fetch live market data for '{yfinance_ticker}'."); st.stop()
                    
                    processed_df = pd.read_csv(data_path, index_col=0)
                    key_ratios_historical = calculate_historical_ratios(processed_df)
                    final_score, recommendation, score_breakdown = calculate_fundamental_score(live_data, key_ratios_historical, user_weights)
                    conclusion_text = generate_conclusion(score_breakdown)
                    
                    st.subheader("Recommendation")
                    if "Buy" in recommendation: st.success(f"**{recommendation.upper()}** (Score: {final_score:.1f}/10)")
                    elif "Sell" in recommendation: st.error(f"**{recommendation.upper()}** (Score: {final_score:.1f}/10)")
                    else: st.warning(f"**{recommendation.upper()}** (Score: {final_score:.1f}/10)")
                    
                    st.markdown(f"**Conclusion:** {conclusion_text}", unsafe_allow_html=True)
                    st.markdown("---")

                    st.subheader("🤖 AI Sales Forecast")
                    with st.spinner("Generating AI prediction..."):
                        model = joblib.load(model_path)
                        prediction, confidence = make_prediction(model, processed_df)
                        if "Error" in prediction or "Insufficient" in prediction:
                            st.warning(f"Could not generate AI forecast: {prediction}")
                        else:
                            st.metric(
                                label="Predicted Next Quarter Sales",
                                value=prediction,
                                help=f"Model confidence is approx. {confidence:.0%}"
                            )
                            st.info("This is a simple forecast based on historical sales trends and should not be the sole basis for an investment decision.", icon="💡")
                    
                    st.subheader("Fundamental Trend Projection")
                    if final_score >= 6.0: st.metric("Long-Term Trend", "Positive", delta="Strong Outlook"); st.info("The company's strong fundamentals suggest a positive long-term outlook.", icon="🚀")
                    elif final_score >= 4.5: st.metric("Long-Term Trend", "Neutral", delta="Mixed Outlook"); st.info("The company's fundamentals are average. Monitor for improvements.", icon="↔️")
                    else: st.metric("Long-Term Trend", "Negative", delta="Weak Outlook", delta_color="inverse"); st.info("The company shows fundamental weaknesses, suggesting a challenging outlook.", icon="⚠️")
                    
                    with st.expander("Show Score Breakdown", expanded=False):
                        st.metric("Valuation Score", f"{score_breakdown['Valuation']['score']:.1f}/10")
                        st.metric("Profitability & Growth Score", f"{score_breakdown['Profitability & Growth']['score']:.1f}/10")
                        st.metric("Financial Health Score", f"{score_breakdown['Health']['score']:.1f}/10")

                except RuntimeError as e:
                    st.error(f"Could not perform fundamental analysis for '{screener_ticker}'.")
                    st.info("This can happen if the company is not available for data export on Screener.in or if the ticker is incorrect.")
                    st.expander("Show Detailed Error").error(e)
                except Exception as e:
                    st.error(f"An unexpected error occurred during fundamental analysis for '{display_ticker}'."); st.exception(e)
            funda_duration = time.perf_counter() - funda_start_time
            funda_timer_placeholder.caption(f"Analysis took: {funda_duration:.2f} seconds (Data Sources: Screener.in & Yahoo Finance)")
else:
    st.markdown("---")
    st.info("### Welcome to the AI Stock Analyzer 360°!\n\nTo get started, enter a stock ticker or company name in the search bar above and click \"Analyze Stock\".", icon="🚀")