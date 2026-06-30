"""
大和証券の公開メニュー構成を参考にした「取扱検討株式・市場情報」ボード。

- Zaibase.Economic Research 向けの学習・検討UI
- 最新1分足データを基にランキングを生成（参考値）
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from data_fetcher import fetch_market_data


SAPPHIRE = "#0F52BA"
SAPPHIRE_DARK = "#0B3A8C"
GOLD = "#C9A961"


JP_PRIME_TICKERS: list[tuple[str, str]] = [
    ("トヨタ自動車", "7203.T"),
    ("ソニーグループ", "6758.T"),
    ("東京エレクトロン", "8035.T"),
    ("ソフトバンクG", "9984.T"),
    ("三菱UFJ", "8306.T"),
    ("ファーストリテイリング", "9983.T"),
    ("任天堂", "7974.T"),
    ("日立製作所", "6501.T"),
    ("三菱商事", "8058.T"),
    ("日本製鉄", "5401.T"),
]

JP_STANDARD_TICKERS: list[tuple[str, str]] = [
    ("北川精機", "6327.T"),
    ("技研製作所", "6289.T"),
    ("サクサ", "6675.T"),
    ("ランド", "8918.T"),
    ("リード", "6982.T"),
    ("北日本紡績", "3409.T"),
    ("フルサト・マルカ", "7128.T"),
    ("伊勢化学工業", "4107.T"),
]

US_CORE_TICKERS: list[tuple[str, str]] = [
    ("Apple", "AAPL"),
    ("Microsoft", "MSFT"),
    ("NVIDIA", "NVDA"),
    ("Amazon", "AMZN"),
    ("Google", "GOOGL"),
    ("Meta", "META"),
]

INDEX_TICKERS: list[tuple[str, str]] = [
    ("日経平均", "^N225"),
    ("TOPIX", "^TPX"),
    ("NYダウ", "^DJI"),
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
]


PRODUCT_ROWS = [
    ["国内株式", "IPO", "PO", "米国株式"],
    ["中国株式", "投資信託", "債券", "円預金"],
    ["外貨預金", "ロボアドバイザー", "ラップ口座", "FX"],
    ["年金・保険", "証券担保ローン", "セキュリティ・トークン", "その他"],
]

MARKET_INFO_BLOCKS = {
    "検索": ["国内株式検索", "米国株式検索", "株主優待検索", "ファンド検索"],
    "お気に入りリスト": ["国内株式", "米国株式", "投資信託"],
    "ランキング": ["国内株式ランキング", "米国株式ランキング", "株主優待ランキング", "投資信託ランキング"],
    "マーケットお役立ち情報": ["指数一覧", "適時開示情報", "株talk", "投信情報通知サービス"],
}

CREDIT_SERVICE_ITEMS = [
    "外国株式",
    "IPO（新規公開株式）",
    "PO（公募・売出株式）",
    "ETF（上場投資信託）",
    "ETN（指標連動証券）",
    "REIT（不動産投資信託）",
    "るいとう（株式累積投資）",
]

RANK_TABS = [
    ("売買代金上位", "売買代金(百万円)", False),
    ("出来高上位", "出来高(株)", False),
    ("値上がり率ランキング", "騰落率(%)", False),
    ("値下がり率ランキング", "騰落率(%)", True),
    ("値上がり幅ランキング", "値幅(円)", False),
    ("値下がり幅ランキング", "値幅(円)", True),
]


def _display_ticker_name_map(pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    return {ticker: name for name, ticker in pairs}


@st.cache_data(ttl=55)
def _download_minute_snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    """
    1分足スナップショットをまとめて取得。
    ttl=55秒でキャッシュし、ほぼ1分刻みで最新化。
    """
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(
            tickers=list(tickers),
            period="1d",
            interval="1m",
            auto_adjust=False,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()
    if data is None or data.empty:
        return pd.DataFrame()
    return data


def _extract_single_ticker_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if ticker not in raw.columns.get_level_values(0):
            return pd.DataFrame()
        part = raw[ticker].copy()
    else:
        part = raw.copy()

    part = part.dropna(subset=["Close"], how="any")
    if part.empty:
        return pd.DataFrame()
    return part


def _build_live_rows(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    ticker_to_name = _display_ticker_name_map(pairs)
    tickers = tuple(t for _, t in pairs)
    raw = _download_minute_snapshot(tickers)
    rows: list[dict] = []

    for ticker in tickers:
        frame = _extract_single_ticker_frame(raw, ticker)
        if len(frame) < 2:
            continue

        close = frame["Close"].astype(float)
        volume = frame["Volume"].fillna(0).astype(float) if "Volume" in frame.columns else pd.Series([0] * len(frame))
        price = float(close.iloc[-1])
        prev_1m = float(close.iloc[-2])
        open_day = float(close.iloc[0])
        vol_latest = float(volume.iloc[-1]) if len(volume) else 0.0
        vol_sum = float(volume.sum()) if len(volume) else 0.0

        one_min_pct = (price / prev_1m - 1) * 100 if prev_1m else 0.0
        day_pct = (price / open_day - 1) * 100 if open_day else 0.0

        rows.append(
            {
                "銘柄": ticker_to_name[ticker],
                "ティッカー": ticker,
                "現在値": round(price, 4),
                "1分前": round(prev_1m, 4),
                "1分変化(%)": round(one_min_pct, 3),
                "騰落率(%)": round(day_pct, 3),
                "出来高(株)": int(vol_sum),
                "直近出来高(株)": int(vol_latest),
                "売買代金(百万円)": round((price * vol_sum) / 1_000_000, 2),
                "値幅(円)": round(price - prev_1m, 4),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _rank_table(source: pd.DataFrame, sort_col: str, ascending: bool, top_n: int = 10) -> pd.DataFrame:
    if source is None or source.empty or sort_col not in source.columns:
        return pd.DataFrame()
    ranked = source.sort_values(sort_col, ascending=ascending).head(top_n).copy()
    ranked.insert(0, "順位", range(1, len(ranked) + 1))
    return ranked


def _render_minute_chart(ticker: str, label: str) -> None:
    df = fetch_market_data(ticker, period="1d", interval="1m")
    if df is None or df.empty:
        st.info(f"{label} の1分足データを取得できませんでした。")
        return

    df = df.tail(120).copy()
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["日時"],
            open=df["始値"],
            high=df["高値"],
            low=df["安値"],
            close=df["終値"],
            increasing_line_color="#D32030",
            decreasing_line_color=SAPPHIRE,
            name="1分足",
        )
    )
    fig.update_layout(
        title=f"{label}（最新1分足）",
        height=350,
        margin=dict(l=4, r=4, t=32, b=4),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FBFF",
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_market_info_grid() -> None:
    cols = st.columns(2)
    keys = list(MARKET_INFO_BLOCKS.keys())
    for i, key in enumerate(keys):
        with cols[i % 2]:
            st.markdown(
                f"""
