"""
🎴 酒田五法・天井圏 売りシグナル検出モジュール

検出する12パターン（すべて売り）:
  1. 🪢 首吊り線 (Hanging Man)
  2. 🐦 三羽鳥 (Three Black Crows)
  3. 🍡 団子天井 (Dango Top)
  4. 👶 捨て子線 (Abandoned Baby Top)
  5. 🟩 陽の陽はらみ (Yang-Yang Harami at Top)
  6. 🫂 最後の抱き線 (Last Engulfing Top)
  7. ⚔ ツタイの打ち返し (Counter-Attack Line)
  8. 🔝 三手放れ寄せ線 (Three Gap Doji)
  9. ☁ 下げ足の被せ (Dark Cloud Cover / Kabuse)
 10. 🟥 陽の陰はらみ (Yang-Yin Harami at Top)
 11. 🌊 波高い線 (High Wave Candle)
 12. 🪦 陰線五本 (Five Bearish Crows)

各パターンは以下の条件を前提:
  - 直近が「天井圏」である（直近高値付近 or 大きな上昇の後）
  - ローソク足の形状条件を満たす
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# ════════════════════════════════════════════════
#  ヘルパー
# ════════════════════════════════════════════════

def _candle_metrics(row) -> dict:
    """1本のローソク足のメトリクス"""
    o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
    body = abs(c - o)
    total = max(h - l, 1e-9)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return {
        "o": o, "h": h, "l": l, "c": c,
        "body": body, "total": total,
        "upper": upper, "lower": lower,
        "is_bull": c > o,
        "is_bear": c < o,
        "body_ratio": body / total,   # 実体比率
        "upper_ratio": upper / total,
        "lower_ratio": lower / total,
        "mid": (o + c) / 2,
    }


def _is_top_zone(df: pd.DataFrame, lookback: int = 30, near_high_pct: float = 0.02,
                 min_rise_pct: float = 0.05) -> bool:
    """
    直近が天井圏か判定
      - 過去 lookback 本の最高値から near_high_pct 以内に現在値がある
      - または lookback 本で min_rise_pct 以上の上昇
    """
    if len(df) < lookback:
        return False
    seg = df.iloc[-lookback:]
    high = float(seg["High"].max())
    current = float(df["Close"].iloc[-1])
    start = float(seg["Close"].iloc[0])

    near_high = (high - current) / high <= near_high_pct
    big_rally = (current - start) / max(start, 1e-9) >= min_rise_pct
    return near_high or big_rally


def _is_downtrend_zone(df: pd.DataFrame, lookback: int = 20, min_drop_pct: float = 0.03) -> bool:
    """
    下降トレンド中か判定（「待って売れ」の前提）
      - 過去 lookback 本で min_drop_pct 以上の下落
      - または MA が下向き
    """
    if len(df) < lookback + 5:
        return False
    seg = df.iloc[-lookback:]
    start = float(seg["Close"].iloc[0])
    end = float(seg["Close"].iloc[-1])
    drop = (start - end) / max(start, 1e-9)
    if drop >= min_drop_pct:
        return True

    ma = df["Close"].rolling(10).mean()
    if len(ma.dropna()) >= 5:
        ma_slope = (ma.iloc[-1] - ma.iloc[-5]) / ma.iloc[-5]
        if ma_slope < -0.005:
            return True
    return False


# ════════════════════════════════════════════════
#  1. 首吊り線 (Hanging Man)
# ════════════════════════════════════════════════

def detect_hanging_man(df: pd.DataFrame) -> Optional[dict]:
    """
    首吊り線: 天井圏で、小さな実体＋長い下ヒゲ＋ほぼない上ヒゲ
      下ヒゲ >= 実体の2倍
      上ヒゲ < 実体の0.3倍
      終値周辺に実体
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    last = _candle_metrics(df.iloc[-1])
    if last["body"] == 0:
        return None

    if last["lower"] < last["body"] * 2.0:
        return None
    if last["upper"] > last["body"] * 0.3:
        return None
    if last["body_ratio"] > 0.35:  # 実体は全体の35%以内
        return None

    # 直前のローソクが陽線（上昇トレンド中）
    prev_bull_count = sum(1 for i in range(-5, 0) if df["Close"].iloc[i] > df["Open"].iloc[i])

    confidence = 60
    if last["lower"] >= last["body"] * 3:
        confidence += 15
    if prev_bull_count >= 3:
        confidence += 15
    if last["is_bear"]:
        confidence += 10  # 陰線の首吊りはさらに強い
    confidence = min(100, confidence)

    entry = last["c"]
    stop_loss = last["h"] * 1.005
    target = last["c"] - (last["h"] - last["l"]) * 2

    return {
        "pattern": "首吊り線（Hanging Man）",
        "icon": "🪢",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（天井圏の首吊り線）",
        "description": "天井圏で長い下ヒゲ＋小実体。押し目買いが失敗しやすく、反落警戒。",
    }


# ════════════════════════════════════════════════
#  2. 三羽鳥 (Three Black Crows)
# ════════════════════════════════════════════════

def detect_three_black_crows(df: pd.DataFrame) -> Optional[dict]:
    """
    三羽鳥: 3本連続の陰線、それぞれが前日終値近辺から始まり、前日終値を下回って終わる
    """
    if len(df) < 30 or not _is_top_zone(df, lookback=30):
        return None

    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])

    if not (c1["is_bear"] and c2["is_bear"] and c3["is_bear"]):
        return None

    # それぞれ終値が前日終値より低い
    if not (c2["c"] < c1["c"] and c3["c"] < c2["c"]):
        return None

    # それぞれの始値が前日実体内からスタート
    if not (c1["c"] <= c2["o"] <= c1["o"] and c2["c"] <= c3["o"] <= c2["o"]):
        return None

    # 実体がしっかりある（十字線ではない）
    for c in [c1, c2, c3]:
        if c["body_ratio"] < 0.4:
            return None

    confidence = 75
    total_drop = (c1["o"] - c3["c"]) / c1["o"]
    if total_drop > 0.03:
        confidence += 15
    if total_drop > 0.05:
        confidence += 10
    confidence = min(100, confidence)

    entry = c3["c"]
    stop_loss = c1["h"] * 1.005
    target = c3["c"] - (c1["h"] - c3["l"])

    return {
        "pattern": "三羽鳥（Three Black Crows）",
        "icon": "🐦",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（3連続陰線の天井反転）",
        "description": "3本連続陰線で段階的に下げる強力な売りシグナル。天井反転の典型。",
    }


# ════════════════════════════════════════════════
#  3. 団子天井 (Dango Top)
# ════════════════════════════════════════════════

def detect_dango_top(df: pd.DataFrame, bars: int = 5, tolerance_pct: float = 0.012) -> Optional[dict]:
    """
    団子天井: 数本のローソクが高値ほぼ同水準でクラスター、上抜けできずに反落
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    recent = df.iloc[-bars:]
    highs = recent["High"].values
    high_mean = float(np.mean(highs))
    high_std_ratio = float(np.std(highs)) / high_mean

    if high_std_ratio > tolerance_pct:
        return None

    # 直近のローソクが陰線で反落開始
    last = _candle_metrics(df.iloc[-1])
    if not last["is_bear"]:
        return None

    # 反落の幅
    drop = (high_mean - last["c"]) / high_mean
    if drop < 0.005:
        return None

    confidence = 65
    confidence += (1 - high_std_ratio / tolerance_pct) * 15
    if drop > 0.015:
        confidence += 15
    if bars >= 5:
        confidence += 5
    confidence = min(100, int(confidence))

    entry = last["c"]
    stop_loss = high_mean * 1.005
    target = last["c"] - (high_mean - float(recent["Low"].min())) * 1.5

    return {
        "pattern": "団子天井（Dango Top）",
        "icon": "🍡",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "ceiling_price": round(high_mean, 4),
        "bars_in_cluster": bars,
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🔴 売り（団子天井・{bars}本の上値抵抗）",
        "description": f"{bars}本連続で同じ高値に頭を抑えられ、上抜け失敗。典型的な天井圏。",
    }


# ════════════════════════════════════════════════
#  4. 捨て子線 (Abandoned Baby Top)
# ════════════════════════════════════════════════

def detect_abandoned_baby(df: pd.DataFrame, gap_pct: float = 0.003) -> Optional[dict]:
    """
    捨て子線（天井型）: ギャップアップ → 十字線（同時線）→ ギャップダウン
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])

    # c1 は陽線
    if not c1["is_bull"]:
        return None

    # c2 は十字線（実体比率 < 10%）
    if c2["body_ratio"] > 0.1:
        return None

    # ギャップアップ: c2 の安値 > c1 の高値
    if c2["l"] <= c1["h"] * (1 + gap_pct):
        return None

    # ギャップダウン: c3 の高値 < c2 の安値
    if c3["h"] >= c2["l"] * (1 - gap_pct):
        return None

    # c3 は陰線
    if not c3["is_bear"]:
        return None

    confidence = 85  # 非常に珍しい強力パターン
    if c3["body_ratio"] > 0.5:
        confidence += 10
    confidence = min(100, confidence)

    entry = c3["c"]
    stop_loss = c2["h"] * 1.005
    target = c3["c"] - (c2["h"] - c1["o"])

    return {
        "pattern": "捨て子線（Abandoned Baby Top）",
        "icon": "👶",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴🔴 最強の売り（捨て子線・極めて珍しい天井反転）",
        "description": "ギャップアップ→十字線→ギャップダウンの3本構成。最強の天井反転パターン。",
    }


