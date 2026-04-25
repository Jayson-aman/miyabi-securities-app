"""
📐 チャートパターン検出モジュール（買いシグナル特化）

大和証券社員の実践手法に基づく「買いパターン」5種を自動検出:
  1. ダブルボトム (Double Bottom)
  2. 逆三尊 (Inverse Head & Shoulders)
  3. 上昇フラッグ (Bullish Flag)
  4. 上昇トライアングル (Ascending Triangle)
  5. 切り下げレジスタンス転換 (Descending Trendline Breakout / Resistance→Support Flip)

各パターンに対して:
  - 検出の有無
  - 信頼度スコア (0-100)
  - エントリー価格・損切り価格・目標価格
  - 発生時期（足番）
  - 推奨アクション
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf


# ════════════════════════════════════════════════
#  ヘルパー: ピボット（スイング）検出
# ════════════════════════════════════════════════

def _find_pivots(series: pd.Series, window: int = 5, mode: str = "low") -> List[int]:
    """
    ローカル極値（ピボット）のインデックスを返す
    window: 左右それぞれ何本分見るか
    mode: "low" -> 谷、"high" -> 山
    """
    idxs = []
    n = len(series)
    for i in range(window, n - window):
        left = series.iloc[i - window: i]
        right = series.iloc[i + 1: i + 1 + window]
        val = series.iloc[i]
        if mode == "low":
            if val < left.min() and val < right.min():
                idxs.append(i)
        else:
            if val > left.max() and val > right.max():
                idxs.append(i)
    return idxs


def _linear_regression(y: np.ndarray):
    """x を 0..n-1 として y の線形回帰 (slope, intercept) を返す"""
    n = len(y)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept


# ════════════════════════════════════════════════
#  1. ダブルボトム
# ════════════════════════════════════════════════

def detect_double_bottom(df: pd.DataFrame, window: int = 5, tolerance: float = 0.025) -> Optional[dict]:
    """
    ダブルボトム (W底) を検出
      - 2つの谷の価格がほぼ同じ (tolerance以内)
      - 谷と谷の間に山（ネックライン）がある
      - 現在価格がネックラインを上抜けた or 接近中
    """
    if len(df) < window * 4 + 10:
        return None

    closes = df["Close"]
    lows = df["Low"]
    highs = df["High"]

    low_piv = _find_pivots(lows, window=window, mode="low")
    high_piv = _find_pivots(highs, window=window, mode="high")

    if len(low_piv) < 2:
        return None

    # 直近2つの谷を取得
    bottom2_idx = low_piv[-1]
    bottom1_idx = low_piv[-2]

    bottom1 = lows.iloc[bottom1_idx]
    bottom2 = lows.iloc[bottom2_idx]

    # 谷2つがほぼ同値か判定
    diff_ratio = abs(bottom1 - bottom2) / bottom1
    if diff_ratio > tolerance:
        return None

    # 2つの谷の間の山（ネックライン）
    between_highs = [h for h in high_piv if bottom1_idx < h < bottom2_idx]
    if not between_highs:
        return None
    neckline_idx = max(between_highs, key=lambda i: highs.iloc[i])
    neckline = highs.iloc[neckline_idx]

    current_price = closes.iloc[-1]
    bars_from_last_bottom = len(df) - 1 - bottom2_idx

    # 信頼度計算
    confidence = 50
    # 谷2つの近さ
    confidence += (1 - diff_ratio / tolerance) * 20
    # ボトム2が最近か
    if bars_from_last_bottom < 10:
        confidence += 10
    # 深さ（上昇余地）
    depth_ratio = (neckline - bottom1) / bottom1
    if depth_ratio > 0.03:
        confidence += 10
    if depth_ratio > 0.06:
        confidence += 10

    breakout = current_price > neckline
    if breakout:
        confidence += 10
    confidence = min(100, int(confidence))

    # 目標値幅 = ネックライン - ボトム の分を上に加算
    target = neckline + (neckline - bottom1)
    stop_loss = min(bottom1, bottom2) * 0.995

    return {
        "pattern": "ダブルボトム",
        "icon": "🆎",
        "detected": True,
        "confidence": confidence,
        "bottom1_price": round(bottom1, 4),
        "bottom2_price": round(bottom2, 4),
        "neckline": round(neckline, 4),
        "current_price": round(current_price, 4),
        "entry_price": round(neckline, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - neckline) / max(neckline - stop_loss, 1e-9), 2),
        "breakout_confirmed": breakout,
        "bars_ago": bars_from_last_bottom,
        "verdict": "🟢 買い確定" if breakout else "🟡 ネックライン突破待ち",
        "description": "W字型の底値圏反転パターン。ネックライン上抜けで買い。",
    }


# ════════════════════════════════════════════════
#  2. 逆三尊 (Inverse Head & Shoulders)
# ════════════════════════════════════════════════

def detect_inverse_head_shoulders(df: pd.DataFrame, window: int = 5, tolerance: float = 0.04) -> Optional[dict]:
    """
    逆三尊を検出:
      左肩 > 頭 < 右肩
      左肩と右肩の価格がほぼ同じ
      頭が一番深い
    """
    if len(df) < window * 6 + 10:
        return None

    closes = df["Close"]
    lows = df["Low"]
    highs = df["High"]

    low_piv = _find_pivots(lows, window=window, mode="low")
    high_piv = _find_pivots(highs, window=window, mode="high")

    if len(low_piv) < 3:
        return None

    # 直近3つの谷 (左肩, 頭, 右肩)
    l_idx, h_idx, r_idx = low_piv[-3], low_piv[-2], low_piv[-1]
    left_shoulder = lows.iloc[l_idx]
    head = lows.iloc[h_idx]
    right_shoulder = lows.iloc[r_idx]

    # 頭が一番深いか
    if not (head < left_shoulder and head < right_shoulder):
        return None

    # 左右の肩がほぼ同じ高さか
    shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
    if shoulder_diff > tolerance:
        return None

    # 肩の間の山（ネックライン）
    between_1 = [h for h in high_piv if l_idx < h < h_idx]
    between_2 = [h for h in high_piv if h_idx < h < r_idx]
    if not between_1 or not between_2:
        return None
    neck_left = highs.iloc[max(between_1, key=lambda i: highs.iloc[i])]
    neck_right = highs.iloc[max(between_2, key=lambda i: highs.iloc[i])]
    neckline = (neck_left + neck_right) / 2

    current_price = closes.iloc[-1]
    bars_from_rs = len(df) - 1 - r_idx

    confidence = 55
    confidence += (1 - shoulder_diff / tolerance) * 15
    head_depth = (left_shoulder - head) / left_shoulder
    if head_depth > 0.03:
        confidence += 10
    if head_depth > 0.06:
        confidence += 10

    breakout = current_price > neckline
    if breakout:
        confidence += 10
    confidence = min(100, int(confidence))

    # 目標値 = ネックライン + (ネックライン - 頭)
    target = neckline + (neckline - head)
    stop_loss = head * 0.995

    return {
        "pattern": "逆三尊（ヘッド&ショルダーズ底）",
        "icon": "👤",
        "detected": True,
        "confidence": confidence,
        "left_shoulder": round(left_shoulder, 4),
        "head": round(head, 4),
        "right_shoulder": round(right_shoulder, 4),
        "neckline": round(neckline, 4),
        "current_price": round(current_price, 4),
        "entry_price": round(neckline, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - neckline) / max(neckline - stop_loss, 1e-9), 2),
        "breakout_confirmed": breakout,
        "bars_ago": bars_from_rs,
        "verdict": "🟢 買い確定" if breakout else "🟡 ネックライン突破待ち",
        "description": "底値圏の強力な反転パターン。3つの谷で頭が最深、両肩同値、ネック上抜けで買い。",
    }


# ════════════════════════════════════════════════
#  3. 上昇フラッグ (Bullish Flag)
# ════════════════════════════════════════════════

def detect_bullish_flag(df: pd.DataFrame, pole_window: int = 10, flag_window: int = 10) -> Optional[dict]:
    """
    上昇フラッグを検出:
      フラグポール: 急上昇 (直近 pole_window 本で大きく上昇)
      フラグ部分 : 小さく下降 or 横ばい (直近 flag_window 本で下向きチャネル)
    """
    total = pole_window + flag_window
    if len(df) < total + 5:
        return None

    closes = df["Close"]
    highs = df["High"]
    lows = df["Low"]

    # 直近 total 本
    pole_seg = closes.iloc[-total:-flag_window]
    flag_seg = closes.iloc[-flag_window:]

    # フラグポール: 急上昇判定
    pole_gain = (pole_seg.iloc[-1] - pole_seg.iloc[0]) / pole_seg.iloc[0]
    if pole_gain < 0.05:  # 5%以上の急騰
        return None

    # フラグ部分: 下降 or 横ばい
    flag_highs = highs.iloc[-flag_window:].values
    flag_lows = lows.iloc[-flag_window:].values

    upper_slope, upper_int = _linear_regression(flag_highs)
    lower_slope, lower_int = _linear_regression(flag_lows)

    avg_price = np.mean(flag_seg.values)
    upper_slope_pct = upper_slope / avg_price
    lower_slope_pct = lower_slope / avg_price

    # 両方ともマイナス or ゼロ付近（下向きチャネル or 横ばい）
    if upper_slope_pct > 0.002:  # 上昇してたらフラッグではない
        return None
    if lower_slope_pct > 0.002:
        return None

    current_price = closes.iloc[-1]
    flag_top = upper_int + upper_slope * (flag_window - 1)

    # ブレイク判定
    breakout = current_price > flag_top

    # 信頼度
    confidence = 50
    if pole_gain > 0.10:
        confidence += 20
    elif pole_gain > 0.07:
        confidence += 10
    # フラッグ部の収束度
    flag_range = (np.max(flag_highs) - np.min(flag_lows)) / avg_price
    if flag_range < 0.05:
        confidence += 15
    if breakout:
        confidence += 15
    confidence = min(100, int(confidence))

    # 目標 = ポール分の値幅を加算
    pole_height = pole_seg.iloc[-1] - pole_seg.iloc[0]
    target = flag_top + pole_height
    stop_loss = float(np.min(flag_lows)) * 0.995

    return {
        "pattern": "上昇フラッグ",
        "icon": "🚩",
        "detected": True,
        "confidence": confidence,
        "pole_start": round(pole_seg.iloc[0], 4),
        "pole_top": round(pole_seg.iloc[-1], 4),
        "pole_gain_pct": round(pole_gain * 100, 2),
        "flag_top": round(flag_top, 4),
        "flag_bottom": round(float(np.min(flag_lows)), 4),
        "current_price": round(current_price, 4),
        "entry_price": round(flag_top, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - flag_top) / max(flag_top - stop_loss, 1e-9), 2),
        "breakout_confirmed": bool(breakout),
        "verdict": "🟢 買い確定" if breakout else "🟡 フラッグ上限突破待ち",
        "description": "急騰後の小休止（旗竿＋旗型）。上限突破でさらに値幅分の上昇期待。",
    }


# ════════════════════════════════════════════════
#  4. 上昇トライアングル (Ascending Triangle)
# ════════════════════════════════════════════════

def detect_ascending_triangle(df: pd.DataFrame, lookback: int = 30, window: int = 3) -> Optional[dict]:
    """
    上昇トライアングルを検出:
      上辺: 水平な抵抗線（高値が同水準で何度も反発）
      下辺: 右肩上がりの支持線（安値が切り上げ）
    """
    if len(df) < lookback + 5:
        return None

    seg = df.iloc[-lookback:].copy().reset_index(drop=True)
    highs = seg["High"]
    lows = seg["Low"]
    closes = seg["Close"]

    high_piv = _find_pivots(highs, window=window, mode="high")
    low_piv = _find_pivots(lows, window=window, mode="low")

    if len(high_piv) < 2 or len(low_piv) < 2:
        return None

    # 上辺：高値ピボットのばらつき（水平に近いか）
    high_prices = np.array([highs.iloc[i] for i in high_piv])
    high_mean = high_prices.mean()
    high_std_ratio = high_prices.std() / high_mean

    # 水平抵抗と言えるか (ばらつき 1.5% 以内)
    if high_std_ratio > 0.015:
        return None

    resistance = float(high_mean)

    # 下辺：安値ピボットが右肩上がりか
    low_idxs = np.array(low_piv)
    low_prices = np.array([lows.iloc[i] for i in low_piv])
    slope, intercept = _linear_regression(low_prices)
    avg_low = low_prices.mean()
    slope_pct = slope / avg_low

    # 上昇傾斜があるか
    if slope_pct < 0.001:
        return None

    current_price = float(closes.iloc[-1])
    support_at_current = intercept + slope * (len(low_piv) - 1)

    breakout = current_price > resistance

    confidence = 50
    confidence += (1 - min(high_std_ratio / 0.015, 1)) * 15
    if slope_pct > 0.003:
        confidence += 15
    if breakout:
        confidence += 20
    if len(high_piv) >= 3 and len(low_piv) >= 3:
        confidence += 10  # テスト回数多い方が信頼度高い
    confidence = min(100, int(confidence))

    # 目標 = トライアングルの最大値幅を抵抗線に加算
    tri_height = resistance - low_prices.min()
    target = resistance + tri_height
    stop_loss = float(low_prices.min()) * 0.995

    return {
        "pattern": "上昇トライアングル",
        "icon": "📐",
        "detected": True,
        "confidence": confidence,
        "resistance": round(resistance, 4),
        "support_slope_pct_per_bar": round(slope_pct * 100, 3),
        "low_prices": [round(p, 4) for p in low_prices.tolist()],
        "high_touches": len(high_piv),
        "low_touches": len(low_piv),
        "current_price": round(current_price, 4),
        "entry_price": round(resistance, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - resistance) / max(resistance - stop_loss, 1e-9), 2),
        "breakout_confirmed": bool(breakout),
        "verdict": "🟢 買い確定" if breakout else "🟡 水平抵抗線突破待ち",
        "description": "水平抵抗＋切り上げ支持線。上抜けで強い買いシグナル。",
    }


# ════════════════════════════════════════════════
#  5. 切り下げレジスタンス転換 (Descending Trendline Breakout)
# ════════════════════════════════════════════════

def detect_descending_resistance_breakout(df: pd.DataFrame, lookback: int = 40, window: int = 3) -> Optional[dict]:
    """
    下降トレンドラインを上抜けて、その線が支持線に転換するパターン
      - 過去の高値が右肩下がり (切り下げ)
      - 現在の価格がその切り下げラインを上抜け
      - 一度ラインまで戻ってサポートとして機能すればさらに強い
    """
    if len(df) < lookback + 5:
        return None

    seg = df.iloc[-lookback:].copy().reset_index(drop=True)
    highs = seg["High"]
    lows = seg["Low"]
    closes = seg["Close"]

    high_piv = _find_pivots(highs, window=window, mode="high")
    if len(high_piv) < 2:
        return None

    piv_prices = np.array([highs.iloc[i] for i in high_piv])
    piv_idx = np.array(high_piv, dtype=float)

    # 高値ピボットで線形回帰
    if len(piv_prices) < 2:
        return None
    slope, intercept = np.polyfit(piv_idx, piv_prices, 1)
    avg = piv_prices.mean()
    slope_pct = slope / avg

    # 下降していること
    if slope_pct > -0.001:
        return None

    # 最新バー位置でのトレンドライン値
    last_idx = len(seg) - 1
    trendline_now = intercept + slope * last_idx
    current_price = float(closes.iloc[-1])

    # 上抜けしているか
    broke_above = current_price > trendline_now
    if not broke_above:
        return None

    # 上抜け後の戻り（リテスト）でサポート転換しているか
    # 直近10本で一度 trendline に接近（±1%以内）→再上昇
    tested = False
    retest_idx = None
    for i in range(max(last_idx - 10, 0), last_idx):
        tl_i = intercept + slope * i
        if abs(lows.iloc[i] - tl_i) / tl_i < 0.01 and closes.iloc[i] >= tl_i:
            tested = True
            retest_idx = i
            break

    # 安値ピボットから損切り設定
    low_piv = _find_pivots(lows, window=window, mode="low")
    recent_lows = [lows.iloc[i] for i in low_piv[-3:]] if low_piv else [lows.min()]
    stop_loss = float(np.min(recent_lows)) * 0.995

    # 目標: 下落幅の半値戻し or 直近高値
    recent_high = float(highs.iloc[-lookback:].max())
    drop_range = recent_high - float(lows.iloc[-lookback:].min())
    target = current_price + drop_range * 0.5

    confidence = 55
    if slope_pct < -0.003:
        confidence += 10
    if tested:
        confidence += 20
    breakout_strength = (current_price - trendline_now) / trendline_now
    if breakout_strength > 0.02:
        confidence += 10
    if len(high_piv) >= 3:
        confidence += 5
    confidence = min(100, int(confidence))

    return {
        "pattern": "切り下げレジスタンス転換（下降TL上抜け＋サポ転換）",
        "icon": "🔄",
        "detected": True,
        "confidence": confidence,
        "trendline_now": round(trendline_now, 4),
        "slope_pct_per_bar": round(slope_pct * 100, 4),
        "pivot_count": len(high_piv),
        "current_price": round(current_price, 4),
        "retest_confirmed": tested,
        "retest_bars_ago": (last_idx - retest_idx) if retest_idx is not None else None,
        "entry_price": round(trendline_now, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - trendline_now) / max(trendline_now - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢🟢 強い買い（サポ転換確認）" if tested else "🟢 買い（上抜け確認済・リテスト待ち）",
        "description": "下降トレンドラインを上抜け、元の抵抗が支持に転換。最強の順張りエントリー。",
    }


# ════════════════════════════════════════════════
#  【売りパターン】6. ダブルトップ
# ════════════════════════════════════════════════

def detect_double_top(df: pd.DataFrame, window: int = 5, tolerance: float = 0.025) -> Optional[dict]:
    """
    ダブルトップ (M字天井):
      2つの山がほぼ同値
      2山の間の谷がネックライン
      現在価格がネックラインを下抜けで売り確定
    """
    if len(df) < window * 4 + 10:
        return None

    closes = df["Close"]
    lows = df["Low"]
    highs = df["High"]

    high_piv = _find_pivots(highs, window=window, mode="high")
    low_piv = _find_pivots(lows, window=window, mode="low")

    if len(high_piv) < 2:
        return None

    top2_idx = high_piv[-1]
    top1_idx = high_piv[-2]
    top1 = highs.iloc[top1_idx]
    top2 = highs.iloc[top2_idx]

    diff_ratio = abs(top1 - top2) / top1
    if diff_ratio > tolerance:
        return None

    between_lows = [l for l in low_piv if top1_idx < l < top2_idx]
    if not between_lows:
        return None
    neckline_idx = min(between_lows, key=lambda i: lows.iloc[i])
    neckline = lows.iloc[neckline_idx]

    current_price = closes.iloc[-1]
    bars_from_last_top = len(df) - 1 - top2_idx

    confidence = 50
    confidence += (1 - diff_ratio / tolerance) * 20
    if bars_from_last_top < 10:
        confidence += 10
    height_ratio = (top1 - neckline) / neckline
    if height_ratio > 0.03:
        confidence += 10
    if height_ratio > 0.06:
        confidence += 10

    breakdown = current_price < neckline
    if breakdown:
        confidence += 10
    confidence = min(100, int(confidence))

    target = neckline - (top1 - neckline)
    stop_loss = max(top1, top2) * 1.005

    return {
        "pattern": "ダブルトップ",
        "icon": "🅜",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "top1_price": round(top1, 4),
        "top2_price": round(top2, 4),
        "neckline": round(neckline, 4),
        "current_price": round(current_price, 4),
        "entry_price": round(neckline, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((neckline - target) / max(stop_loss - neckline, 1e-9), 2),
        "breakout_confirmed": breakdown,
        "bars_ago": bars_from_last_top,
        "verdict": "🔴 売り確定" if breakdown else "🟡 ネックライン割れ待ち",
        "description": "M字型の天井圏反転パターン。ネックライン下抜けで売り。",
    }


# ════════════════════════════════════════════════
#  【売りパターン】7. 三尊 (Head & Shoulders Top)
# ════════════════════════════════════════════════

def detect_head_shoulders_top(df: pd.DataFrame, window: int = 5, tolerance: float = 0.04) -> Optional[dict]:
    """
    三尊天井:
      左肩 < 頭 > 右肩、左右の肩ほぼ同値、頭が最高
      ネックラインは肩の間の谷
      ネック下抜けで売り
    """
    if len(df) < window * 6 + 10:
        return None

    closes = df["Close"]
    highs = df["High"]
    lows = df["Low"]

    high_piv = _find_pivots(highs, window=window, mode="high")
    low_piv = _find_pivots(lows, window=window, mode="low")

    if len(high_piv) < 3:
        return None

    l_idx, h_idx, r_idx = high_piv[-3], high_piv[-2], high_piv[-1]
    left_shoulder = highs.iloc[l_idx]
    head = highs.iloc[h_idx]
    right_shoulder = highs.iloc[r_idx]

    if not (head > left_shoulder and head > right_shoulder):
        return None

    shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
    if shoulder_diff > tolerance:
        return None

    between_1 = [l for l in low_piv if l_idx < l < h_idx]
    between_2 = [l for l in low_piv if h_idx < l < r_idx]
    if not between_1 or not between_2:
        return None
    neck_left = lows.iloc[min(between_1, key=lambda i: lows.iloc[i])]
    neck_right = lows.iloc[min(between_2, key=lambda i: lows.iloc[i])]
    neckline = (neck_left + neck_right) / 2

    current_price = closes.iloc[-1]
    bars_from_rs = len(df) - 1 - r_idx

    confidence = 55
    confidence += (1 - shoulder_diff / tolerance) * 15
    head_height = (head - left_shoulder) / left_shoulder
    if head_height > 0.03:
        confidence += 10
    if head_height > 0.06:
        confidence += 10

    breakdown = current_price < neckline
    if breakdown:
        confidence += 10
    confidence = min(100, int(confidence))

    target = neckline - (head - neckline)
    stop_loss = head * 1.005

    return {
        "pattern": "三尊天井（ヘッド&ショルダーズ）",
        "icon": "👑",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "left_shoulder": round(left_shoulder, 4),
        "head": round(head, 4),
        "right_shoulder": round(right_shoulder, 4),
        "neckline": round(neckline, 4),
        "current_price": round(current_price, 4),
        "entry_price": round(neckline, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((neckline - target) / max(stop_loss - neckline, 1e-9), 2),
        "breakout_confirmed": breakdown,
        "bars_ago": bars_from_rs,
        "verdict": "🔴 売り確定" if breakdown else "🟡 ネックライン割れ待ち",
        "description": "天井圏の強力な反転パターン。3つの山で頭が最高、両肩同値、ネック下抜けで売り。",
    }


# ════════════════════════════════════════════════
#  【売りパターン】8. 下降フラッグ (Bearish Flag)
# ════════════════════════════════════════════════

def detect_bearish_flag(df: pd.DataFrame, pole_window: int = 10, flag_window: int = 10) -> Optional[dict]:
    """
    下降フラッグ:
      フラグポール: 急落
      フラグ部分 : 小さく上昇 or 横ばい
      フラッグ下限割れで売り
    """
    total = pole_window + flag_window
    if len(df) < total + 5:
        return None

    closes = df["Close"]
    highs = df["High"]
    lows = df["Low"]

    pole_seg = closes.iloc[-total:-flag_window]
    flag_seg = closes.iloc[-flag_window:]

    pole_drop = (pole_seg.iloc[-1] - pole_seg.iloc[0]) / pole_seg.iloc[0]
    if pole_drop > -0.05:  # 5%以上の急落
        return None

    flag_highs = highs.iloc[-flag_window:].values
    flag_lows = lows.iloc[-flag_window:].values

    upper_slope, upper_int = _linear_regression(flag_highs)
    lower_slope, lower_int = _linear_regression(flag_lows)

    avg_price = np.mean(flag_seg.values)
    upper_slope_pct = upper_slope / avg_price
    lower_slope_pct = lower_slope / avg_price

    # フラッグ部は上向き or 横ばい（戻しのリバウンド）
    if upper_slope_pct < -0.002:
        return None
    if lower_slope_pct < -0.002:
        return None

    current_price = closes.iloc[-1]
    flag_bottom = lower_int + lower_slope * (flag_window - 1)

    breakdown = current_price < flag_bottom

    confidence = 50
    if pole_drop < -0.10:
        confidence += 20
    elif pole_drop < -0.07:
        confidence += 10
    flag_range = (np.max(flag_highs) - np.min(flag_lows)) / avg_price
    if flag_range < 0.05:
        confidence += 15
    if breakdown:
        confidence += 15
    confidence = min(100, int(confidence))

    pole_height = pole_seg.iloc[0] - pole_seg.iloc[-1]
    target = flag_bottom - pole_height
    stop_loss = float(np.max(flag_highs)) * 1.005

    return {
        "pattern": "下降フラッグ",
        "icon": "🏴",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "pole_start": round(pole_seg.iloc[0], 4),
        "pole_bottom": round(pole_seg.iloc[-1], 4),
        "pole_drop_pct": round(pole_drop * 100, 2),
        "flag_top": round(float(np.max(flag_highs)), 4),
        "flag_bottom": round(flag_bottom, 4),
        "current_price": round(current_price, 4),
        "entry_price": round(flag_bottom, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((flag_bottom - target) / max(stop_loss - flag_bottom, 1e-9), 2),
        "breakout_confirmed": bool(breakdown),
        "verdict": "🔴 売り確定" if breakdown else "🟡 フラッグ下限割れ待ち",
        "description": "急落後の自律反発（旗竿＋旗型）。下限割れでさらに値幅分の下落期待。",
    }


# ════════════════════════════════════════════════
#  【売りパターン】9. 下降トライアングル (Descending Triangle)
# ════════════════════════════════════════════════

def detect_descending_triangle(df: pd.DataFrame, lookback: int = 30, window: int = 3) -> Optional[dict]:
    """
    下降トライアングル:
      下辺: 水平な支持線（同水準で何度も反発）
      上辺: 右肩下がりの抵抗線（高値切り下げ）
      下辺割れで売り
    """
    if len(df) < lookback + 5:
        return None

    seg = df.iloc[-lookback:].copy().reset_index(drop=True)
    highs = seg["High"]
    lows = seg["Low"]
    closes = seg["Close"]

    high_piv = _find_pivots(highs, window=window, mode="high")
    low_piv = _find_pivots(lows, window=window, mode="low")

    if len(high_piv) < 2 or len(low_piv) < 2:
        return None

    # 下辺：安値ピボットが水平か
    low_prices = np.array([lows.iloc[i] for i in low_piv])
    low_mean = low_prices.mean()
    low_std_ratio = low_prices.std() / low_mean

    if low_std_ratio > 0.015:
        return None

    support = float(low_mean)

    # 上辺：高値ピボットが右肩下がり
    high_prices = np.array([highs.iloc[i] for i in high_piv])
    slope, intercept = np.polyfit(np.arange(len(high_prices)), high_prices, 1)
    avg_high = high_prices.mean()
    slope_pct = slope / avg_high

    if slope_pct > -0.001:
        return None

    current_price = float(closes.iloc[-1])

    breakdown = current_price < support

    confidence = 50
    confidence += (1 - min(low_std_ratio / 0.015, 1)) * 15
    if slope_pct < -0.003:
        confidence += 15
    if breakdown:
        confidence += 20
    if len(high_piv) >= 3 and len(low_piv) >= 3:
        confidence += 10
    confidence = min(100, int(confidence))

    tri_height = high_prices.max() - support
    target = support - tri_height
    stop_loss = float(high_prices.max()) * 1.005

    return {
        "pattern": "下降トライアングル",
        "icon": "📉",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "support": round(support, 4),
        "resistance_slope_pct_per_bar": round(slope_pct * 100, 3),
        "high_touches": len(high_piv),
        "low_touches": len(low_piv),
        "current_price": round(current_price, 4),
        "entry_price": round(support, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((support - target) / max(stop_loss - support, 1e-9), 2),
        "breakout_confirmed": bool(breakdown),
        "verdict": "🔴 売り確定" if breakdown else "🟡 水平支持線割れ待ち",
        "description": "水平支持＋切り下げ抵抗線。下抜けで強い売りシグナル。",
    }


# ════════════════════════════════════════════════
#  【売りパターン】10. 切り上げサポート転換 (Ascending Trendline Breakdown)
# ════════════════════════════════════════════════

def detect_ascending_support_breakdown(df: pd.DataFrame, lookback: int = 40, window: int = 3) -> Optional[dict]:
    """
    上昇トレンドラインを下抜けて、その線が抵抗線に転換するパターン
      - 過去の安値が右肩上がり（切り上げ）
      - 現在の価格がその切り上げラインを下抜け
      - 一度ラインまで戻って抵抗として機能すればさらに強い
    """
    if len(df) < lookback + 5:
        return None

    seg = df.iloc[-lookback:].copy().reset_index(drop=True)
    highs = seg["High"]
    lows = seg["Low"]
    closes = seg["Close"]

    low_piv = _find_pivots(lows, window=window, mode="low")
    if len(low_piv) < 2:
        return None

    piv_prices = np.array([lows.iloc[i] for i in low_piv])
    piv_idx = np.array(low_piv, dtype=float)

    slope, intercept = np.polyfit(piv_idx, piv_prices, 1)
    avg = piv_prices.mean()
    slope_pct = slope / avg

    # 上昇していること
    if slope_pct < 0.001:
        return None

    last_idx = len(seg) - 1
    trendline_now = intercept + slope * last_idx
    current_price = float(closes.iloc[-1])

    broke_below = current_price < trendline_now
    if not broke_below:
        return None

    # 下抜け後の戻り（リテスト）で抵抗転換しているか
    tested = False
    retest_idx = None
    for i in range(max(last_idx - 10, 0), last_idx):
        tl_i = intercept + slope * i
        if abs(highs.iloc[i] - tl_i) / tl_i < 0.01 and closes.iloc[i] <= tl_i:
            tested = True
            retest_idx = i
            break

    high_piv = _find_pivots(highs, window=window, mode="high")
    recent_highs = [highs.iloc[i] for i in high_piv[-3:]] if high_piv else [highs.max()]
    stop_loss = float(np.max(recent_highs)) * 1.005

    # 目標: 上昇幅の半値戻し or 直近安値
    recent_low = float(lows.iloc[-lookback:].min())
    rise_range = float(highs.iloc[-lookback:].max()) - recent_low
    target = current_price - rise_range * 0.5

    confidence = 55
    if slope_pct > 0.003:
        confidence += 10
    if tested:
        confidence += 20
    breakdown_strength = (trendline_now - current_price) / trendline_now
    if breakdown_strength > 0.02:
        confidence += 10
    if len(low_piv) >= 3:
        confidence += 5
    confidence = min(100, int(confidence))

    return {
        "pattern": "切り上げサポート転換（上昇TL下抜け＋レジ転換）",
        "icon": "🔀",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "trendline_now": round(trendline_now, 4),
        "slope_pct_per_bar": round(slope_pct * 100, 4),
        "pivot_count": len(low_piv),
        "current_price": round(current_price, 4),
        "retest_confirmed": tested,
        "retest_bars_ago": (last_idx - retest_idx) if retest_idx is not None else None,
        "entry_price": round(trendline_now, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((trendline_now - target) / max(stop_loss - trendline_now, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（レジ転換確認）" if tested else "🔴 売り（下抜け確認済・リテスト待ち）",
        "description": "上昇トレンドラインを下抜け、元の支持が抵抗に転換。最強の順張り（戻り売り）エントリー。",
    }


# ════════════════════════════════════════════════
#  【買い】11. ゴールデンクロス (Golden Cross)
# ════════════════════════════════════════════════

def detect_golden_cross(df: pd.DataFrame, short: int = 25, long: int = 75,
                        lookback_cross: int = 5) -> Optional[dict]:
    """
    ゴールデンクロス: 短期移動平均線が長期移動平均線を下から上に突き抜ける
      - 直近 lookback_cross 本以内にクロス発生
      - 両MAが上向きならさらに強い
      - 大底圏のGCが最強（長期MAが下向き→上向きに転換中）
    """
    if len(df) < long + lookback_cross + 5:
        return None

    closes = df["Close"]
    short_ma = closes.rolling(short).mean()
    long_ma = closes.rolling(long).mean()

    if short_ma.dropna().empty or long_ma.dropna().empty:
        return None

    # 直近 lookback_cross 本でクロス発生をチェック
    diff = short_ma - long_ma
    cross_idx = None
    for i in range(len(df) - 1, max(len(df) - lookback_cross - 2, long), -1):
        if pd.isna(diff.iloc[i]) or pd.isna(diff.iloc[i - 1]):
            continue
        if diff.iloc[i - 1] <= 0 and diff.iloc[i] > 0:
            cross_idx = i
            break

    if cross_idx is None:
        return None

    current_price = float(closes.iloc[-1])
    cross_price = float(closes.iloc[cross_idx])
    cross_short = float(short_ma.iloc[cross_idx])
    cross_long = float(long_ma.iloc[cross_idx])

    # 両MAの傾き（直近5本）
    short_slope = (short_ma.iloc[-1] - short_ma.iloc[-5]) / short_ma.iloc[-5]
    long_slope = (long_ma.iloc[-1] - long_ma.iloc[-5]) / long_ma.iloc[-5]

    # 信頼度計算
    confidence = 55
    # クロスの鮮度（直近ほど高評価）
    bars_since_cross = len(df) - 1 - cross_idx
    if bars_since_cross == 0:
        confidence += 15  # 本日発生
    elif bars_since_cross <= 2:
        confidence += 10

    # 両MAが上向き
    if short_slope > 0:
        confidence += 10
    if long_slope > 0:
        confidence += 15  # 長期MAも上向きは強い
    else:
        confidence -= 10  # 長期MAが下向きは「だまし」の可能性

    # 価格がMAの上に位置
    if current_price > short_ma.iloc[-1] > long_ma.iloc[-1]:
        confidence += 10

    # 出来高（あれば）が増加
    if "Volume" in df.columns:
        recent_vol = df["Volume"].iloc[-5:].mean()
        past_vol = df["Volume"].iloc[-30:-5].mean()
        if past_vol > 0 and recent_vol > past_vol * 1.2:
            confidence += 5

    confidence = min(100, max(0, int(confidence)))

    # エントリー・損切り・目標
    entry_price = current_price  # クロス確認後の成行
    stop_loss = float(long_ma.iloc[-1]) * 0.99  # 長期MA割れで損切り
    # 目標: 短期MA−長期MAの乖離幅×3
    gap = float(short_ma.iloc[-1] - long_ma.iloc[-1])
    target_price = entry_price + max(gap * 3, entry_price * 0.05)

    return {
        "pattern": f"ゴールデンクロス（{short}MA × {long}MA）",
        "icon": "✨",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "cross_bar_ago": bars_since_cross,
        "cross_price": round(cross_price, 4),
        "cross_short_ma": round(cross_short, 4),
        "cross_long_ma": round(cross_long, 4),
        "short_ma_now": round(float(short_ma.iloc[-1]), 4),
        "long_ma_now": round(float(long_ma.iloc[-1]), 4),
        "short_slope_pct": round(short_slope * 100, 2),
        "long_slope_pct": round(long_slope * 100, 2),
        "current_price": round(current_price, 4),
        "entry_price": round(entry_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((target_price - entry_price) / max(entry_price - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,  # クロスした時点で確定扱い
        "verdict": (
            "🟢🟢 最強の買い（両MA上向き）" if long_slope > 0 and short_slope > 0 else
            "🟢 買い（クロス確定）" if short_slope > 0 else
            "🟡 買い警戒（長期MA下向きでだまし懸念）"
        ),
        "description": f"短期{short}日MAが長期{long}日MAを上抜け。長期MAも上向きなら大相場の入り口。",
    }


# ════════════════════════════════════════════════
#  【売り】12. デッドクロス (Dead Cross)
# ════════════════════════════════════════════════

def detect_dead_cross(df: pd.DataFrame, short: int = 25, long: int = 75,
                      lookback_cross: int = 5) -> Optional[dict]:
    """
    デッドクロス: 短期移動平均線が長期移動平均線を上から下に突き抜ける
    """
    if len(df) < long + lookback_cross + 5:
        return None

    closes = df["Close"]
    short_ma = closes.rolling(short).mean()
    long_ma = closes.rolling(long).mean()

    if short_ma.dropna().empty or long_ma.dropna().empty:
        return None

    diff = short_ma - long_ma
    cross_idx = None
    for i in range(len(df) - 1, max(len(df) - lookback_cross - 2, long), -1):
        if pd.isna(diff.iloc[i]) or pd.isna(diff.iloc[i - 1]):
            continue
        if diff.iloc[i - 1] >= 0 and diff.iloc[i] < 0:
            cross_idx = i
            break

    if cross_idx is None:
        return None

    current_price = float(closes.iloc[-1])
    cross_price = float(closes.iloc[cross_idx])

    short_slope = (short_ma.iloc[-1] - short_ma.iloc[-5]) / short_ma.iloc[-5]
    long_slope = (long_ma.iloc[-1] - long_ma.iloc[-5]) / long_ma.iloc[-5]

    confidence = 55
    bars_since_cross = len(df) - 1 - cross_idx
    if bars_since_cross == 0:
        confidence += 15
    elif bars_since_cross <= 2:
        confidence += 10

    if short_slope < 0:
        confidence += 10
    if long_slope < 0:
        confidence += 15
    else:
        confidence -= 10

    if current_price < short_ma.iloc[-1] < long_ma.iloc[-1]:
        confidence += 10

    confidence = min(100, max(0, int(confidence)))

    entry_price = current_price
    stop_loss = float(long_ma.iloc[-1]) * 1.01
    gap = float(long_ma.iloc[-1] - short_ma.iloc[-1])
    target_price = entry_price - max(gap * 3, entry_price * 0.05)

    return {
        "pattern": f"デッドクロス（{short}MA × {long}MA）",
        "icon": "💀",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "cross_bar_ago": bars_since_cross,
        "cross_price": round(cross_price, 4),
        "short_ma_now": round(float(short_ma.iloc[-1]), 4),
        "long_ma_now": round(float(long_ma.iloc[-1]), 4),
        "short_slope_pct": round(short_slope * 100, 2),
        "long_slope_pct": round(long_slope * 100, 2),
        "current_price": round(current_price, 4),
        "entry_price": round(entry_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((entry_price - target_price) / max(stop_loss - entry_price, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": (
            "🔴🔴 最強の売り（両MA下向き）" if long_slope < 0 and short_slope < 0 else
            "🔴 売り（クロス確定）" if short_slope < 0 else
            "🟡 売り警戒（長期MA上向きでだまし懸念）"
        ),
        "description": f"短期{short}日MAが長期{long}日MAを下抜け。長期MAも下向きなら下落相場入り。",
    }


# ════════════════════════════════════════════════
#  ヘルパー: 水平サポート・レジスタンス候補を抽出
# ════════════════════════════════════════════════

def _find_horizontal_levels(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 0.012,
                            min_touches: int = 2) -> dict:
    """
    ピボットから水平サポート・レジスタンス候補を抽出
    同じ価格帯（tolerance_pct以内）に min_touches 回以上タッチしたラインを返す
    Returns: {"supports": [{"price", "touches", "last_touch_idx"}, ...],
              "resistances": [...]}
    """
    highs = df["High"]
    lows = df["Low"]

    low_piv_idx = _find_pivots(lows, window=window, mode="low")
    high_piv_idx = _find_pivots(highs, window=window, mode="high")

    def _cluster(pivot_idxs: list, series: pd.Series) -> list:
        prices = [(i, float(series.iloc[i])) for i in pivot_idxs]
        clusters = []  # 各: {"price", "touches" (list of (idx,price))}
        for idx, price in prices:
            placed = False
            for c in clusters:
                if abs(c["price"] - price) / max(c["price"], 1e-9) <= tolerance_pct:
                    c["touches"].append((idx, price))
                    c["price"] = float(np.mean([t[1] for t in c["touches"]]))
                    placed = True
                    break
            if not placed:
                clusters.append({"price": price, "touches": [(idx, price)]})
        # フィルタ
        return [
            {
                "price": round(c["price"], 4),
                "touches": len(c["touches"]),
                "last_touch_idx": max(t[0] for t in c["touches"]),
            }
            for c in clusters if len(c["touches"]) >= min_touches
        ]

    return {
        "supports": _cluster(low_piv_idx, lows),
        "resistances": _cluster(high_piv_idx, highs),
    }


# ════════════════════════════════════════════════
#  【買い】13. 水平サポートライン反発 (Support Bounce)
# ════════════════════════════════════════════════

def detect_support_bounce(df: pd.DataFrame, window: int = 5,
                          tolerance_pct: float = 0.012, proximity_pct: float = 0.015) -> Optional[dict]:
    """
    水平サポートラインでの反発（買い）
      - 過去に2回以上タッチした水平ライン
      - 現在価格がそのラインから proximity_pct 以内で上に位置
      - 直近で一度ライン付近まで下落→反発（陽線や下ヒゲ）
    """
    if len(df) < window * 3 + 10:
        return None

    levels = _find_horizontal_levels(df, window=window, tolerance_pct=tolerance_pct, min_touches=2)
    supports = levels["supports"]
    if not supports:
        return None

    current_price = float(df["Close"].iloc[-1])
    lows = df["Low"]

    # 現在価格の下にあるサポートで、過去20本以内にタッチしているものから最適なものを選ぶ
    candidates = []
    for s in supports:
        if s["price"] >= current_price:
            continue
        distance = (current_price - s["price"]) / s["price"]
        if distance > proximity_pct * 3:  # 遠すぎは除外
            continue
        # 直近20本以内のタッチ
        recent_touch = any(lows.iloc[-20:].between(s["price"] * (1 - tolerance_pct), s["price"] * (1 + tolerance_pct)))
        if not recent_touch and s["last_touch_idx"] < len(df) - 20:
            continue
        candidates.append({**s, "distance_pct": distance})

    if not candidates:
        return None

    # 最も多くタッチされているサポートを選択（同着はより近いもの）
    candidates.sort(key=lambda c: (-c["touches"], c["distance_pct"]))
    support = candidates[0]

    # 反発確認: 直近3本のうち下ヒゲが支持線に触れ、終値が支持線より上
    recent = df.iloc[-5:]
    bounced = False
    for _, row in recent.iterrows():
        if (row["Low"] <= support["price"] * (1 + tolerance_pct) and
                row["Close"] > support["price"] and
                row["Close"] > row["Open"] * 0.999):  # 陽線または引け値が高い
            bounced = True
            break

    confidence = 50
    confidence += min(support["touches"] * 8, 25)
    if support["distance_pct"] < proximity_pct:
        confidence += 15
    if bounced:
        confidence += 15
    confidence = min(100, int(confidence))

    # 目標: 直近のレジスタンスまで or 最近30本の高値
    resistances_above = [r for r in levels["resistances"] if r["price"] > current_price]
    if resistances_above:
        resistances_above.sort(key=lambda r: r["price"])
        target_price = resistances_above[0]["price"]
    else:
        target_price = float(df["High"].iloc[-30:].max())

    stop_loss = support["price"] * 0.99

    return {
        "pattern": "水平サポートライン反発",
        "icon": "📍",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "support_price": support["price"],
        "touches": support["touches"],
        "current_price": round(current_price, 4),
        "distance_to_support_pct": round(support["distance_pct"] * 100, 2),
        "bounce_confirmed": bounced,
        "entry_price": round(current_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((target_price - current_price) / max(current_price - stop_loss, 1e-9), 2),
        "breakout_confirmed": bounced,
        "verdict": (
            f"🟢 買い（サポート反発確認・{support['touches']}回タッチ）" if bounced
            else f"🟡 買い警戒（サポート接近中・{support['touches']}回タッチ）"
        ),
        "description": f"過去{support['touches']}回反発した水平サポート({support['price']})。反発確認で押し目買い。",
    }


# ════════════════════════════════════════════════
#  【売り】14. 水平レジスタンスライン反落 (Resistance Rejection)
# ════════════════════════════════════════════════

def detect_resistance_rejection(df: pd.DataFrame, window: int = 5,
                                tolerance_pct: float = 0.012, proximity_pct: float = 0.015) -> Optional[dict]:
    """
    水平レジスタンスラインでの反落（売り）
    """
    if len(df) < window * 3 + 10:
        return None

    levels = _find_horizontal_levels(df, window=window, tolerance_pct=tolerance_pct, min_touches=2)
    resistances = levels["resistances"]
    if not resistances:
        return None

    current_price = float(df["Close"].iloc[-1])
    highs = df["High"]

    candidates = []
    for r in resistances:
        if r["price"] <= current_price:
            continue
        distance = (r["price"] - current_price) / current_price
        if distance > proximity_pct * 3:
            continue
        recent_touch = any(highs.iloc[-20:].between(r["price"] * (1 - tolerance_pct), r["price"] * (1 + tolerance_pct)))
        if not recent_touch and r["last_touch_idx"] < len(df) - 20:
            continue
        candidates.append({**r, "distance_pct": distance})

    if not candidates:
        return None

    candidates.sort(key=lambda c: (-c["touches"], c["distance_pct"]))
    resistance = candidates[0]

    # 反落確認: 直近3本のうち上ヒゲが抵抗線に触れ、終値が抵抗線より下
    recent = df.iloc[-5:]
    rejected = False
    for _, row in recent.iterrows():
        if (row["High"] >= resistance["price"] * (1 - tolerance_pct) and
                row["Close"] < resistance["price"] and
                row["Close"] < row["Open"] * 1.001):  # 陰線 or 引け値が安い
            rejected = True
            break

    confidence = 50
    confidence += min(resistance["touches"] * 8, 25)
    if resistance["distance_pct"] < proximity_pct:
        confidence += 15
    if rejected:
        confidence += 15
    confidence = min(100, int(confidence))

    # 目標: 直近のサポートまで
    supports_below = [s for s in levels["supports"] if s["price"] < current_price]
    if supports_below:
        supports_below.sort(key=lambda s: -s["price"])
        target_price = supports_below[0]["price"]
    else:
        target_price = float(df["Low"].iloc[-30:].min())

    stop_loss = resistance["price"] * 1.01

    return {
        "pattern": "水平レジスタンスライン反落",
        "icon": "📌",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "resistance_price": resistance["price"],
        "touches": resistance["touches"],
        "current_price": round(current_price, 4),
        "distance_to_resistance_pct": round(resistance["distance_pct"] * 100, 2),
        "rejection_confirmed": rejected,
        "entry_price": round(current_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((current_price - target_price) / max(stop_loss - current_price, 1e-9), 2),
        "breakout_confirmed": rejected,
        "verdict": (
            f"🔴 売り（レジスタンス反落確認・{resistance['touches']}回タッチ）" if rejected
            else f"🟡 売り警戒（レジスタンス接近中・{resistance['touches']}回タッチ）"
        ),
        "description": f"過去{resistance['touches']}回反落した水平レジスタンス({resistance['price']})。反落確認で戻り売り。",
    }


# ════════════════════════════════════════════════
#  【買い】15. レジスタンス→サポート転換 (Resistance to Support Flip)
# ════════════════════════════════════════════════

def detect_resistance_to_support_flip(df: pd.DataFrame, window: int = 5,
                                      tolerance_pct: float = 0.012) -> Optional[dict]:
    """
    レジスタンスライン上抜け後、そのラインがサポートとして機能する「役割反転」
      - 過去2回以上タッチしたレジスタンス
      - 現在価格はそのライン上
      - ライン上抜け後、一度ラインまで戻り（リテスト）跳ね返っている
      → 強い買い
    """
    if len(df) < window * 3 + 15:
        return None

    levels = _find_horizontal_levels(df, window=window, tolerance_pct=tolerance_pct, min_touches=2)
    resistances = levels["resistances"]
    if not resistances:
        return None

    current_price = float(df["Close"].iloc[-1])
    closes = df["Close"]
    lows = df["Low"]

    # 現在価格より下にある旧レジスタンス（＝上抜けた）を探す
    flipped = []
    for r in resistances:
        if r["price"] >= current_price:
            continue
        # ブレイク時点を特定
        breakout_idx = None
        for i in range(r["last_touch_idx"] + 1, len(df)):
            if closes.iloc[i] > r["price"] * (1 + tolerance_pct * 0.5):
                breakout_idx = i
                break
        if breakout_idx is None:
            continue

        # ブレイク後にサポートとしての挙動（リテスト後に反発）を探す
        retest_idx = None
        for i in range(breakout_idx + 1, len(df)):
            tl = r["price"]
            # 安値が近接
            if lows.iloc[i] <= tl * (1 + tolerance_pct) and lows.iloc[i] >= tl * (1 - tolerance_pct):
                # その後終値が line より上にある
                if closes.iloc[i] >= tl:
                    retest_idx = i
                    break

        if retest_idx is None:
            continue

        bars_since_flip = len(df) - 1 - retest_idx
        if bars_since_flip > 15:
            continue

        flipped.append({
            **r,
            "breakout_idx": breakout_idx,
            "retest_idx": retest_idx,
            "bars_since_flip": bars_since_flip,
        })

    if not flipped:
        return None

    flipped.sort(key=lambda x: (-x["touches"], x["bars_since_flip"]))
    flip = flipped[0]

    confidence = 60
    confidence += min(flip["touches"] * 6, 20)
    if flip["bars_since_flip"] <= 5:
        confidence += 15
    # 現在価格がラインから乖離している（力強い上昇）
    distance = (current_price - flip["price"]) / flip["price"]
    if distance > 0.015:
        confidence += 10
    confidence = min(100, int(confidence))

    # 目標: 直近60本の高値
    target_price = float(df["High"].iloc[-60:].max())
    if target_price < current_price * 1.02:
        target_price = current_price * 1.06

    stop_loss = flip["price"] * 0.99

    return {
        "pattern": "レジスタンス→サポート転換（役割反転・買い）",
        "icon": "🔼",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "flipped_line_price": flip["price"],
        "original_touches_as_resistance": flip["touches"],
        "bars_since_retest": flip["bars_since_flip"],
        "current_price": round(current_price, 4),
        "entry_price": round(current_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((target_price - current_price) / max(current_price - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🟢🟢 強い買い（元抵抗が支持に転換・{flip['touches']}回の強ライン）",
        "description": f"かつて{flip['touches']}回跳ね返した抵抗({flip['price']})を上抜け、戻り売りを吸収してサポートに転換。最強の順張り買い。",
    }


# ════════════════════════════════════════════════
#  【売り】16. サポート→レジスタンス転換 (Support to Resistance Flip)
# ════════════════════════════════════════════════

def detect_support_to_resistance_flip(df: pd.DataFrame, window: int = 5,
                                      tolerance_pct: float = 0.012) -> Optional[dict]:
    """
    サポートライン下抜け後、そのラインがレジスタンスとして機能する役割反転
    """
    if len(df) < window * 3 + 15:
        return None

    levels = _find_horizontal_levels(df, window=window, tolerance_pct=tolerance_pct, min_touches=2)
    supports = levels["supports"]
    if not supports:
        return None

    current_price = float(df["Close"].iloc[-1])
    closes = df["Close"]
    highs = df["High"]

    flipped = []
    for s in supports:
        if s["price"] <= current_price:
            continue
        # 下抜けイベントを探す
        breakdown_idx = None
        for i in range(s["last_touch_idx"] + 1, len(df)):
            if closes.iloc[i] < s["price"] * (1 - tolerance_pct * 0.5):
                breakdown_idx = i
                break
        if breakdown_idx is None:
            continue

        # 下抜け後、戻しでラインを上値で試して跳ね返されているか
        retest_idx = None
        for i in range(breakdown_idx + 1, len(df)):
            tl = s["price"]
            if highs.iloc[i] <= tl * (1 + tolerance_pct) and highs.iloc[i] >= tl * (1 - tolerance_pct):
                if closes.iloc[i] <= tl:
                    retest_idx = i
                    break

        if retest_idx is None:
            continue

        bars_since_flip = len(df) - 1 - retest_idx
        if bars_since_flip > 15:
            continue

        flipped.append({
            **s,
            "breakdown_idx": breakdown_idx,
            "retest_idx": retest_idx,
            "bars_since_flip": bars_since_flip,
        })

    if not flipped:
        return None

    flipped.sort(key=lambda x: (-x["touches"], x["bars_since_flip"]))
    flip = flipped[0]

    confidence = 60
    confidence += min(flip["touches"] * 6, 20)
    if flip["bars_since_flip"] <= 5:
        confidence += 15
    distance = (flip["price"] - current_price) / current_price
    if distance > 0.015:
        confidence += 10
    confidence = min(100, int(confidence))

    target_price = float(df["Low"].iloc[-60:].min())
    if target_price > current_price * 0.98:
        target_price = current_price * 0.94

    stop_loss = flip["price"] * 1.01

    return {
        "pattern": "サポート→レジスタンス転換（役割反転・売り）",
        "icon": "🔽",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "flipped_line_price": flip["price"],
        "original_touches_as_support": flip["touches"],
        "bars_since_retest": flip["bars_since_flip"],
        "current_price": round(current_price, 4),
        "entry_price": round(current_price, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target_price, 4),
        "risk_reward": round((current_price - target_price) / max(stop_loss - current_price, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🔴🔴 強い売り（元支持が抵抗に転換・{flip['touches']}回の強ライン）",
        "description": f"かつて{flip['touches']}回支えた支持線({flip['price']})を割り込み、戻り買いを吸収して抵抗に転換。最強の戻り売り。",
    }


# ════════════════════════════════════════════════
#  一括検出
# ════════════════════════════════════════════════

# 既存5つ（買い）に direction="BUY" を内部的に付与
def _wrap_buy(fn):
    def wrapped(df):
        r = fn(df)
        if r:
            r.setdefault("direction", "BUY")
        return r
    return wrapped


PATTERN_DETECTORS_BUY = [
    ("double_bottom", _wrap_buy(detect_double_bottom)),
    ("inverse_hs", _wrap_buy(detect_inverse_head_shoulders)),
    ("bull_flag", _wrap_buy(detect_bullish_flag)),
    ("ascending_triangle", _wrap_buy(detect_ascending_triangle)),
    ("descending_resistance_breakout", _wrap_buy(detect_descending_resistance_breakout)),
    ("golden_cross", detect_golden_cross),
    ("support_bounce", detect_support_bounce),
    ("resistance_to_support_flip", detect_resistance_to_support_flip),
]

PATTERN_DETECTORS_SELL = [
    ("double_top", detect_double_top),
    ("hs_top", detect_head_shoulders_top),
    ("bear_flag", detect_bearish_flag),
    ("descending_triangle", detect_descending_triangle),
    ("ascending_support_breakdown", detect_ascending_support_breakdown),
    ("dead_cross", detect_dead_cross),
    ("resistance_rejection", detect_resistance_rejection),
    ("support_to_resistance_flip", detect_support_to_resistance_flip),
]

# 酒田五法・天井圏ローソク足パターン（売り19種）を統合
try:
    from candlestick_patterns import CANDLESTICK_SELL_DETECTORS as _CSD
    PATTERN_DETECTORS_SELL = PATTERN_DETECTORS_SELL + _CSD
except Exception:
    pass

# 酒田五法・底値圏ローソク足パターン（買い10種 = 爆益2 + 益8）を統合
try:
    from candlestick_patterns import CANDLESTICK_BUY_DETECTORS as _CBD
    PATTERN_DETECTORS_BUY = PATTERN_DETECTORS_BUY + _CBD
except Exception:
    pass

PATTERN_DETECTORS = PATTERN_DETECTORS_BUY + PATTERN_DETECTORS_SELL


def scan_all_patterns(df: pd.DataFrame, direction: str = "ALL") -> List[dict]:
    """
    パターンを一括検出。direction: "BUY" | "SELL" | "ALL"
    """
    if direction == "BUY":
        detectors = PATTERN_DETECTORS_BUY
    elif direction == "SELL":
        detectors = PATTERN_DETECTORS_SELL
    else:
        detectors = PATTERN_DETECTORS

    results = []
    for _, detector in detectors:
        try:
            r = detector(df)
            if r and r.get("detected"):
                results.append(r)
        except Exception:
            continue
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return results


def analyze_ticker_patterns(ticker: str, period: str = "6mo", interval: str = "1d",
                            direction: str = "ALL") -> Optional[dict]:
    """
    ティッカー指定でパターン総合分析。direction: "BUY" | "SELL" | "ALL"
    """
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()
        if len(df) < 30:
            return None

        patterns = scan_all_patterns(df, direction=direction)
        current_price = float(df["Close"].iloc[-1])

        buy_patterns = [p for p in patterns if p.get("direction") == "BUY"]
        sell_patterns = [p for p in patterns if p.get("direction") == "SELL"]

        confirmed_buy = sum(1 for p in buy_patterns if p.get("breakout_confirmed"))
        confirmed_sell = sum(1 for p in sell_patterns if p.get("breakout_confirmed"))

        # 総合判定
        if not patterns:
            verdict = "🔍 パターン未検出"
            overall = "NEUTRAL"
        elif confirmed_buy >= 2 and confirmed_sell == 0:
            verdict = f"🟢🟢🟢 超強力な買いシグナル（買い{len(buy_patterns)} / 確定{confirmed_buy}）"
            overall = "STRONG_BUY"
        elif confirmed_sell >= 2 and confirmed_buy == 0:
            verdict = f"🔴🔴🔴 超強力な売りシグナル（売り{len(sell_patterns)} / 確定{confirmed_sell}）"
            overall = "STRONG_SELL"
        elif confirmed_buy >= 1 and confirmed_sell == 0:
            verdict = f"🟢 買いシグナル（買い{len(buy_patterns)} / 確定{confirmed_buy}）"
            overall = "BUY"
        elif confirmed_sell >= 1 and confirmed_buy == 0:
            verdict = f"🔴 売りシグナル（売り{len(sell_patterns)} / 確定{confirmed_sell}）"
            overall = "SELL"
        elif confirmed_buy > 0 and confirmed_sell > 0:
            verdict = f"⚠ 相反シグナル（買い確定{confirmed_buy} / 売り確定{confirmed_sell}）様子見"
            overall = "CONFLICT"
        elif len(buy_patterns) > 0 and len(sell_patterns) == 0:
            verdict = f"🟡 買い警戒（買い{len(buy_patterns)}形成中）"
            overall = "WATCH_BUY"
        elif len(sell_patterns) > 0 and len(buy_patterns) == 0:
            verdict = f"🟡 売り警戒（売り{len(sell_patterns)}形成中）"
            overall = "WATCH_SELL"
        else:
            verdict = f"🟡 パターン形成中（買い{len(buy_patterns)} / 売り{len(sell_patterns)}）"
            overall = "WATCH"

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "direction_filter": direction,
            "current_price": round(current_price, 4),
            "patterns": patterns,
            "buy_patterns": buy_patterns,
            "sell_patterns": sell_patterns,
            "confirmed_buy": confirmed_buy,
            "confirmed_sell": confirmed_sell,
            "total_score": sum(p["confidence"] for p in patterns),
            "verdict": verdict,
            "overall": overall,
            "df": df,
        }
    except Exception:
        return None
