"""
3画面モニター向けパネル — FX / 石油・商品 / ドル関連を同時表示
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_fetcher import fetch_market_data, get_latest_price

# 各物理モニター用パネル定義
PANELS = {
    "fx": {
        "title": "💴 為替（円クロス中心）",
        "subtitle": "USD/JPY · EUR/JPY · GBP/JPY · AUD/JPY",
        "tickers": [
            ("USDJPY=X", "USD/JPY"),
            ("EURJPY=X", "EUR/JPY"),
            ("GBPJPY=X", "GBP/JPY"),
            ("AUDJPY=X", "AUD/JPY"),
        ],
        "chart_ticker": "USDJPY=X",
        "chart_label": "USD/JPY",
        "table_category": "FX",
    },
    "oil": {
        "title": "🛢 石油・エネルギー・貴金属",
        "subtitle": "WTI · ブレント · 天然ガス · 金 · 銀",
        "tickers": [
            ("CL=F", "WTI原油"),
            ("BZ=F", "ブレント"),
            ("NG=F", "天然ガス"),
            ("GC=F", "金"),
            ("SI=F", "銀"),
        ],
        "chart_ticker": "CL=F",
        "chart_label": "WTI原油",
        "table_category": "原油・商品CFD",
    },
    "dollar": {
        "title": "💵 ドル・指数・主要指数",
        "subtitle": "EUR/USD · GBP/USD · DXY · 日経 · S&P",
        "tickers": [
            ("EURUSD=X", "EUR/USD"),
            ("GBPUSD=X", "GBP/USD"),
            ("DX-Y.NYB", "DXY"),
            ("^N225", "日経225"),
            ("^GSPC", "S&P500"),
            ("^VIX", "VIX"),
        ],
        "chart_ticker": "EURUSD=X",
        "chart_label": "EUR/USD",
        "table_category": "FX",
    },
}


def _price_cards(tickers: list[tuple[str, str]]) -> None:
    cols = st.columns(min(len(tickers), 3))
    for i, (tk, label) in enumerate(tickers):
        with cols[i % len(cols)]:
            info = get_latest_price(tk)
            if not info:
                st.metric(label, "—")
                continue
            sign = info["change_pct"]
            st.metric(
                label,
                f"{info['price']:,.3f}" if info["price"] < 1000 else f"{info['price']:,.2f}",
                f"{info['change']:+.3f} ({sign:+.2f}%)",
                delta_color="normal" if sign >= 0 else "inverse",
            )


def _mini_chart(ticker: str, label: str, height: int = 220) -> None:
    df = fetch_market_data(ticker, period="2d", interval="15m")
    if df is None or df.empty:
        st.caption(f"{label}: チャート取得不可")
        return
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["日時"],
            y=df["終値"],
            mode="lines",
            line=dict(color="#0B3D91", width=2),
            name=label,
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=24, b=8),
        title=dict(text=label, font=dict(size=13, color="#0B3D91")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FAFBFD",
        xaxis=dict(showgrid=False, tickformat="%m/%d %H:%M"),
        yaxis=dict(showgrid=True, gridcolor="#E9EFF7"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _prediction_table(
    compact_tables: dict[str, pd.DataFrame],
    category: str,
    labels: Optional[list[str]] = None,
) -> None:
    df = compact_tables.get(category)
    if df is None or df.empty:
        st.caption("予測テーブルなし")
        return
    if labels:
        mask = df.iloc[:, 0].astype(str).isin(labels) if len(df.columns) else None
        if mask is not None and mask.any():
            df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(220, 48 + len(df) * 32))


def render_panel(
    panel_key: str,
    compact_tables: dict[str, Any],
    *,
    show_chart: bool = True,
    show_predictions: bool = True,
) -> None:
    cfg = PANELS[panel_key]
    st.markdown(
        f"""
        <div class="monitor-panel-head">
            <div class="monitor-panel-title">{cfg['title']}</div>
            <div class="monitor-panel-sub">{cfg['subtitle']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _price_cards(cfg["tickers"])
    if show_chart:
        _mini_chart(cfg["chart_ticker"], cfg["chart_label"])
    if show_predictions and compact_tables:
        labels = [lb for _, lb in cfg["tickers"] if lb in ("USD/JPY", "EUR/JPY", "WTI原油", "ブレント", "EUR/USD", "GBP/USD")]
        st.markdown("**15分・60分先 予測（コンパクト）**")
        _prediction_table(compact_tables, cfg["table_category"], labels or None)


def render_tri_monitor(
    compact_tables: dict[str, Any],
    panel_filter: str = "all",
) -> None:
    """
    panel_filter: all | fx | oil | dollar
    """
    if panel_filter == "all":
        c1, c2, c3 = st.columns(3)
        with c1:
            render_panel("fx", compact_tables)
        with c2:
            render_panel("oil", compact_tables)
        with c3:
            render_panel("dollar", compact_tables)
    elif panel_filter in PANELS:
        render_panel(panel_filter, compact_tables, show_chart=True)
    else:
        st.warning(f"不明な panel 指定: {panel_filter}")