# ════════════════════════════════════════════════
#  5. 陽の陽はらみ (Yang-Yang Harami at Top)
# ════════════════════════════════════════════════

def detect_yang_yang_harami(df: pd.DataFrame) -> Optional[dict]:
    """
    陽の陽はらみ: 大きな陽線の実体内に、小さな陽線が完全に含まれる（天井圏）
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not (c1["is_bull"] and c2["is_bull"]):
        return None
    # c1は大陽線
    if c1["body_ratio"] < 0.6:
        return None
    # c2は小陽線
    if c2["body"] > c1["body"] * 0.5:
        return None
    # c2の実体がc1の実体内
    if not (c1["o"] < c2["l"] and c2["h"] < c1["c"]):
        return None

    confidence = 65
    if c2["body"] < c1["body"] * 0.3:
        confidence += 15
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c1["h"] * 1.005
    target = c2["c"] - c1["body"] * 1.5

    return {
        "pattern": "陽の陽はらみ（Yang-Yang Harami at Top）",
        "icon": "🟩",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（天井圏の陽の陽はらみ・上昇鈍化）",
        "description": "大陽線の翌日に小陽線で収まる。買い勢い失速のサインで天井圏では反落警戒。",
    }


# ════════════════════════════════════════════════
#  6. 最後の抱き線 (Last Engulfing Top)
# ════════════════════════════════════════════════

def detect_last_engulfing_top(df: pd.DataFrame) -> Optional[dict]:
    """
    最後の抱き線: 天井圏で陰線の翌日に大陽線が包み込むが、上昇が続かない（騙し）
    条件: c1陰線、c2が陽線でc1を包み込む、しかしc3(現在)が陰線でc2の安値を割る
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])

    if not c1["is_bear"]:
        return None
    if not c2["is_bull"]:
        return None
    if not (c2["o"] < c1["c"] and c2["c"] > c1["o"]):  # 抱き
        return None
    if not c3["is_bear"]:
        return None
    if c3["c"] >= c2["o"]:
        return None

    confidence = 75
    if c3["body_ratio"] > 0.5:
        confidence += 15
    confidence = min(100, confidence)

    entry = c3["c"]
    stop_loss = c2["h"] * 1.005
    target = c3["c"] - c2["body"] * 1.5

    return {
        "pattern": "最後の抱き線（Last Engulfing Top）",
        "icon": "🫂",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（最後の抱き線・騙しの大陽線）",
        "description": "抱き陽線で買いを誘うが続かず、翌日陰線で下げる。天井からの売りが勝った証拠。",
    }


# ════════════════════════════════════════════════
#  7. ツタイの打ち返し (Counter-Attack Line)
# ════════════════════════════════════════════════

