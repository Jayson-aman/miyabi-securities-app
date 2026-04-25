"""
円安/円高ピーク時刻予測モジュール
過去の時間帯パターン + テクニカル指標 + 市場セッション情報を組み合わせ、
円安・円高がピークに達する時刻を推測する
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

# 主要市場セッション（日本時間）
MARKET_SESSIONS = {
    "東京": {"open": 9, "close": 15, "description": "東京市場（9:00〜15:00）"},
    "ロンドン": {"open": 16, "close": 1, "description": "ロンドン市場（16:00〜翌1:00）"},
    "ニューヨーク": {"open": 22, "close": 7, "description": "NY市場（22:00〜翌7:00）"},
}

# 統計的に為替が動きやすい時間帯（日本時間）
HIGH_VOLATILITY_HOURS = {
    9: "東京市場オープン",
    10: "東京仲値（9:55前後）の影響",
    15: "東京市場クローズ",
    16: "ロンドン市場オープン",
    17: "欧州勢参入ラッシュ",
    21: "米国経済指標発表（21:30前後）",
    22: "NY市場オープン",
    0: "ロンドンフィキシング（0:00前後）",
    1: "ロンドン市場クローズ",
}


def predict_yen_peaks(
    df: pd.DataFrame,
    pair_name: str = "USD/JPY",
) -> Optional[dict]:
    """
    円安/円高のピーク時刻を予測する

    Args:
        df: 1分足〜1時間足の価格データ（日時, 始値, 高値, 安値, 終値）
        pair_name: 通貨ペア名

    Returns:
        {
            "yen_weak_peak": {"time": 予測時刻, "price": 予測価格, "confidence": 信頼度, "reasons": [根拠]},
            "yen_strong_peak": {"time": 予測時刻, "price": 予測価格, "confidence": 信頼度, "reasons": [根拠]},
            "current_trend": "円安進行中" / "円高進行中" / "レンジ内",
            "hourly_pattern": {時間: 平均変動率},
            "historical_peaks": {"high_hours": [...], "low_hours": [...]},
            "next_volatile_times": [次の値動きが大きくなりそうな時間帯],
        }
    """
    if df.empty or "終値" not in df.columns or len(df) < 20:
        return None

    result = {}

    # 現在のトレンドを判定
    result["current_trend"] = _detect_current_trend(df)

    # 時間帯別の値動きパターンを分析
    hourly = _analyze_hourly_pattern(df)
    result["hourly_pattern"] = hourly

    # 過去データからピーク時刻の統計を取得
    hist_peaks = _find_historical_peak_hours(df)
    result["historical_peaks"] = hist_peaks

    # テクニカル指標ベースの反転予測
    technical = _predict_reversal(df)

    # 次の値動きが大きくなる時間帯
    result["next_volatile_times"] = _get_next_volatile_times()

    # 円安ピーク予測（= 価格が最も高くなるポイント、USD/JPYなら数値が大きい）
    result["yen_weak_peak"] = _estimate_peak(
        df, hourly, hist_peaks, technical,
        peak_type="high", pair_name=pair_name,
    )

    # 円高ピーク予測（= 価格が最も低くなるポイント、USD/JPYなら数値が小さい）
    result["yen_strong_peak"] = _estimate_peak(
        df, hourly, hist_peaks, technical,
        peak_type="low", pair_name=pair_name,
    )

    return result


def _detect_current_trend(df: pd.DataFrame) -> str:
    """直近データから現在のトレンドを判定"""
    close = df["終値"]
    n = min(20, len(close))
    recent = close.tail(n)

    ma_short = recent.tail(5).mean()
    ma_long = recent.mean()
    current = close.iloc[-1]

    slope = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0] * 100

    if slope > 0.05 and current > ma_short > ma_long:
        return "円安進行中"
    elif slope < -0.05 and current < ma_short < ma_long:
        return "円高進行中"
    else:
        return "レンジ内"


def _analyze_hourly_pattern(df: pd.DataFrame) -> dict:
    """時間帯別の平均変動率を分析"""
    work = df.copy()
    work["hour"] = work["日時"].dt.hour
    work["return"] = work["終値"].pct_change() * 100

    hourly_stats = {}
    grouped = work.groupby("hour")["return"]
    for hour, group in grouped:
        if len(group) > 2:
            hourly_stats[int(hour)] = {
                "avg_return": round(group.mean(), 4),
                "volatility": round(group.std(), 4),
                "count": len(group),
            }

    return hourly_stats


def _find_historical_peak_hours(df: pd.DataFrame) -> dict:
    """過去データから高値・安値がよく出現する時間帯を特定"""
    work = df.copy()
    work["hour"] = work["日時"].dt.hour
    work["date"] = work["日時"].dt.date

    high_hours = []
    low_hours = []

    for date, group in work.groupby("date"):
        if len(group) < 5:
            continue
        high_idx = group["高値"].idxmax()
        low_idx = group["安値"].idxmin()
        high_hours.append(group.loc[high_idx, "日時"].hour)
        low_hours.append(group.loc[low_idx, "日時"].hour)

    high_freq = _count_frequency(high_hours)
    low_freq = _count_frequency(low_hours)

    return {
        "high_hours": high_freq[:5],
        "low_hours": low_freq[:5],
    }


def _count_frequency(hours: list) -> list:
    """時間の出現頻度をカウントしてランキング化"""
    if not hours:
        return []
    freq = {}
    for h in hours:
        freq[h] = freq.get(h, 0) + 1
    total = len(hours)
    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [{"hour": h, "count": c, "pct": round(c / total * 100, 1)} for h, c in ranked]


def _predict_reversal(df: pd.DataFrame) -> dict:
    """テクニカル指標から反転の可能性を予測"""
    close = df["終値"]

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).iloc[-1] if len(close) > 14 else 50

    # ボリンジャーバンド位置
    ma25 = close.rolling(25).mean()
    std25 = close.rolling(25).std()
    if len(close) >= 25 and not np.isnan(std25.iloc[-1]) and std25.iloc[-1] > 0:
        bb_position = (close.iloc[-1] - ma25.iloc[-1]) / (std25.iloc[-1] * 2)
    else:
        bb_position = 0

    # モメンタム
    if len(close) >= 10:
        momentum = (close.iloc[-1] / close.iloc[-10] - 1) * 100
    else:
        momentum = 0

    reversal_signal = "none"
    reversal_strength = 0.0

    if rsi > 70 or bb_position > 0.9:
        reversal_signal = "下降反転"
        reversal_strength = min(1.0, (rsi - 50) / 50 + max(0, bb_position - 0.5))
    elif rsi < 30 or bb_position < -0.9:
        reversal_signal = "上昇反転"
        reversal_strength = min(1.0, (50 - rsi) / 50 + max(0, -bb_position - 0.5))

    return {
        "rsi": round(rsi, 1) if not np.isnan(rsi) else 50,
        "bb_position": round(bb_position, 3),
        "momentum": round(momentum, 4),
        "reversal_signal": reversal_signal,
        "reversal_strength": round(reversal_strength, 3),
    }


def _estimate_peak(
    df: pd.DataFrame,
    hourly: dict,
    hist_peaks: dict,
    technical: dict,
    peak_type: str,
    pair_name: str,
) -> dict:
    """ピーク時刻を総合的に推定する"""
    now = df["日時"].iloc[-1]
    close = df["終値"]
    current_price = close.iloc[-1]
    reasons = []

    # 1) 過去の統計パターンから最も頻度の高い時間帯を取得
    peak_key = "high_hours" if peak_type == "high" else "low_hours"
    freq_hours = hist_peaks.get(peak_key, [])

    candidate_hours = []
    if freq_hours:
        top_hour = freq_hours[0]["hour"]
        candidate_hours.append(top_hour)
        pct = freq_hours[0]["pct"]
        reasons.append(f"過去データで{top_hour}時台にピークが最多（{pct}%）")

    # 2) ボラティリティの高い時間帯
    volatile_hours = []
    for hour, stats in sorted(hourly.items()):
        if stats["volatility"] > 0:
            volatile_hours.append((hour, stats["volatility"]))
    volatile_hours.sort(key=lambda x: x[1], reverse=True)

    if volatile_hours:
        top_volatile_hour = volatile_hours[0][0]
        if top_volatile_hour not in candidate_hours:
            candidate_hours.append(top_volatile_hour)
        reasons.append(f"{top_volatile_hour}時台がボラティリティ最大")

    # 3) 市場セッションの影響
    known_peak_hours = []
    if peak_type == "high":
        known_peak_hours = [10, 16, 22]  # 仲値、ロンドンOP、NYOP
        reasons.append("東京仲値(10時)・ロンドンOP(16時)・NYOP(22時)が注目ポイント")
    else:
        known_peak_hours = [15, 6, 1]
        reasons.append("東京CL(15時)・NY深夜(6時)・ロンドンCL(1時)が注目ポイント")

    for h in known_peak_hours:
        if h not in candidate_hours:
            candidate_hours.append(h)

    # 4) テクニカル指標から反転タイミングを推定
    rsi = technical["rsi"]
    bb_pos = technical["bb_position"]
    reversal = technical["reversal_signal"]

    if peak_type == "high" and reversal == "下降反転":
        reasons.append(f"RSI={rsi}（買われすぎ圏） → まもなく円安ピークの可能性")
        estimated_minutes = max(5, int((100 - rsi) * 3))
    elif peak_type == "low" and reversal == "上昇反転":
        reasons.append(f"RSI={rsi}（売られすぎ圏） → まもなく円高ピークの可能性")
        estimated_minutes = max(5, int(rsi * 3))
    else:
        estimated_minutes = None

    # 5) 予測時刻を決定
    if estimated_minutes and (rsi > 65 or rsi < 35):
        peak_time = now + timedelta(minutes=estimated_minutes)
        confidence = 40 + technical["reversal_strength"] * 30
        reasons.insert(0, f"テクニカル反転シグナル検出 → 約{estimated_minutes}分後と推定")
    elif candidate_hours:
        next_time = _find_next_occurrence(now, candidate_hours[0])
        peak_time = next_time
        confidence = 25 + (freq_hours[0]["pct"] * 0.3 if freq_hours else 0)
        reasons.insert(0, f"過去パターンから{candidate_hours[0]}時台を推定")
    else:
        peak_time = now + timedelta(hours=2)
        confidence = 15
        reasons.append("十分なパターンが見つからないため、大まかな推定です")

    # 予測価格の推定
    recent_range = df["高値"].tail(20).max() - df["安値"].tail(20).min()
    if peak_type == "high":
        est_price = current_price + recent_range * 0.3
    else:
        est_price = current_price - recent_range * 0.3

    confidence = min(75, max(10, confidence))

    label = "円安ピーク（高値）" if peak_type == "high" else "円高ピーク（安値）"

    return {
        "label": label,
        "time": peak_time.strftime("%Y-%m-%d %H:%M"),
        "hour": peak_time.hour,
        "minute": peak_time.minute,
        "estimated_price": round(est_price, 3),
        "confidence": round(confidence, 1),
        "reasons": reasons,
        "candidate_hours": candidate_hours[:5],
    }


def _find_next_occurrence(now: datetime, target_hour: int) -> datetime:
    """現在時刻から次にtarget_hourが来る時刻を返す"""
    candidate = now.replace(hour=target_hour, minute=30, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _get_next_volatile_times() -> list:
    """今後の値動きが大きくなりやすい時間帯を返す"""
    now = datetime.now()
    times = []

    schedule = [
        (9, 55, "東京仲値"),
        (15, 0, "東京市場クローズ"),
        (16, 0, "ロンドン市場オープン"),
        (21, 30, "米国経済指標発表"),
        (22, 0, "NY市場オープン"),
        (0, 0, "ロンドンフィキシング"),
    ]

    for hour, minute, label in schedule:
        t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        times.append({
            "time": t.strftime("%H:%M"),
            "label": label,
            "minutes_until": int((t - now).total_seconds() / 60),
        })

    times.sort(key=lambda x: x["minutes_until"])
    return times
