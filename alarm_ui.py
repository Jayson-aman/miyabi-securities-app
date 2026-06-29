"""
ブラウザアラーム — 大和証券風お知らせバー + ビープ音
"""

from __future__ import annotations

import hashlib
import streamlit as st
import streamlit.components.v1 as components

from daiwa_margin_alerts import STATUS_LABELS, thresholds_for_loss_cut_base


def _alarm_fingerprint(events: list[dict]) -> str:
    raw = "|".join(sorted(e.get("id", e.get("message", "")) for e in events))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def play_alarm_sound(severity: int = 2) -> None:
    """Web Audio API でビープ（ユーザー操作後のページ内で鳴る）。"""
    repeats = 1 if severity <= 1 else 2 if severity == 2 else 3
    freq = 660 if severity <= 1 else 880 if severity == 2 else 1100
    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var Ctx = window.AudioContext || window.webkitAudioContext;
                if (!Ctx) return;
                var ctx = new Ctx();
                function beep(i) {{
                    var o = ctx.createOscillator();
                    var g = ctx.createGain();
                    o.type = 'square';
                    o.frequency.value = {freq};
                    g.gain.value = 0.08;
                    o.connect(g);
                    g.connect(ctx.destination);
                    o.start(ctx.currentTime + i * 0.35);
                    o.stop(ctx.currentTime + i * 0.35 + 0.25);
                }}
                for (var i = 0; i < {repeats}; i++) beep(i);
            }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
    )


def render_daiwa_notice_bar(metrics: list[dict] | None) -> None:
    """取引画面「お知らせ欄」風ステータスバー。"""
    if not metrics:
        return
    m = metrics[0]
    status = m.get("status", "normal")
    label, color, bg = STATUS_LABELS.get(status, STATUS_LABELS["normal"])
    th = m.get("thresholds") or thresholds_for_loss_cut_base(100)
    st.markdown(
        f"""
        <div style="background:{bg};border-left:5px solid {color};padding:10px 14px;
            border-radius:4px;margin:8px 0;font-size:0.85rem;line-height:1.5;">
            <b style="color:{color};">大和証券FXルール参考（検討用）— {label}</b><br>
            {m.get('label', '')} ｜ 維持率 <b>{m.get('margin_ratio_pct', 0):.1f}%</b>
            ｜ プレアラート &lt; {th['pre_alert']:.0f}% ｜ アラート &lt; {th['alert']:.0f}%
            ｜ ロスカット &lt; {th['loss_cut']:.0f}%
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_alarm_events(events: list[dict], *, play_sound: bool = True) -> None:
    if not events:
        return

    fp = _alarm_fingerprint(events)
    prev = st.session_state.get("_alarm_fp")
    is_new = fp != prev
    if is_new:
        st.session_state["_alarm_fp"] = fp

    max_sev = max(e.get("severity", 1) for e in events)

    st.markdown(
        f"""
        <div style="background:linear-gradient(90deg,#8B0000 0%,#D32030 100%);color:#fff;
            padding:12px 16px;border-radius:4px;margin-bottom:8px;border:2px solid #ffd166;">
            <div style="font-weight:700;font-size:1rem;">🔔 アラーム発火（{len(events)}件）</div>
            <div style="font-size:0.75rem;opacity:0.9;margin-top:4px;">
                大和証券FXの証拠金通知ルールを参考にした検討用アラートです
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for e in events:
        sev = e.get("severity", 1)
        if sev >= 3:
            st.error(e["message"])
        elif sev >= 2:
            st.warning(e["message"])
        else:
            st.info(e["message"])

    if play_sound and is_new and st.session_state.get("alarm_sound_enabled", True):
        play_alarm_sound(max_sev)


def render_alarm_settings_sidebar() -> None:
    st.session_state.setdefault("alarm_sound_enabled", True)
    st.session_state.setdefault("daiwa_alert_cooldown_min", 15)
    with st.expander("🔔 アラーム設定", expanded=False):
        st.checkbox("アラーム音を鳴らす", key="alarm_sound_enabled")
        st.number_input(
            "同一通知のクールダウン（分）",
            min_value=1,
            max_value=120,
            key="daiwa_alert_cooldown_min",
        )
        st.caption(
            "参考: ダイワFX — ロスカット基準100%時 "
            "プレアラート160% / アラート130% / ロスカット100%"
        )