def detect_counter_attack_line(df: pd.DataFrame, tolerance_pct: float = 0.005) -> Optional[dict]:
    """
    ツタイの打ち返し（天井型）:
      前日陽線 → 当日ギャップアップして始まるが、長大陰線で前日終値付近まで売り戻される
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not c1["is_bull"]:
        return None
    if not c2["is_bear"]:
        return None
    # ギャップアップ始まり
    if c2["o"] <= c1["c"] * 1.002:
        return None
    # 終値が前日終値付近
    if abs(c2["c"] - c1["c"]) / c1["c"] > tolerance_pct * 3:
        return None
    # 長大陰線
    if c2["body_ratio"] < 0.6:
        return None

    confidence = 75
    if c2["body"] > c1["body"] * 1.2:
        confidence += 10
    if c2["body_ratio"] > 0.8:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c2["h"] * 1.005
    target = c2["c"] - c2["body"] * 2

    return {
        "pattern": "ツタイの打ち返し（Counter-Attack）",
        "icon": "⚔",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（ツタイ打ち返し・売り方の反撃）",
        "description": "ギャップアップで始まった天井圏の買いを、長大陰線で一気に打ち返す売り優勢の証拠。",
    }


# ════════════════════════════════════════════════
#  8. 三手放れ寄せ線 (Three Gap Doji)
# ════════════════════════════════════════════════

def detect_three_gap_doji(df: pd.DataFrame, gap_pct: float = 0.002) -> Optional[dict]:
    """
    三手放れ寄せ線: ギャップアップを伴う陽線が3本連続した後、寄せ線（十字）が現れる
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-4])
    c2 = _candle_metrics(df.iloc[-3])
    c3 = _candle_metrics(df.iloc[-2])
    c4 = _candle_metrics(df.iloc[-1])

    # c1,c2,c3 は陽線
    if not (c1["is_bull"] and c2["is_bull"] and c3["is_bull"]):
        return None
    # ギャップアップ
    if not (c2["l"] > c1["h"] * (1 + gap_pct) and c3["l"] > c2["h"] * (1 + gap_pct)):
        return None
    # c4 は寄せ線（十字線）
    if c4["body_ratio"] > 0.12:
        return None

    confidence = 88  # 超レアな極天井シグナル
    if c4["upper_ratio"] > 0.3 and c4["lower_ratio"] > 0.3:
        confidence += 7
    confidence = min(100, confidence)

    entry = c4["c"]
    stop_loss = c4["h"] * 1.005
    # 3つのギャップ分を目標に
    total_gap = (c2["l"] - c1["h"]) + (c3["l"] - c2["h"])
    target = c4["c"] - total_gap * 3

    return {
        "pattern": "三手放れ寄せ線（Three Gap Doji）",
        "icon": "🔝",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c4["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴🔴 最強の売り（三手放れ寄せ線・極天井反転）",
        "description": "ギャップ3連＋寄せ線。買われ過ぎで市場が迷い始め、急反落しやすい極天井。",
    }


# ════════════════════════════════════════════════
#  9. 下げ足の被せ (Dark Cloud Cover / Kabuse)
# ════════════════════════════════════════════════

def detect_dark_cloud_cover(df: pd.DataFrame) -> Optional[dict]:
    """
    下げ足の被せ（被せ線）:
      前日大陽線 → 当日は前日高値を上回って始まるが、陰線で終わり前日実体の中値より下で引ける
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not c1["is_bull"]:
        return None
    if c1["body_ratio"] < 0.5:
        return None
    if not c2["is_bear"]:
        return None
    # 寄付きが前日高値より上
    if c2["o"] <= c1["h"]:
        return None
    # 終値が前日実体の中値より下
    c1_mid = c1["mid"]
    if c2["c"] >= c1_mid:
        return None
    # 前日実体の下限（始値）より下には行っていない（完全な包み足ではなく「被せ」）
    if c2["c"] < c1["o"]:
        return None

    confidence = 75
    penetration = (c1["c"] - c2["c"]) / c1["body"]
    if penetration > 0.7:
        confidence += 15
    if c2["body_ratio"] > 0.5:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c2["h"] * 1.005
    target = c2["c"] - c1["body"] * 1.5

    return {
        "pattern": "下げ足の被せ（Dark Cloud Cover）",
        "icon": "☁",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（被せ線・買い失敗）",
        "description": "前日大陽線の勢いを止める被せの陰線。買い失速の典型的天井サイン。",
    }


# ════════════════════════════════════════════════
#  10. 陽の陰はらみ (Yang-Yin Harami at Top)
# ════════════════════════════════════════════════

def detect_yang_yin_harami(df: pd.DataFrame) -> Optional[dict]:
    """
    陽の陰はらみ: 大陽線の実体内に、小さな陰線が完全に含まれる
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not c1["is_bull"]:
        return None
    if not c2["is_bear"]:
        return None
    if c1["body_ratio"] < 0.6:
        return None
    if c2["body"] > c1["body"] * 0.5:
        return None
    # c2 の実体全体が c1 の実体内
    if not (c1["o"] < c2["c"] and c2["o"] < c1["c"]):
        return None

    confidence = 72
    if c2["body"] < c1["body"] * 0.3:
        confidence += 15
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c1["h"] * 1.005
    target = c2["c"] - c1["body"] * 1.5

    return {
        "pattern": "陽の陰はらみ（Yang-Yin Harami at Top）",
        "icon": "🟥",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（陽の陰はらみ・天井反転サイン）",
        "description": "大陽線の翌日に小陰線で収まる。買い勢い失速・反転初動の可能性。",
    }


# ════════════════════════════════════════════════
#  11. 波高い線 (High Wave Candle)
# ════════════════════════════════════════════════

def detect_high_wave(df: pd.DataFrame) -> Optional[dict]:
    """
    波高い線: 上下ヒゲが非常に長く、実体が小さい十字的ローソク（迷い）
    """
    if len(df) < 30 or not _is_top_zone(df):
        return None

    last = _candle_metrics(df.iloc[-1])
    if last["total"] == 0:
        return None

    # 上下ヒゲが実体の3倍以上
    if last["upper"] < last["body"] * 2.5:
        return None
    if last["lower"] < last["body"] * 2.5:
        return None
    # 実体は全体の20%以下
    if last["body_ratio"] > 0.2:
        return None

    # 直近5本のボラティリティが高まっている
    recent_range = (df["High"].iloc[-5:].max() - df["Low"].iloc[-5:].min()) / df["Close"].iloc[-5]
    past_range = (df["High"].iloc[-20:-5].max() - df["Low"].iloc[-20:-5].min()) / df["Close"].iloc[-20]

    confidence = 60
    if recent_range > past_range * 1.3:
        confidence += 20
    if last["body_ratio"] < 0.1:
        confidence += 10
    if last["upper"] > last["lower"] * 1.2:
        confidence += 10  # 上ヒゲが特に長い＝上値重い
    confidence = min(100, confidence)

    entry = last["c"]
    stop_loss = last["h"] * 1.005
    target = last["c"] - last["total"] * 2

    return {
        "pattern": "波高い線（High Wave Candle）",
        "icon": "🌊",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（天井圏の波高い線・相場の迷い）",
        "description": "上下ヒゲが長く実体が小さい「迷い線」。天井圏では反落しやすい。",
    }


# ════════════════════════════════════════════════
#  12. 陰線五本 (Five Bearish Crows)
# ════════════════════════════════════════════════

def detect_five_bears(df: pd.DataFrame) -> Optional[dict]:
    """
    陰線五本: 5本連続の陰線（強力な下落基調への転換）
    """
    if len(df) < 30 or not _is_top_zone(df, lookback=40):
        return None

    last5 = df.iloc[-5:]
    metrics = [_candle_metrics(row) for _, row in last5.iterrows()]

    if not all(m["is_bear"] for m in metrics):
        return None

    # 5本の実体が平均して実体比率0.35以上
    body_ratios = [m["body_ratio"] for m in metrics]
    if np.mean(body_ratios) < 0.35:
        return None

    total_drop = (metrics[0]["o"] - metrics[-1]["c"]) / metrics[0]["o"]

    confidence = 78
    if total_drop > 0.04:
        confidence += 12
    if total_drop > 0.07:
        confidence += 10
    confidence = min(100, confidence)

    entry = metrics[-1]["c"]
    stop_loss = max(m["h"] for m in metrics) * 1.005
    target = metrics[-1]["c"] - (metrics[0]["o"] - metrics[-1]["c"])

    return {
        "pattern": "陰線五本（Five Bearish Crows）",
        "icon": "🪦",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "total_drop_pct": round(total_drop * 100, 2),
        "current_price": round(metrics[-1]["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴🔴 最強の売り（陰線五本連続）",
        "description": "5本連続陰線。強烈な売り圧力で下降トレンド確立。戻り売り優勢。",
    }


# ════════════════════════════════════════════════
#  「待って売れ」下降継続パターン（ダウントレンド前提）
#  ─────────────────────────────────────────
#  下降トレンド中に現れる「戻り売り」シグナル群
# ════════════════════════════════════════════════

# 13. 下放れ二本黒 (Gap Down with Two Black Candles)
def detect_gapdown_two_blacks(df: pd.DataFrame, gap_pct: float = 0.003) -> Optional[dict]:
    """
    下放れ二本黒: 下降トレンド中にギャップダウンして始まり、2本連続陰線が続く
    """
    if len(df) < 30 or not _is_downtrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-3])  # 前日
    c1 = _candle_metrics(df.iloc[-2])  # 下放れ1本目
    c2 = _candle_metrics(df.iloc[-1])  # 下放れ2本目

    # c1 は c0 からギャップダウン
    if c1["h"] >= c0["l"] * (1 - gap_pct):
        return None
    # c1,c2 ともに陰線
    if not (c1["is_bear"] and c2["is_bear"]):
        return None
    # c2 は c1 と重なって下方向に進行
    if c2["c"] >= c1["c"]:
        return None
    if c1["body_ratio"] < 0.4 or c2["body_ratio"] < 0.4:
        return None

    confidence = 75
    gap_size = (c0["l"] - c1["h"]) / c0["l"]
    if gap_size > 0.01:
        confidence += 10
    total_drop = (c0["c"] - c2["c"]) / c0["c"]
    if total_drop > 0.03:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c1["h"] * 1.005
    target = c2["c"] - (c0["c"] - c2["c"]) * 1.5

    return {
        "pattern": "下放れ二本黒（Gap Down Two Blacks）",
        "icon": "⬇",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（下放れ＋二本陰線・下降継続）",
        "description": "下降途中でギャップダウンして二本の陰線。戻りは売りで継続下落。",
    }


# 14. 下げ三法 (Falling Three Methods)
def detect_falling_three_methods(df: pd.DataFrame) -> Optional[dict]:
    """
    下げ三法: 大陰線 → 小陽線×3本（前陰線の実体内に収まる）→ 大陰線で突き抜け
    """
    if len(df) < 30 or not _is_downtrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-5])
    c1 = _candle_metrics(df.iloc[-4])
    c2 = _candle_metrics(df.iloc[-3])
    c3 = _candle_metrics(df.iloc[-2])
    c4 = _candle_metrics(df.iloc[-1])

    # c0 大陰線
    if not c0["is_bear"] or c0["body_ratio"] < 0.55:
        return None
    # c1,c2,c3 は小陽線（または陰線でも小さい）、すべて c0 の実体内
    for cs in [c1, c2, c3]:
        if cs["body"] > c0["body"] * 0.7:
            return None
        if cs["h"] > c0["o"]:  # 高値が c0 の始値（上端）を超えたら失敗
            return None
        if cs["l"] < c0["c"]:  # 安値が c0 の終値（下端）を割ったら失敗
            return None
    # c4 は大陰線で c0 の安値を下回る
    if not c4["is_bear"] or c4["body_ratio"] < 0.5:
        return None
    if c4["c"] >= c0["l"]:
        return None

    confidence = 85
    if c4["c"] < c0["l"] * 0.995:
        confidence += 10
    confidence = min(100, confidence)

    entry = c4["c"]
    stop_loss = c0["o"] * 1.005
    target = c4["c"] - c0["body"] * 2

    return {
        "pattern": "下げ三法（Falling Three Methods）",
        "icon": "📉",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c4["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴🔴 最強の売り（下げ三法・下降継続確定）",
        "description": "大陰線→小休止3本→大陰線で突き抜け。下降相場の王道継続シグナル。",
    }


# 15. バケ線 (Bake-sen / Ghost Line)
def detect_bake_line(df: pd.DataFrame) -> Optional[dict]:
    """
    バケ線: 小幅な陽線・陰線が続いた後、突如現れる非常に大きな陰線（化けた線）
    """
    if len(df) < 30 or not _is_downtrend_zone(df, lookback=15, min_drop_pct=0.02):
        return None

    last = _candle_metrics(df.iloc[-1])
    if not last["is_bear"]:
        return None
    if last["body_ratio"] < 0.7:
        return None

    # 過去5本の平均実体サイズと比較
    prev5 = df.iloc[-6:-1]
    prev_bodies = [abs(row["Close"] - row["Open"]) for _, row in prev5.iterrows()]
    prev_body_avg = float(np.mean(prev_bodies))
    if prev_body_avg <= 0:
        return None

    # バケ線: 直近5本平均の2.5倍以上の実体
    if last["body"] < prev_body_avg * 2.5:
        return None

    confidence = 78
    multiplier = last["body"] / prev_body_avg
    if multiplier > 4:
        confidence += 15
    elif multiplier > 3:
        confidence += 10
    confidence = min(100, confidence)

    entry = last["c"]
    stop_loss = last["h"] * 1.005
    target = last["c"] - last["body"] * 2

    return {
        "pattern": "バケ線（Bake-sen）",
        "icon": "👻",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "body_multiplier": round(multiplier, 2),
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴🔴 強い売り（バケ線・突然の大陰線）",
        "description": "小動き続きで油断した所に突然の巨大陰線。戻り売りで追随。",
    }


# 16. 下値遊び (Low-level Consolidation)
def detect_low_consolidation(df: pd.DataFrame, bars: int = 5,
                             range_pct: float = 0.025) -> Optional[dict]:
    """
    下値遊び: 下降後の安値圏で数本の小動きがある（休憩後にさらに下）
      - 直前に明確な下落
      - 直近 bars 本が狭いレンジ
      - 戻りは弱い
    """
    if len(df) < 30 or not _is_downtrend_zone(df, lookback=30, min_drop_pct=0.04):
        return None

    recent = df.iloc[-bars:]
    r_high = float(recent["High"].max())
    r_low = float(recent["Low"].min())
    range_ratio = (r_high - r_low) / max(r_low, 1e-9)

    if range_ratio > range_pct:
        return None

    # 直近 bars 本がすべて小さな実体
    for _, row in recent.iterrows():
        m = _candle_metrics(row)
        if m["body_ratio"] > 0.55:
            return None

    # 直近 bars 本の前が陰線的下落
    prev_seg = df.iloc[-(bars + 10):-bars]
    prev_drop = (float(prev_seg["Close"].iloc[0]) - float(prev_seg["Close"].iloc[-1])) / float(prev_seg["Close"].iloc[0])
    if prev_drop < 0.03:
        return None

    confidence = 68
    if range_ratio < range_pct * 0.6:
        confidence += 12
    if prev_drop > 0.06:
        confidence += 10
    confidence = min(100, confidence)

    current_price = float(df["Close"].iloc[-1])
    entry = current_price
    stop_loss = r_high * 1.005
    target = r_low - (r_high - r_low) * 2

    return {
        "pattern": "下値遊び（Low Consolidation）",
        "icon": "😴",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "consolidation_bars": bars,
        "range_pct": round(range_ratio * 100, 2),
        "current_price": round(current_price, 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🔴 売り（下値遊び・{bars}本の休憩後にさらに下落）",
        "description": "下落後の安値圏で持ち合い。エネルギーを貯めて次の下落を待つ局面。",
    }


# 17. 下放れタスキ (Gap Down Tasuki)
def detect_gapdown_tasuki(df: pd.DataFrame, gap_pct: float = 0.003) -> Optional[dict]:
    """
    下放れタスキ:
      下降トレンド中に陰線からギャップダウンで始まる陰線
      その翌日にギャップを埋めない陽線（戻りが弱く、ギャップは残る → 下降継続）
    """
    if len(df) < 30 or not _is_downtrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-3])  # 陰線
    c1 = _candle_metrics(df.iloc[-2])  # 下放れ陰線
    c2 = _candle_metrics(df.iloc[-1])  # 陽線（タスキ返し）

    if not c0["is_bear"]:
        return None
    if not c1["is_bear"]:
        return None
    # c1 は c0 からギャップダウン
    if c1["h"] >= c0["l"] * (1 - gap_pct):
        return None
    # c2 は陽線
    if not c2["is_bull"]:
        return None
    # c2 の始値は c1 の実体内
    if not (c1["c"] <= c2["o"] <= c1["o"]):
        return None
    # c2 の終値は c1 の始値より上だが、c0 の安値（ギャップ）は埋めていない
    if not (c2["c"] > c1["o"]):
        return None
    if c2["c"] >= c0["l"]:
        return None

    confidence = 75
    gap_size = (c0["l"] - c1["h"]) / c0["l"]
    if gap_size > 0.01:
        confidence += 10
    if c2["body_ratio"] < 0.5:
        confidence += 10  # 戻り陽線の勢いが弱い方が継続確度高い
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c0["l"] * 1.005  # ギャップ上限を損切
    target = c2["c"] - (c0["c"] - c1["c"]) * 2

    return {
        "pattern": "下放れタスキ（Gap Down Tasuki）",
        "icon": "🎀",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（下放れタスキ・戻りは弱い、ギャップ残存）",
        "description": "下放れ陰線の後の陽線でもギャップを埋めない。戻りは売りが継続。",
    }