<div style="background:linear-gradient(180deg,#F7FAFF 0%,#EDF4FF 100%);
            border:1px solid #D4E1F5;border-left:4px solid {SAPPHIRE};
            border-radius:4px;padding:10px 12px;margin-bottom:10px;">
  <div style="font-weight:700;color:{SAPPHIRE_DARK};margin-bottom:6px;">{key}</div>
  <div style="font-size:0.84rem;line-height:1.7;color:#334155;">
    {" / ".join(MARKET_INFO_BLOCKS[key])}
  </div>
</div>
                """,
                unsafe_allow_html=True,
            )


def render_daiwa_market_board() -> None:
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,{SAPPHIRE} 0%,{SAPPHIRE_DARK} 100%);
            color:#fff;border:1px solid {GOLD};border-radius:6px;padding:14px 16px;margin-bottom:10px;">
  <div style="font-size:1.05rem;font-weight:700;letter-spacing:0.5px;">
    🏛 取扱検討株式・市場情報（Zaibase Sapphire Board）
  </div>
  <div style="font-size:0.82rem;opacity:0.92;margin-top:4px;line-height:1.5;">
    添付画像にある「取扱商品」「市場情報」「ランキング」「信用取引サービス」を網羅し、
    1分足ベースの最新データで表示します（学習・検討用）。
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} JST（1分足データ）")

    tab_products, tab_market, tab_rank, tab_watch = st.tabs(
        ["📦 取扱商品一覧", "📊 マーケット情報", "🏆 国内株式ランキング", "⏱ 1分足ウォッチ"]
    )

    with tab_products:
        st.markdown("#### 取扱商品一覧（検討カテゴリ）")
        st.dataframe(
            pd.DataFrame(PRODUCT_ROWS, columns=["区分1", "区分2", "区分3", "区分4"]),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("#### 信用取引サービス（参考）")
        st.dataframe(pd.DataFrame({"サービス": CREDIT_SERVICE_ITEMS}), use_container_width=True, hide_index=True)

    with tab_market:
        st.markdown("#### マーケット情報トップ（構成）")
        _render_market_info_grid()
        st.info(
            "検索・お気に入り・ランキング・お役立ち情報の4ブロックを搭載。"
            "実データ連携は下のランキング/ウォッチタブで1分足反映します。"
        )

    with tab_rank:
        prime_df = _build_live_rows(JP_PRIME_TICKERS)
        standard_df = _build_live_rows(JP_STANDARD_TICKERS)

        ptab, stab = st.tabs(["東証プライム（参考）", "東証スタンダード（参考）"])

        def _render_rank_tabs(base_df: pd.DataFrame, key_prefix: str) -> None:
            if base_df.empty:
                st.warning("1分データを取得できませんでした。時間をおいて再読み込みしてください。")
                return
            r_tabs = st.tabs([name for name, _, _ in RANK_TABS])
            for t, (name, metric, asc) in zip(r_tabs, RANK_TABS):
                with t:
                    table = _rank_table(base_df, metric, asc, top_n=10)
                    st.dataframe(table, use_container_width=True, hide_index=True)
                    st.caption(f"{metric} で並び替え（{datetime.now().strftime('%H:%M:%S')}時点）")

        with ptab:
            _render_rank_tabs(prime_df, "prime")
        with stab:
            _render_rank_tabs(standard_df, "std")

    with tab_watch:
        all_watch = JP_PRIME_TICKERS[:6] + JP_STANDARD_TICKERS[:4] + US_CORE_TICKERS[:4] + INDEX_TICKERS
        names = [name for name, _ in all_watch]
        tickers = [ticker for _, ticker in all_watch]
        selected = st.selectbox("銘柄を選択（1分足）", names, index=0, key="sapphire_watch_symbol")
        ticker = tickers[names.index(selected)]
        _render_minute_chart(ticker, selected)

        snap_df = _build_live_rows(all_watch)
        if not snap_df.empty:
            show_cols = ["銘柄", "現在値", "1分変化(%)", "騰落率(%)", "直近出来高(株)"]
            st.markdown("#### 最新スナップショット（1分）")
            st.dataframe(snap_df[show_cols], use_container_width=True, hide_index=True)
