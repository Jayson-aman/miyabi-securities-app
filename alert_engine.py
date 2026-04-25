"""
アラート・通知エンジン
価格変動、テクニカルシグナル、ニュースイベントなどをトリガーに
ユーザーに通知を発信する
"""

import json
import os
from datetime import datetime
from typing import List, Optional
import yfinance as yf
import pandas as pd
import numpy as np


ALERTS_FILE = "alerts_config.json"
ALERT_LOG_FILE = "alert_log.json"


# ════════════════════════════════════════════════
#  アラート設定の永続化
# ════════════════════════════════════════════════

def load_alerts() -> List[dict]:
    """アラート設定を読み込む"""
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_alerts(alerts: List[dict]) -> None:
    """アラート設定を保存"""
    try:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_alert(alert: dict) -> None:
    """アラートを追加"""
    alerts = load_alerts()
    alert["id"] = f"alert_{int(datetime.now().timestamp() * 1000)}"
    alert["created_at"] = datetime.now().isoformat()
    alert["enabled"] = True
    alert["triggered_count"] = 0
    alerts.append(alert)
    save_alerts(alerts)


def delete_alert(alert_id: str) -> None:
    """アラートを削除"""
    alerts = load_alerts()
    alerts = [a for a in alerts if a.get("id") != alert_id]
    save_alerts(alerts)


def toggle_alert(alert_id: str) -> None:
    """アラートのオン/オフ切替"""
    alerts = load_alerts()
    for a in alerts:
        if a.get("id") == alert_id:
            a["enabled"] = not a.get("enabled", True)
    save_alerts(alerts)


# ════════════════════════════════════════════════
#  アラート判定エンジン
# ════════════════════════════════════════════════

def check_price_alert(alert: dict) -> Optional[dict]:
    """
    価格条件アラートをチェック

    alert: {
        "type": "price_above" / "price_below" / "change_pct_above" / "change_pct_below",
        "ticker": ティッカー,
        "threshold": 閾値,
        "name": 表示名
    }
    """
    try:
        t = yf.Ticker(alert["ticker"])
        hist = t.history(period="2d")
        if hist is None or hist.empty:
            return None
        current = hist["Close"].iloc[-1]
        previous = hist["Close"].iloc[-2] if len(hist) >= 2 else current
        change_pct = (current / previous - 1) * 100

        triggered = False
        message = ""
        atype = alert.get("type", "")
        threshold = alert.get("threshold", 0)

        if atype == "price_above" and current > threshold:
            triggered = True
            message = f"💹 {alert['name']} が {threshold} を上抜け（現在 {current:.2f}）"
        elif atype == "price_below" and current < threshold:
            triggered = True
            message = f"📉 {alert['name']} が {threshold} を下抜け（現在 {current:.2f}）"
        elif atype == "change_pct_above" and change_pct > threshold:
            triggered = True
            message = f"🚀 {alert['name']} が +{threshold}% を超過（{change_pct:+.2f}%）"
        elif atype == "change_pct_below" and change_pct < -abs(threshold):
            triggered = True
            message = f"⚠️ {alert['name']} が -{abs(threshold)}% を下回る（{change_pct:+.2f}%）"

        if triggered:
            return {
                "alert_id": alert.get("id"),
                "name": alert["name"],
                "ticker": alert["ticker"],
                "type": atype,
                "message": message,
                "current_price": round(current, 4),
                "change_pct": round(change_pct, 2),
                "triggered_at": datetime.now().isoformat(),
            }
    except Exception:
        return None
    return None