# 18. 下放れ並び赤 (Gap Down Side-by-Side White)
def detect_gapdown_side_by_side_whites(df: pd.DataFrame, gap_pct: float = 0.003,
                                       tolerance_pct: float = 0.01) -> Optional[dict]:
    """
    下放れ並び赤:
      下降トレンド中に下放れし、その後2本の陽線が並ぶ（ただし下ギャップは残る）
      → 買い戻しの動きが出ても戻りきらず、さらに下落する継続サイン
    """
    if len(df) < 30 or not _is_downtrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-3])
    c1 = _candle_metrics(df.iloc[-2])  # 下放れ後の陽線1
    c2 = _candle_metrics(df.iloc[-1])  # 陽線2（並び）

    # c0 からギャップダウン
    if c1["h"] >= c0["l"] * (1 - gap_pct):
        return None
    # c1,c2 ともに陽線
    if not (c1["is_bull"] and c2["is_bull"]):
        return None
    # c1,c2 の始値・終値が似たレベル（並び）
    if abs(c1["o"] - c2["o"]) / max(c1["o"], 1e-9) > tolerance_pct:
        return None
    if abs(c1["c"] - c2["c"]) / max(c1["c"], 1e-9) > tolerance_pct:
        return None
    # ギャップは埋まっていない
    if max(c1["h"], c2["h"]) >= c0["l"]:
        return None

    confidence = 72
    gap_size = (c0["l"] - max(c1["h"], c2["h"])) / c0["l"]
    if gap_size > 0.01:
        confidence += 12
    if c1["body_ratio"] < 0.5 and c2["body_ratio"] < 0.5:
        confidence += 10  # 弱い陽線が並ぶほど強い継続
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c0["l"] * 1.005
    target = c2["c"] - (c0["o"] - c2["c"]) * 1.5

    return {
        "pattern": "下放れ並び赤（Gap Down Side-by-Side Whites）",
        "icon": "🔻",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（下放れ並び赤・ギャップ未埋・下降継続）",
        "description": "下放れ後に陽線が2本並ぶも、ギャップは埋まらず下降継続。戻り売りの好機。",
    }


