"""
新興・新発掘銘柄モジュール
AI、量子コンピュータ、レアアース、宇宙、新エネルギー、バイオ等の
最先端テーマ銘柄を分類し、買い時/売り時シグナルを判定する
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional


# ════════════════════════════════════════════════
#  テーマ別 新興・新発掘銘柄
# ════════════════════════════════════════════════

EMERGING_STOCKS = {
    "🤖 AI・人工知能": {
        "NVDA": "NVIDIA（AI半導体の覇者）",
        "AMD": "AMD（AI推論チップ）",
        "AVGO": "Broadcom（カスタムAIチップ）",
        "PLTR": "Palantir（AI解析プラットフォーム）",
        "AI": "C3.ai（エンタープライズAI）",
        "SMCI": "Super Micro（AIサーバー）",
        "ARM": "Arm Holdings（AI向け省電力チップ）",
        "SNOW": "Snowflake（AIデータプラットフォーム）",
    },
    "⚛️ 量子コンピュータ": {
        "IONQ": "IonQ（イオントラップ量子）",
        "RGTI": "Rigetti Computing（超伝導量子）",
        "QBTS": "D-Wave Quantum（量子アニーリング）",
        "QUBT": "Quantum Computing Inc.",
        "IBM": "IBM（量子クラウド）",
        "GOOGL": "Alphabet（Google量子AI）",
    },
    "💎 レアアース・重要鉱物": {
        "MP": "MP Materials（米国唯一のレアアース鉱山）",
        "TMC": "TMC the Metals Company（深海鉱物）",
        "LAC": "Lithium Americas（リチウム）",
        "ALB": "Albemarle（リチウム最大手）",
        "SQM": "SQM（チリのリチウム）",
        "FCX": "Freeport-McMoRan（銅）",
        "USAR": "USA Rare Earth",
        "5713.T": "住友金属鉱山（レアメタル日本最大）",
    },
    "🚀 宇宙・衛星": {
        "RKLB": "Rocket Lab（小型ロケット）",
        "ASTS": "AST SpaceMobile（衛星携帯通信）",
        "PL": "Planet Labs（地球観測衛星）",
        "IRDM": "Iridium（衛星通信）",
        "LMT": "Lockheed Martin（宇宙防衛）",
        "BA": "Boeing（宇宙開発）",
        "MAXR": "Maxar Technologies（衛星画像）",
    },
    "🔋 次世代エネルギー": {
        "TSLA": "Tesla（EV+蓄電池）",
        "ENPH": "Enphase Energy（太陽光）",
        "SEDG": "SolarEdge（太陽光インバーター）",
        "PLUG": "Plug Power（水素燃料電池）",
        "BE": "Bloom Energy（燃料電池）",
        "BLDP": "Ballard Power（水素）",
        "FSLR": "First Solar（薄膜太陽電池）",
        "NEE": "NextEra Energy（再エネ最大手）",
        "QS": "QuantumScape（全固体電池）",
        "9501.T": "東京電力HD（原発・再エネ）",
    },
    "🧬 バイオテック・遺伝子治療": {
        "MRNA": "Moderna（mRNAワクチン）",
        "BNTX": "BioNTech（mRNA技術）",
        "CRSP": "CRISPR Therapeutics（遺伝子編集）",
        "NTLA": "Intellia Therapeutics（CRISPR）",
        "BEAM": "Beam Therapeutics（塩基編集）",
        "EDIT": "Editas Medicine（遺伝子編集）",
        "VRTX": "Vertex Pharmaceuticals",
        "REGN": "Regeneron",
        "4151.T": "協和キリン（バイオ医薬）",
    },
    "🤖 ロボティクス・自動化": {
        "ABBNY": "ABB（産業ロボット）",
        "ISRG": "Intuitive Surgical（手術ロボット）",
        "IRBT": "iRobot（民生ロボット）",
        "6954.T": "ファナック（産業ロボット）",
        "6506.T": "安川電機（モーター・ロボット）",
        "6857.T": "アドバンテスト（半導体検査）",
    },
    "🌐 サイバーセキュリティ": {
        "CRWD": "CrowdStrike（クラウドセキュリティ）",
        "PANW": "Palo Alto Networks",
        "ZS": "Zscaler（ゼロトラスト）",
        "S": "SentinelOne（AI防御）",
        "OKTA": "Okta（ID認証）",
        "FTNT": "Fortinet",
        "NET": "Cloudflare",
    },
    "💊 GLP-1・肥満治療": {
        "LLY": "Eli Lilly（マンジャロ・ゼップバウンド）",
        "NVO": "Novo Nordisk（ウゴービ・オゼンピック）",
        "VKTX": "Viking Therapeutics（次世代GLP-1）",
        "AMGN": "Amgen（GLP-1パイプライン）",
    },
    "💎 半導体製造装置": {
        "ASML": "ASML（EUV露光装置独占）",
        "AMAT": "Applied Materials",
        "LRCX": "Lam Research",
        "KLAC": "KLA Corporation",
        "8035.T": "東京エレクトロン",
        "6920.T": "レーザーテック（EUV検査）",
        "6857.T": "アドバンテスト",
    },
    "🌊 核融合・次世代原子力": {
        "BWXT": "BWX Technologies（小型原子炉SMR）",
        "CCJ": "Cameco（ウラン採掘）",
        "LEU": "Centrus Energy（濃縮ウラン）",
        "NNE": "Nano Nuclear Energy",
        "OKLO": "Oklo（次世代原子炉）",
        "SMR": "NuScale Power（SMR）",
        "URA": "Global X Uranium ETF",
    },
}


def get_all_emerging_tickers() -> dict:
    """全ての新興銘柄をフラットな辞書で返す"""
    flat = {}
    for theme, stocks in EMERGING_STOCKS.items():
        for ticker, name in stocks.items():
            flat[ticker] = {"name": name, "theme": theme}
    return flat


def analyze_emerging_stock(ticker: str) -> Optional[dict]:
    """
    新興銘柄を分析し、買い時/売り時シグナルを生成

    Returns:
        {
            "ticker": ティッカー,
            "name": 銘柄名,
            "theme": テーマ,
            "price": 現在値,
            "change_1d": 1日変動率,
            "change_1w": 1週間変動率,
            "change_1m": 1ヶ月変動率,
            "change_3m": 3ヶ月変動率,
            "rsi": RSI,
            "ma_position": MA位置 ("above_all" / "between" / "below_all"),
            "volume_signal": 出来高シグナル,
            "verdict": "買い時" / "売り時" / "様子見" / "ホールド",
            "verdict_strength": "強" / "中" / "弱",
            "buy_signals": [買いシグナルリスト],
            "sell_signals": [売りシグナルリスト],
            "entry_price": 推奨エントリー価格,
            "stop_loss": 損切り価格,
            "target_price": 利益確定目標価格,
            "risk_reward": リスクリワード比,
        }
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="6mo", interval="1d")

        if df is None or df.empty or len(df) < 30:
            return None
    except Exception:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series([0] * len(close))

    current = close.iloc[-1]

    # 各期間の変動率
    def chg(periods):
        if len(close) > periods:
            return (current / close.iloc[-1 - periods] - 1) * 100
        return 0.0

    change_1d = chg(1)
    change_1w = chg(5)
    change_1m = chg(20)
    change_3m = chg(60)

    # 移動平均
    ma20 = close.tail(20).mean()
    ma50 = close.tail(50).mean() if len(close) >= 50 else ma20
    ma200 = close.tail(200).mean() if len(close) >= 200 else ma50

    if current > ma20 > ma50 > ma200:
        ma_position = "above_all"
        ma_label = "強い上昇トレンド（全MA上回る）"
    elif current < ma20 < ma50 < ma200:
        ma_position = "below_all"
        ma_label = "強い下降トレンド（全MA下回る）"
    else:
        ma_position = "between"
        ma_label = "もみ合い"

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi = rsi_series.iloc[-1] if not rsi_series.dropna().empty else 50

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_now = macd.iloc[-1]
    sig_now = signal.iloc[-1]
    macd_prev = macd.iloc[-2] if len(macd) > 1 else macd_now
    sig_prev = signal.iloc[-2] if len(signal) > 1 else sig_now

    # ボリンジャーバンド位置
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    if not bb_std.iloc[-1] == 0 and not np.isnan(bb_std.iloc[-1]):
        bb_pos = (current - bb_mid.iloc[-1]) / (bb_std.iloc[-1] * 2)
    else:
        bb_pos = 0

    # 出来高シグナル
    avg_vol = volume.tail(20).mean()
    vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1.0
    if vol_ratio > 2.0 and change_1d > 0:
        volume_signal = "急増（買い圧力）"
    elif vol_ratio > 2.0 and change_1d < 0:
        volume_signal = "急増（売り圧力）"
    elif vol_ratio < 0.5:
        volume_signal = "閑散"
    else:
        volume_signal = "通常"

    # ─── シグナル生成 ───
    buy_signals = []
    sell_signals = []
    buy_score = 0
    sell_score = 0

    # 1. RSI
    if rsi < 30:
        buy_signals.append(f"✅ RSI={rsi:.0f}（売られすぎ → 反発期待）")
        buy_score += 3
    elif rsi < 40:
        buy_signals.append(f"⚠️ RSI={rsi:.0f}（やや売られ気味）")
        buy_score += 1
    elif rsi > 70:
        sell_signals.append(f"⚠️ RSI={rsi:.0f}（買われすぎ → 利確検討）")
        sell_score += 3
    elif rsi > 60:
        sell_signals.append(f"💡 RSI={rsi:.0f}（やや買われ気味）")
        sell_score += 1

    # 2. MACD クロス
    if macd_prev < sig_prev and macd_now > sig_now:
        buy_signals.append("🟢 MACDゴールデンクロス発生（強い買いシグナル）")
        buy_score += 4
    elif macd_prev > sig_prev and macd_now < sig_now:
        sell_signals.append("🔴 MACDデッドクロス発生（強い売りシグナル）")
        sell_score += 4
    elif macd_now > sig_now:
        buy_signals.append("✅ MACD > シグナル（上昇継続）")
        buy_score += 1
    else:
        sell_signals.append("⚠️ MACD < シグナル（下降継続）")
        sell_score += 1

    # 3. 移動平均
    if ma_position == "above_all":
        buy_signals.append("✅ 価格が全移動平均線を上回る（強い上昇トレンド）")
        buy_score += 2
    elif ma_position == "below_all":
        sell_signals.append("⚠️ 価格が全移動平均線を下回る（強い下降トレンド）")
        sell_score += 2

    # 4. ゴールデンクロス（MA20 > MA50）
    if len(close) >= 50:
        ma20_prev = close.iloc[-2:-22].mean() if len(close) >= 22 else ma20
        ma50_prev = close.iloc[-2:-52].mean() if len(close) >= 52 else ma50
        if ma20_prev < ma50_prev and ma20 > ma50:
            buy_signals.append("🟢 移動平均ゴールデンクロス（中期上昇転換）")
            buy_score += 3
        elif ma20_prev > ma50_prev and ma20 < ma50:
            sell_signals.append("🔴 移動平均デッドクロス（中期下降転換）")
            sell_score += 3

    # 5. ボリンジャーバンド
    if bb_pos < -0.9:
        buy_signals.append(f"✅ ボリンジャーバンド下限接触（反発期待）")
        buy_score += 2
    elif bb_pos > 0.9:
        sell_signals.append(f"⚠️ ボリンジャーバンド上限接触（過熱）")
        sell_score += 2

    # 6. 出来高
    if "買い圧力" in volume_signal:
        buy_signals.append(f"🟢 {volume_signal}（出来高{vol_ratio:.1f}倍）")
        buy_score += 2
    elif "売り圧力" in volume_signal:
        sell_signals.append(f"🔴 {volume_signal}（出来高{vol_ratio:.1f}倍）")
        sell_score += 2

    # 7. 中期トレンド
    if change_1m > 10 and change_3m > 20:
        buy_signals.append(f"✅ 中期上昇継続（1ヶ月+{change_1m:.1f}% / 3ヶ月+{change_3m:.1f}%）")
        buy_score += 1
    elif change_1m < -10 and change_3m < -20:
        sell_signals.append(f"⚠️ 中期下落継続（1ヶ月{change_1m:.1f}% / 3ヶ月{change_3m:.1f}%）")
        sell_score += 1

    # ─── 総合判定 ───
    if buy_score >= 7 and buy_score > sell_score + 3:
        verdict = "買い時"
        if buy_score >= 10:
            strength = "強"
        elif buy_score >= 8:
            strength = "中"
        else:
            strength = "弱"
    elif sell_score >= 7 and sell_score > buy_score + 3:
        verdict = "売り時"
        if sell_score >= 10:
            strength = "強"
        elif sell_score >= 8:
            strength = "中"
        else:
            strength = "弱"
    elif buy_score > sell_score + 1:
        verdict = "ホールド（やや買い）"
        strength = "弱"
    elif sell_score > buy_score + 1:
        verdict = "ホールド（やや売り）"
        strength = "弱"
    else:
        verdict = "様子見"
        strength = "弱"

    # ─── エントリー・損切り・利確価格 ───
    atr = (high - low).tail(14).mean()  # Average True Range（簡易版）

    if verdict == "買い時":
        entry = current
        stop_loss = current - atr * 2
        target = current + atr * 4
    elif verdict == "売り時":
        entry = current
        stop_loss = current + atr * 2
        target = current - atr * 4
    else:
        entry = current
        stop_loss = current - atr * 1.5
        target = current + atr * 3

    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    rr = reward / risk if risk > 0 else 0

    all_tickers = get_all_emerging_tickers()
    info = all_tickers.get(ticker, {"name": ticker, "theme": "その他"})

    return {
        "ticker": ticker,
        "name": info["name"],
        "theme": info["theme"],
        "price": round(current, 2),
        "change_1d": round(change_1d, 2),
        "change_1w": round(change_1w, 2),
        "change_1m": round(change_1m, 2),
        "change_3m": round(change_3m, 2),
        "rsi": round(rsi, 1) if not np.isnan(rsi) else 50,
        "ma_position": ma_position,
        "ma_label": ma_label,
        "volume_signal": volume_signal,
        "vol_ratio": round(vol_ratio, 1),
        "verdict": verdict,
        "verdict_strength": strength,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "buy_score": buy_score,
        "sell_score": sell_score,
        "entry_price": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target_price": round(target, 2),
        "risk_reward": round(rr, 2),
    }


def scan_emerging_by_theme(theme: str) -> List[dict]:
    """指定テーマの全銘柄を分析"""
    results = []
    if theme not in EMERGING_STOCKS:
        return results

    for ticker in EMERGING_STOCKS[theme]:
        result = analyze_emerging_stock(ticker)
        if result:
            results.append(result)

    results.sort(key=lambda x: x["buy_score"] - x["sell_score"], reverse=True)
    return results


def scan_all_emerging() -> dict:
    """全テーマをスキャンして買い時銘柄を抽出"""
    all_results = []
    by_theme = {}

    for theme in EMERGING_STOCKS:
        theme_results = scan_emerging_by_theme(theme)
        by_theme[theme] = theme_results
        all_results.extend(theme_results)

    buy_now = [r for r in all_results if r["verdict"] == "買い時"]
    sell_now = [r for r in all_results if r["verdict"] == "売り時"]
    buy_now.sort(key=lambda x: x["buy_score"], reverse=True)
    sell_now.sort(key=lambda x: x["sell_score"], reverse=True)

    return {
        "all": all_results,
        "by_theme": by_theme,
        "buy_now": buy_now[:10],
        "sell_now": sell_now[:10],
    }