def check_technical_alert(alert: dict) -> Optional[dict]:
    """
    テクニカル条件アラート（RSI過熱・MACDクロスなど）

    alert: {
        "type": "rsi_oversold" / "rsi_overbought" / "macd_golden_cross" / "macd_dead_cross",
        "ticker": ティッカー,
        "threshold": 閾値（RSI用）,
        "name": 表示名
    }
    """
    try:
        t = yf.Ticker(alert["ticker"])
        df = t.history(period="3mo", interval="1d")
        if df is None or df.empty or len(df) < 30:
            return None

        close = df["Close"]
        atype = alert.get("type", "")
        threshold = alert.get("threshold", 30)
        triggered = False
        message = ""

        if "rsi" in atype:
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = (100 - (100 / (1 + rs))).iloc[-1]

            if atype == "rsi_oversold" and rsi < threshold:
                triggered = True
                message = f"🔻 {alert['name']} RSI={rsi:.1f}（売られすぎ → 反発期待）"
            elif atype == "rsi_overbought" and rsi > threshold:
                triggered = True
                message = f"🔺 {alert['name']} RSI={rsi:.1f}（買われすぎ → 利確検討）"

        elif "macd" in atype:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            sig = macd.ewm(span=9, adjust=False).mean()

            if atype == "macd_golden_cross":
                if macd.iloc[-2] < sig.iloc[-2] and macd.iloc[-1] > sig.iloc[-1]:
                    triggered = True
                    message = f"🟢 {alert['name']} MACDゴールデンクロス発生"
            elif atype == "macd_dead_cross":
                if macd.iloc[-2] > sig.iloc[-2] and macd.iloc[-1] < sig.iloc[-1]:
                    triggered = True
                    message = f"🔴 {alert['name']} MACDデッドクロス発生"

        if triggered:
            return {
                "alert_id": alert.get("id"),
                "name": alert["name"],
                "ticker": alert["ticker"],
                "type": atype,
                "message": message,
                "current_price": round(close.iloc[-1], 4),
                "triggered_at": datetime.now().isoformat(),
            }
    except Exception:
        return None
    return None


def check_all_alerts() -> List[dict]:
    """設定された全アラートを評価"""
    alerts = load_alerts()
    triggered = []

    for alert in alerts:
        if not alert.get("enabled", True):
            continue

        atype = alert.get("type", "")
        result = None

        if atype.startswith("price_") or atype.startswith("change_pct_"):
            result = check_price_alert(alert)
        elif atype.startswith("rsi_") or atype.startswith("macd_"):
            result = check_technical_alert(alert)

        if result:
            triggered.append(result)
            alert["triggered_count"] = alert.get("triggered_count", 0) + 1
            alert["last_triggered"] = result["triggered_at"]

    save_alerts(alerts)

    if triggered:
        log = load_alert_log()
        log.extend(triggered)
        save_alert_log(log[-200:])

    return triggered


# ════════════════════════════════════════════════
#  アラートログ
# ════════════════════════════════════════════════

