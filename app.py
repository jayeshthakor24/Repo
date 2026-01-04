import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
from datetime import datetime
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

# ----------------------------------------------------------
# AUTO LOAD ALL NSE STOCK SYMBOLS
# ----------------------------------------------------------
@st.cache_data
def get_all_nse_stocks():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df = pd.read_csv(url)
        return [s + ".NS" for s in df["SYMBOL"].tolist()]
    except:
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

nse_stock_list = get_all_nse_stocks()

# ---------------- MARKET CAP FORMAT ----------------
def format_market_cap(value):
    try:
        return f"₹{value/1e7:.2f} Cr"
    except:
        return "N/A"

# ---------------- RATINGS ----------------
def pe_rating(pe):
    if pe is None or pe <= 0: return "N/A"
    if pe < 20: return "Excellent"
    if pe <= 35: return "Good"
    return "Poor"

# ---------------- BUYING RECOMMENDATION ----------------
def buying_recommendation(df):
    try:
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        delta = df["Close"].diff()
        gain = delta.mask(delta < 0, 0).rolling(14).mean()
        loss = (-delta.mask(delta > 0, 0)).rolling(14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        latest = df.iloc[-1]
        score = 0
        score += 40 if latest["Close"] > latest["SMA20"] else 0
        score += 40 if latest["Close"] > latest["EMA20"] else 0
        score += 20 if latest["RSI"] < 70 else 0

        return min(score, 100)
    except:
        return 50

# ---------------- PERFORMANCE ----------------
def performance(df):
    perf = {}
    for days, label in [(21,"1 Month"), (63,"3 Month"), (126,"6 Month")]:
        if len(df) > days:
            perf[label] = round(((df["Close"].iloc[-1] - df["Close"].iloc[-days]) / df["Close"].iloc[-days]) * 100, 2)
        else:
            perf[label] = "N/A"
    return perf

# ---------------- IPO EXTRA DETAILS ----------------
def get_ipo_extra_details():
    return {
        "Price Range": "N/A",
        "Issue Size": "N/A",
        "Lot Size": "N/A",
        "Subscription Rate": "N/A"
    }

# ---------------- PDF SAVE ----------------
def save_pdf(symbol, data):
    folder = "Stock_Reports"
    os.makedirs(folder, exist_ok=True)

    now = datetime.now()
    filename = f"{symbol} - Jayesh Thakor Analysis - {now.strftime('%d-%m-%Y %H-%M-%S')}.pdf"
    path = os.path.join(folder, filename)

    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "title", fontSize=20, alignment=TA_CENTER,
        textColor=colors.HexColor("#003366"),
        fontName="Helvetica-Bold", spaceAfter=14
    )
    header = ParagraphStyle(
        "header", alignment=TA_CENTER, fontSize=11,
        textColor=colors.grey, spaceAfter=18
    )
    section = ParagraphStyle(
        "section", fontSize=13,
        textColor=colors.HexColor("#0b5394"),
        fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6
    )
    body = ParagraphStyle("body", fontSize=10, spaceAfter=5)

    story = []
    story.append(Paragraph("STOCK ANALYSIS REPORT", title))
    story.append(Paragraph(
        f"Report Created By : <b>Jayesh Thakor</b><br/>"
        f"Date : {now.strftime('%d-%m-%Y')} | "
        f"Day : {now.strftime('%A')} | "
        f"Time : {now.strftime('%H:%M:%S')}",
        header
    ))

    for sec, lines in data.items():
        story.append(Paragraph(sec, section))
        for l in lines:
            story.append(Paragraph(l.replace("₹","Rs."), body))

    doc.build(story)
    return path


# ----------------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------------
st.set_page_config(page_title="Stock Analyzer by Jayesh", layout="wide")

st.markdown("<h1 style='text-align:center;color:#00ffcc;'>📈 Stock Market Analyzer — By Jayesh Thakor</h1>", unsafe_allow_html=True)

search = st.text_input("Search Stock Symbol", "").upper()

suggestions = [s for s in nse_stock_list if search in s][:20]
symbol = st.selectbox("Select Stock", suggestions)

if st.button("ANALYZE STOCK"):
    if not symbol:
        st.warning("Please select stock.")
    else:
        stock = yf.Ticker(symbol)
        df = stock.history(period="6mo")
        info = stock.info

        current = info.get("currentPrice", 0)
        prev = info.get("previousClose", current)
        momentum = round(((current - prev) / prev) * 100, 2)

        hist = stock.history(period="max")
        listing_date = hist.index[0].strftime("%d-%m-%Y") if not hist.empty else "N/A"
        listing_price = round(hist.iloc[0]["Open"], 2) if not hist.empty else "N/A"

        profit_pct = round(((current - listing_price) / listing_price) * 100, 2) if listing_price != "N/A" else "N/A"

        perf = performance(df)
        rec = buying_recommendation(df)
        ipo_extra = get_ipo_extra_details()

        # -------------------- SHOW REPORT --------------------
        st.subheader("📄 Stock Report")
        st.write(f"**Stock:** {symbol}")
        st.write(f"**Current Price:** ₹{current}")
        st.write(f"**Momentum:** {momentum}%")

        st.subheader("IPO DETAILS")
        st.write(f"IPO Date: {listing_date}")
        st.write(f"IPO Price: ₹{listing_price}")
        st.write(f"Return Since IPO: {profit_pct}%")

        st.subheader("FUNDAMENTALS")
        st.write(f"Market Cap: {format_market_cap(info.get('marketCap',0))}")
        st.write(f"P/E Ratio: {info.get('trailingPE','N/A')} ({pe_rating(info.get('trailingPE'))})")

        st.subheader("PERFORMANCE")
        st.write(perf)

        st.subheader("BUYING SCORE")
        st.write(f"**Overall Score: {rec}%**")

        # -------------------- PDF --------------------
        report_data = {
            "STOCK REPORT BY JAYESH THAKOR": [
                f"Stock : {symbol}",
                f"Current Price : ₹{current}",
                f"Momentum : {momentum} %"
            ],
            "IPO DETAILS": [
                f"IPO Listing Date : {listing_date}",
                f"IPO Listing Price : ₹{listing_price}",
                f"Price Range : {ipo_extra['Price Range']}",
                f"Issue Size : {ipo_extra['Issue Size']}",
                f"Lot Size : {ipo_extra['Lot Size']}",
                f"Subscription Rate : {ipo_extra['Subscription Rate']}",
                f"Return Since IPO : {profit_pct} %"
            ],
            "FUNDAMENTALS": [
                f"Market Cap : {format_market_cap(info.get('marketCap',0))}",
                f"P/E Ratio : {info.get('trailingPE','N/A')} ({pe_rating(info.get('trailingPE'))})"
            ],
            "PERFORMANCE": [
                f"1 Month : {perf['1 Month']} %",
                f"3 Month : {perf['3 Month']} %",
                f"6 Month : {perf['6 Month']} %"
            ],
            "RECOMMENDATION FOR BUYING": [
                f"Overall Score : {rec} %"
            ]
        }

        pdf_path = save_pdf(symbol, report_data)
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name=os.path.basename(pdf_path))

        # -------------------- CHART --------------------
        st.subheader("📊 Candlestick Chart")
        df2 = yf.download(symbol, period="15d", interval="1d")
        mpf.plot(df2, type="candle", volume=True, style="charles")
        st.pyplot(mpf.plot(df2, type="candle", volume=True, style="charles"))