# 19. 入り首 (In-neck Line)
def detect_in_neck_line(df: pd.DataFrame, penetration_max: float = 0.10) -> Optional[dict]:
    """
    入り首:
      下降トレンド中の陰線の翌日、安値でギャップダウンして始まり、
      終値が前日終値をわずかに上回って引ける（戻りが極めて弱い）
      → 戻り売りの好機（継続の売りシグナル）
    """
    if len(df) < 30 or not _is_downtrend_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    # c1 は陰線
    if not c1["is_bear"]:
        return None
    # c2 は陽線
    if not c2["is_bull"]:
        return None
    # c2 は c1 の安値を下回って始まる（ギャップダウン）
    if c2["o"] >= c1["l"]:
        return None
    # c2 の終値が c1 の終値付近（終値を少しだけ上回る、10%以内）
    penetration = (c2["c"] - c1["c"]) / c1["body"] if c1["body"] > 0 else 0
    if penetration < 0 or penetration > penetration_max:
        return None

    confidence = 70
    if penetration < 0.05:
        confidence += 15  # ほとんど戻っていないほど強い
    if c2["body_ratio"] < 0.5:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c1["o"] * 1.005  # 前日始値を超えたら損切
    target = c2["c"] - c1["body"] * 2

    return {
        "pattern": "入り首（In-neck Line）",
        "icon": "🗡",
        "direction": "SELL",
        "detected": True,
        "confidence": confidence,
        "penetration_pct": round(penetration * 100, 2),
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((entry - target) / max(stop_loss - entry, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🔴 売り（入り首・戻りは極めて弱い）",
        "description": "下降途中、前日安値を割って始まり、わずかに戻しただけで引ける弱い陽線。戻り売り継続。",
    }


# ════════════════════════════════════════════════
#  🟢 買いパターン（底値圏・上昇継続）
# ════════════════════════════════════════════════
#
#  【爆益】逆三尊（chart_patterns.py 実装済） / 上げ三法 / 被せの上抜き
#  【益】  陽の二つ星 / 陰線連続後の大陽線 / つばめ返し / 陽のたすき線
#          陰の両つつみ / 切り込み線 / 二本たくり線 / 上振れたすき
# ════════════════════════════════════════════════


def _is_bottom_zone(df: pd.DataFrame, lookback: int = 30, near_low_pct: float = 0.03,
                    min_drop_pct: float = 0.04) -> bool:
    """底値圏か判定（直近安値付近 or 大きな下落の後）"""
    if len(df) < lookback:
        return False
    seg = df.iloc[-lookback:]
    low = float(seg["Low"].min())
    current = float(df["Close"].iloc[-1])
    start = float(seg["Close"].iloc[0])

    near_low = (current - low) / max(low, 1e-9) <= near_low_pct
    big_drop = (start - current) / max(start, 1e-9) >= min_drop_pct
    return near_low or big_drop


def _is_uptrend_zone(df: pd.DataFrame, lookback: int = 20, min_rise_pct: float = 0.03) -> bool:
    """上昇トレンド中か判定"""
    if len(df) < lookback + 5:
        return False
    seg = df.iloc[-lookback:]
    start = float(seg["Close"].iloc[0])
    end = float(seg["Close"].iloc[-1])
    rise = (end - start) / max(start, 1e-9)
    if rise >= min_rise_pct:
        return True
    ma = df["Close"].rolling(10).mean()
    if len(ma.dropna()) >= 5:
        ma_slope = (ma.iloc[-1] - ma.iloc[-5]) / ma.iloc[-5]
        if ma_slope > 0.005:
            return True
    return False


# ─── 【爆益】1. 上げ三法 (Rising Three Methods) ────
def detect_rising_three_methods(df: pd.DataFrame) -> Optional[dict]:
    """大陽線 → 小陰線×3本（前陽線の実体内）→ 大陽線で突き抜け"""
    if len(df) < 30 or not _is_uptrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-5])
    c1 = _candle_metrics(df.iloc[-4])
    c2 = _candle_metrics(df.iloc[-3])
    c3 = _candle_metrics(df.iloc[-2])
    c4 = _candle_metrics(df.iloc[-1])

    if not c0["is_bull"] or c0["body_ratio"] < 0.55:
        return None
    for cs in [c1, c2, c3]:
        if cs["body"] > c0["body"] * 0.7:
            return None
        if cs["l"] < c0["o"]:
            return None
        if cs["h"] > c0["c"]:
            return None
    if not c4["is_bull"] or c4["body_ratio"] < 0.5:
        return None
    if c4["c"] <= c0["h"]:
        return None

    confidence = 85
    if c4["c"] > c0["h"] * 1.005:
        confidence += 10
    confidence = min(100, confidence)

    entry = c4["c"]
    stop_loss = c0["o"] * 0.995
    target = c4["c"] + c0["body"] * 2

    return {
        "pattern": "上げ三法（Rising Three Methods）",
        "icon": "📈",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c4["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢🟢🟢 爆益（上げ三法・上昇継続確定）",
        "description": "大陽線→小休止3本→大陽線で突き抜け。上昇相場の王道継続シグナル。",
    }


# ─── 【爆益】2. 被せの上抜き (Dark Cloud Cover Upper Break) ────
def detect_kabuse_upper_break(df: pd.DataFrame) -> Optional[dict]:
    """被せ線（陽→陰で上半分をくい込む）を後日の陽線が高値を抜く（ダマシ反転＝強い買い）"""
    if len(df) < 30:
        return None

    # 過去 2〜5 本前に被せ線が成立しているか
    for idx in range(-5, -2):
        if abs(idx) + 1 > len(df):
            continue
        a = _candle_metrics(df.iloc[idx - 1])
        b = _candle_metrics(df.iloc[idx])
        if not a["is_bull"] or a["body_ratio"] < 0.5:
            continue
        if not b["is_bear"]:
            continue
        if b["o"] <= a["h"]:  # 被せは前日高値を超えて始まる
            continue
        mid_a = (a["o"] + a["c"]) / 2
        if b["c"] > mid_a or b["c"] < a["o"]:  # 前日実体の半分以上を食い込むが下回らない
            continue

        kabuse_high = max(a["h"], b["h"])

        # 現在のローソク足が被せ線の高値を上抜きした陽線か
        last = _candle_metrics(df.iloc[-1])
        if not last["is_bull"] or last["body_ratio"] < 0.4:
            continue
        if last["c"] <= kabuse_high:
            continue

        confidence = 80
        break_margin = (last["c"] - kabuse_high) / kabuse_high
        if break_margin > 0.01:
            confidence += 15
        confidence = min(100, confidence)

        entry = last["c"]
        stop_loss = b["l"] * 0.995
        target = last["c"] + (last["c"] - stop_loss) * 2.5

        return {
            "pattern": "被せの上抜き（Kabuse Upper Break）",
            "icon": "🚀",
            "direction": "BUY",
            "detected": True,
            "confidence": confidence,
            "current_price": round(last["c"], 4),
            "entry_price": round(entry, 4),
            "stop_loss": round(stop_loss, 4),
            "target_price": round(target, 4),
            "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
            "breakout_confirmed": True,
            "verdict": "🟢🟢🟢 爆益（被せのダマシ → 強い反転上昇）",
            "description": "一度被せ線で売りサインが出た後に高値を上抜き。騙された空売りの買い戻しで急騰しやすい。",
        }
    return None


# ─── 【益】1. 陽の二つ星 (Two Bullish Stars) ────
def detect_two_bullish_stars(df: pd.DataFrame) -> Optional[dict]:
    """底値圏での小さな陽線2本（小さな星型）→ 下げ止まり〜反転"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    prev = _candle_metrics(df.iloc[-3])
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not prev["is_bear"] or prev["body_ratio"] < 0.5:
        return None
    if not (c1["is_bull"] and c2["is_bull"]):
        return None
    # 実体が小さい星型
    if c1["body"] > prev["body"] * 0.4 or c2["body"] > prev["body"] * 0.4:
        return None
    # 下ヒゲがある（支持されている）
    if c1["lower"] < c1["body"] * 0.8 or c2["lower"] < c2["body"] * 0.8:
        return None

    confidence = 70
    if c2["c"] > c1["c"]:
        confidence += 10
    if c2["l"] >= c1["l"]:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = min(c1["l"], c2["l"]) * 0.995
    target = c2["c"] + (c2["c"] - stop_loss) * 2

    return {
        "pattern": "陽の二つ星（Two Bullish Stars）",
        "icon": "✨",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（陽の二つ星・底固め）",
        "description": "底値圏で小陽線が2本並び下ヒゲで支持される。反転上昇の初動。",
    }


# ─── 【益】2. 陰線連続後の大陽線 (Big Bullish after Consecutive Bears) ────
def detect_big_bull_after_bears(df: pd.DataFrame, min_bears: int = 3) -> Optional[dict]:
    """3本以上の連続陰線の後に出る大陽線（強い反発）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    last = _candle_metrics(df.iloc[-1])
    if not last["is_bull"] or last["body_ratio"] < 0.65:
        return None

    # 直前が連続陰線
    consec_bears = 0
    total_bear_body = 0.0
    for i in range(2, 2 + min_bears + 3):
        if i > len(df):
            break
        c = _candle_metrics(df.iloc[-i])
        if c["is_bear"]:
            consec_bears += 1
            total_bear_body += c["body"]
        else:
            break
    if consec_bears < min_bears:
        return None
    # 大陽線が直前の陰線群の実体の半分以上を取り返す
    avg_bear = total_bear_body / consec_bears
    if last["body"] < avg_bear * 1.2:
        return None

    confidence = 74
    if consec_bears >= 4:
        confidence += 10
    if last["body"] > avg_bear * 2:
        confidence += 10
    confidence = min(100, confidence)

    entry = last["c"]
    stop_loss = last["l"] * 0.995
    target = last["c"] + last["body"] * 2

    return {
        "pattern": f"陰線{consec_bears}本後の大陽線（Bull after Bears）",
        "icon": "🔥",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "consec_bears": consec_bears,
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🟢 益（陰線{consec_bears}本後の大陽線・強反発）",
        "description": f"陰線{consec_bears}本連続の売り圧力を一気に飲み込む大陽線。売り方踏み上げで急騰。",
    }


# ─── 【益】3. つばめ返し (Tsubame-gaeshi / Swallow Return) ────
def detect_tsubame_gaeshi(df: pd.DataFrame) -> Optional[dict]:
    """底値圏で下ヒゲから急反発する長陽線（前日陰線の始値を上抜く）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not c1["is_bear"] or c1["body_ratio"] < 0.4:
        return None
    if not c2["is_bull"] or c2["body_ratio"] < 0.55:
        return None
    # c2 は c1 の終値付近か下で始まる
    if c2["o"] > c1["c"] * 1.005:
        return None
    # c2 は c1 の始値を上抜ける（=前日陰線を完全否定）
    if c2["c"] <= c1["o"]:
        return None
    # 下ヒゲが存在
    if c2["lower"] < c2["body"] * 0.3:
        return None

    confidence = 77
    takeback = (c2["c"] - c1["o"]) / c1["body"] if c1["body"] > 0 else 0
    if takeback > 0.3:
        confidence += 10
    if c2["lower"] > c2["body"] * 0.6:
        confidence += 8
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c2["l"] * 0.995
    target = c2["c"] + (c2["c"] - stop_loss) * 2.5

    return {
        "pattern": "つばめ返し（Tsubame-gaeshi）",
        "icon": "🦅",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（つばめ返し・急反発）",
        "description": "前日陰線の始値を一気に上抜く長陽線。つばめが翻るように急反発する強買いサイン。",
    }


# ─── 【益】4. 陽のたすき線 (Yang no Tasuki) ────
def detect_yang_tasuki(df: pd.DataFrame, gap_pct: float = 0.002) -> Optional[dict]:
    """上昇中に陽線からギャップアップした陽線 → 軽い押し陰線がギャップを埋めない継続サイン"""
    if len(df) < 30 or not _is_uptrend_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-3])
    c1 = _candle_metrics(df.iloc[-2])  # ギャップアップ陽線
    c2 = _candle_metrics(df.iloc[-1])  # 押しの陰線

    if not c0["is_bull"]:
        return None
    if not c1["is_bull"]:
        return None
    # c1 は c0 からギャップアップ
    if c1["l"] <= c0["h"] * (1 + gap_pct):
        return None
    # c2 は陰線で c1 の実体内で始まり、c1 の始値を下回らず終わる
    if not c2["is_bear"]:
        return None
    if not (c1["o"] <= c2["o"] <= c1["c"]):
        return None
    # ギャップを埋めない
    if c2["c"] <= c0["h"]:
        return None

    confidence = 74
    gap_size = (c1["l"] - c0["h"]) / c0["h"]
    if gap_size > 0.01:
        confidence += 10
    if c2["body_ratio"] < 0.5:
        confidence += 8
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c0["h"] * 0.995
    target = c2["c"] + (c1["c"] - c0["c"]) * 2

    return {
        "pattern": "陽のたすき線（Yang Tasuki）",
        "icon": "🎏",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（陽のたすき・上昇継続）",
        "description": "上昇中のギャップアップ後の小陰線もギャップを埋めず。押し目買いの継続シグナル。",
    }


# ─── 【益】5. 陰の両つつみ (Double Engulfing In) ────
def detect_yin_ryo_tsutsumi(df: pd.DataFrame) -> Optional[dict]:
    """底値圏で陰線→それを完全に包む大陽線（包み線の強化版、直前の陰線も飲み込む）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    c0 = _candle_metrics(df.iloc[-3])
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    # c0,c1 両方陰線
    if not (c0["is_bear"] and c1["is_bear"]):
        return None
    # c2 は大陽線で c0 の高値と c1 の安値を両方飲む
    if not c2["is_bull"] or c2["body_ratio"] < 0.6:
        return None
    combined_high = max(c0["h"], c1["h"])
    combined_low = min(c0["l"], c1["l"])
    if c2["o"] > combined_low:
        return None
    if c2["c"] < combined_high:
        return None

    confidence = 82
    size_ratio = c2["body"] / max(c0["body"] + c1["body"], 1e-9)
    if size_ratio > 1.3:
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c2["l"] * 0.995
    target = c2["c"] + c2["body"] * 2

    return {
        "pattern": "陰の両つつみ（Double Engulfing）",
        "icon": "🫶",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（陰の両つつみ・2本同時飲込の強い買い）",
        "description": "陰線2本を1本の大陽線が丸ごと包む。強力な買い転換サイン。",
    }


# ─── 【益】6. 切り込み線 (Kirikomi-sen / Piercing Line) ────
def detect_kirikomi_sen(df: pd.DataFrame) -> Optional[dict]:
    """陰線の翌日にギャップダウンで始まり、陰線実体の半分以上を取り返す陽線"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    if not c1["is_bear"] or c1["body_ratio"] < 0.45:
        return None
    if not c2["is_bull"] or c2["body_ratio"] < 0.45:
        return None
    # c2 は c1 の安値を下回って始まる
    if c2["o"] >= c1["l"]:
        return None
    # c2 終値は c1 実体の半分以上取り返すが、c1 の始値は超えない
    mid_c1 = (c1["o"] + c1["c"]) / 2
    if c2["c"] < mid_c1:
        return None
    if c2["c"] >= c1["o"]:
        return None  # 完全包みなら別パターン

    confidence = 76
    penetration = (c2["c"] - c1["c"]) / c1["body"] if c1["body"] > 0 else 0
    if penetration > 0.7:
        confidence += 12
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c2["l"] * 0.995
    target = c2["c"] + c1["body"] * 2

    return {
        "pattern": "切り込み線（Piercing Line）",
        "icon": "⚔️",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "penetration_pct": round(penetration * 100, 1),
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（切り込み線・強い反転シグナル）",
        "description": "前日陰線を半分以上取り返す陽線。売り方の降参を示す反転シグナル。",
    }


# ─── 【益】7. 二本たくり線 (Nihon Takuri-sen) ────
def detect_nihon_takuri(df: pd.DataFrame) -> Optional[dict]:
    """底値圏で長い下ヒゲを持つ小実体ローソク足が2本連続（売りが吸収された反発の兆し）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None

    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])

    # 両方とも実体が小さく、下ヒゲが実体の2倍以上、上ヒゲが小さい
    for cs in [c1, c2]:
        if cs["body_ratio"] > 0.35:
            return None
        if cs["lower"] < cs["body"] * 2:
            return None
        if cs["upper"] > cs["body"] * 1.2:
            return None

    # 安値が同水準または2本目の方が切り上げ
    if c2["l"] < c1["l"] * 0.995:
        return None

    confidence = 72
    if c2["is_bull"]:
        confidence += 10
    if c2["l"] > c1["l"]:
        confidence += 8
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = min(c1["l"], c2["l"]) * 0.995
    target = c2["c"] + (c2["c"] - stop_loss) * 2.5

    return {
        "pattern": "二本たくり線（Nihon Takuri）",
        "icon": "🎣",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（二本たくり線・底値吸収）",
        "description": "長い下ヒゲの小実体が2本連続。売り圧力が下で吸収され反発に繋がる底打ちサイン。",
    }


