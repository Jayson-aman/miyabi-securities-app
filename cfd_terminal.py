"""
FX/CFD ブローカー風ターミナル（検討用・シミュレーションのみ）

GMO 等の取引画面を「参考にした」レイアウト。公式UIの複製ではない。
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from brand import APP_NAME
from data_fetcher import fetch_market_data, get_latest_price
from fx_simulator import JAPAN_LEVERAGE, LOT_SIZE, SWAP_POINTS, simulate_trade
from interval_predictor import predict_intervals
from daiwa_margin_alerts import (
    check_all_daiwa_alerts,
    clear_virtual_positions,
    get_virtual_positions,
    set_virtual_position,
    compute_position_metrics,
)
from alarm_ui import render_daiwa_notice_bar
from candlestick_guide import render_candlestick_guide, analyze_live_candle_hint

TERMINAL_SYMBOLS = {
    "USDJPY=X": {"label": "USD/JPY", "type": "FX", "pip": 0.01},
    "EURJPY=X": {"label": "EUR/JPY", "type": "FX", "pip": 0.01},
    "GBPJPY=X": {"label": "GBP/JPY", "type": "FX", "pip": 0.01},
    "AUDJPY=X": {"label": "AUD/JPY", "type": "FX", "pip": 0.01},
    "CL=F": {"label": "WTI原油", "type": "CFD", "pip": 0.01},
    "BZ=F": {"label": "ブレント", "type": "CFD", "pip": 0.01},
    "GC=F": {"label": "金", "type": "CFD", "pip": 0.1},
}


def broker_terminal_css() -> str:
    return """
