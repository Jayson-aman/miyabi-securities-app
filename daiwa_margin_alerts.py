"""
大和証券 FX 取引ルールを参考にした証拠金アラート（検討用・シミュレーション）

参考: ダイワFX — ロスカット基準100%の場合
  プレアラート 160% / アラート 130% / ロスカット 100%
  維持率 = 有効証拠金 ÷ 建玉必要証拠金 × 100

※ 大和証券の公式サービスではありません。Zaibase.finance の仮想口座向け。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import streamlit as st

from fx_simulator import JAPAN_LEVERAGE, LOT_SIZE, calc_margin_required, calc_pnl
from data_fetcher import get_latest_price

# ロスカット基準100%時の倍率（大和証券 FX 利用規則より）
PRE_ALERT_MULT = 1.60
ALERT_MULT = 1.30
LOSS_CUT_MULT = 1.00

STATUS_LEVEL = {
    "normal": 0,
    "pre_alert": 1,
    "alert": 2,
    "loss_cut": 3,
}

STATUS_LABELS = {
    "normal": ("🟢 正常", "#1565C0", "#E3F2FD"),
    "pre_alert": ("🟡 プレアラート", "#F57C00", "#FFF8E1"),
    "alert": ("🟠 アラート", "#E65100", "#FFE0B2"),
    "loss_cut": ("🔴 ロスカット水準", "#C62828", "#FFEBEE"),
}


def thresholds_for_loss_cut_base(loss_cut_base_pct: float = 100.0) -> dict[str, float]:
    """ロスカット基準（例: 100%）から各段階の維持率しきい値を算出。"""
    base = float(loss_cut_base_pct)
    return {
        "pre_alert": base * PRE_ALERT_MULT,
        "alert": base * ALERT_MULT,
        "loss_cut": base * LOSS_CUT_MULT,
    }


def classify_margin_ratio(
    ratio_pct: float,
    loss_cut_base_pct: float = 100.0,
) -> str:
    th = thresholds_for_loss_cut_base(loss_cut_base_pct)
    if ratio_pct < th["loss_cut"]:
        return "loss_cut"
    if ratio_pct < th["alert"]:
        return "alert"
    if ratio_pct < th["pre_alert"]:
        return "pre_alert"
    return "normal"


def compute_position_metrics(position: dict) -> Optional[dict]:
    """仮想建玉1件の維持率・含み損益を更新。"""
    ticker = position.get("ticker")
    if not ticker:
        return None
    info = get_latest_price(ticker)
    if not info:
        return None

    entry = float(position["entry_price"])
    lots = float(position["lots"])
    side = position.get("side", "buy")
    capital = float(position.get("capital", 300_000))
    leverage = int(position.get("leverage", JAPAN_LEVERAGE))
    loss_cut_base = float(position.get("loss_cut_base_pct", 100.0))

    current = float(info["price"])
    margin_req = float(position.get("margin_required") or calc_margin_required(entry, lots, leverage))
    pnl = calc_pnl(entry, current, lots, side)
    effective = capital + pnl
    ratio = (effective / margin_req * 100) if margin_req > 0 else 999.0
    status = classify_margin_ratio(ratio, loss_cut_base)

    return {
        "ticker": ticker,
        "label": position.get("label", ticker),
        "side": side,
        "lots": lots,
        "entry_price": entry,
        "current_price": current,
        "capital": capital,
        "margin_required": margin_req,
        "effective_margin": effective,
        "unrealized_pnl": pnl,
        "margin_ratio_pct": round(ratio, 1),
        "status": status,
        "loss_cut_base_pct": loss_cut_base,
        "thresholds": thresholds_for_loss_cut_base(loss_cut_base),
    }


def get_virtual_positions() -> list[dict]:
    return list(st.session_state.get("virtual_positions", []))


def set_virtual_position(position: dict) -> None:
    pos = dict(position)
    pos["opened_at"] = datetime.now().isoformat()
    st.session_state["virtual_positions"] = [pos]


def clear_virtual_positions() -> None:
    st.session_state["virtual_positions"] = []


def _event(
    *,
    status: str,
    message: str,
    metrics: dict,
    severity: int,
) -> dict:
    return {
        "id": f"daiwa_{status}_{metrics['ticker']}_{datetime.now().strftime('%Y%m%d%H%M')}",
        "source": "daiwa_margin",
        "status": status,
        "severity": severity,
        "message": message,
        "margin_ratio_pct": metrics["margin_ratio_pct"],
        "ticker": metrics["ticker"],
        "label": metrics["label"],
        "triggered_at": datetime.now().isoformat(),
        "metrics": metrics,
    }


def check_daiwa_margin_alerts() -> list[dict]:
    """
    仮想建玉の維持率を評価し、大和証券 FX ルールに沿った通知イベントを返す。
    同一ステータスはクールダウン内なら再通知しない。
    """
    positions = get_virtual_positions()
    if not positions:
        return []

    fired: list[dict] = []
    state: dict = st.session_state.setdefault("daiwa_alert_state", {})
    cooldown_min = int(st.session_state.get("daiwa_alert_cooldown_min", 15))

    for pos in positions:
        m = compute_position_metrics(pos)
        if not m:
            continue

        status = m["status"]
        th = m["thresholds"]
        key = f"{m['ticker']}_{status}"

        if status == "normal":
            state.pop(f"{m['ticker']}_pre_alert", None)
            state.pop(f"{m['ticker']}_alert", None)
            state.pop(f"{m['ticker']}_loss_cut", None)
            continue

        last = state.get(key)
        if last:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 60
                if elapsed < cooldown_min:
                    continue
            except Exception:
                pass

        if status == "pre_alert":
            msg = (
                f"🟡 【プレアラート】{m['label']} — 証拠金維持率 {m['margin_ratio_pct']:.1f}% "
                f"（基準 {th['pre_alert']:.0f}% 未満）有効証拠金の余裕が減少しています。"
            )
            fired.append(_event(status=status, message=msg, metrics=m, severity=1))
        elif status == "alert":
            msg = (
                f"🟠 【アラート】{m['label']} — 証拠金維持率 {m['margin_ratio_pct']:.1f}% "
                f"（基準 {th['alert']:.0f}% 未満）追加証拠金または建玉整理を検討してください。"
            )
            fired.append(_event(status=status, message=msg, metrics=m, severity=2))
        elif status == "loss_cut":
            msg = (
                f"🔴 【ロスカット水準】{m['label']} — 証拠金維持率 {m['margin_ratio_pct']:.1f}% "
                f"（基準 {th['loss_cut']:.0f}% 未満）実口座では全建玉の強制決済対象です（本アプリはシミュレーション）。"
            )
            fired.append(_event(status=status, message=msg, metrics=m, severity=3))

        state[key] = datetime.now().isoformat()

    st.session_state["daiwa_alert_state"] = state
    st.session_state["daiwa_last_metrics"] = [
        compute_position_metrics(p) for p in positions
    ]
    return fired


def check_price_move_alerts(threshold_yen: float = 0.3) -> list[dict]:
    """USD/JPY 等の短期変動アラート（検討用）。"""
    from interval_predictor import predict_intervals

    fired = []
    state = st.session_state.setdefault("daiwa_price_alert_state", {})
    tickers = ["USDJPY=X", "EURJPY=X", "CL=F"]

    for tk in tickers:
        try:
            r = predict_intervals(tk, steps=4)
            if not r or len(r["intervals"]) < 4:
                continue
            cur = float(r["current_bid"])
            pred60 = float(r["intervals"][-1]["bid"])
            diff = pred60 - cur
            if "JPY" in tk:
                if abs(diff) < threshold_yen:
                    continue
                unit = "円"
            else:
                if abs(diff) < 0.5:
                    continue
                unit = ""
            direction = "上昇" if diff > 0 else "下落"
            key = f"{tk}_{direction}"
            if state.get(key):
                continue
            fired.append({
                "id": f"price_{tk}_{datetime.now().strftime('%H%M')}",
                "source": "price_forecast",
                "status": "price_move",
                "severity": 1,
                "message": (
                    f"📊 【価格変動予測】{r['label']} 60分先 {direction} "
                    f"{abs(diff):.3f}{unit}（現在 {cur:.3f} → 予測 {pred60:.3f}）"
                ),
                "triggered_at": datetime.now().isoformat(),
            })
            state[key] = datetime.now().isoformat()
        except Exception:
            continue

    st.session_state["daiwa_price_alert_state"] = state
    return fired


def check_all_daiwa_alerts(*, include_price: bool = True) -> list[dict]:
    events = check_daiwa_margin_alerts()
    if include_price:
        events.extend(check_price_move_alerts())
    events.sort(key=lambda e: e.get("severity", 0), reverse=True)
    return events