# ─── 【益】8. 上振れたすき (Upper Gap Tasuki) ────
def detect_upper_gap_tasuki(df: pd.DataFrame, gap_pct: float = 0.003) -> Optional[dict]:
    """底値圏でギャップアップした陽線の後に、小陰線がギャップを埋めない反転継続サイン"""
    if len(df) < 30:
        return None
    # 底値圏から立ち上がり始めている状態も対象
    if not (_is_bottom_zone(df, lookback=30, min_drop_pct=0.03) or _is_uptrend_zone(df, lookback=10, min_rise_pct=0.015)):
        return None

    c0 = _candle_metrics(df.iloc[-3])
    c1 = _candle_metrics(df.iloc[-2])  # ギャップアップ陽線
    c2 = _candle_metrics(df.iloc[-1])  # 小陰線（たすき）

    if not c1["is_bull"] or c1["body_ratio"] < 0.45:
        return None
    # c1 は c0 からギャップアップ
    if c1["l"] <= c0["h"] * (1 + gap_pct):
        return None
    if not c2["is_bear"]:
        return None
    # c2 の始値が c1 の実体内、終値は c1 の始値以上（ギャップ維持）
    if not (c1["o"] <= c2["o"] <= c1["c"]):
        return None
    if c2["c"] < c1["o"]:
        return None
    if c2["c"] <= c0["h"]:  # ギャップを埋めない
        return None

    confidence = 73
    gap_size = (c1["l"] - c0["h"]) / c0["h"]
    if gap_size > 0.01:
        confidence += 10
    if c2["body_ratio"] < 0.45:
        confidence += 8
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c0["h"] * 0.995
    target = c2["c"] + (c1["c"] - c0["c"]) * 2

    return {
        "pattern": "上振れたすき（Upper Gap Tasuki）",
        "icon": "🎋",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟢 益（上振れたすき・ギャップ維持で上昇継続）",
        "description": "ギャップアップ陽線の後の小陰線もギャップを埋めず、上昇トレンドの強さを示す。",
    }


