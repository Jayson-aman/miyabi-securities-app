"""
FX予測メール通知

15分/60分先のFX予測で、円建て通貨ペアが指定幅以上に動く見込みのとき、
理由付きでメール通知する。SMTP設定は Streamlit Secrets から読む。
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Any

import pandas as pd
import streamlit as st


DEFAULT_RECIPIENT = "masaya.happylife@gmail.com"
STATE_FILE = "fx_email_alert_state.json"


def _email_config() -> dict[str, Any]:
    cfg = {}
    try:
        cfg = dict(st.secrets.get("email_alert", {}))
    except Exception:
        cfg = {}

    return {
        "enabled": bool(cfg.get("enabled", True)),
        "smtp_host": cfg.get("smtp_host", "smtp.gmail.com"),
        "smtp_port": int(cfg.get("smtp_port", 587)),
        "smtp_user": cfg.get("smtp_user", ""),
        "smtp_password": cfg.get("smtp_password", ""),
        "from_addr": cfg.get("from_addr", cfg.get("smtp_user", "")),
        "to_addr": cfg.get("to_addr", DEFAULT_RECIPIENT),
        "threshold_yen": float(cfg.get("threshold_yen", 0.3)),
        "cooldown_minutes": int(cfg.get("cooldown_minutes", 60)),
    }


def _load_state() -> dict[str, str]:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict[str, str]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _recently_sent(state: dict[str, str], key: str, cooldown_minutes: int) -> bool:
    sent_at = state.get(key)
    if not sent_at:
        return False
    try:
        last = datetime.fromisoformat(sent_at)
    except ValueError:
        return False
    return datetime.now() - last < timedelta(minutes=cooldown_minutes)


def _send_email(subject: str, body: str, cfg: dict[str, Any]) -> tuple[bool, str]:
    if not cfg["enabled"]:
        return False, "email_alert.enabled が false です"
    if not cfg["smtp_user"] or not cfg["smtp_password"] or not cfg["from_addr"]:
        return False, "SMTP設定が未設定です"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = cfg["to_addr"]

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=20) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)


def _reasoning_by_label(reasonings: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    fx_reasonings = reasonings.get("FX", []) if isinstance(reasonings, dict) else []
    return {r.get("label"): r for r in fx_reasonings if r.get("label")}


def _build_body(candidate: dict[str, Any], reasoning: dict[str, Any] | None) -> str:
    lines = [
        "雅証券 FX 予測アラート",
        "",
        f"銘柄: {candidate['label']}",
        f"判断: {candidate['trade_side']}",
        f"現在値: {candidate['current_price']:.3f}",
        f"60分後予測: {candidate['predicted_60min']:.3f}",
        f"予測変化幅: {candidate['diff_yen']:+.3f}円",
        f"しきい値: {candidate['threshold_yen']:.3f}円",
        f"信頼度(15分): {candidate.get('confidence_15', '—')}",
        "",
        "原因・根拠:",
    ]

    if reasoning:
        rsn = reasoning.get("reasoning", {})
        lines.append(f"- 概要: {rsn.get('summary', '—')}")
        lines.append(f"- マクロ要因: {rsn.get('macro_drivers', '—')}")
        lines.append(f"- リスク: {rsn.get('key_risk', '—')}")
        tech = rsn.get("technical_reasons", [])
        if tech:
            lines.append("- テクニカル:")
            lines.extend(f"  {x}" for x in tech[:5])
    else:
        lines.append("- 詳細根拠データを取得できませんでした。")

    lines.extend([
        "",
        "注意: これは短期予測であり、投資判断の最終決定ではありません。",
        "急変時はスプレッド拡大・約定ずれ・指標発表に注意してください。",
    ])
    return "\n".join(lines)


def check_and_send_fx_move_alerts(
    compact_tables: dict[str, pd.DataFrame],
    reasonings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """FXで60分先予測が0.3円以上動く場合にメール通知する。"""
    cfg = _email_config()
    fx_df = compact_tables.get("FX") if isinstance(compact_tables, dict) else None
    result: dict[str, Any] = {
        "configured": bool(cfg["smtp_user"] and cfg["smtp_password"]),
        "candidates": [],
        "sent": [],
        "skipped": [],
        "errors": [],
    }

    if fx_df is None or fx_df.empty:
        return result

    state = _load_state()
    reasons = _reasoning_by_label(reasonings)
    threshold = cfg["threshold_yen"]

    for _, row in fx_df.iterrows():
        label = str(row.get("銘柄", ""))
        if not label.endswith("/JPY"):
            continue
        try:
            current = float(row["現在値"])
            predicted = float(row["60分後 予想"])
        except Exception:
            continue

        diff_yen = predicted - current
        if abs(diff_yen) < threshold:
            continue

        trade_side = "ロング候補（上昇予測）" if diff_yen > 0 else "ショート候補（下落予測）"
        candidate = {
            "label": label,
            "trade_side": trade_side,
            "current_price": current,
            "predicted_60min": predicted,
            "diff_yen": diff_yen,
            "threshold_yen": threshold,
            "confidence_15": row.get("信頼度(15)", "—"),
        }
        result["candidates"].append(candidate)

        cooldown_key = f"{label}:{'long' if diff_yen > 0 else 'short'}"
        if _recently_sent(state, cooldown_key, cfg["cooldown_minutes"]):
            result["skipped"].append({**candidate, "reason": "cooldown"})
            continue

        subject = f"【雅証券FX】{label} {trade_side} {diff_yen:+.3f}円"
        body = _build_body(candidate, reasons.get(label))
        ok, message = _send_email(subject, body, cfg)
        if ok:
            state[cooldown_key] = datetime.now().isoformat()
            result["sent"].append(candidate)
        else:
            result["errors"].append({**candidate, "error": message})

    if result["sent"]:
        _save_state(state)
    return result