<style>
    /* ブローカーターミナル風（検討用） */
    .broker-shell {
        background: #0f1419;
        border: 1px solid #2a3f5f;
        border-radius: 6px;
        padding: 0;
        margin-bottom: 12px;
        overflow: hidden;
    }
    .broker-topbar {
        background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%);
        color: #e8f1ff;
        padding: 8px 14px;
        font-size: 0.78rem;
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        border-bottom: 2px solid #0066cc;
    }
    .broker-topbar b { color: #7ec8ff; }
    .broker-quote-row {
        display: flex;
        gap: 6px;
        padding: 8px 10px;
        background: #141b24;
        border-bottom: 1px solid #243044;
        font-family: ui-monospace, monospace;
        font-size: 0.82rem;
    }
    .broker-bid {
        flex: 1; background: #1a2838; color: #6bb6ff;
        padding: 8px; text-align: center; border-radius: 3px;
        border: 1px solid #2a5080;
    }
    .broker-ask {
        flex: 1; background: #1a2838; color: #ff8a80;
        padding: 8px; text-align: center; border-radius: 3px;
        border: 1px solid #804040;
    }
    .broker-spread {
        flex: 0.6; background: #1a1f28; color: #ffd166;
        padding: 8px; text-align: center; border-radius: 3px;
        font-size: 0.75rem;
    }
    .broker-disclaimer {
        background: #1a1508;
        border-top: 1px solid #665500;
        color: #c9a227;
        padding: 8px 12px;
        font-size: 0.72rem;
        line-height: 1.5;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #eef3f9 0%, #dde8f4 100%) !important;
    }
    .main .block-container {
        background: #f0f4f8;
    }
</style>
"""


def _quote_block(ticker: str, meta: dict) -> tuple[float, float, float]:
    info = get_latest_price(ticker)
    pred = predict_intervals(ticker, steps=1)
    spread = 0.003 if meta["type"] == "FX" else 0.04
    if pred:
        bid = float(pred["current_bid"])
        ask = float(pred["current_ask"])
        spread = ask - bid
    elif info:
        mid = float(info["price"])
        bid = mid - spread / 2
        ask = mid + spread / 2
    else:
        bid = ask = 0.0
    return bid, ask, spread


def _fmt_quote(value: float, meta: dict) -> str:
    """FXは3桁、CFDは2桁表示"""
    return f"{value:.3f}" if meta.get("type") == "FX" else f"{value:.2f}"


def _chart(ticker: str, label: str, height: int = 340) -> pd.DataFrame | None:
    df = fetch_market_data(ticker, period="2d", interval="5m")
    if df is None or df.empty:
        st.caption(f"{label}: チャートなし")
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["日時"],
            open=df["始値"],
            high=df["高値"],
            low=df["安値"],
            close=df["終値"],
            increasing_line_color="#ef5350",
            decreasing_line_color="#42a5f5",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=4, t=28, b=4),
        title=dict(text=label, font=dict(size=12, color="#5eb3ff")),
        paper_bgcolor="#0f1419",
        plot_bgcolor="#141b24",
        xaxis=dict(showgrid=False, color="#8899aa"),
        yaxis=dict(showgrid=True, gridcolor="#243044", color="#8899aa"),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    return df


def render_cfd_terminal() -> None:
    st.markdown(broker_terminal_css(), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="broker-shell">
          <div class="broker-topbar">
            <span><b>{APP_NAME}</b> — FX/CFD Research Terminal</span>
            <span>口座: <b>デモ（検討用）</b></span>
            <span>証拠金: <b>¥300,000</b>（仮想）</span>
            <span>維持率: <b>—</b></span>
            <span>{datetime.now().strftime("%Y/%m/%d %H:%M:%S")} JST</span>
          </div>
          <div class="broker-disclaimer">
            ⚠ <b>シミュレーション専用</b> — GMOクリック証券・大和証券等の<b>公式アプリではありません</b>（提携・後援なし）。
            口座開設・入金・実注文はできません。表示は研究・学習目的のみ。投資助言ではありません。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sym_keys = list(TERMINAL_SYMBOLS.keys())
    labels = [TERMINAL_SYMBOLS[k]["label"] for k in sym_keys]
    stored = st.session_state.get("cfd_symbol", "USDJPY=X")
    idx = sym_keys.index(stored) if stored in sym_keys else 0

    col_list, col_main, col_order = st.columns([1.1, 2.2, 1])

    with col_list:
        st.markdown("**銘柄リスト**")
        selected_label = st.radio(
            "銘柄",
            labels,
            index=idx,
            label_visibility="collapsed",
            key="cfd_symbol_radio",
        )
        ticker = sym_keys[labels.index(selected_label)]
        st.session_state["cfd_symbol"] = ticker
        meta = TERMINAL_SYMBOLS[ticker]

        rows = []
        for tk, m in TERMINAL_SYMBOLS.items():
            info = get_latest_price(tk)
            ch = f"{info['change_pct']:+.2f}%" if info else "—"
            rows.append({"銘柄": m["label"], "種別": m["type"], "変動": ch})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=220)

    bid, ask, spread = _quote_block(ticker, meta)
    bid_s, ask_s, spread_s = _fmt_quote(bid, meta), _fmt_quote(ask, meta), _fmt_quote(spread, meta)

    with col_main:
        st.markdown(
            f"""
            <div class="broker-quote-row">
              <div class="broker-bid">SELL / Bid<br><span style="font-size:1.2rem;font-weight:700;">{bid_s}</span></div>
              <div class="broker-spread">Spread<br>{spread_s}</div>
              <div class="broker-ask">BUY / Ask<br><span style="font-size:1.2rem;font-weight:700;">{ask_s}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        chart_df = _chart(ticker, meta["label"])

        # 直近足の利確ヒント（日足優先、なければ5分足）
        hint_df = None
        daily_df = fetch_market_data(ticker, period="1mo", interval="1d")
        if daily_df is not None and not daily_df.empty and len(daily_df) >= 10:
            hint_df = daily_df
        elif chart_df is not None and not chart_df.empty and len(chart_df) >= 10:
            hint_df = chart_df
        if hint_df is not None and len(hint_df) >= 10:
            hint = analyze_live_candle_hint(hint_df, meta["label"])
            if hint.get("ok"):
                st.markdown(
                    f"**📖 ローソク読み** {hint['urgency']} "
                    f"｜ {hint['candle_label']}（実体{hint['body_pct']}%）"
                    f"｜ 高値−{hint['dist_high_pct']}% / 安値+{hint['dist_low_pct']}%"
                )
                for a in hint["actions"][:2]:
                    st.caption(f"💡 {a}")

        with st.expander("📖 ローソク足の読み方・利確表（詳細）", expanded=False):
            render_candlestick_guide(live_df=hint_df, symbol=meta["label"], key_prefix=f"cfd_{ticker}")

        pred = predict_intervals(ticker, steps=4)
        if pred:
            iv_rows = [
                {
                    "時間": x["time_offset"],
                    "Bid": x["bid"],
                    "Ask": x["ask"],
                    "方向": x["direction"],
                }
                for x in pred["intervals"]
            ]
            st.markdown("**15分刻み AI予測（参考）**")
            st.dataframe(pd.DataFrame(iv_rows), use_container_width=True, hide_index=True)

    with col_order:
        st.markdown("**注文パネル（仮想）**")
        side = st.radio("売買", ["買い", "売り"], horizontal=True, key="cfd_side")
        lots = st.number_input("ロット", 0.1, 50.0, 1.0, 0.1, key="cfd_lots")
        capital = st.number_input("想定資金(円)", 10000, 50_000_000, 300_000, 10000, key="cfd_cap")

        swap = SWAP_POINTS.get(ticker, {})
        if swap:
            sw = swap["buy"] if side == "買い" else swap["sell"]
            st.caption(f"参考スワップ: {sw:+.0f} 円/万通貨/日")

        st.caption(f"レバレッジ上限 {JAPAN_LEVERAGE}倍 / 1Lot={LOT_SIZE:,}通貨")

        if st.button("仮想注文をシミュレート", type="primary", use_container_width=True, key="cfd_sim_btn"):
            side_code = "buy" if side == "買い" else "sell"
            if ticker not in SWAP_POINTS and meta["type"] == "FX":
                st.warning("この銘柄のFXシミュレーション定義がありません")
            elif ticker in SWAP_POINTS:
                r = simulate_trade(ticker, side_code, None, lots, capital, JAPAN_LEVERAGE, None, None, 1)
                if "error" in r:
                    st.error(r["error"])
                else:
                    set_virtual_position({
                        "ticker": ticker,
                        "label": meta["label"],
                        "side": side_code,
                        "lots": lots,
                        "entry_price": r["entry_price"],
                        "capital": capital,
                        "margin_required": r["margin_required"],
                        "leverage": JAPAN_LEVERAGE,
                        "loss_cut_base_pct": 100.0,
                    })
                    st.success(f"仮想約定 @ {r['entry_price']:.4f}")
                    st.metric("必要証拠金", f"¥{r['margin_required']:,.0f}")
                    st.metric("ロスカット目安", f"{r['loss_cut_price']:.4f}")
            else:
                st.info("CFDはチャート・予測のみ（損益シミュはFXペア中心）")

        metrics_list = [compute_position_metrics(p) for p in get_virtual_positions()]
        metrics_list = [m for m in metrics_list if m]
        if metrics_list:
            render_daiwa_notice_bar(metrics_list)

        st.markdown("---")
        st.markdown("**建玉（デモ）**")
        if get_virtual_positions():
            for m in metrics_list:
                st.caption(
                    f"{m['label']} {m['side']} {m['lots']}Lot "
                    f"｜ 維持率 {m['margin_ratio_pct']:.1f}% ｜ 含み {m['unrealized_pnl']:+,.0f}円"
                )
            if st.button("建玉をクリア", key="cfd_clear_pos"):
                clear_virtual_positions()
                st.rerun()
        else:
            st.caption("仮想注文を実行すると、大和証券FXルール参考の維持率アラートが有効になります")