# ════════════════════════════════════════════════
#  🟡 微益（小さな買い利益）10パターン
# ════════════════════════════════════════════════


# ─── 微益 1. はらみ線 (Bullish Harami) ────
def detect_bullish_harami(df: pd.DataFrame) -> Optional[dict]:
    """大陰線の実体内に収まる小陽線（売り圧力の減退）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])
    if not c1["is_bear"] or c1["body_ratio"] < 0.55:
        return None
    if not c2["is_bull"]:
        return None
    if c2["body"] >= c1["body"] * 0.6:
        return None
    if not (c1["c"] <= c2["o"] and c2["c"] <= c1["o"]):
        return None
    if c2["l"] < c1["c"]:
        return None

    confidence = 62
    if c2["body"] < c1["body"] * 0.3:
        confidence += 10
    confidence = min(100, confidence)
    entry = c2["c"]
    stop_loss = c1["l"] * 0.995
    target = c2["c"] + c1["body"] * 1.2
    return {
        "pattern": "はらみ線（Bullish Harami）",
        "icon": "🤰",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": False,
        "verdict": "🟡 微益（はらみ線・下落鈍化）",
        "description": "大陰線の実体内に収まる小陽線。売り圧力の減退を示す初期反転サイン。",
    }


# ─── 微益 2. 上昇窓 (Rising Window / Gap Up) ────
def detect_rising_window(df: pd.DataFrame, gap_pct: float = 0.005) -> Optional[dict]:
    """前日高値を上回って始まる陽線（ギャップアップ）"""
    if len(df) < 30:
        return None
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])
    if c2["l"] <= c1["h"] * (1 + gap_pct):
        return None
    if not c2["is_bull"]:
        return None

    confidence = 60
    gap_size = (c2["l"] - c1["h"]) / c1["h"]
    if gap_size > 0.01:
        confidence += 12
    if c2["body_ratio"] > 0.55:
        confidence += 8
    if _is_uptrend_zone(df, lookback=10, min_rise_pct=0.02):
        confidence += 10
    confidence = min(100, confidence)

    entry = c2["c"]
    stop_loss = c1["h"] * 0.995
    target = c2["c"] + (c2["c"] - stop_loss) * 1.5
    return {
        "pattern": "上昇窓（Rising Window）",
        "icon": "🪟",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "gap_pct": round(gap_size * 100, 2),
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（上昇窓・ギャップで買い意欲）",
        "description": "前日高値を上放れてスタートする陽線。買い意欲の強さを示す継続サイン。",
    }


# ─── 微益 3. だきの一本立ち (Bullish Engulfing) ────
def detect_bullish_engulfing(df: pd.DataFrame) -> Optional[dict]:
    """陰線を完全に飲み込む陽線（1本で包み反転）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])
    if not c1["is_bear"] or c1["body_ratio"] < 0.4:
        return None
    if not c2["is_bull"] or c2["body_ratio"] < 0.55:
        return None
    if c2["o"] > c1["c"]:
        return None
    if c2["c"] < c1["o"]:
        return None
    if c2["body"] < c1["body"] * 1.1:
        return None

    confidence = 70
    ratio = c2["body"] / max(c1["body"], 1e-9)
    if ratio > 1.5:
        confidence += 12
    confidence = min(100, confidence)
    entry = c2["c"]
    stop_loss = c2["l"] * 0.995
    target = c2["c"] + c2["body"] * 1.8
    return {
        "pattern": "だきの一本立ち（Bullish Engulfing）",
        "icon": "🤝",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "engulf_ratio": round(ratio, 2),
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（だきの一本立ち・包み陽線）",
        "description": "前日陰線を1本で完全に飲み込む陽線。買い方優勢への転換サイン。",
    }