def load_alert_log() -> List[dict]:
    if not os.path.exists(ALERT_LOG_FILE):
        return []
    try:
        with open(ALERT_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_alert_log(log: List[dict]) -> None:
    try:
        with open(ALERT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_alert_log() -> None:
    save_alert_log([])


# ════════════════════════════════════════════════
#  アラートタイプの定義（UI用）
# ════════════════════════════════════════════════

ALERT_TYPES = {
    "price_above": "価格が指定値を上抜け",
    "price_below": "価格が指定値を下抜け",
    "change_pct_above": "前日比が +X% を超える",
    "change_pct_below": "前日比が -X% を下回る",
    "rsi_oversold": "RSI が売られすぎ（X以下）",
    "rsi_overbought": "RSI が買われすぎ（X以上）",
    "macd_golden_cross": "MACD ゴールデンクロス発生",
    "macd_dead_cross": "MACD デッドクロス発生",
}


# ════════════════════════════════════════════════
#  各アラートタイプの詳細説明（UI表示用）
# ════════════════════════════════════════════════

ALERT_TYPE_DETAILS = {
    "price_above": {
        "icon": "💹",
        "category": "価格",
        "watched_value": "終値（現在値）",
        "trigger_rule": "現在価格 > 指定した価格",
        "explanation": "価格が上に抜けたら発火（目標値達成・ブレイクアウト検知）",
        "example": "USD/JPY 155.00円を上抜け → アラート",
        "threshold_label": "発火させたい価格（例: 155.00）",
        "threshold_default": 155.0,
        "threshold_step": 0.01,
        "use_case": "🎯 利確目標到達 / ブレイクアウト検知",
    },
    "price_below": {
        "icon": "📉",
        "category": "価格",
        "watched_value": "終値（現在値）",
        "trigger_rule": "現在価格 < 指定した価格",
        "explanation": "価格が下に抜けたら発火（押し目買い・損切りライン）",
        "example": "ビットコイン 60,000ドルを下抜け → アラート",
        "threshold_label": "発火させたい価格（例: 60000）",
        "threshold_default": 0.0,
        "threshold_step": 0.01,
        "use_case": "🛑 損切りライン到達 / 押し目買いタイミング",
    },
    "change_pct_above": {
        "icon": "🚀",
        "category": "変動率",
        "watched_value": "前営業日比の変動率(%)",
        "trigger_rule": "前日比 > +X%",
        "explanation": "前日比で大きく上昇したら発火（急騰検知）",
        "example": "前日比 +3% を超えたら発火",
        "threshold_label": "上昇率(%) 例: 3.0",
        "threshold_default": 3.0,
        "threshold_step": 0.5,
        "use_case": "📈 急騰銘柄を逃さない",
    },
    "change_pct_below": {
        "icon": "⚠️",
        "category": "変動率",
        "watched_value": "前営業日比の変動率(%)",
        "trigger_rule": "前日比 < -X%",
        "explanation": "前日比で大きく下落したら発火（急落検知・押し目）",
        "example": "前日比 -3% を下回ったら発火",
        "threshold_label": "下落率(%) 例: 3.0（数値はプラスで入力）",
        "threshold_default": 3.0,
        "threshold_step": 0.5,
        "use_case": "📉 急落 → 反発狙いの押し目買い検知",
    },
    "rsi_oversold": {
        "icon": "🔻",
        "category": "テクニカル",
        "watched_value": "RSI(14日)の値",
        "trigger_rule": "RSI < 指定値（標準: 30）",
        "explanation": "RSI が低くなりすぎたら発火（売られすぎ → 反発期待）",
        "example": "RSI < 30 → 売られすぎゾーン",
        "threshold_label": "RSI下限（標準: 30）",
        "threshold_default": 30.0,
        "threshold_step": 1.0,
        "use_case": "🟢 逆張り買いタイミング検知",
    },
    "rsi_overbought": {
        "icon": "🔺",
        "category": "テクニカル",
        "watched_value": "RSI(14日)の値",
        "trigger_rule": "RSI > 指定値（標準: 70）",
        "explanation": "RSI が高くなりすぎたら発火（買われすぎ → 利確検討）",
        "example": "RSI > 70 → 買われすぎゾーン",
        "threshold_label": "RSI上限（標準: 70）",
        "threshold_default": 70.0,
        "threshold_step": 1.0,
        "use_case": "🔴 利確・天井注意",
    },
    "macd_golden_cross": {
        "icon": "🟢",
        "category": "テクニカル",
        "watched_value": "MACD線とシグナル線の位置関係",
        "trigger_rule": "MACD線がシグナル線を下から上へクロス",
        "explanation": "上昇トレンド転換のシグナル（買いサイン）",
        "example": "MACD = -0.5 → +0.2（シグナル線を上抜け）",
        "threshold_label": "（しきい値不要）",
        "threshold_default": 0.0,
        "threshold_step": 0.0,
        "use_case": "📈 中期上昇トレンド入り検知",
    },
    "macd_dead_cross": {
        "icon": "🔴",
        "category": "テクニカル",
        "watched_value": "MACD線とシグナル線の位置関係",
        "trigger_rule": "MACD線がシグナル線を上から下へクロス",
        "explanation": "下降トレンド転換のシグナル（売りサイン）",
        "example": "MACD = +0.3 → -0.1（シグナル線を下抜け）",
        "threshold_label": "（しきい値不要）",
        "threshold_default": 0.0,
        "threshold_step": 0.0,
        "use_case": "📉 中期下降トレンド入り → 利確/ショート",
    },
}


# ════════════════════════════════════════════════
#  プレビュー機能：現在値と発火までの距離を返す
# ════════════════════════════════════════════════

def get_alert_preview(ticker: str, atype: str, threshold: float) -> Optional[dict]:
    """
    アラートの「現在の状態」を返す（UIプレビュー用）

    Returns:
        {
            "watched_label": 監視している指標名,
            "current_value": 現在値,
            "threshold": 閾値,
            "would_trigger": 今すぐ発火するか,
            "distance": 発火までの差,
            "distance_pct": 発火までの距離(%),
            "status_message": "○○に達するまであと△△",
        }
    """
    try:
        t = yf.Ticker(ticker)

        # ─ 価格・変動率系 ─
        if atype.startswith("price_") or atype.startswith("change_pct_"):
            hist = t.history(period="2d")
            if hist is None or hist.empty:
                return None
            current_price = float(hist["Close"].iloc[-1])
            previous = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current_price
            change_pct = (current_price / previous - 1) * 100

            if atype == "price_above":
                distance = threshold - current_price
                pct = (distance / current_price) * 100 if current_price else 0
                return {
                    "watched_label": "現在価格",
                    "current_value": round(current_price, 4),
                    "threshold": threshold,
                    "would_trigger": current_price > threshold,
                    "distance": round(distance, 4),
                    "distance_pct": round(pct, 2),
                    "status_message": (
                        f"✅ 既に発火中（{current_price:.4f} > {threshold}）"
                        if current_price > threshold
                        else f"あと +{distance:.4f}（+{pct:.2f}%）上昇で発火"
                    ),
                    "rule_text": f"現在価格 ({current_price:.4f}) > {threshold} になったら発火",
                }
            elif atype == "price_below":
                distance = current_price - threshold
                pct = (distance / current_price) * 100 if current_price else 0
                return {
                    "watched_label": "現在価格",
                    "current_value": round(current_price, 4),
                    "threshold": threshold,
                    "would_trigger": current_price < threshold,
                    "distance": round(distance, 4),
                    "distance_pct": round(pct, 2),
                    "status_message": (
                        f"✅ 既に発火中（{current_price:.4f} < {threshold}）"
                        if current_price < threshold
                        else f"あと -{distance:.4f}（-{pct:.2f}%）下落で発火"
                    ),
                    "rule_text": f"現在価格 ({current_price:.4f}) < {threshold} になったら発火",
                }
            elif atype == "change_pct_above":
                distance = threshold - change_pct
                return {
                    "watched_label": "前日比(%)",
                    "current_value": round(change_pct, 2),
                    "threshold": threshold,
                    "would_trigger": change_pct > threshold,
                    "distance": round(distance, 2),
                    "distance_pct": round(distance, 2),
                    "status_message": (
                        f"✅ 既に発火中（前日比 {change_pct:+.2f}% > +{threshold}%）"
                        if change_pct > threshold
                        else f"前日比 {change_pct:+.2f}% → あと +{distance:.2f}% 上昇で発火"
                    ),
                    "rule_text": f"前日比 ({change_pct:+.2f}%) > +{threshold}% になったら発火",
                }
            elif atype == "change_pct_below":
                distance = change_pct - (-abs(threshold))
                return {
                    "watched_label": "前日比(%)",
                    "current_value": round(change_pct, 2),
                    "threshold": -abs(threshold),
                    "would_trigger": change_pct < -abs(threshold),
                    "distance": round(distance, 2),
                    "distance_pct": round(distance, 2),
                    "status_message": (
                        f"✅ 既に発火中（前日比 {change_pct:+.2f}% < -{abs(threshold)}%）"
                        if change_pct < -abs(threshold)
                        else f"前日比 {change_pct:+.2f}% → あと -{distance:.2f}% 下落で発火"
                    ),
                    "rule_text": f"前日比 ({change_pct:+.2f}%) < -{abs(threshold)}% になったら発火",
                }

        # ─ テクニカル系 ─
        elif atype.startswith("rsi_") or atype.startswith("macd_"):
            df = t.history(period="3mo", interval="1d")
            if df is None or df.empty or len(df) < 30:
                return None
            close = df["Close"]

            if atype.startswith("rsi_"):
                delta = close.diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = float((100 - (100 / (1 + rs))).iloc[-1])

                if atype == "rsi_oversold":
                    distance = rsi - threshold
                    return {
                        "watched_label": "RSI(14)",
                        "current_value": round(rsi, 1),
                        "threshold": threshold,
                        "would_trigger": rsi < threshold,
                        "distance": round(distance, 1),
                        "distance_pct": 0,
                        "status_message": (
                            f"✅ 既に発火中（RSI={rsi:.1f} < {threshold} 売られすぎ）"
                            if rsi < threshold
                            else f"RSI={rsi:.1f} → あと {distance:.1f} 下がれば発火（{threshold}以下）"
                        ),
                        "rule_text": f"RSI ({rsi:.1f}) < {threshold} になったら発火（売られすぎ）",
                    }
                elif atype == "rsi_overbought":
                    distance = threshold - rsi
                    return {
                        "watched_label": "RSI(14)",
                        "current_value": round(rsi, 1),
                        "threshold": threshold,
                        "would_trigger": rsi > threshold,
                        "distance": round(distance, 1),
                        "distance_pct": 0,
                        "status_message": (
                            f"✅ 既に発火中（RSI={rsi:.1f} > {threshold} 買われすぎ）"
                            if rsi > threshold
                            else f"RSI={rsi:.1f} → あと {distance:.1f} 上がれば発火（{threshold}以上）"
                        ),
                        "rule_text": f"RSI ({rsi:.1f}) > {threshold} になったら発火（買われすぎ）",
                    }

            elif atype.startswith("macd_"):
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                sig = macd.ewm(span=9, adjust=False).mean()
                m_now, m_prev = float(macd.iloc[-1]), float(macd.iloc[-2])
                s_now, s_prev = float(sig.iloc[-1]), float(sig.iloc[-2])
                spread = m_now - s_now

                if atype == "macd_golden_cross":
                    will_trigger = m_prev < s_prev and m_now > s_now
                    return {
                        "watched_label": "MACD vs シグナル線",
                        "current_value": round(spread, 4),
                        "threshold": 0.0,
                        "would_trigger": will_trigger,
                        "distance": round(abs(spread), 4),
                        "distance_pct": 0,
                        "status_message": (
                            f"✅ 今ゴールデンクロス発生中（MACD={m_now:.3f}, シグナル={s_now:.3f}）"
                            if will_trigger
                            else (
                                f"MACD={m_now:.3f}, シグナル={s_now:.3f}（差 {spread:+.4f}）"
                                + ("｜現在 MACD がシグナルの上 → 既に上昇局面" if spread > 0 else "｜MACD がシグナルを上抜けた瞬間に発火")
                            )
                        ),
                        "rule_text": "MACD線がシグナル線を下から上にクロスした瞬間に発火",
                    }
                elif atype == "macd_dead_cross":
                    will_trigger = m_prev > s_prev and m_now < s_now
                    return {
                        "watched_label": "MACD vs シグナル線",
                        "current_value": round(spread, 4),
                        "threshold": 0.0,
                        "would_trigger": will_trigger,
                        "distance": round(abs(spread), 4),
                        "distance_pct": 0,
                        "status_message": (
                            f"✅ 今デッドクロス発生中（MACD={m_now:.3f}, シグナル={s_now:.3f}）"
                            if will_trigger
                            else (
                                f"MACD={m_now:.3f}, シグナル={s_now:.3f}（差 {spread:+.4f}）"
                                + ("｜現在 MACD がシグナルの下 → 既に下降局面" if spread < 0 else "｜MACD がシグナルを下抜けた瞬間に発火")
                            )
                        ),
                        "rule_text": "MACD線がシグナル線を上から下にクロスした瞬間に発火",
                    }

    except Exception:
        return None
    return None
