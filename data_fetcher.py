"""
市場データ取得モジュール
Yahoo Finance API を使ってFX・先物・株式指数の価格データを取得する
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# ─── 通貨ペア定義 ───
CURRENCY_PAIRS = {
    "USD/JPY (米ドル/円)": "USDJPY=X",
    "EUR/JPY (ユーロ/円)": "EURJPY=X",
    "GBP/JPY (英ポンド/円)": "GBPJPY=X",
    "AUD/JPY (豪ドル/円)": "AUDJPY=X",
    "EUR/USD (ユーロ/米ドル)": "EURUSD=X",
    "GBP/USD (英ポンド/米ドル)": "GBPUSD=X",
}

# ─── 先物銘柄定義 ───
FUTURES_SYMBOLS = {
    "WTI原油": "CL=F",
    "ブレント原油": "BZ=F",
    "天然ガス": "NG=F",
    "金（ゴールド）": "GC=F",
    "銀（シルバー）": "SI=F",
}

# ─── 株式指数定義 ───
STOCK_INDICES = {
    "日経平均株価": "^N225",
    "TOPIX": "^TPX",
    "NYダウ（ダウ平均）": "^DJI",
    "S&P 500": "^GSPC",
    "NASDAQ総合": "^IXIC",
    "NASDAQ 100": "^NDX",
    "ラッセル2000": "^RUT",
    "VIX（恐怖指数）": "^VIX",
}

# ─── 日本個別株（人気銘柄） ───
JP_STOCKS = {
    "トヨタ自動車 (7203)": "7203.T",
    "ソニーグループ (6758)": "6758.T",
    "任天堂 (7974)": "7974.T",
    "ソフトバンクG (9984)": "9984.T",
    "ファーストリテイリング (9983)": "9983.T",
    "キーエンス (6861)": "6861.T",
    "東京エレクトロン (8035)": "8035.T",
    "三菱UFJ (8306)": "8306.T",
}

# ─── 米国個別株（人気銘柄） ───
US_STOCKS = {
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "NVIDIA (NVDA)": "NVDA",
    "Amazon (AMZN)": "AMZN",
    "Google/Alphabet (GOOGL)": "GOOGL",
    "Meta (META)": "META",
    "Tesla (TSLA)": "TSLA",
    "Berkshire Hathaway (BRK-B)": "BRK-B",
}

# ─── 海外個別株（米国以外） ───
OVERSEAS_STOCKS = {
    # アジア
    "TSMC (台湾, 2330)": "2330.TW",
    "鴻海 / Foxconn (台湾, 2317)": "2317.TW",
    "Samsung Electronics (韓国, 005930)": "005930.KS",
    "SK Hynix (韓国, 000660)": "000660.KS",
    "Tencent (香港, 0700)": "0700.HK",
    "Alibaba HK (香港, 9988)": "9988.HK",
    # 欧州
    "ASML (オランダ)": "ASML.AS",
    "SAP (ドイツ)": "SAP.DE",
    "LVMH (フランス)": "MC.PA",
    "Novo Nordisk (デンマーク)": "NOVO-B.CO",
    "Nestle (スイス)": "NESN.SW",
    "Shell (英国)": "SHEL.L",
    # カナダ・豪州
    "Shopify (カナダ)": "SHOP.TO",
    "Royal Bank of Canada": "RY.TO",
    "BHP Group (豪州)": "BHP.AX",
    "Commonwealth Bank (豪州)": "CBA.AX",
}

# ─── 債券・金利（国債ETF/主要金利） ───
BOND_SYMBOLS = {
    # 米国債ETF
    "iShares 20+ Year Treasury (TLT)": "TLT",
    "iShares 7-10 Year Treasury (IEF)": "IEF",
    "iShares 1-3 Year Treasury (SHY)": "SHY",
    "Vanguard Total Bond Market (BND)": "BND",
    "iShares Core US Aggregate Bond (AGG)": "AGG",
    "iShares iBoxx IG Corp Bond (LQD)": "LQD",
    "iShares iBoxx HY Corp Bond (HYG)": "HYG",
    "iShares JP Morgan EM Bond (EMB)": "EMB",
    # 主要金利指数（参考）
    "米10年国債利回り (^TNX)": "^TNX",
    "米30年国債利回り (^TYX)": "^TYX",
    "米5年国債利回り (^FVX)": "^FVX",
}

# ─── 仮想通貨（暗号資産） ───
CRYPTO_SYMBOLS = {
    "Bitcoin (BTC/USD)": "BTC-USD",
    "Ethereum (ETH/USD)": "ETH-USD",
    "BNB (BNB/USD)": "BNB-USD",
    "Solana (SOL/USD)": "SOL-USD",
    "XRP (XRP/USD)": "XRP-USD",
    "Cardano (ADA/USD)": "ADA-USD",
    "Dogecoin (DOGE/USD)": "DOGE-USD",
    "Polygon (MATIC/USD)": "MATIC-USD",
    "Avalanche (AVAX/USD)": "AVAX-USD",
    "Chainlink (LINK/USD)": "LINK-USD",
    "Bitcoin (BTC/JPY)": "BTC-JPY",
    "Ethereum (ETH/JPY)": "ETH-JPY",
}

# ─── コモディティ・貴金属 ───
COMMODITIES = {
    "プラチナ": "PL=F",
    "パラジウム": "PA=F",
    "銅": "HG=F",
    "コーン（とうもろこし）": "ZC=F",
    "大豆": "ZS=F",
    "小麦": "ZW=F",
    "コーヒー": "KC=F",
    "砂糖": "SB=F",
}

# ─── 時間足の選択肢 ───
INTERVAL_OPTIONS = {
    "1分足": "1m",
    "5分足": "5m",
    "15分足": "15m",
    "30分足": "30m",
    "1時間足": "1h",
    "日足": "1d",
}

# 各時間足で取得可能な最大期間（Yahoo Finance の制限）
INTERVAL_MAX_PERIOD = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "1h": "730d",
    "1d": "max",
}

PERIOD_OPTIONS = {
    "1日": "1d",
    "5日": "5d",
    "1週間": "5d",
    "1ヶ月": "1mo",
    "3ヶ月": "3mo",
    "6ヶ月": "6mo",
    "1年": "1y",
    "2年": "2y",
}


def fetch_market_data(
    ticker_symbol: str,
    period: str = "5d",
    interval: str = "1m",
) -> pd.DataFrame:
    """
    指定した銘柄の価格データを取得する（1分足対応）

    Args:
        ticker_symbol: Yahoo Finance ティッカー (例: "CL=F", "USDJPY=X")
        period: 取得期間 (例: "1d", "5d", "1mo")
        interval: 時間足 (例: "1m", "5m", "1h", "1d")
    """
    max_period = INTERVAL_MAX_PERIOD.get(interval, "max")
    period_days = _period_to_days(period)
    max_days = _period_to_days(max_period)
    if period_days > max_days:
        period = max_period

    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Tokyo").tz_localize(None)

    df = df.reset_index()

    date_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={
        date_col: "日時",
        "Open": "始値",
        "High": "高値",
        "Low": "安値",
        "Close": "終値",
        "Volume": "出来高",
    })

    cols = ["日時", "始値", "高値", "安値", "終値"]
    if "出来高" in df.columns:
        cols.append("出来高")
    return df[cols]


def _period_to_days(period: str) -> int:
    """期間文字列をおおよその日数に変換"""
    mapping = {
        "1d": 1, "5d": 5, "7d": 7, "1mo": 30, "3mo": 90,
        "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 9999,
    }
    return mapping.get(period, 30)


def get_latest_price(ticker_symbol: str) -> Optional[dict]:
    """最新の価格情報と前日比を取得する"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d")

        if hist is None or hist.empty or len(hist) < 2:
            return None

        current = hist["Close"].iloc[-1]
        previous = hist["Close"].iloc[-2]
        change = current - previous
        change_pct = (change / previous) * 100

        return {
            "price": round(current, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 3),
        }
    except Exception:
        return None


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    テクニカル指標を計算する
    - 移動平均線 (短期5, 中期25, 長期75)
    - RSI (14期間)
    - MACD
    - ボリンジャーバンド (±2σ)
    """
    if df.empty or "終値" not in df.columns:
        return df

    result = df.copy()
    close = result["終値"]

    # 移動平均線
    result["MA5"] = close.rolling(window=5).mean()
    result["MA25"] = close.rolling(window=25).mean()
    result["MA75"] = close.rolling(window=75).mean()

    # RSI (14期間)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    result["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    result["MACD"] = ema12 - ema26
    result["MACDシグナル"] = result["MACD"].ewm(span=9, adjust=False).mean()
    result["MACDヒストグラム"] = result["MACD"] - result["MACDシグナル"]

    # ボリンジャーバンド
    rolling_25 = close.rolling(window=25)
    result["BB上限(+2σ)"] = rolling_25.mean() + (rolling_25.std() * 2)
    result["BB下限(-2σ)"] = rolling_25.mean() - (rolling_25.std() * 2)

    return result