# ─── 微益 4. 赤三兵（案星）(Three White Soldiers) ────
def detect_three_white_soldiers(df: pd.DataFrame) -> Optional[dict]:
    """連続する3本の陽線で終値が切り上がり続ける"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None
    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])
    for cs in [c1, c2, c3]:
        if not cs["is_bull"] or cs["body_ratio"] < 0.5:
            return None
    if not (c1["c"] < c2["c"] < c3["c"]):
        return None
    if not (c1["o"] < c2["o"] < c3["o"]):
        return None
    for cs in [c1, c2, c3]:
        if cs["upper"] > cs["body"] * 0.6:
            return None

    confidence = 72
    total_gain = (c3["c"] - c1["o"]) / c1["o"]
    if total_gain > 0.04:
        confidence += 12
    confidence = min(100, confidence)
    entry = c3["c"]
    stop_loss = c1["l"] * 0.995
    target = c3["c"] + (c3["c"] - c1["o"])
    return {
        "pattern": "赤三兵（Three White Soldiers）",
        "icon": "🎖",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "total_gain_pct": round(total_gain * 100, 2),
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（赤三兵・三本陽線の押し上げ）",
        "description": "連続3本の陽線で着実に切り上がる押し上げ。順調な買い上がり。",
    }


# ─── 微益 5. 三積み上げ (Three Stack Up) ────
def detect_three_stack_up(df: pd.DataFrame) -> Optional[dict]:
    """3本連続で陽線かつ高値・安値ともに切り上げ"""
    if len(df) < 30:
        return None
    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])
    if not (c1["is_bull"] and c2["is_bull"] and c3["is_bull"]):
        return None
    if not (c1["h"] < c2["h"] < c3["h"]):
        return None
    if not (c1["l"] < c2["l"] < c3["l"]):
        return None
    if not (c1["c"] < c2["c"] < c3["c"]):
        return None

    confidence = 63
    gain = (c3["c"] - c1["o"]) / c1["o"]
    if gain > 0.03:
        confidence += 10
    if _is_uptrend_zone(df, lookback=10, min_rise_pct=0.015):
        confidence += 8
    confidence = min(100, confidence)
    entry = c3["c"]
    stop_loss = c1["l"] * 0.995
    target = c3["c"] + (c3["c"] - c1["l"])
    return {
        "pattern": "三積み上げ（Three Stack Up）",
        "icon": "🧱",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（三積み上げ・高安両切り上げ）",
        "description": "3本連続陽線で高値・安値ともに切り上げ。安定した上昇トレンド継続。",
    }


# ─── 微益 6. リバーサルハイ (Reversal High) ────
def detect_reversal_high(df: pd.DataFrame, lookback: int = 20) -> Optional[dict]:
    """前日までの高値を上抜く陽線（ブレイクアウト）"""
    if len(df) < lookback + 5:
        return None
    prior_high = float(df["High"].iloc[-(lookback + 1):-1].max())
    last = _candle_metrics(df.iloc[-1])
    if not last["is_bull"] or last["body_ratio"] < 0.55:
        return None
    if last["c"] <= prior_high:
        return None

    confidence = 68
    break_margin = (last["c"] - prior_high) / prior_high
    if break_margin > 0.01:
        confidence += 12
    # 出来高の観点も盛り込みたいが yfinance volume は 'Volume' 列
    try:
        vol_recent = float(df["Volume"].iloc[-1])
        vol_avg = float(df["Volume"].iloc[-lookback:].mean())
        if vol_recent > vol_avg * 1.3:
            confidence += 10
    except Exception:
        pass
    confidence = min(100, confidence)

    entry = last["c"]
    stop_loss = prior_high * 0.99
    target = last["c"] + (last["c"] - stop_loss) * 2
    return {
        "pattern": "リバーサルハイ（Reversal High）",
        "icon": "🔝",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "prior_high": round(prior_high, 4),
        "break_pct": round(break_margin * 100, 2),
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": f"🟡 微益（リバーサルハイ・{lookback}本高値ブレイク）",
        "description": f"過去{lookback}本の高値を上抜く陽線。新高値ブレイクアウト。",
    }


# ─── 微益 7. スラストアップ (Thrust Up) ────
def detect_thrust_up(df: pd.DataFrame) -> Optional[dict]:
    """前日陽線の終値と高値の中間以上で引ける陽線（弱い継続）"""
    if len(df) < 30:
        return None
    c1 = _candle_metrics(df.iloc[-2])
    c2 = _candle_metrics(df.iloc[-1])
    if not c1["is_bull"]:
        return None
    if not c2["is_bull"] or c2["body_ratio"] < 0.4:
        return None
    thrust_line = (c1["c"] + c1["h"]) / 2
    if c2["c"] < thrust_line:
        return None
    if c2["c"] >= c1["h"] * 1.02:  # 大きすぎるならむしろ別パターン
        return None

    confidence = 60
    if c2["c"] > c1["h"]:
        confidence += 12
    confidence = min(100, confidence)
    entry = c2["c"]
    stop_loss = c1["c"] * 0.995
    target = c2["c"] + (c2["c"] - stop_loss) * 1.5
    return {
        "pattern": "スラストアップ（Thrust Up）",
        "icon": "🏹",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c2["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（スラストアップ・緩やかな突き上げ）",
        "description": "前日陽線の高値付近で引ける陽線。買い継続の緩やかなサイン。",
    }


# ─── 微益 8. うえピンバー (Upper Pinbar) ────
def detect_upper_pinbar(df: pd.DataFrame) -> Optional[dict]:
    """長い下ヒゲ＋小実体が上寄りにあるローソク（ハンマーの買いバージョン）"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None
    last = _candle_metrics(df.iloc[-1])
    if last["body_ratio"] > 0.33:
        return None
    if last["lower"] < last["body"] * 2:
        return None
    if last["upper"] > last["body"] * 0.5:
        return None

    confidence = 66
    if last["lower"] > last["body"] * 3:
        confidence += 12
    if last["is_bull"]:
        confidence += 8
    confidence = min(100, confidence)
    entry = last["c"]
    stop_loss = last["l"] * 0.995
    target = last["c"] + (last["c"] - stop_loss) * 2
    return {
        "pattern": "うえピンバー（Upper Pinbar）",
        "icon": "📌",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "wick_to_body_ratio": round(last["lower"] / max(last["body"], 1e-9), 2),
        "current_price": round(last["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（うえピンバー・下ヒゲ長い反発）",
        "description": "長い下ヒゲで売り圧力を跳ね返した小実体。底値拾いのピンバー。",
    }


# ─── 微益 9. 宴の明星 (Morning Star) ────
def detect_morning_star(df: pd.DataFrame) -> Optional[dict]:
    """大陰線 → 小さな星 → 大陽線の3本パターン"""
    if len(df) < 30 or not _is_bottom_zone(df):
        return None
    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])
    if not c1["is_bear"] or c1["body_ratio"] < 0.55:
        return None
    if c2["body"] > c1["body"] * 0.4:
        return None
    if not c3["is_bull"] or c3["body_ratio"] < 0.55:
        return None
    # 星は前日終値より下に沈む
    if c2["c"] > c1["c"]:
        return None
    # 大陽線が陰線実体の半分以上を取り返す
    c1_mid = (c1["o"] + c1["c"]) / 2
    if c3["c"] < c1_mid:
        return None

    confidence = 76
    if c3["c"] >= c1["o"]:
        confidence += 12
    confidence = min(100, confidence)
    entry = c3["c"]
    stop_loss = min(c2["l"], c3["l"]) * 0.995
    target = c3["c"] + c1["body"] * 1.8
    return {
        "pattern": "宴の明星（Morning Star）",
        "icon": "🌟",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": True,
        "verdict": "🟡 微益（宴の明星・三本反転）",
        "description": "大陰線→小星→大陽線の3本。底打ち反転を告げる明星パターン。",
    }


# ─── 微益 10. 赤三兵先詰まり (Advance Block) ────
def detect_advance_block(df: pd.DataFrame) -> Optional[dict]:
    """
    赤三兵の形だが、陽線実体が徐々に小さくなり上ヒゲが伸びる
    買い勢い減退。小さな益を狙う初期段階のサイン。
    """
    if len(df) < 30:
        return None
    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])
    for cs in [c1, c2, c3]:
        if not cs["is_bull"]:
            return None
    if not (c1["c"] < c2["c"] < c3["c"]):
        return None
    # 実体が縮小
    if not (c1["body"] > c2["body"] >= c3["body"]):
        return None
    # 上ヒゲが次第に長くなる
    if not (c2["upper"] >= c1["upper"] and c3["upper"] >= c2["upper"]):
        return None
    if c3["upper"] < c3["body"] * 0.3:
        return None

    confidence = 58
    if c3["upper"] > c3["body"]:
        confidence += 10
    confidence = min(100, confidence)
    entry = c3["c"]
    stop_loss = c1["l"] * 0.995
    target = c3["c"] + c1["body"] * 0.8  # 小さな利確
    return {
        "pattern": "赤三兵先詰まり（Advance Block）",
        "icon": "🚧",
        "direction": "BUY",
        "detected": True,
        "confidence": confidence,
        "current_price": round(c3["c"], 4),
        "entry_price": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "target_price": round(target, 4),
        "risk_reward": round((target - entry) / max(entry - stop_loss, 1e-9), 2),
        "breakout_confirmed": False,
        "verdict": "🟡 微益（赤三兵先詰まり・勢い減退）",
        "description": "赤三兵だが実体縮小＋上ヒゲ拡大。買い勢い減退で微益狙い・要利確早め。",
    }


# 買いパターン一括エクスポート
CANDLESTICK_BUY_DETECTORS = [
    # 爆益
    ("rising_three_methods", detect_rising_three_methods),
    ("kabuse_upper_break", detect_kabuse_upper_break),
    # 益
    ("two_bullish_stars", detect_two_bullish_stars),
    ("big_bull_after_bears", detect_big_bull_after_bears),
    ("tsubame_gaeshi", detect_tsubame_gaeshi),
    ("yang_tasuki", detect_yang_tasuki),
    ("yin_ryo_tsutsumi", detect_yin_ryo_tsutsumi),
    ("kirikomi_sen", detect_kirikomi_sen),
    ("nihon_takuri", detect_nihon_takuri),
    ("upper_gap_tasuki", detect_upper_gap_tasuki),
    # 微益
    ("bullish_harami", detect_bullish_harami),
    ("rising_window", detect_rising_window),
    ("bullish_engulfing", detect_bullish_engulfing),
    ("three_white_soldiers", detect_three_white_soldiers),
    ("three_stack_up", detect_three_stack_up),
    ("reversal_high", detect_reversal_high),
    ("thrust_up", detect_thrust_up),
    ("upper_pinbar", detect_upper_pinbar),
    ("morning_star", detect_morning_star),
    ("advance_block", detect_advance_block),
]


# ════════════════════════════════════════════════
#  一括エクスポート
# ════════════════════════════════════════════════

CANDLESTICK_SELL_DETECTORS = [
    # 天井圏（反転）
    ("hanging_man", detect_hanging_man),
    ("three_black_crows", detect_three_black_crows),
    ("dango_top", detect_dango_top),
    ("abandoned_baby", detect_abandoned_baby),
    ("yang_yang_harami", detect_yang_yang_harami),
    ("last_engulfing_top", detect_last_engulfing_top),
    ("counter_attack", detect_counter_attack_line),
    ("three_gap_doji", detect_three_gap_doji),
    ("dark_cloud_cover", detect_dark_cloud_cover),
    ("yang_yin_harami", detect_yang_yin_harami),
    ("high_wave", detect_high_wave),
    ("five_bears", detect_five_bears),
    # 待って売れ（下降継続）
    ("gapdown_two_blacks", detect_gapdown_two_blacks),
    ("falling_three_methods", detect_falling_three_methods),
    ("bake_line", detect_bake_line),
    ("low_consolidation", detect_low_consolidation),
    ("gapdown_tasuki", detect_gapdown_tasuki),
    ("gapdown_side_by_side_whites", detect_gapdown_side_by_side_whites),
    ("in_neck_line", detect_in_neck_line),
]
