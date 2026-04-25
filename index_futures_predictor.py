"""
株価指数先物 総合予測モジュール
日経225 / 米国D30 / S&P500 / NASDAQ100 / DAX / FTSE / Hang Seng 他

機能：
- 世界主要17銘柄の先物データ取得
- マルチタイムフレーム予測（短期/中期/長期）
- 強気/中立/弱気のシナリオ確率
- サポート・レジスタンス自動計算
- カタリスト（材料）と注目イベント
- クロスアセット相関分析
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# ════════════════════════════════════════════════
#  世界主要 株価指数先物
# ════════════════════════════════════════════════

INDEX_FUTURES = {
    # ─── 日本 ───
    "NK=F": {
        "name": "日経225先物",
        "short": "日本225",
        "country": "🇯🇵",
        "region": "アジア",
        "trading_hours_jst": "08:45-15:15 / 16:30-翌06:00（夜間）",
        "tick_size": 5,
        "tick_value_jpy": 5000,
        "key_drivers": ["米株（特にNASDAQ）", "USD/JPY", "中国経済", "日銀政策"],
        "correlation": "S&P500: 0.85, USD/JPY: +0.7（円安で上昇）",
    },
    "JPM": {  # placeholder JP small (TOPIX futures)
        "name": "TOPIX先物",
        "short": "TOPIX",
        "country": "🇯🇵",
        "region": "アジア",
        "trading_hours_jst": "08:45-15:15 / 16:30-翌06:00",
        "tick_size": 0.5,
        "tick_value_jpy": 5000,
        "key_drivers": ["銀行株", "金利上昇", "円安"],
        "correlation": "日経225: 0.95, 国債利回り: +0.5",
        "yf_symbol": "1306.T",  # TOPIX ETF as proxy
    },

    # ─── 米国 ───
    "ES=F": {
        "name": "S&P 500 E-mini先物",
        "short": "SP500",
        "country": "🇺🇸",
        "region": "北米",
        "trading_hours_jst": "ほぼ24時間（22:30-翌06:15メイン）",
        "tick_size": 0.25,
        "tick_value_jpy": 1875,  # $12.50 ≈
        "key_drivers": ["FRB金利", "決算", "米経済指標", "VIX"],
        "correlation": "NASDAQ: 0.95, VIX: -0.85, 10年債利回り: -0.5",
    },
    "YM=F": {
        "name": "ダウ E-mini先物",
        "short": "米国D30",
        "country": "🇺🇸",
        "region": "北米",
        "trading_hours_jst": "ほぼ24時間",
        "tick_size": 1,
        "tick_value_jpy": 750,
        "key_drivers": ["大型バリュー株", "金利", "シクリカル", "原油"],
        "correlation": "S&P500: 0.93, 原油: +0.4",
    },
    "NQ=F": {
        "name": "NASDAQ 100 E-mini先物",
        "short": "NASDAQ100",
        "country": "🇺🇸",
        "region": "北米",
        "trading_hours_jst": "ほぼ24時間",
        "tick_size": 0.25,
        "tick_value_jpy": 750,
        "key_drivers": ["AI/半導体株", "金利感応度高", "メガテック決算"],
        "correlation": "S&P500: 0.95, 10年債利回り: -0.7（金利感応度高）",
    },
    "RTY=F": {
        "name": "Russell 2000先物（米小型株）",
        "short": "Russell2000",
        "country": "🇺🇸",
        "region": "北米",
        "trading_hours_jst": "ほぼ24時間",
        "tick_size": 0.1,
        "tick_value_jpy": 750,
        "key_drivers": ["米国内景気", "金利", "ドル安"],
        "correlation": "S&P500: 0.85, 米景気指数: +0.7",
    },

    # ─── 欧州 ───
    "^GDAXI": {  # DAX index proxy
        "name": "ドイツDAX",
        "short": "独DAX",
        "country": "🇩🇪",
        "region": "欧州",
        "trading_hours_jst": "16:00-翌00:30",
        "tick_size": 0.5,
        "tick_value_jpy": 0,
        "key_drivers": ["ECB政策", "ドイツ製造業", "中国景気（輸出）"],
        "correlation": "S&P500: 0.75, ユーロ: -0.4",
    },
    "^FTSE": {
        "name": "英国FTSE 100",
        "short": "英FTSE100",
        "country": "🇬🇧",
        "region": "欧州",
        "trading_hours_jst": "17:00-翌01:30",
        "tick_size": 0.5,
        "tick_value_jpy": 0,
        "key_drivers": ["BOE金利", "原油・資源株比率高", "ポンド"],
        "correlation": "WTI原油: +0.6, ポンド: -0.5",
    },
    "^FCHI": {
        "name": "フランスCAC 40",
        "short": "仏CAC40",
        "country": "🇫🇷",
        "region": "欧州",
        "trading_hours_jst": "17:00-翌01:30",
        "tick_size": 0.5,
        "tick_value_jpy": 0,
        "key_drivers": ["LVMH等高級品", "ECB政策", "中国景気"],
        "correlation": "DAX: 0.92, 中国株: +0.5",
    },
    "^STOXX50E": {
        "name": "Euro Stoxx 50",
        "short": "EuroStoxx50",
        "country": "🇪🇺",
        "region": "欧州",
        "trading_hours_jst": "16:00-翌00:30",
        "tick_size": 1,
        "tick_value_jpy": 0,
        "key_drivers": ["ECB", "ユーロ圏景気指標", "ロシア情勢"],
        "correlation": "DAX: 0.96, S&P500: 0.75",
    },

    # ─── 中華圏 ───
    "^HSI": {
        "name": "香港ハンセン指数",
        "short": "ハンセン",
        "country": "🇭🇰",
        "region": "アジア",
        "trading_hours_jst": "10:30-13:00 / 14:00-17:00",
        "tick_size": 1,
        "tick_value_jpy": 0,
        "key_drivers": ["中国経済", "テック規制", "テンセント・アリババ", "PBOC政策"],
        "correlation": "上海総合: 0.85, 米中対立で急変",
    },
    "000001.SS": {
        "name": "上海総合指数",
        "short": "上海総合",
        "country": "🇨🇳",
        "region": "アジア",
        "trading_hours_jst": "10:30-12:30 / 14:00-16:00",
        "tick_size": 0.01,
        "tick_value_jpy": 0,
        "key_drivers": ["人民銀行政策", "不動産市況", "輸出データ"],
        "correlation": "ハンセン: 0.85, 銅: +0.6",
    },
    "^TWII": {
        "name": "台湾加権指数",
        "short": "台湾加権",
        "country": "🇹🇼",
        "region": "アジア",
        "trading_hours_jst": "10:00-14:30",
        "tick_size": 0.01,
        "tick_value_jpy": 0,
        "key_drivers": ["TSMC等半導体", "AI需要", "米中対立", "地政学"],
        "correlation": "NASDAQ: 0.85, 半導体株: +0.9",
    },
    "^KS11": {
        "name": "韓国KOSPI",
        "short": "KOSPI",
        "country": "🇰🇷",
        "region": "アジア",
        "trading_hours_jst": "09:00-15:30",
        "tick_size": 0.01,
        "tick_value_jpy": 0,
        "key_drivers": ["サムスン・SK半導体", "輸出", "ウォン", "北朝鮮リスク"],
        "correlation": "NASDAQ: 0.75, 台湾加権: 0.8",
    },

    # ─── オセアニア ───
    "^AXJO": {
        "name": "豪ASX 200",
        "short": "ASX200",
        "country": "🇦🇺",
        "region": "オセアニア",
        "trading_hours_jst": "09:00-15:00",
        "tick_size": 0.1,
        "tick_value_jpy": 0,
        "key_drivers": ["資源価格", "RBA政策", "中国景気"],
        "correlation": "鉄鉱石: +0.7, 中国株: +0.6",
    },

    # ─── 新興国 ───
    "^BSESN": {
        "name": "インドSENSEX",
        "short": "SENSEX",
        "country": "🇮🇳",
        "region": "新興国",
        "trading_hours_jst": "12:45-19:00",
        "tick_size": 0.01,
        "tick_value_jpy": 0,
        "key_drivers": ["RBI政策", "原油（輸入）", "FII資金流入"],
        "correlation": "MSCI EM: 0.75",
    },
    "^BVSP": {
        "name": "ブラジルボベスパ",
        "short": "ボベスパ",
        "country": "🇧🇷",
        "region": "新興国",
        "trading_hours_jst": "22:00-翌03:00",
        "tick_size": 1,
        "tick_value_jpy": 0,
        "key_drivers": ["コモディティ", "レアル", "中国需要"],
        "correlation": "鉄鉱石: +0.65, 大豆: +0.6",
    },

    # ─── ボラティリティ ───
    "^VIX": {
        "name": "VIX恐怖指数",
        "short": "VIX",
        "country": "🇺🇸",
        "region": "ボラ指数",
        "trading_hours_jst": "S&P500と同じ",
        "tick_size": 0.05,
        "tick_value_jpy": 0,
        "key_drivers": ["S&P500の急変", "地政学", "FOMC前後"],
        "correlation": "S&P500: -0.85（逆相関）",
    },
}


# ════════════════════════════════════════════════
#  テクニカル分析
# ════════════════════════════════════════════════

def _calc_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def _calc_macd(close: pd.Series) -> dict:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    return {
        "macd": float(macd.iloc[-1]),
        "signal": float(sig.iloc[-1]),
        "hist": float((macd - sig).iloc[-1]),
        "trend": "上昇" if macd.iloc[-1] > sig.iloc[-1] else "下降",
    }


def _calc_support_resistance(df: pd.DataFrame, lookback: int = 60) -> dict:
    """直近N日の高値・安値からサポート/レジスタンスを抽出"""
    recent = df.tail(lookback)
    highs = recent["High"]
    lows = recent["Low"]
    close = float(df["Close"].iloc[-1])

    # ピボット
    p_high = float(highs.max())
    p_low = float(lows.min())

    # フィボナッチリトレースメント
    diff = p_high - p_low
    fib_618 = p_high - 0.618 * diff
    fib_500 = p_high - 0.500 * diff
    fib_382 = p_high - 0.382 * diff

    return {
        "resistance_strong": round(p_high, 2),
        "resistance_mid": round(fib_382, 2) if fib_382 > close else round(p_high, 2),
        "support_mid": round(fib_618, 2) if fib_618 < close else round(p_low, 2),
        "support_strong": round(p_low, 2),
        "fib_500": round(fib_500, 2),
    }


# ════════════════════════════════════════════════
#  予測ロジック
# ════════════════════════════════════════════════

def _multi_timeframe_predict(df: pd.DataFrame) -> dict:
    """短期(1日)/中期(1週)/長期(1ヶ月)/超長期(3ヶ月)の方向と信頼度を予測"""
    close = df["Close"]
    if len(close) < 200:
        ma200 = close.rolling(min(len(close), 50)).mean().iloc[-1]
    else:
        ma200 = close.rolling(200).mean().iloc[-1]
    ma50 = close.rolling(min(len(close), 50)).mean().iloc[-1]
    ma20 = close.rolling(min(len(close), 20)).mean().iloc[-1]
    ma5 = close.rolling(5).mean().iloc[-1]
    last = float(close.iloc[-1])

    rsi = _calc_rsi(close)
    macd_info = _calc_macd(close)

    # ───── 短期（1日先）─────
    short_score = 0
    short_reasons = []
    if last > ma5:
        short_score += 1
        short_reasons.append("5日線の上で推移")
    else:
        short_score -= 1
        short_reasons.append("5日線割れ")
    if macd_info["hist"] > 0:
        short_score += 1
        short_reasons.append(f"MACDヒストグラム+ ({macd_info['hist']:+.2f})")
    else:
        short_score -= 1
        short_reasons.append("MACDヒストグラム-")
    if 30 < rsi < 70:
        short_reasons.append(f"RSI={rsi:.0f}（中立圏）")
    elif rsi >= 70:
        short_score -= 1
        short_reasons.append(f"RSI={rsi:.0f} 過熱")
    else:
        short_score += 1
        short_reasons.append(f"RSI={rsi:.0f} 売られすぎ→反発期待")

    # ───── 中期（1週間〜1ヶ月）─────
    mid_score = 0
    mid_reasons = []
    if ma20 > ma50:
        mid_score += 1
        mid_reasons.append("20日線 > 50日線（中期上昇）")
    else:
        mid_score -= 1
        mid_reasons.append("20日線 < 50日線")
    if last > ma20:
        mid_score += 1
        mid_reasons.append("価格 > 20日線")
    else:
        mid_score -= 1
        mid_reasons.append("価格 < 20日線")
    if macd_info["trend"] == "上昇":
        mid_score += 1
        mid_reasons.append("MACDシグナル上抜け状態")

    # ───── 長期（3ヶ月〜半年）─────
    long_score = 0
    long_reasons = []
    if last > ma200:
        long_score += 2
        long_reasons.append("200日線の上 → 長期強気トレンド")
    else:
        long_score -= 2
        long_reasons.append("200日線の下 → 長期弱気")
    # 200日線の傾き
    if len(close) >= 220:
        ma200_20 = close.rolling(200).mean().iloc[-21]
        slope = ma200 - ma200_20
        if slope > 0:
            long_score += 1
            long_reasons.append("200日線が上向き")
        else:
            long_score -= 1
            long_reasons.append("200日線が下向き")

    def _label(s):
        if s >= 2:
            return ("強気", "🟢", min(95, 60 + s * 8))
        elif s == 1:
            return ("やや強気", "🟢", 55)
        elif s == 0:
            return ("中立", "⚪", 50)
        elif s == -1:
            return ("やや弱気", "🔴", 55)
        else:
            return ("弱気", "🔴", min(95, 60 + abs(s) * 8))

    s_dir, s_icon, s_conf = _label(short_score)
    m_dir, m_icon, m_conf = _label(mid_score)
    l_dir, l_icon, l_conf = _label(long_score)

    return {
        "short_term": {"horizon": "1日先", "direction": s_dir, "icon": s_icon, "confidence": s_conf, "reasons": short_reasons, "score": short_score},
        "mid_term": {"horizon": "1週〜1ヶ月", "direction": m_dir, "icon": m_icon, "confidence": m_conf, "reasons": mid_reasons, "score": mid_score},
        "long_term": {"horizon": "3〜6ヶ月", "direction": l_dir, "icon": l_icon, "confidence": l_conf, "reasons": long_reasons, "score": long_score},
        "rsi": round(rsi, 1),
        "macd": macd_info,
    }


def _build_scenarios(price: float, sr: dict, predictions: dict, vol: float) -> list:
    """強気・中立・弱気の3シナリオを構築"""
    short_score = predictions["short_term"]["score"]
    mid_score = predictions["mid_term"]["score"]
    long_score = predictions["long_term"]["score"]
    total = short_score + mid_score + long_score

    # シナリオ確率（合計100）
    if total >= 4:
        prob = (60, 25, 15)  # bull / base / bear
    elif total >= 2:
        prob = (45, 35, 20)
    elif total <= -4:
        prob = (15, 25, 60)
    elif total <= -2:
        prob = (20, 35, 45)
    else:
        prob = (30, 40, 30)

    # 上下の値幅予測（ボラティリティから）
    upside = price * (1 + vol * 2)
    downside = price * (1 - vol * 2)

    return [
        {
            "name": "🟢 強気シナリオ",
            "probability": prob[0],
            "target_1m": round(min(upside, sr["resistance_strong"]), 2),
            "target_3m": round(sr["resistance_strong"] * 1.05, 2),
            "trigger": "金利低下・好決算・地政学リスク後退・好材料相次ぐ",
            "color": "#D32030",
        },
        {
            "name": "⚪ 中立シナリオ（レンジ）",
            "probability": prob[1],
            "target_1m": round(price, 2),
            "target_3m": round(price * 1.02, 2),
            "trigger": "材料出尽くし・サポート/レジスタンス間で揉み合い",
            "color": "#FDB813",
        },
        {
            "name": "🔴 弱気シナリオ",
            "probability": prob[2],
            "target_1m": round(max(downside, sr["support_strong"]), 2),
            "target_3m": round(sr["support_strong"] * 0.95, 2),
            "trigger": "金利急上昇・決算ミス・地政学激化・景気後退懸念",
            "color": "#1565C0",
        },
    ]


def _identify_catalysts(symbol: str, info: dict) -> list:
    """銘柄ごとの注目カタリスト（材料）"""
    region = info["region"]
    catalysts = []

    if region == "アジア" and info["country"] == "🇯🇵":
        catalysts = [
            "📅 日銀金融政策決定会合（年8回）",
            "📊 米雇用統計→米株→翌朝の日経反応",
            "💴 USD/JPY 152円・155円水準（介入リスク）",
            "🏢 主要企業決算（4月末・10月末）",
            "🌍 米中関係・台湾情勢",
        ]
    elif info["country"] == "🇺🇸":
        catalysts = [
            "📅 FOMC（年8回）→ 政策金利・ドットチャート",
            "📊 米CPI（毎月10日前後 22:30 JST）",
            "📊 米雇用統計（第1金曜 21:30 JST）",
            "🏢 GAFAM決算（1月末・4月末・7月末・10月末）",
            "📉 VIX 20超でリスクオフ",
            "🪙 10年債利回り 4.5%超で警戒",
        ]
    elif region == "欧州":
        catalysts = [
            "📅 ECB理事会（毎月）",
            "📊 ユーロ圏CPI・PMI",
            "🌍 ロシア・ウクライナ情勢",
            "⛽ エネルギー価格動向",
        ]
    elif info["country"] in ["🇭🇰", "🇨🇳"]:
        catalysts = [
            "📅 中国LPR金利発表（毎月20日前後）",
            "📅 PBOC（中国人民銀行）政策",
            "🏢 不動産デベロッパー動向",
            "🌍 米中貿易摩擦・関税",
            "🏦 GAFAM版（テンセント・アリババ等）決算",
        ]
    elif info["country"] == "🇹🇼":
        catalysts = [
            "📅 TSMC月次売上発表（毎月10日頃）",
            "🇺🇸 NVIDIA・AMD決算",
            "🌍 台湾選挙・米中関係",
            "🤖 AI半導体需要",
        ]
    elif info["country"] == "🇰🇷":
        catalysts = [
            "📅 韓国輸出統計（毎月1日）",
            "🏢 サムスン・SKハイニックス決算",
            "📦 メモリ半導体価格",
            "🌍 北朝鮮情勢",
        ]
    elif info["country"] == "🇦🇺":
        catalysts = [
            "📅 RBA政策金利会合（月初）",
            "🏗 鉄鉱石・石炭価格",
            "🇨🇳 中国景気指標",
        ]
    elif info["country"] == "🇮🇳":
        catalysts = [
            "📅 RBI政策金利",
            "📊 GDP成長率（世界最速）",
            "💰 FII（外国人投資家）資金フロー",
            "⛽ 原油価格（輸入大）",
        ]
    elif info["country"] == "🇧🇷":
        catalysts = [
            "📅 中銀（COPOM）政策金利",
            "📊 鉄鉱石・大豆価格",
            "🇨🇳 中国需要",
        ]
    else:
        catalysts = ["材料は地政学・金融政策・経済指標が中心"]

    return catalysts


# ════════════════════════════════════════════════
#  メインAPI
# ════════════════════════════════════════════════

def analyze_index_future(symbol: str) -> Optional[dict]:
    """
    指数先物を総合分析し、予測・シナリオ・カタリストを返す
    """
    if symbol not in INDEX_FUTURES:
        return None

    info = INDEX_FUTURES[symbol]
    yf_symbol = info.get("yf_symbol", symbol)

    try:
        t = yf.Ticker(yf_symbol)
        df = t.history(period="1y", interval="1d")
        if df is None or df.empty or len(df) < 30:
            return None
    except Exception:
        return None

    df = df.dropna(subset=["Close"])
    current_price = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else current_price
    change_1d = (current_price / prev_close - 1) * 100

    # 期間別パフォーマンス
    def _chg(days):
        if len(df) < days + 1:
            return 0.0
        past = float(df["Close"].iloc[-days - 1])
        return round((current_price / past - 1) * 100, 2)

    perf = {
        "1d": round(change_1d, 2),
        "1w": _chg(5),
        "1m": _chg(20),
        "3m": _chg(60),
        "6m": _chg(120),
        "1y": _chg(min(240, len(df) - 1)),
    }

    # ボラティリティ（過去20日標準偏差・年率化）
    returns = df["Close"].pct_change().dropna()
    vol = float(returns.tail(20).std()) if len(returns) >= 20 else 0.02
    annual_vol = vol * np.sqrt(252) * 100

    # サポート・レジスタンス
    sr = _calc_support_resistance(df)

    # マルチタイムフレーム予測
    predictions = _multi_timeframe_predict(df)

    # シナリオ
    scenarios = _build_scenarios(current_price, sr, predictions, vol)

    # カタリスト
    catalysts = _identify_catalysts(symbol, info)

    # 総合判定
    total_score = (
        predictions["short_term"]["score"]
        + predictions["mid_term"]["score"]
        + predictions["long_term"]["score"]
    )
    if total_score >= 4:
        verdict = "🚀 強気"
        verdict_detail = "全タイムフレームで上昇シグナル → 押し目買い有効"
        verdict_color = "#D32030"
    elif total_score >= 2:
        verdict = "🟢 やや強気"
        verdict_detail = "中長期は強気だが短期は注意"
        verdict_color = "#D32030"
    elif total_score >= -1:
        verdict = "⚪ 中立"
        verdict_detail = "方向感乏しく様子見推奨"
        verdict_color = "#FDB813"
    elif total_score >= -3:
        verdict = "🟡 やや弱気"
        verdict_detail = "下値リスク注意・利確検討"
        verdict_color = "#FDB813"
    else:
        verdict = "📉 弱気"
        verdict_detail = "全タイムフレーム下降 → 戻り売り戦略"
        verdict_color = "#1565C0"

    return {
        "symbol": symbol,
        "name": info["name"],
        "short_name": info["short"],
        "country": info["country"],
        "region": info["region"],
        "trading_hours": info["trading_hours_jst"],
        "current_price": round(current_price, 2),
        "change_1d": round(change_1d, 2),
        "performance": perf,
        "volatility_pct": round(annual_vol, 1),
        "support_resistance": sr,
        "predictions": predictions,
        "scenarios": scenarios,
        "catalysts": catalysts,
        "key_drivers": info["key_drivers"],
        "correlation": info["correlation"],
        "total_score": total_score,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "verdict_color": verdict_color,
        "df": df,
    }


def scan_all_index_futures() -> list:
    """全指数先物を一括スキャンしランキングを返す"""
    results = []
    for symbol in INDEX_FUTURES.keys():
        try:
            r = analyze_index_future(symbol)
            if r is None:
                continue
            results.append({
                "symbol": symbol,
                "country": r["country"],
                "short_name": r["short_name"],
                "name": r["name"],
                "current_price": r["current_price"],
                "change_1d": r["change_1d"],
                "perf_1m": r["performance"]["1m"],
                "perf_3m": r["performance"]["3m"],
                "rsi": r["predictions"]["rsi"],
                "verdict": r["verdict"],
                "total_score": r["total_score"],
                "short_dir": r["predictions"]["short_term"]["direction"],
                "mid_dir": r["predictions"]["mid_term"]["direction"],
                "long_dir": r["predictions"]["long_term"]["direction"],
                "volatility": r["volatility_pct"],
            })
        except Exception:
            continue

    # スコアでソート
    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results
