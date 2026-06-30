"""
株式スクリーニング・予測モジュール
全銘柄を横断スキャンし、リーダー/出遅れ/大変動/急騰候補を抽出。
1分足ベースの短期予測も行う。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


# ─── スキャン対象の全銘柄 ───

SCAN_TARGETS = {
    # 日本主要株
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニーグループ",
    "7974.T": "任天堂",
    "9984.T": "ソフトバンクG",
    "9983.T": "ファーストリテイリング",
    "6861.T": "キーエンス",
    "8035.T": "東京エレクトロン",
    "8306.T": "三菱UFJ",
    "6902.T": "デンソー",
    "6501.T": "日立製作所",
    "6367.T": "ダイキン工業",
    "4063.T": "信越化学",
    "6594.T": "日本電産",
    "7267.T": "ホンダ",
    "9432.T": "NTT",
    # 米国主要株
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Google/Alphabet",
    "META": "Meta",
    "TSLA": "Tesla",
    "BRK-B": "Berkshire Hathaway",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "UNH": "UnitedHealth",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
}


def scan_all_stocks() -> List[dict]:
    """
    全銘柄をスキャンし、各銘柄のスコア・分類を返す

    Returns:
        [
            {
                "ticker": ティッカー,
                "name": 銘柄名,
                "price": 現在値,
                "change_pct": 変動率(%),
                "volume_ratio": 出来高倍率（平均比）,
                "momentum": モメンタムスコア,
                "volatility": ボラティリティ,
                "rsi": RSI値,
                "category": "リーダー" / "出遅れ" / "大変動" / "安定",
                "prediction": "上昇" / "下降" / "横ばい",
                "confidence": 信頼度,
                "signals": [シグナルリスト],
                "market": "JP" / "US",
            }, ...
        ]
    """
    results = []

    tickers_str = " ".join(SCAN_TARGETS.keys())
    try:
        data = yf.download(tickers_str, period="1mo", interval="1d", group_by="ticker", progress=False)
    except Exception:
        data = None

    for ticker, name in SCAN_TARGETS.items():
        try:
            result = _analyze_single_stock(ticker, name, data)
            if result:
                results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["momentum"]), reverse=True)
    return results


def _analyze_single_stock(ticker: str, name: str, bulk_data) -> Optional[dict]:
    """個別銘柄の分析"""
    try:
        if bulk_data is not None and ticker in bulk_data.columns.get_level_values(0):
            df = bulk_data[ticker].dropna()
        else:
            t = yf.Ticker(ticker)
            df = t.history(period="1mo", interval="1d")

        if df.empty or len(df) < 5:
            return None

        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series([0] * len(df))
        high = df["High"]
        low = df["Low"]

        current = close.iloc[-1]
        prev = close.iloc[-2]
        change_pct = (current / prev - 1) * 100

        # 出来高倍率
        avg_vol = volume.tail(20).mean()
        vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1.0

        # モメンタム（5日リターン）
        if len(close) >= 5:
            momentum = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        else:
            momentum = change_pct

        # ボラティリティ
        volatility = close.pct_change().tail(10).std() * 100

        # RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1] if not rsi_series.dropna().empty else 50

        # 移動平均
        ma5 = close.tail(5).mean()
        ma25 = close.tail(25).mean() if len(close) >= 25 else ma5

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = (ema12 - ema26).iloc[-1]
        signal = (ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1]

        # シグナル判定
        signals = []
        category = "安定"

        # リーダー判定
        if momentum > 3 and current > ma5 > ma25 and rsi > 50:
            category = "リーダー"
            signals.append("強い上昇トレンド + 移動平均線が全て上向き")

        # 出遅れ（反発候補）判定
        elif momentum < -3 and rsi < 35:
            category = "出遅れ"
            signals.append("大幅下落後 + RSI売られすぎ → 反発の可能性")
        elif momentum < -2 and current < ma25 and rsi < 40:
            category = "出遅れ"
            signals.append("中期移動平均を下回る + 売られすぎ圏に接近")

        # 大変動判定
        if volatility > 2.5 or abs(change_pct) > 3 or vol_ratio > 2.0:
            category = "大変動"
            if abs(change_pct) > 3:
                signals.append(f"本日{change_pct:+.1f}%の大幅変動")
            if vol_ratio > 2.0:
                signals.append(f"出来高が平均の{vol_ratio:.1f}倍 → 異常な売買")
            if volatility > 3:
                signals.append(f"ボラティリティ {volatility:.2f}% → 高変動銘柄")

        # 予測
        prediction, confidence = _predict_direction(close, rsi, macd, signal, momentum, vol_ratio)

        if rsi > 70:
            signals.append(f"RSI={rsi:.0f}（買われすぎ）→ 反落注意")
        elif rsi < 30:
            signals.append(f"RSI={rsi:.0f}（売られすぎ）→ 反発期待")

        if macd > signal:
            signals.append("MACD買いシグナル")
        else:
            signals.append("MACD売りシグナル")

        if not signals:
            signals.append("特段のシグナルなし")

        market = "JP" if ticker.endswith(".T") else "US"

        return {
            "ticker": ticker,
            "name": name,
            "price": round(current, 2),
            "change_pct": round(change_pct, 2),
            "volume_ratio": round(vol_ratio, 1),
            "momentum": round(momentum, 2),
            "volatility": round(volatility, 3),
            "rsi": round(rsi, 1) if not np.isnan(rsi) else 50,
            "category": category,
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "signals": signals,
            "market": market,
        }

    except Exception:
        return None


def _predict_direction(close, rsi, macd, signal, momentum, vol_ratio):
    """テクニカル指標ベースの方向予測"""
    score = 0.0

    # モメンタム
    if momentum > 2:
        score += 0.3
    elif momentum < -2:
        score -= 0.3

    # RSI
    if rsi > 70:
        score -= 0.2  # 反落リスク
    elif rsi < 30:
        score += 0.2  # 反発期待
    elif rsi > 55:
        score += 0.1
    elif rsi < 45:
        score -= 0.1

    # MACD
    if macd > signal:
        score += 0.2
    else:
        score -= 0.2

    # 出来高（異常出来高は方向を増幅）
    if vol_ratio > 2.0:
        score *= 1.3

    # 直近トレンド
    if len(close) >= 3:
        recent = (close.iloc[-1] / close.iloc[-3] - 1) * 100
        if recent > 1:
            score += 0.15
        elif recent < -1:
            score -= 0.15

    if score > 0.15:
        prediction = "上昇"
        confidence = min(85, 50 + abs(score) * 50)
    elif score < -0.15:
        prediction = "下降"
        confidence = min(85, 50 + abs(score) * 50)
    else:
        prediction = "横ばい"
        confidence = 40

    return prediction, confidence


def predict_stock_1min(ticker: str) -> Optional[dict]:
    """
    1分足データで短期予測を行う

    Returns:
        {
            "direction": "上昇" / "下降" / "横ばい",
            "confidence": 信頼度,
            "current_price": 現在値,
            "predicted_range": (下限, 上限),
            "next_peak_time": 次のピーク予測時刻,
            "factors": [根拠],
        }
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="5d", interval="1m")
    except Exception:
        return None

    if df.empty or len(df) < 30:
        return None

    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Tokyo").tz_localize(None)

    close = df["Close"]
    current = close.iloc[-1]
    factors = []

    # 短期移動平均
    ma5 = close.tail(5).mean()
    ma15 = close.tail(15).mean()

    # 短期RSI (7期間)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(7).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(7).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi7 = (100 - (100 / (1 + rs))).iloc[-1]

    # 直近の値動き
    last_5 = close.tail(5)
    micro_trend = (last_5.iloc[-1] / last_5.iloc[0] - 1) * 100

    score = 0.0

    if current > ma5 > ma15:
        score += 0.3
        factors.append("現在値 > MA5 > MA15（上昇トレンド）")
    elif current < ma5 < ma15:
        score -= 0.3
        factors.append("現在値 < MA5 < MA15（下降トレンド）")

    if rsi7 > 75:
        score -= 0.2
        factors.append(f"短期RSI={rsi7:.0f}（買われすぎ → 調整入りの可能性）")
    elif rsi7 < 25:
        score += 0.2
        factors.append(f"短期RSI={rsi7:.0f}（売られすぎ → 反発の可能性）")

    if micro_trend > 0.1:
        score += 0.15
        factors.append(f"直近5分で+{micro_trend:.2f}%上昇中")
    elif micro_trend < -0.1:
        score -= 0.15
        factors.append(f"直近5分で{micro_trend:.2f}%下落中")

    # 突発変動（ショック）判定
    ret_1m = close.pct_change().dropna()
    base_vol = float(ret_1m.tail(60).std()) if len(ret_1m) >= 60 else float(ret_1m.std())
    move_1m = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else 0.0
    move_3m = (close.iloc[-1] / close.iloc[-4] - 1) * 100 if len(close) >= 4 else move_1m
    z_1m = abs((move_1m / 100) / base_vol) if base_vol > 0 else 0.0
    z_3m = abs((move_3m / 100) / (base_vol * np.sqrt(3))) if base_vol > 0 else 0.0
    is_shock = (z_1m >= 3.0) or (z_3m >= 3.0) or (abs(move_1m) >= 0.7) or (abs(move_3m) >= 1.2)

    if is_shock:
        shock_dir = "急騰" if move_3m > 0 else "急落"
        shock_msg = f"⚠️ 突発変動検知: 3分で{move_3m:+.2f}%（z≈{max(z_1m, z_3m):.2f}）"
        factors.insert(0, shock_msg)
        # 急変時は直近変動を強く反映して追従
        score += 0.35 if move_3m > 0 else -0.35
        factors.append(f"{shock_dir}局面のため、短期予測は直近値動き追従を優先")

    # 予測レンジ
    recent_vol = close.pct_change().tail(30).std()
    range_pct = recent_vol * 2 * current
    predicted_low = current - range_pct
    predicted_high = current + range_pct

    if score > 0.15:
        direction = "上昇"
        confidence = min(80, 50 + abs(score) * 50)
    elif score < -0.15:
        direction = "下降"
        confidence = min(80, 50 + abs(score) * 50)
    else:
        direction = "横ばい"
        confidence = 35

    # ピーク時刻推測
    df_reset = df.reset_index()
    dt_col = "Datetime" if "Datetime" in df_reset.columns else "index"
    if dt_col in df_reset.columns:
        df_reset["hour"] = df_reset[dt_col].dt.hour
        df_reset["date"] = df_reset[dt_col].dt.date
        hourly_vol = df_reset.groupby("hour")["Close"].apply(lambda x: x.pct_change().std())
        if not hourly_vol.empty:
            peak_hour = hourly_vol.idxmax()
            factors.append(f"過去の値動きは{peak_hour}時台が最も活発")

    return {
        "direction": direction,
        "confidence": confidence,
        "current_price": round(current, 2),
        "predicted_range": (round(predicted_low, 2), round(predicted_high, 2)),
        "factors": factors,
        "shock": {
            "is_shock": bool(is_shock),
            "move_1m_pct": round(move_1m, 3),
            "move_3m_pct": round(move_3m, 3),
            "zscore": round(max(z_1m, z_3m), 2),
        },
    }


