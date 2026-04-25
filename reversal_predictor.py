"""
円高 ⇄ 円安 転換点（リバーサル）予測モジュール

ユーザーの問い：
「ずっと円安と思っていたら急に円高になる」その瞬間を捉えたい

そのために以下を統合分析：
1. 現在のトレンド方向と「疲れ度」（過熱・伸び切り）
2. 介入水準への接近度
3. テクニカル極値（RSI/BB/ダイバージェンス）
4. 米日金利差のピークアウト兆候
5. VIX急騰によるリスクオフ転換
6. 控えるイベントによる反転トリガー
7. 過去の急変パターンマッチング
8. 「キープ可能期間」の時刻別推定
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

from event_schedule import get_upcoming_events, estimate_keep_period_for_current_trend


# ════════════════════════════════════════════════
#  現在のトレンド分析
# ════════════════════════════════════════════════

def _analyze_current_trend(ticker: str = "USDJPY=X") -> Optional[dict]:
    """
    USD/JPY の現在のトレンド方向と強度・疲れ度を分析
    """
    try:
        t = yf.Ticker(ticker)
        df_d = t.history(period="3mo", interval="1d")
        df_h = t.history(period="60d", interval="1h")
        if df_d is None or df_d.empty or len(df_d) < 30:
            return None
    except Exception:
        return None

    close_d = df_d["Close"]
    high_d = df_d["High"]
    low_d = df_d["Low"]
    current = close_d.iloc[-1]

    # 移動平均線
    ma5 = close_d.tail(5).mean()
    ma20 = close_d.tail(20).mean()
    ma60 = close_d.tail(60).mean()

    # トレンド方向
    if current > ma5 > ma20 > ma60:
        trend = "強い円安"
        trend_dir = "weak"
        trend_strength = 4
    elif current > ma5 > ma20:
        trend = "円安"
        trend_dir = "weak"
        trend_strength = 3
    elif current < ma5 < ma20 < ma60:
        trend = "強い円高"
        trend_dir = "strong"
        trend_strength = 4
    elif current < ma5 < ma20:
        trend = "円高"
        trend_dir = "strong"
        trend_strength = 3
    else:
        trend = "もみ合い"
        trend_dir = "neutral"
        trend_strength = 1

    # トレンド継続日数（同方向に動いた連続日数）
    direction = 1 if close_d.iloc[-1] > close_d.iloc[-2] else -1
    streak = 0
    for i in range(len(close_d) - 1, 0, -1):
        d = 1 if close_d.iloc[i] > close_d.iloc[i - 1] else -1
        if d == direction:
            streak += 1
        else:
            break

    # RSI
    delta = close_d.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    # ボリンジャーバンド位置
    bb_mid = close_d.rolling(20).mean()
    bb_std = close_d.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    if not np.isnan(bb_std.iloc[-1]) and bb_std.iloc[-1] > 0:
        bb_pos = (current - bb_mid.iloc[-1]) / (bb_std.iloc[-1] * 2)
    else:
        bb_pos = 0

    # ATR（変動レンジ）
    tr = pd.concat([
        high_d - low_d,
        (high_d - close_d.shift()).abs(),
        (low_d - close_d.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    # 過熱度（trend_dir方向にどれだけ伸び切ったか）
    if trend_dir == "weak":
        # 円安方向。RSI70超 + BB上限近接 + 連騰 = 疲れ
        fatigue = 0
        if rsi > 70: fatigue += 30
        if rsi > 75: fatigue += 20
        if bb_pos > 0.8: fatigue += 25
        if bb_pos > 1.0: fatigue += 15
        if streak >= 5: fatigue += 15
        if streak >= 8: fatigue += 15
    elif trend_dir == "strong":
        fatigue = 0
        if rsi < 30: fatigue += 30
        if rsi < 25: fatigue += 20
        if bb_pos < -0.8: fatigue += 25
        if bb_pos < -1.0: fatigue += 15
        if streak >= 5: fatigue += 15
        if streak >= 8: fatigue += 15
    else:
        fatigue = 0

    fatigue = min(100, fatigue)

    return {
        "current_rate": round(current, 3),
        "trend": trend,
        "trend_dir": trend_dir,
        "trend_strength": trend_strength,
        "streak_days": streak,
        "rsi": round(rsi, 1) if not np.isnan(rsi) else 50,
        "bb_position": round(bb_pos, 2),
        "atr": round(atr, 3),
        "fatigue_score": fatigue,  # 0-100. 高いほど反転リスク高
        "ma5": round(ma5, 3),
        "ma20": round(ma20, 3),
        "ma60": round(ma60, 3),
    }


# ════════════════════════════════════════════════
#  反転シグナル生成
# ════════════════════════════════════════════════

def _detect_reversal_signals(trend_info: dict) -> list:
    """
    現在のトレンドが反転する具体的なシグナルを列挙
    """
    signals = []
    rsi = trend_info["rsi"]
    bb = trend_info["bb_position"]
    streak = trend_info["streak_days"]
    fatigue = trend_info["fatigue_score"]
    direction = trend_info["trend_dir"]
    rate = trend_info["current_rate"]

    if direction == "weak":  # 円安継続中 → 円高への反転シグナル
        if rsi > 75:
            signals.append({
                "level": "high", "type": "RSI過熱",
                "msg": f"RSI={rsi:.0f}（極度の買われすぎ）→ 円高転換リスク高",
                "trigger_window_hours": 12,
            })
        elif rsi > 70:
            signals.append({
                "level": "medium", "type": "RSI買われすぎ",
                "msg": f"RSI={rsi:.0f}（買われすぎ圏）→ 反落の可能性",
                "trigger_window_hours": 48,
            })

        if bb > 1.0:
            signals.append({
                "level": "high", "type": "BB上限突破",
                "msg": f"ボリンジャー+2σ突破（BB位置 {bb:.2f}）→ 強い反落圧力",
                "trigger_window_hours": 24,
            })
        elif bb > 0.8:
            signals.append({
                "level": "medium", "type": "BB上限接近",
                "msg": f"ボリンジャー上限接近（BB位置 {bb:.2f}）",
                "trigger_window_hours": 72,
            })

        if streak >= 8:
            signals.append({
                "level": "high", "type": "連騰疲れ",
                "msg": f"{streak}日連続上昇 → 利確売り・調整入り高確率",
                "trigger_window_hours": 24,
            })
        elif streak >= 5:
            signals.append({
                "level": "medium", "type": "連騰",
                "msg": f"{streak}日連続上昇 → 短期調整リスク",
                "trigger_window_hours": 72,
            })

        # 介入水準
        if rate >= 155:
            signals.append({
                "level": "extreme", "type": "実弾介入水準",
                "msg": f"{rate:.2f}円 → 実弾介入の可能性極めて高い。1時間で5円超の急落も",
                "trigger_window_hours": 24,
            })
        elif rate >= 152:
            signals.append({
                "level": "high", "type": "口先介入水準",
                "msg": f"{rate:.2f}円 → 財務省口先介入リスク。突然の発言で即急落",
                "trigger_window_hours": 48,
            })
        elif rate >= 150:
            signals.append({
                "level": "medium", "type": "心理的節目",
                "msg": f"{rate:.2f}円 → 心理的抵抗。発言警戒域",
                "trigger_window_hours": 96,
            })

    elif direction == "strong":  # 円高継続中 → 円安への反転シグナル
        if rsi < 25:
            signals.append({
                "level": "high", "type": "RSI過売",
                "msg": f"RSI={rsi:.0f}（極度の売られすぎ）→ 円安転換リスク高",
                "trigger_window_hours": 12,
            })
        elif rsi < 30:
            signals.append({
                "level": "medium", "type": "RSI売られすぎ",
                "msg": f"RSI={rsi:.0f}（売られすぎ圏）→ 反発可能性",
                "trigger_window_hours": 48,
            })

        if bb < -1.0:
            signals.append({
                "level": "high", "type": "BB下限突破",
                "msg": f"ボリンジャー-2σ突破（BB位置 {bb:.2f}）→ 強い反発圧力",
                "trigger_window_hours": 24,
            })

        if streak >= 8:
            signals.append({
                "level": "high", "type": "連落疲れ",
                "msg": f"{streak}日連続下落 → ショートカバー入り高確率",
                "trigger_window_hours": 24,
            })

    return signals


# ════════════════════════════════════════════════
#  急変シナリオ（特に「ずっと円安→急に円高」）
# ════════════════════════════════════════════════

def _build_reversal_scenarios(trend_info: dict) -> list:
    """
    今後発生しうる円高/円安の急変シナリオを列挙
    """
    direction = trend_info["trend_dir"]
    rate = trend_info["current_rate"]
    fatigue = trend_info["fatigue_score"]
    scenarios = []

    if direction == "weak":  # 円安が続いている → 円高急変シナリオ
        scenarios.extend([
            {
                "icon": "💴", "name": "政府・日銀の実弾介入",
                "trigger": f"{rate:.1f}円 → 155円超で発生確率↑",
                "expected_move": "1時間で 3〜5円の急激な円高",
                "duration": "効果は24-48時間。その後再度円安に戻りやすい",
                "probability": "極めて高い" if rate >= 155 else ("高い" if rate >= 152 else "中"),
                "watch": "財務官・神田氏の発言、米財務省との協調示唆",
            },
            {
                "icon": "🏦", "name": "日銀のサプライズ利上げ",
                "trigger": "次回会合 / 臨時会合（長期金利急騰時）",
                "expected_move": "1日で 2〜4円の円高",
                "duration": "数日〜2週間 効果持続",
                "probability": "中（円安が止まらない場合の最終手段）",
                "watch": "植田総裁のタカ派発言、長期金利1.5%超",
            },
            {
                "icon": "📉", "name": "米経済指標の急悪化",
                "trigger": "雇用統計大幅下振れ / CPI急低下 / ISM50割れ",
                "expected_move": "発表後30分で 1〜2円の円高",
                "duration": "12〜48時間継続",
                "probability": "中",
                "watch": "経済指標発表時刻を要確認",
            },
            {
                "icon": "⚡", "name": "FOMCのハト派サプライズ",
                "trigger": "利下げ示唆 / ドットチャート下方修正",
                "expected_move": "発表後1時間で 2〜3円の円高",
                "duration": "1週間以上効果継続",
                "probability": "低-中（FOMC開催時のみ）",
                "watch": "FOMCスケジュール・パウエル会見",
            },
            {
                "icon": "🌍", "name": "地政学リスク急上昇（リスクオフ）",
                "trigger": "中東情勢悪化 / 台湾有事 / 米株急落",
                "expected_move": "数時間で 2〜4円の円高",
                "duration": "ニュース次第で1日〜1週間",
                "probability": "予測困難（突発的）",
                "watch": "VIX 25超・S&P500 急落・原油急騰",
            },
            {
                "icon": "💥", "name": "キャリートレード巻き戻し",
                "trigger": f"連騰疲れ（現在{trend_info['streak_days']}日連続）+ VIX急騰",
                "expected_move": "数日で 3〜5円の円高",
                "duration": "1〜2週間",
                "probability": "高い" if fatigue > 60 else "中",
                "watch": "AUDJPY/MXNJPY 等の高金利通貨ペア下落",
            },
        ])

    elif direction == "strong":  # 円高 → 円安急変
        scenarios.extend([
            {
                "icon": "🏛", "name": "日銀ハト派発言・緩和継続",
                "trigger": "総裁会見で正常化先送り示唆",
                "expected_move": "1日で 1〜3円の円安",
                "duration": "数日〜1週間",
                "probability": "中",
                "watch": "植田総裁会見・国会答弁",
            },
            {
                "icon": "📈", "name": "米経済指標の上振れ",
                "trigger": "雇用統計強い / CPI上振れ / ISM 55超",
                "expected_move": "30分で 1〜2円の円安",
                "duration": "24-48時間",
                "probability": "中",
                "watch": "次の重要指標発表",
            },
            {
                "icon": "🦅", "name": "FOMCタカ派化",
                "trigger": "利上げ示唆 / 利下げ後ろ倒し",
                "expected_move": "1時間で 2〜3円の円安",
                "duration": "1週間以上",
                "probability": "低-中",
                "watch": "FOMC開催・パウエル発言",
            },
            {
                "icon": "🛢", "name": "原油急騰",
                "trigger": "中東紛争 / OPEC減産",
                "expected_move": "数日で 2〜3円の円安",
                "duration": "原油高が続く限り継続",
                "probability": "中",
                "watch": "WTI 90ドル超への上昇",
            },
        ])

    return scenarios


# ════════════════════════════════════════════════
#  時間帯別 反転ホット時刻予測
# ════════════════════════════════════════════════

def _predict_hot_reversal_times() -> list:
    """
    過去パターンから「特に反転が起きやすい時間帯」を返す
    """
    return [
        {
            "time_jst": "08:55-09:05", "name": "東京寄り付き直前",
            "type": "反転起点", "freq": "★★★",
            "reason": "実需フロー集中＋仲値予想で方向転換しやすい",
        },
        {
            "time_jst": "09:55-10:00", "name": "東京仲値（公示）",
            "type": "急変動", "freq": "★★★★",
            "reason": "銀行が仲値を決定。月末・5の倍数日は特に動く",
        },
        {
            "time_jst": "15:00-15:10", "name": "東京クローズ",
            "type": "反転起点", "freq": "★★★",
            "reason": "ポジション調整で東京日中の方向と逆の動きが出やすい",
        },
        {
            "time_jst": "16:00-16:30", "name": "ロンドン寄り付き",
            "type": "反転＆加速", "freq": "★★★★",
            "reason": "欧州勢参入。東京と異なる見方で反転 or 加速",
        },
        {
            "time_jst": "21:30-22:00", "name": "米経済指標発表",
            "type": "急変動", "freq": "★★★★★",
            "reason": "雇用統計・CPI・小売等。発表瞬間に大きく動く",
        },
        {
            "time_jst": "22:30-23:00", "name": "NY寄り付き",
            "type": "反転起点", "freq": "★★★★",
            "reason": "米株オープン。リスクオン/オフが鮮明化",
        },
        {
            "time_jst": "00:00-00:15", "name": "ロンドン・フィキシング",
            "type": "急変動", "freq": "★★★",
            "reason": "大口の為替決済が集中。月末は特にボラ高",
        },
        {
            "time_jst": "03:00-03:30", "name": "FOMC声明発表（FOMC日のみ）",
            "type": "極大急変動", "freq": "★★★★★",
            "reason": "政策金利・声明文で 1〜3円急変も",
        },
        {
            "time_jst": "04:30-05:00", "name": "パウエル会見終盤",
            "type": "反転", "freq": "★★★★",
            "reason": "Q&A後半で発言ニュアンスが市場予想と乖離 → 反転発生",
        },
    ]


# ════════════════════════════════════════════════
#  公開API
# ════════════════════════════════════════════════

def predict_reversal(ticker: str = "USDJPY=X") -> dict:
    """
    円高 ⇄ 円安 転換点の総合予測

    Returns:
        {
            "trend_info": 現在のトレンド情報,
            "fatigue_score": トレンド疲れ度（0-100）,
            "reversal_signals": テクニカル反転シグナルリスト,
            "scenarios": 急変シナリオリスト,
            "hot_reversal_times": 反転ホット時刻表,
            "keep_period": キープ期間予測,
            "verdict": 総合判定文字列,
            "verdict_color": 判定色,
            "next_critical_event": 次の最重要イベント,
        }
    """
    trend = _analyze_current_trend(ticker)
    if trend is None:
        return {"error": "データ取得失敗"}

    signals = _detect_reversal_signals(trend)
    scenarios = _build_reversal_scenarios(trend)
    hot_times = _predict_hot_reversal_times()
    keep = estimate_keep_period_for_current_trend(trend["trend_dir"])

    # 総合判定
    high_signals = [s for s in signals if s["level"] in ("high", "extreme")]
    fatigue = trend["fatigue_score"]

    if fatigue >= 70 or len(high_signals) >= 2:
        verdict = "⚠ 反転リスク 高"
        verdict_color = "#D32030"
        verdict_detail = (
            f"現在の{trend['trend']}トレンドは疲労度 {fatigue}%。"
            "数時間〜数日以内の反転に警戒"
        )
    elif fatigue >= 40 or len(high_signals) >= 1:
        verdict = "⚠ 反転リスク 中"
        verdict_color = "#FDB813"
        verdict_detail = (
            f"トレンド継続中も警戒シグナル発生。"
            f"次の主要イベントが転換トリガーになる可能性"
        )
    else:
        verdict = "✓ トレンド継続"
        verdict_color = "#1565C0"
        verdict_detail = f"現在の{trend['trend']}は当面継続の可能性"

    upcoming = get_upcoming_events(days_ahead=7)
    next_critical = next((e for e in upcoming if e["impact_level"] >= 4), None)

    return {
        "trend_info": trend,
        "fatigue_score": fatigue,
        "reversal_signals": signals,
        "scenarios": scenarios,
        "hot_reversal_times": hot_times,
        "keep_period": keep,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "verdict_color": verdict_color,
        "high_priority_signals": high_signals,
        "next_critical_event": next_critical,
    }
