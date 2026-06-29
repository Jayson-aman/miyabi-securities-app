"""
Zaibase.finance — 検討用サブスクリプション / ライセンス

実際の決済は Stripe Payment Link 等（Secrets 設定）。
口座開設・実取引は行わない。
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Any

import streamlit as st

PLANS = {
    "free": {
        "label": "Free",
        "price_jpy": 0,
        "desc": "ダッシュボード・基本チャート",
    },
    "pro": {
        "label": "Pro Research",
        "price_jpy": 1980,
        "desc": "CFDターミナル・3画面モニター・詳細予測",
    },
}

PRO_FEATURES = frozenset({"cfd_terminal", "monitor", "fx_alerts"})


def _billing_cfg() -> dict[str, Any]:
    try:
        return dict(st.secrets.get("billing", {}))
    except Exception:
        return {}


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


def _valid_license_keys() -> set[str]:
    cfg = _billing_cfg()
    raw = cfg.get("pro_license_keys", [])
    if isinstance(raw, str):
        raw = [raw]
    out: set[str] = set()
    for item in raw:
        s = str(item).strip()
        if not s:
            continue
        if len(s) == 64 and all(c in "0123456789abcdef" for c in s.lower()):
            out.add(s.lower())
        else:
            out.add(_hash_key(s))
    return out


def billing_enabled() -> bool:
    try:
        from auth import is_closed_until_notice
        if is_closed_until_notice():
            return False
    except Exception:
        pass
    cfg = _billing_cfg()
    if cfg.get("enabled") is False:
        return False
    return bool(cfg.get("stripe_payment_link") or _valid_license_keys())


def get_tier() -> str:
    if st.session_state.get("subscription_tier") == "pro":
        return "pro"
    entered = (st.session_state.get("license_key_input") or "").strip()
    if entered and entered in _valid_license_keys():
        st.session_state["subscription_tier"] = "pro"
        return "pro"
    hashed = _hash_key(entered) if entered else ""
    if hashed and hashed in _valid_license_keys():
        st.session_state["subscription_tier"] = "pro"
        return "pro"
    return "free"


def has_pro() -> bool:
    if not billing_enabled():
        return True
    return get_tier() == "pro"


def require_pro(feature: str, *, title: str = "Pro Research") -> bool:
    """Pro 未加入ならペイウォールを表示し False。"""
    if has_pro():
        return True
    render_paywall(feature, title=title)
    return False


def render_paywall(feature: str, *, title: str = "Pro Research") -> None:
    cfg = _billing_cfg()
    price = cfg.get("pro_price_display", "¥1,980 / 月（検討用）")
    link = cfg.get("stripe_payment_link", "")
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1a2332 0%,#0d1520 100%);color:#fff;
            border:1px solid #2a6fdb;border-radius:8px;padding:20px;margin:12px 0;">
            <div style="font-size:1.1rem;font-weight:700;color:#5eb3ff;">🔒 {title}</div>
            <div style="font-size:0.85rem;color:#a8c4e8;margin-top:8px;line-height:1.6;">
                <b>{PLANS['pro']['desc']}</b><br>
                機能: <code>{feature}</code><br>
                <span style="color:#ffd166;">{price}</span> — 研究・検討目的（実口座・取引執行なし）
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if link:
        st.link_button("💳 お支払い（Stripe）", link, use_container_width=True)
    st.caption(
        "お支払い後、**ライセンスキー** をサイドバー「Pro ライセンス」に入力してください。"
        " Pro は分析機能へのアクセス権であり、投資成果を保証しません。"
        " 返金・解約は「📜 利用規約・免責」→ 有料プランを参照。"
    )


def render_billing_sidebar() -> None:
    if not billing_enabled():
        st.caption("💡 課金は未設定（全機能利用可）")
        return

    tier = get_tier()
    badge = "✅ Pro" if tier == "pro" else "Free"
    st.markdown(f"**プラン:** {badge}")

    if tier != "pro":
        with st.expander("🔑 Pro ライセンス", expanded=False):
            st.text_input(
                "ライセンスキー",
                type="password",
                key="license_key_input",
                placeholder="XXXX-XXXX-XXXX",
            )
            if st.button("適用", key="license_apply_btn", use_container_width=True):
                if has_pro():
                    st.success("Pro が有効になりました")
                    st.rerun()
                else:
                    st.error("キーが無効です")
            cfg = _billing_cfg()
            if cfg.get("stripe_payment_link"):
                st.link_button("💳 Pro に加入", cfg["stripe_payment_link"], use_container_width=True)