def predict_multi_horizon_path(
    ticker: str,
    horizons: Optional[list[int]] = None,
) -> Optional[dict]:
    """
    1分足を使って、複数時間軸（例: 1/3/5/15/30/60分）の予測価格を返す。
    FX・株式のどちらでも利用可能。
    """
    if horizons is None:
        horizons = [1, 3, 5, 15, 30, 60]

    try:
        t = yf.Ticker(ticker)
        df = t.history(period="5d", interval="1m")
    except Exception:
        return None

    if df is None or df.empty or len(df) < 80:
        return None

    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Tokyo").tz_localize(None)

    close = df["Close"].dropna()
    if close.empty:
        return None

    current = float(close.iloc[-1])
    now_ts = datetime.now()

    diff = close.diff().dropna()
    if diff.empty:
        return None

    base_step = float(diff.tail(20).mean())
    recent_step = float(diff.tail(5).mean())
    last_step = float(diff.iloc[-1])
    vol_1m = float(close.pct_change().dropna().tail(60).std()) if len(close) >= 61 else 0.0

    # 急変時は直近1本を強く反映して追従
    shock_ratio = abs(last_step) / max(abs(recent_step), 1e-9) if recent_step != 0 else abs(last_step) * 100
    shock_weight = 0.45 if shock_ratio >= 2.2 else 0.15
    step = base_step * 0.45 + recent_step * (0.55 - shock_weight) + last_step * shock_weight

    points = [{
        "minutes": 0,
        "label": "現在",
        "time": now_ts.strftime("%H:%M"),
        "price": round(current, 4),
        "diff_pct": 0.0,
        "confidence": 100,
    }]

    for m in horizons:
        decay = 0.98 ** max(0, m - 1)
        pred = current + (step * m * decay)
        diff_pct = (pred / current - 1) * 100 if current else 0.0

        # 時間が遠いほど信頼度を落とす（ショック時はさらに低下）
        conf = 86 - (m * 0.75) - (8 if shock_ratio >= 2.2 else 0)
        conf = int(max(25, min(90, conf)))

        points.append({
            "minutes": m,
            "label": f"{m}分",
            "time": (now_ts + timedelta(minutes=m)).strftime("%H:%M"),
            "price": round(float(pred), 4),
            "diff_pct": round(float(diff_pct), 3),
            "confidence": conf,
        })

    reasons = [
        f"直近20本平均変化: {base_step:+.5f}",
        f"直近5本平均変化: {recent_step:+.5f}",
        f"直近1本変化: {last_step:+.5f}",
    ]
    if vol_1m > 0:
        reasons.append(f"1分ボラティリティ: {vol_1m * 100:.3f}%")
    if shock_ratio >= 2.2:
        reasons.append("⚠️ 急変モード: 直近値動きを重視して追従予測")
    else:
        reasons.append("通常モード: モメンタム平均ベース予測")

    return {
        "ticker": ticker,
        "current_price": round(current, 4),
        "points": points,
        "reasons": reasons,
        "shock_ratio": round(float(shock_ratio), 2),
    }


def get_top_movers(results: List[dict], n: int = 5) -> dict:
    """スキャン結果から各カテゴリのトップ銘柄を抽出"""
    leaders = [r for r in results if r["category"] == "リーダー"]
    laggards = [r for r in results if r["category"] == "出遅れ"]
    big_movers = sorted(results, key=lambda x: abs(x["change_pct"]), reverse=True)
    high_vol = sorted(results, key=lambda x: x["volume_ratio"], reverse=True)
    up_predicted = [r for r in results if r["prediction"] == "上昇"]
    up_predicted.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "leaders": leaders[:n],
        "laggards": laggards[:n],
        "big_movers": big_movers[:n],
        "high_volume": high_vol[:n],
        "up_predicted": up_predicted[:n],
    }
