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

    def _label(minutes: int) -> str:
        if minutes < 60:
            return f"{minutes}分"
        if minutes % 1440 == 0:
            return f"{minutes // 1440}日"
        if minutes % 60 == 0:
            return f"{minutes // 60}時間"
        return f"{minutes}分"

    points = [{
        "minutes": 0,
        "label": "現在",
        "time": now_ts.strftime("%H:%M"),
        "price": round(current, 4),
        "diff_pct": 0.0,
        "confidence": 100,
    }]

    for m in horizons:
        # 長時間になるほど1分足ノイズの影響を抑え、緩やかなドリフトに減衰
        decay = 0.997 ** max(0, m - 1)
        pred = current + (step * m * decay)
        diff_pct = (pred / current - 1) * 100 if current else 0.0

        # 時間が遠いほど信頼度を落とす（ショック時はさらに低下）
        conf = 86 - (m * 0.75) - (8 if shock_ratio >= 2.2 else 0)
        conf = int(max(25, min(90, conf)))

        points.append({
            "minutes": m,
            "label": _label(m),
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


def _extract_plan_notes(ticker_obj: yf.Ticker, base_ticker: str) -> tuple[list[str], list[str]]:
    """
    企業の公開情報（概要・ニュース）から中長期の計画テーマを抽出する。
    """
    notes: list[str] = []
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}

    summary = str(info.get("longBusinessSummary") or "")
    revenue_growth = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")
    capex = info.get("capitalExpenditure")

    if isinstance(revenue_growth, (int, float)):
        notes.append(f"売上成長率（YoY）: {revenue_growth * 100:+.1f}%")
    if isinstance(earnings_growth, (int, float)):
        notes.append(f"利益成長率（YoY）: {earnings_growth * 100:+.1f}%")
    if isinstance(capex, (int, float)):
        notes.append(f"設備投資（直近報告）: {capex:,.0f}")

    keyword_map = {
        "AI・半導体投資": ["ai", "artificial intelligence", "gpu", "semiconductor", "chip", "データセンター", "半導体"],
        "クラウド/ソフト拡張": ["cloud", "saas", "software", "platform", "subscription"],
        "EV・電池戦略": ["ev", "battery", "electric vehicle", "自動運転", "蓄電池"],
        "工場増設・能力増強": ["capacity", "plant", "facility", "fab", "expansion", "増産", "工場"],
        "M&A・提携": ["acquisition", "merger", "partnership", "strategic alliance", "提携", "買収"],
        "株主還元": ["buyback", "dividend", "shareholder return", "自社株買い", "増配"],
    }

    text_pool = [summary.lower()]
    participant_tickers: set[str] = set()
    try:
        news_items = getattr(ticker_obj, "news", []) or []
    except Exception:
        news_items = []

    for item in news_items[:8]:
        title = str(item.get("title") or "")
        if title:
            text_pool.append(title.lower())
        related = item.get("relatedTickers") or []
        if isinstance(related, list):
            for tk in related:
                tk_s = str(tk).strip().upper()
                if tk_s and tk_s != str(base_ticker).strip().upper():
                    participant_tickers.add(tk_s)

    merged = " ".join(text_pool)
    for theme, kws in keyword_map.items():
        if any(kw in merged for kw in kws):
            notes.append(f"計画テーマ候補: {theme}")

    for item in news_items[:5]:
        title = str(item.get("title") or "").strip()
        if title:
            notes.append(f"直近開示/報道: {title}")

    if participant_tickers:
        participant_names = []
        for tk in sorted(participant_tickers):
            participant_names.append(SCAN_TARGETS.get(tk, tk))
        notes.append(f"計画参加候補企業: {', '.join(participant_names[:8])}")

    if not notes:
        notes.append("公開情報上、明確な中長期計画テーマは抽出できませんでした。")
    participants = sorted(participant_tickers)[:8]
    return notes[:8], participants


def predict_stock_midlong_range(
    ticker: str,
    week_horizons: Optional[list[int]] = None,
    year_horizons: Optional[list[int]] = None,
) -> Optional[dict]:
    """
    株式の中長期予測レンジ（奇数週・数年先）を返す。
    予測は日次リターンのドリフト＋ボラティリティ帯による統計的レンジ。
    """
    if week_horizons is None:
        week_horizons = [1, 3, 5]
    if year_horizons is None:
        year_horizons = [1, 3]

    week_horizons = sorted({int(w) for w in week_horizons if int(w) > 0 and int(w) % 2 == 1})
    year_horizons = sorted({int(y) for y in year_horizons if int(y) > 0 and int(y) % 2 == 1})
    if not week_horizons and not year_horizons:
        return None

    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period="10y", interval="1d")
    except Exception:
        return None

    if df is None or df.empty or len(df) < 120:
        return None

    close = df["Close"].dropna()
    if close.empty:
        return None

    current = float(close.iloc[-1])
    returns = close.pct_change().dropna()
    if returns.empty:
        return None

    mu_d = float(returns.tail(252).mean()) if len(returns) >= 252 else float(returns.mean())
    sigma_d = float(returns.tail(252).std()) if len(returns) >= 252 else float(returns.std())
    sigma_d = max(sigma_d, 0.0005)

    # 直近モメンタムをドリフトへ薄く反映
    mom_60 = float(close.iloc[-1] / close.iloc[-61] - 1) if len(close) >= 61 else 0.0
    mu_adj = mu_d + (mom_60 / 252.0) * 0.25

    # 成長率（企業情報）で微調整
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}
    rev_growth = info.get("revenueGrowth")
    earn_growth = info.get("earningsGrowth")
    growth_adj = 0.0
    if isinstance(rev_growth, (int, float)):
        growth_adj += max(-0.2, min(0.3, float(rev_growth))) * 0.25
    if isinstance(earn_growth, (int, float)):
        growth_adj += max(-0.3, min(0.4, float(earn_growth))) * 0.25
    mu_adj += growth_adj / 252.0

    points = []

    def _append_point(days: int, label: str, z: float) -> None:
        center = current * np.exp((mu_adj - 0.5 * sigma_d * sigma_d) * days)
        band = max(0.02, z * sigma_d * np.sqrt(days))
        low = center * np.exp(-band)
        high = center * np.exp(band)
        diff_center = (center / current - 1) * 100
        points.append({
            "label": label,
            "days": days,
            "center": round(float(center), 2),
            "low": round(float(low), 2),
            "high": round(float(high), 2),
            "center_diff_pct": round(float(diff_center), 2),
            "band_pct": round(float((high / max(center, 1e-9) - 1) * 100), 2),
        })

    for w in week_horizons:
        days = max(3, w * 5)
        _append_point(days, f"{w}週間", z=1.1)
    for y in year_horizons:
        days = max(50, y * 252)
        _append_point(days, f"{y}年", z=1.5 + min(0.6, y * 0.1))

    plan_notes, participant_tickers = _extract_plan_notes(ticker_obj, ticker)

    # 参加候補企業が上場している場合、その値動きをレンジへ加味
    participant_moms = []
    participant_vols = []
    participants_used = []
    for pt in participant_tickers[:5]:
        try:
            pdf = yf.Ticker(pt).history(period="1y", interval="1d")
            if pdf is None or pdf.empty or len(pdf) < 61:
                continue
            pclose = pdf["Close"].dropna()
            if len(pclose) < 61:
                continue
            prem = pclose.pct_change().dropna()
            if prem.empty:
                continue
            pmom_60 = float(pclose.iloc[-1] / pclose.iloc[-61] - 1)
            pvol_d = float(prem.tail(252).std()) if len(prem) >= 252 else float(prem.std())
            participant_moms.append(pmom_60)
            participant_vols.append(max(pvol_d, 0.0005))
            participants_used.append(pt)
        except Exception:
            continue

    if participant_moms:
        p_mom_avg = float(np.mean(participant_moms))
        # 参加企業の直近60営業日モメンタムを中心ドリフトへ反映（控えめ）
        mu_adj += (p_mom_avg / 252.0) * 0.18
        plan_notes.append(f"参加企業モメンタム反映: {p_mom_avg * 100:+.2f}%（60営業日平均）")
    else:
        p_mom_avg = 0.0

    if participant_vols:
        p_vol_avg = float(np.mean(participant_vols))
        # 参加企業のボラをレンジ幅へ反映（過度に拡大しないよう弱めブレンド）
        sigma_d = sigma_d * 0.85 + p_vol_avg * 0.15
    else:
        p_vol_avg = 0.0
    reasons = [
        f"日次平均リターン(年換算): {mu_d * 252 * 100:+.2f}%",
        f"日次ボラ(年換算): {sigma_d * np.sqrt(252) * 100:.2f}%",
        f"直近60営業日モメンタム: {mom_60 * 100:+.2f}%",
    ]
    if participants_used:
        reasons.append(f"参加企業連動加味: {len(participants_used)}社（{', '.join(participants_used[:3])}）")
    if p_vol_avg > 0:
        reasons.append(f"参加企業ボラ加味(年換算): {p_vol_avg * np.sqrt(252) * 100:.2f}%")

    return {
        "ticker": ticker,
        "current_price": round(current, 2),
        "points": points,
        "plan_notes": plan_notes,
        "reasons": reasons,
        "participants_used": participants_used,
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
