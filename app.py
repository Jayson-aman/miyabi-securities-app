"""
原油先物予測ダッシュボード
世界情勢のニュース分析 + テクニカル分析で原油先物の価格方向を予測する
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

from brand import (
    APP_NAME,
    APP_SHORT,
    APP_BRAND_SUFFIX,
    APP_LOGO_LETTER,
    APP_TAGLINE,
    APP_SUBTITLE,
    APP_PAGE_TITLE,
    APP_PWA_TITLE,
    APP_MENU_LABEL,
    APP_FOOTER_LINE1,
    APP_FOOTER_LINE2,
    APP_FOOTER_COPY,
    APP_DISCLAIMER,
)

from data_fetcher import (
    FUTURES_SYMBOLS,
    CURRENCY_PAIRS,
    STOCK_INDICES,
    JP_STOCKS,
    US_STOCKS,
    OVERSEAS_STOCKS,
    BOND_SYMBOLS,
    CRYPTO_SYMBOLS,
    COMMODITIES,
    INTERVAL_OPTIONS,
    PERIOD_OPTIONS,
    fetch_market_data,
    get_latest_price,
    calculate_technical_indicators,
)
from news_fetcher import fetch_and_analyze_all, SEARCH_QUERIES, fetch_news, analyze_sentiment
from predictor import train_and_predict
from yen_predictor import predict_yen_peaks
from economic_calendar import fetch_economic_news, get_summary
from person_profiles import PROFILES, get_profile_summary_for_display
from military_monitor import fetch_military_news, get_military_summary
from stock_screener import (
    scan_all_stocks,
    get_top_movers,
    predict_stock_1min,
    predict_multi_horizon_path,
    predict_stock_midlong_range,
)
from emerging_stocks import (
    EMERGING_STOCKS,
    analyze_emerging_stock,
    scan_emerging_by_theme,
    scan_all_emerging,
)
from alert_engine import (
    load_alerts,
    add_alert,
    delete_alert,
    toggle_alert,
    check_all_alerts,
    load_alert_log,
    clear_alert_log,
    ALERT_TYPES,
    ALERT_TYPE_DETAILS,
    get_alert_preview,
)
from backtester import run_backtest, compare_strategies, STRATEGIES
from yen_factors import (
    analyze_all_factors,
    get_intervention_warning,
    calc_us_jp_yield_spread,
    GEOPOLITICAL_RISKS,
    INTERVENTION_LEVELS,
)
from event_schedule import (
    get_upcoming_events,
    get_critical_events_today_tomorrow,
    KEY_PERSON_SCHEDULE,
)
from reversal_predictor import predict_reversal
from fx_simulator import (
    SWAP_POINTS,
    JAPAN_LEVERAGE,
    LOT_SIZE,
    simulate_trade,
    backtest_simulation,
    get_swap_yield_table,
    calc_margin_required,
    calc_loss_cut_price,
)
from intervention_alerts import (
    get_intervention_table,
    get_intervention_levels_table,
    get_intervention_time_table,
)
from index_futures_predictor import (
    INDEX_FUTURES,
    analyze_index_future,
    scan_all_index_futures,
)
from interval_predictor import (
    INTERVAL_TARGETS,
    predict_intervals,
    predict_all_intervals_table,
    predict_all_intervals_compact,
    get_all_reasonings,
)
from fx_email_alerts import check_and_send_fx_move_alerts
from monitor_panel import render_tri_monitor
from subscription import billing_enabled, has_pro, require_pro, render_billing_sidebar
from cfd_terminal import render_cfd_terminal
from daiwa_market_board import render_daiwa_market_board
from daiwa_margin_alerts import check_all_daiwa_alerts, thresholds_for_loss_cut_base
from alarm_ui import render_alarm_events, render_alarm_settings_sidebar
from candlestick_guide import render_candlestick_guide
from chart_patterns import (
    analyze_ticker_patterns,
    PATTERN_DETECTORS,
)
from fundamental_screener import (
    analyze_fundamentals,
    batch_screen,
    BUY_MARKET_CAP_MAX_JPY,
    BUY_PER_MIN,
    BUY_PER_MAX,
    BUY_CONSEC_GROWTH_YEARS,
    SELL_PAYOUT_RATIO_MAX,
    SELL_CONSEC_DECLINE_YEARS,
    SELL_PER_MIN,
)

# ─── ページ設定 ───
st.set_page_config(
    page_title=APP_PAGE_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 認証ゲート（この下のコードはログイン後のみ実行） ───
from auth import require_login, render_auth_sidebar, render_preview_banner, render_closed_banner
from legal import require_terms_acceptance, render_legal_banner, render_legal_page, TERMS_VERSION
require_login()
require_terms_acceptance()
render_preview_banner()
render_closed_banner()
render_auth_sidebar()

# URL ?panel=fx|oil|dollar で3画面モニターページを直接開く（物理モニター用）
_qp_panel = (st.query_params.get("panel") or "").strip().lower()
if _qp_panel in ("fx", "oil", "dollar", "all"):
    st.session_state["main_page"] = "🖥 3画面モニター"
    st.session_state["monitor_panel_filter"] = _qp_panel

# ════════════════════════════════════════════════
#  Zaibase.Economic Research デザインシステム
#  - メインカラー: Sapphire Blue #0F52BA / アクセント: #C9A961
# ════════════════════════════════════════════════
st.markdown("""
<style>
    /* ─── 全体ベーススタイル ─── */
    html, body, [class*="css"]  {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", "Times New Roman", -apple-system, "Hiragino Sans", "Yu Gothic", "Meiryo", serif;
    }
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 1rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }
    /* 数字・テキスト系はサンセリフへ */
    [data-testid="stMetric"], .stButton, [data-baseweb="tab"],
    [role="radiogroup"], .market-ticker, .stDataFrame, table {
        font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", "Meiryo", sans-serif !important;
    }

    /* Streamlit ヘッダーを透明に */
    header[data-testid="stHeader"] {
        background: rgba(255,255,255,0.0);
        height: 0px;
    }

    /* ════════════════════════════════════════════════
        Zaibase ヘッダーバー
       ════════════════════════════════════════════════ */
    .miyabi-header {
        background:
            radial-gradient(circle at 15% 100%, rgba(244,214,226,0.15) 0%, transparent 50%),
            radial-gradient(circle at 85% 0%, rgba(201,169,97,0.18) 0%, transparent 55%),
            linear-gradient(135deg, #0F52BA 0%, #0B3A8C 50%, #082A66 100%);
        color: #fff;
        padding: 18px 28px;
        margin: -16px -24px 0 -24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid;
        border-image: linear-gradient(90deg, #C9A961 0%, #F0D580 50%, #C9A961 100%) 1;
        box-shadow: 0 4px 16px rgba(15,82,186,0.25);
        position: relative;
        overflow: hidden;
    }
    .miyabi-header::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            radial-gradient(circle at 92% 80%, rgba(201,169,97,0.12) 0%, transparent 8%),
            radial-gradient(circle at 8% 25%, rgba(244,214,226,0.08) 0%, transparent 10%);
        pointer-events: none;
    }
    .miyabi-header-left {
        display: flex;
        align-items: center;
        gap: 18px;
        position: relative;
        z-index: 1;
    }
    .miyabi-logo {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #FFFFFF;
        background: linear-gradient(135deg, #C9A961 0%, #F0D580 50%, #C9A961 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 30px rgba(201,169,97,0.4);
        padding: 0 8px;
        letter-spacing: 4px;
        border-left: 2px solid #C9A961;
        border-right: 2px solid #C9A961;
        line-height: 1;
    }
    .miyabi-logo-en {
        font-family: "Times New Roman", serif;
        font-size: 0.65rem;
        letter-spacing: 6px;
        color: #C9A961;
        text-align: center;
        margin-top: 2px;
        font-weight: 400;
        font-style: italic;
    }
    .miyabi-title {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
        font-size: 1.15rem;
        font-weight: 600;
        letter-spacing: 3px;
        color: #fff;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .miyabi-title-accent { color: #C9A961; }
    .miyabi-subtitle {
        font-size: 0.72rem;
        opacity: 0.85;
        margin-top: 4px;
        letter-spacing: 1.5px;
        font-family: -apple-system, "Hiragino Sans", sans-serif;
    }
    .miyabi-header-right {
        text-align: right;
        font-size: 0.85rem;
        position: relative;
        z-index: 1;
    }
    .miyabi-time {
        font-size: 1.05rem;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        color: #fff;
        font-family: -apple-system, "Hiragino Sans", sans-serif;
    }
    .miyabi-status {
        display: inline-block;
        padding: 3px 10px;
        background: rgba(201,169,97,0.18);
        border: 1px solid #C9A961;
        border-radius: 2px;
        font-size: 0.7rem;
        margin-left: 8px;
        color: #F0D580;
        letter-spacing: 1px;
        font-family: -apple-system, "Hiragino Sans", sans-serif;
    }

    /* ─── 市況ティッカーバー（ネイビー＋ゴールド罫線） ─── */
    .market-ticker {
        background: linear-gradient(180deg, #1A2238 0%, #0F1830 100%);
        color: #fff;
        padding: 9px 16px;
        margin: 0 -24px 14px -24px;
        font-size: 0.82rem;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        overflow-x: auto;
        border-bottom: 2px solid #C9A961;
        border-top: 1px solid rgba(201,169,97,0.3);
    }
    .ticker-item {
        display: inline-block;
        margin-right: 22px;
        padding-right: 22px;
        border-right: 1px solid rgba(201,169,97,0.25);
    }
    .ticker-name { color: #C9A961; margin-right: 6px; font-size: 0.76rem; letter-spacing: 0.5px; }
    .ticker-value { color: #fff; font-weight: 600; }
    .ticker-up { color: #FF6B6B; font-weight: 600; margin-left: 4px; }
    .ticker-down { color: #6BB6FF; font-weight: 600; margin-left: 4px; }

    /* ════════════════════════════════════════════════
        タイポグラフィ
       ════════════════════════════════════════════════ */
    h1 {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif !important;
        color: #0B3D91;
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        border-left: 5px solid;
        border-image: linear-gradient(180deg, #C9A961 0%, #0B3D91 100%) 1;
        padding-left: 14px !important;
        margin: 14px 0 6px 0 !important;
        letter-spacing: 1.5px;
    }
    h2 {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif !important;
        color: #1A2238;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        border-bottom: 2px solid;
        border-image: linear-gradient(90deg, #0B3D91 0%, #C9A961 50%, transparent 100%) 1;
        padding-bottom: 8px !important;
        margin: 22px 0 14px 0 !important;
        letter-spacing: 1px;
    }
    h3 {
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif !important;
        color: #0B3D91;
        font-size: 1rem !important;
        font-weight: 700 !important;
        margin: 16px 0 8px 0 !important;
        letter-spacing: 0.5px;
    }
    h3::before {
        content: "❖ ";
        color: #C9A961;
    }
    h4 {
        color: #1A2238;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        margin: 12px 0 6px 0 !important;
    }

    /* ─── メトリック（株価カード）── 高級感 ─── */
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #fff 0%, #FAFBFD 100%);
        border: 1px solid #D5DDE8;
        border-left: 4px solid #0B3D91;
        padding: 12px 16px;
        border-radius: 4px;
        box-shadow: 0 2px 6px rgba(11,61,145,0.06), 0 1px 0 rgba(201,169,97,0.15) inset;
        position: relative;
    }
    [data-testid="stMetric"]::before {
        content: "";
        position: absolute;
        top: 0; right: 0;
        width: 14px; height: 14px;
        background: linear-gradient(135deg, transparent 50%, #C9A961 50%);
        opacity: 0.6;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        color: #4A5568 !important;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-weight: 700 !important;
        color: #1A2238 !important;
        font-variant-numeric: tabular-nums;
        font-family: -apple-system, "Hiragino Sans", sans-serif !important;
    }

    /* ════════════════════════════════════════════════
        サイドバー
       ════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F4F7FB 0%, #E9EFF7 100%);
        border-right: 2px solid;
        border-image: linear-gradient(180deg, #C9A961 0%, transparent 100%) 1;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: #0B3D91;
        border: none !important;
        padding-left: 0 !important;
    }
    [data-testid="stSidebar"] h2 {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        margin-top: 12px !important;
    }
    [data-testid="stSidebar"] h3::before { content: ""; }

    /* ラジオを雅風に */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        background: #fff;
        border: 1px solid #D5DDE8;
        padding: 9px 14px;
        margin: 4px 0;
        border-radius: 2px;
        transition: all 0.2s;
        font-size: 0.86rem;
        position: relative;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        border-color: #0B3D91;
        background: #F0F4FB;
        box-shadow: 0 2px 8px rgba(11,61,145,0.1);
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, #0B3D91 0%, #1A4FA8 100%);
        border-color: #C9A961;
        color: #fff;
    }

    /* ════════════════════════════════════════════════
        タブ（ブルー＋ゴールドアクセント）
       ════════════════════════════════════════════════ */
    [data-baseweb="tab-list"] {
        background: linear-gradient(180deg, #F4F7FB 0%, #E9EFF7 100%);
        border-bottom: 2px solid #C9A961;
        padding: 0 4px;
        gap: 2px;
    }
    [data-baseweb="tab"] {
        background: #E1E8F2;
        color: #4A5568;
        border-radius: 4px 4px 0 0;
        padding: 9px 18px !important;
        font-weight: 600;
        font-size: 0.86rem;
        border: 1px solid #D5DDE8;
        border-bottom: none;
        letter-spacing: 0.5px;
    }
    [data-baseweb="tab"]:hover {
        background: #D5DEEC;
        color: #0B3D91;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(180deg, #0B3D91 0%, #1A2D6E 100%);
        color: #fff !important;
        border-top: 2px solid #C9A961;
    }

    /* ════════════════════════════════════════════════
        ボタン（ロイヤルブルー＋ゴールド）
       ════════════════════════════════════════════════ */
    .stButton button {
        background: linear-gradient(180deg, #0B3D91 0%, #0A2E70 100%);
        color: #fff;
        border: 1px solid #C9A961;
        border-radius: 2px;
        padding: 8px 20px;
        font-size: 0.86rem;
        font-weight: 600;
        letter-spacing: 1px;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(11,61,145,0.2);
    }
    .stButton button:hover {
        background: linear-gradient(180deg, #1A4FA8 0%, #0B3D91 100%);
        color: #C9A961;
        border-color: #F0D580;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(11,61,145,0.3);
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(180deg, #C9A961 0%, #A8893F 100%);
        color: #fff;
        border-color: #fff;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(180deg, #D4AF37 0%, #C9A961 100%);
        color: #0B3D91;
    }

    /* ─── データフレーム ─── */
    [data-testid="stDataFrame"] {
        border: 1px solid #D5DDE8;
        border-radius: 3px;
        box-shadow: 0 1px 3px rgba(11,61,145,0.04);
    }

    /* ════════════════════════════════════════════════
        予測ボックス（市場色）
       ════════════════════════════════════════════════ */
    .prediction-box {
        border-radius: 4px;
        padding: 22px;
        text-align: center;
        margin: 8px 0;
        background: #fff;
        border: 1px solid #D5DDE8;
        box-shadow: 0 2px 8px rgba(11,61,145,0.08);
    }
    .pred-up {
        background: linear-gradient(180deg, #FFF5F5 0%, #FFE0E0 100%);
        border: 2px solid #D32030;
    }
    .pred-down {
        background: linear-gradient(180deg, #F0F5FF 0%, #DCE7FF 100%);
        border: 2px solid #1565C0;
    }
    .pred-neutral {
        background: #F4F7FB;
        border: 2px solid #B5BFCE;
    }
    .score-gauge {
        font-size: 2.4rem;
        font-weight: bold;
        margin: 8px 0;
        font-variant-numeric: tabular-nums;
        font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
        letter-spacing: 2px;
    }
    .factor-item {
        background: linear-gradient(90deg, #F4F7FB 0%, #fff 100%);
        border-radius: 2px;
        padding: 9px 14px;
        margin: 4px 0;
        border-left: 3px solid #0B3D91;
        font-size: 0.86rem;
        color: #1A2238;
    }

    /* 上昇/下落 数値（日本市場色） */
    .up { color: #D32030 !important; font-weight: 600; }
    .down { color: #1565C0 !important; font-weight: 600; }
    .flat { color: #555 !important; }

    /* キャプション */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #4A5568 !important;
        font-size: 0.78rem !important;
        font-style: italic;
    }

    /* dividers */
    hr { margin: 14px 0 !important; border: 0 !important;
         border-top: 1px solid #D5DDE8 !important;
         background: linear-gradient(90deg, transparent 0%, #C9A961 50%, transparent 100%);
         height: 1px;
    }

    /* スクロールバー */
    ::-webkit-scrollbar { height: 8px; width: 8px; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #0B3D91 0%, #C9A961 100%);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-track { background: #F4F7FB; }

    /* ─── 銘柄カード ─── */
    .stock-row {
        display: grid;
        grid-template-columns: 80px 2fr 1fr 1fr 1fr;
        gap: 8px;
        padding: 9px 14px;
        border-bottom: 1px solid #D5DDE8;
        font-size: 0.86rem;
        align-items: center;
    }
    .stock-row:hover { background: #F4F7FB; }
    .stock-code {
        font-family: monospace;
        font-weight: 700;
        color: #0B3D91;
        background: #E9EFF7;
        padding: 2px 7px;
        border-radius: 2px;
        text-align: center;
        border: 1px solid #C9A961;
    }

    /* ════════════════════════════════════════════════
        📱 モバイル/スマホ対応 (768px以下)
       ════════════════════════════════════════════════ */
    @media (max-width: 768px) {
        /* 全体パディング縮小 */
        .main .block-container {
            padding-top: 0.3rem !important;
            padding-bottom: 0.3rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* タイトル・見出しを小さく */
        h1 { font-size: 1.4rem !important; line-height: 1.3 !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1.0rem !important; }
        h4 { font-size: 0.92rem !important; }
        p, div, span { font-size: 0.88rem !important; }
        .stCaption { font-size: 0.72rem !important; }

        /* ヘッダーバー縦レイアウト */
        .miyabi-header {
            flex-direction: column !important;
            padding: 10px 14px !important;
            margin: -10px -8px 0 -8px !important;
            gap: 8px !important;
            text-align: center !important;
        }
        .miyabi-logo {
            font-size: 1.5rem !important;
            padding: 8px 14px !important;
        }
        .miyabi-title-jp {
            font-size: 1.0rem !important;
        }
        .miyabi-title-en {
            font-size: 0.7rem !important;
            letter-spacing: 1.5px !important;
        }
        .miyabi-header-right {
            text-align: center !important;
        }

        /* ティッカーバーを横スクロール可能に */
        .market-ticker {
            font-size: 0.78rem !important;
            padding: 6px 10px !important;
            overflow-x: auto !important;
            white-space: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
        }
        .ticker-item {
            display: inline-block !important;
            margin-right: 14px !important;
        }

        /* テーブルを横スクロール可能に */
        .stDataFrame, [data-testid="stDataFrame"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            font-size: 0.78rem !important;
        }
        .stDataFrame table {
            min-width: max-content !important;
        }
        .stDataFrame td, .stDataFrame th {
            padding: 4px 6px !important;
            font-size: 0.78rem !important;
        }

        /* メトリクス縮小 */
        [data-testid="stMetric"] {
            padding: 6px 8px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.0rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem !important;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.72rem !important;
        }

        /* カラムを縦に積む（Streamlitの強制マルチカラムレイアウトを単列化） */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 6px !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            min-width: 100% !important;
            width: 100% !important;
            flex: none !important;
        }

        /* タブを横スクロール */
        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            flex-wrap: nowrap !important;
        }
        [data-baseweb="tab"] {
            padding: 6px 10px !important;
            font-size: 0.8rem !important;
            white-space: nowrap !important;
            min-width: max-content !important;
        }

        /* ボタン */
        .stButton button, .stDownloadButton button {
            padding: 8px 12px !important;
            font-size: 0.85rem !important;
            width: 100% !important;
        }

        /* セレクトボックス/インプット */
        .stSelectbox label, .stRadio label, .stNumberInput label, .stTextInput label {
            font-size: 0.8rem !important;
        }
        [data-baseweb="select"] {
            font-size: 0.85rem !important;
        }

        /* ════════════════════════════════════════════════
            サイドバー（メニュー選択を超コンパクト化）
           ════════════════════════════════════════════════ */
        section[data-testid="stSidebar"] {
            width: 78% !important;
            min-width: 78% !important;
            max-width: 320px !important;
        }
        /* サイドバー内パディング縮小 */
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0.4rem !important;
            padding-bottom: 0.4rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* サイドバー内 文字サイズ縮小 */
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] h4,
        section[data-testid="stSidebar"] h5,
        section[data-testid="stSidebar"] h6 {
            font-size: 0.85rem !important;
            margin: 0.3rem 0 0.2rem 0 !important;
        }
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label {
            font-size: 0.78rem !important;
            line-height: 1.3 !important;
        }

        /* ▼ メインメニューのラジオを「2列グリッド」で詰める */
        section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 4px 6px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] label {
            padding: 5px 6px !important;
            margin: 0 !important;
            border: 1px solid rgba(11,61,145,0.18) !important;
            border-radius: 5px !important;
            background: rgba(11,61,145,0.02) !important;
            min-height: 36px !important;
            display: flex !important;
            align-items: center !important;
            cursor: pointer !important;
        }
        /* ラジオの○マーカー自体を非表示にして全面タップ */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-child p {
            font-size: 0.72rem !important;
            line-height: 1.15 !important;
            margin: 0 !important;
            font-weight: 600 !important;
            color: #0B3D91 !important;
        }
        /* 選択中の項目を金色ハイライト */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(135deg, #0B3D91 0%, #1A2D6E 100%) !important;
            border-color: #C9A961 !important;
            box-shadow: 0 2px 6px rgba(11,61,145,0.25) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
            color: #FFFFFF !important;
        }

        /* セレクトボックス・インプット類も詰める */
        section[data-testid="stSidebar"] [data-baseweb="select"],
        section[data-testid="stSidebar"] .stSelectbox,
        section[data-testid="stSidebar"] .stTextInput,
        section[data-testid="stSidebar"] .stNumberInput {
            font-size: 0.78rem !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {
            min-height: 32px !important;
            padding: 2px 6px !important;
        }
        /* divider の余白を狭める */
        section[data-testid="stSidebar"] hr {
            margin: 0.4rem 0 !important;
        }
        /* expanderも詰める */
        section[data-testid="stSidebar"] [data-testid="stExpander"] {
            margin: 0.2rem 0 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
            padding: 4px 6px !important;
            font-size: 0.78rem !important;
        }
        /* サイドバー内ボタン縮小 */
        section[data-testid="stSidebar"] .stButton button {
            padding: 5px 8px !important;
            font-size: 0.75rem !important;
            min-height: 32px !important;
        }
        /* サイドバー上部バッジを縮小 */
        section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child {
            padding: 8px 8px !important;
        }

        /* 予測ボックス */
        .prediction-box {
            padding: 10px !important;
        }
        .prediction-box div {
            font-size: 0.85rem !important;
        }

        /* iframeグラフ最低高さ調整 */
        iframe[title="streamlit_plotly_chart"] {
            min-height: 280px !important;
        }
    }

    /* ════════════════════════════════════════════════
        📱 タブレット (769px - 1024px)
       ════════════════════════════════════════════════ */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        .stDataFrame {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }
    }

    /* ════════════════════════════════════════════════
        🖥 デスクトップ（1200px以上）— 画面を広く使う
       ════════════════════════════════════════════════ */
    @media (min-width: 1200px) {
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        .miyabi-header {
            margin-left: -2rem !important;
            margin-right: -2rem !important;
            padding: 20px 32px !important;
        }
        .market-ticker {
            margin-left: -2rem !important;
            margin-right: -2rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.55rem !important;
        }
    }
    @media (min-width: 1600px) {
        .main .block-container {
            padding-left: 3rem !important;
            padding-right: 3rem !important;
        }
    }

    /* iPhone ノッチ・ホームインジケータ安全域 */
    @supports (padding: max(0px)) {
        .main .block-container {
            padding-left: max(1rem, env(safe-area-inset-left)) !important;
            padding-right: max(1rem, env(safe-area-inset-right)) !important;
            padding-bottom: max(1rem, env(safe-area-inset-bottom)) !important;
        }
        .miyabi-header {
            padding-top: max(18px, env(safe-area-inset-top)) !important;
        }
    }

    /* ユーザー選択: ワイドレイアウト */
    body.zb-layout-wide .main .block-container {
        max-width: 100% !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }
    body.zb-layout-wide .miyabi-header,
    body.zb-layout-wide .market-ticker {
        margin-left: -2.5rem !important;
        margin-right: -2.5rem !important;
    }
    body.zb-layout-phone .main .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    body.zb-layout-phone [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    body.zb-layout-phone [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        width: 100% !important;
    }

    /* 3画面モニター パネル見出し */
    .monitor-panel-head {
        background: linear-gradient(90deg, #0B3D91 0%, #1A2238 100%);
        color: #fff;
        padding: 10px 12px;
        border-radius: 4px;
        border-left: 4px solid #C9A961;
        margin-bottom: 10px;
    }
    .monitor-panel-title {
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .monitor-panel-sub {
        font-size: 0.72rem;
        color: #C9A961;
        margin-top: 3px;
    }
    @media (min-width: 1400px) {
        .monitor-tri-grid [data-testid="column"] {
            min-width: 0 !important;
        }
    }

    /* タッチデバイス共通：タップしやすく */
    @media (pointer: coarse) {
        .stButton button, [data-baseweb="tab"], .stRadio label, [role="radio"] {
            min-height: 38px !important;
        }
        a, button {
            -webkit-tap-highlight-color: rgba(11,61,145,0.15);
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<!-- Web / iPhone viewport & PWA -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{APP_PWA_TITLE}">
<meta name="theme-color" content="#0B3D91">
<meta name="application-name" content="{APP_NAME}">
<meta name="description" content="{APP_SUBTITLE}">
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  Zaibase.Economic Research ヘッダーバー
# ════════════════════════════════════════════════
_now = datetime.now()
_weekday = ["月", "火", "水", "木", "金", "土", "日"][_now.weekday()]
_market_status = "東証 立会中" if (9 <= _now.hour < 15 and _now.weekday() < 5) else "東証 立会外"

st.markdown(f"""
<div class="miyabi-header">
    <div class="miyabi-header-left">
        <div>
            <div class="miyabi-logo">{APP_LOGO_LETTER}</div>
            <div class="miyabi-logo-en">{APP_SHORT.upper()}</div>
        </div>
        <div>
            <div class="miyabi-title"><span class="miyabi-title-accent">{APP_SHORT}</span><span style="color:#C9A961;">.{APP_BRAND_SUFFIX}</span>　<span style="opacity:0.85;font-weight:400;font-size:0.95rem;">{APP_TAGLINE}</span></div>
            <div class="miyabi-subtitle">{APP_SUBTITLE}</div>
        </div>
    </div>
    <div class="miyabi-header-right">
        <div class="miyabi-time">{_now.strftime("%Y年%m月%d日")}（{_weekday}）{_now.strftime("%H:%M")}</div>
        <div><span class="miyabi-status">◆ {_market_status}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  市況ティッカーバー（主要マーケットの一覧表示）
# ════════════════════════════════════════════════
@st.cache_data(ttl=120)
def _get_ticker_data():
    """主要市場の最新価格を一括取得（2分キャッシュ）"""
    items = [
        ("日経平均", "^N225"),
        ("TOPIX", "^TPX"),
        ("ダウ", "^DJI"),
        ("S&P500", "^GSPC"),
        ("NASDAQ", "^IXIC"),
        ("VIX", "^VIX"),
        ("ドル/円", "USDJPY=X"),
        ("ユーロ/円", "EURJPY=X"),
        ("WTI原油", "CL=F"),
        ("金", "GC=F"),
        ("BTC", "BTC-USD"),
        ("ETH", "ETH-USD"),
    ]
    out = []
    for name, tk in items:
        info = get_latest_price(tk)
        out.append((name, info))
    return out


def _currency_for_ticker(ticker_code: str) -> str:
    if ticker_code in {"^TNX", "^TYX", "^FVX"}:
        return ""
    if ticker_code.endswith(".T") or ticker_code in ["^N225", "^TPX"]:
        return "¥"
    suffix_map = {
        ".HK": "HK$",
        ".KS": "₩",
        ".TW": "NT$",
        ".L": "£",
        ".AS": "€",
        ".DE": "€",
        ".PA": "€",
        ".SW": "CHF",
        ".TO": "C$",
        ".AX": "A$",
    }
    for suf, ccy in suffix_map.items():
        if ticker_code.endswith(suf):
            return ccy
    return "$"


def _render_midlong_range_block(
    ticker_code: str,
    currency: str,
    key_prefix: str,
    title: str,
    note_title: str = "計画内容メモ（公開情報ベース）",
):
    st.markdown(f"#### {title}")
    wk_col, yr_col = st.columns(2)
    with wk_col:
        week_choices = st.multiselect(
            "奇数週（複数選択）",
            options=[1, 3, 5, 7, 9, 11],
            default=[1, 3, 5],
            key=f"{key_prefix}_odd_weeks",
        )
    with yr_col:
        year_choices = st.multiselect(
            "奇数年（複数選択）",
            options=[1, 3, 5],
            default=[1, 3],
            key=f"{key_prefix}_odd_years",
        )

    long_pred = predict_stock_midlong_range(
        ticker_code,
        week_horizons=week_choices or [1, 3, 5],
        year_horizons=year_choices or [1, 3],
    )
    if not long_pred or not long_pred.get("points"):
        st.info("中長期レンジを生成できませんでした。時間を空けて再試行してください。")
        return

    lp_df = pd.DataFrame(long_pred["points"]).sort_values("days")
    band_fig = go.Figure()
    band_fig.add_trace(go.Scatter(
        x=lp_df["label"],
        y=lp_df["high"],
        mode="lines",
        line=dict(color="rgba(211, 32, 48, 0.35)", width=1),
        name="上限",
    ))
    band_fig.add_trace(go.Scatter(
        x=lp_df["label"],
        y=lp_df["low"],
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(21, 101, 192, 0.15)",
        line=dict(color="rgba(21, 101, 192, 0.35)", width=1),
        name="下限",
    ))
    band_fig.add_trace(go.Scatter(
        x=lp_df["label"],
        y=lp_df["center"],
        mode="lines+markers+text",
        text=[f"{v:+.1f}%" for v in lp_df["center_diff_pct"]],
        textposition="top center",
        line=dict(color="#0F52BA", width=3),
        marker=dict(size=8, color="#C9A961"),
        name="中心予測",
    ))
    band_fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="予測期間",
        yaxis_title=f"価格 ({currency})" if currency else "価格",
    )
    st.plotly_chart(band_fig, use_container_width=True)

    long_table = lp_df[["label", "center", "low", "high", "center_diff_pct", "band_pct"]].rename(columns={
        "label": "期間",
        "center": "中心予測価格",
        "low": "下限レンジ",
        "high": "上限レンジ",
        "center_diff_pct": "中心変化率(%)",
        "band_pct": "片側レンジ幅(%)",
    })
    st.dataframe(long_table, use_container_width=True, hide_index=True)

    st.markdown(f"**{note_title}**")
    for note in long_pred.get("plan_notes", []):
        st.markdown(f"- {note}")
    if long_pred.get("participants_used"):
        st.caption(f"連動加味した上場参加候補: {', '.join(long_pred['participants_used'])}")
    if long_pred.get("reasons"):
        with st.expander("中長期レンジ算出の根拠を見る"):
            for r in long_pred.get("reasons", []):
                st.markdown(f"- {r}")
    st.caption("※ メモは企業概要・成長指標・公開ニュース見出しからの自動抽出です。")


_ticker_html = '<div class="market-ticker">'
for name, info in _get_ticker_data():
    if info:
        cls = "ticker-up" if info["change_pct"] >= 0 else "ticker-down"
        sign = "▲" if info["change_pct"] >= 0 else "▼"
        _ticker_html += (
            f'<span class="ticker-item">'
            f'<span class="ticker-name">{name}</span>'
            f'<span class="ticker-value">{info["price"]:,.2f}</span>'
            f'<span class="{cls}">{sign}{abs(info["change_pct"]):.2f}%</span>'
            f'</span>'
        )
    else:
        _ticker_html += (
            f'<span class="ticker-item">'
            f'<span class="ticker-name">{name}</span>'
            f'<span class="ticker-value">—</span></span>'
        )
_ticker_html += '</div>'
st.markdown(_ticker_html, unsafe_allow_html=True)
render_legal_banner()

# ─── サイドバー ───
with st.sidebar:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0F52BA 0%,#0B3A8C 100%);color:#fff;padding:14px 12px;border-radius:3px;margin-bottom:14px;text-align:center;border:1px solid #C9A961;box-shadow:0 2px 8px rgba(15,82,186,0.2);">
        <div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:1.1rem;font-weight:700;letter-spacing:0.5px;background:linear-gradient(135deg,#C9A961 0%,#F0D580 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.25;">{APP_SHORT}<span style="font-size:0.72rem;">.{APP_BRAND_SUFFIX}</span></div>
        <div style="font-size:0.65rem;letter-spacing:3px;color:#C9A961;margin-top:4px;">MENU</div>
        <div style="font-size:0.7rem;opacity:0.85;margin-top:2px;letter-spacing:1px;">{APP_MENU_LABEL}</div>
    </div>
    """, unsafe_allow_html=True)

    _layout_labels = {
        "auto": "自動（画面サイズに合わせる）",
        "phone": "iPhone向け（1列・コンパクト）",
        "standard": "標準",
        "wide": "ワイド（PC全幅）",
    }
    layout_mode = st.radio(
        "📐 表示レイアウト",
        options=list(_layout_labels.keys()),
        format_func=lambda k: _layout_labels[k],
        index=0,
        key="layout_mode",
        horizontal=False,
    )

    st.markdown("##### ❖ メニュー選択")

    render_billing_sidebar()
    render_alarm_settings_sidebar()
    st.divider()

    page_options = [
        "📊 ダッシュボード",
        "🏛 取扱検討株式・市場情報",
        "🏦 FX/CFD ターミナル",
        "🖥 3画面モニター",
        "💴 円相場 総合分析",
        "⏰ 転換点・反転予測",
        "📅 経済イベント・カレンダー",
        "🚨 要人介入・警戒水準表",
        "💹 FX レバレッジ シミュレーター",
        "📊 株価指数先物 総合予測",
        "📐 チャートパターン検出（買い/売り）",
        "💎 ファンダメンタル売買判断",
        "原油先物予測",
        "株式ビューア",
        "FXビューア",
        "🚀 新興・新発掘銘柄",
        "₿ 仮想通貨",
        "🔔 アラート",
        "📈 バックテスト",
        "📜 利用規約・免責",
    ]

    # ダッシュボード内ボタンからの遷移要求を安全に反映（widget生成前のみ main_page を更新）
    _service_nav_target = st.session_state.pop("_service_nav_target", None)
    if _service_nav_target in page_options:
        st.session_state["main_page"] = _service_nav_target

    page = st.radio(
        " ",
        page_options,
        label_visibility="collapsed",
        key="main_page",
    )

    st.caption(f"版 {TERMS_VERSION} — メニュー「📜 利用規約・免責」")

    st.divider()

    ticker = None
    display_name = None
    interval = "1d"
    period = "1mo"
    chart_type = "ローソク足"
    show_bb = False
    show_comparison = False
    selected_future = None

    if page == "原油先物予測":
        selected_future = st.selectbox(
            "銘柄",
            options=list(FUTURES_SYMBOLS.keys()),
            index=0,
        )
        ticker = FUTURES_SYMBOLS[selected_future]
        display_name = selected_future

        selected_interval = st.selectbox(
            "時間足",
            options=list(INTERVAL_OPTIONS.keys()),
            index=0,
        )
        interval = INTERVAL_OPTIONS[selected_interval]

        if interval == "1m":
            period_choices = {"1日": "1d", "2日": "2d", "5日": "5d"}
        elif interval in ["5m", "15m", "30m"]:
            period_choices = {"1日": "1d", "5日": "5d", "1ヶ月": "1mo"}
        elif interval == "1h":
            period_choices = {"5日": "5d", "1ヶ月": "1mo", "3ヶ月": "3mo", "6ヶ月": "6mo"}
        else:
            period_choices = PERIOD_OPTIONS

        selected_period = st.selectbox(
            "表示期間",
            options=list(period_choices.keys()),
            index=0,
        )
        period = period_choices[selected_period]

        chart_type = st.radio("チャート", ["ローソク足", "ライン"])
        show_bb = st.checkbox("ボリンジャーバンド", value=False)

    elif page == "株式ビューア":
        stock_category = st.selectbox(
            "カテゴリ",
            ["株価指数", "日本個別株", "米国個別株", "海外個別株", "債券"],
        )
        if stock_category == "株価指数":
            stock_dict = STOCK_INDICES
        elif stock_category == "日本個別株":
            stock_dict = JP_STOCKS
        elif stock_category == "米国個別株":
            stock_dict = US_STOCKS
        elif stock_category == "債券":
            stock_dict = BOND_SYMBOLS
        else:
            stock_dict = OVERSEAS_STOCKS

        selected_stock = st.selectbox(
            "銘柄",
            options=list(stock_dict.keys()),
            index=0,
        )
        ticker = stock_dict[selected_stock]
        display_name = selected_stock

        selected_interval = st.selectbox(
            "時間足",
            options=list(INTERVAL_OPTIONS.keys()),
            index=5,
        )
        interval = INTERVAL_OPTIONS[selected_interval]

        if interval == "1m":
            period_choices = {"1日": "1d", "2日": "2d", "5日": "5d"}
        elif interval in ["5m", "15m", "30m"]:
            period_choices = {"1日": "1d", "5日": "5d", "1ヶ月": "1mo"}
        elif interval == "1h":
            period_choices = {"5日": "5d", "1ヶ月": "1mo", "3ヶ月": "3mo", "6ヶ月": "6mo"}
        else:
            period_choices = PERIOD_OPTIONS

        selected_period = st.selectbox(
            "表示期間",
            options=list(period_choices.keys()),
            index=2,
        )
        period = period_choices[selected_period]

        chart_type = st.radio("チャート", ["ローソク足", "ライン"])
        show_bb = st.checkbox("ボリンジャーバンド", value=False)
        show_comparison = st.checkbox("日経 vs NYダウ 比較", value=False)

    elif page == "FXビューア":
        selected_pair = st.selectbox(
            "通貨ペア",
            options=list(CURRENCY_PAIRS.keys()),
            index=0,
        )
        ticker = CURRENCY_PAIRS[selected_pair]
        display_name = selected_pair
        selected_interval = st.selectbox(
            "時間足",
            options=list(INTERVAL_OPTIONS.keys()),
            index=3,
        )
        interval = INTERVAL_OPTIONS[selected_interval]
        selected_period = st.selectbox(
            "表示期間",
            options=list(PERIOD_OPTIONS.keys()),
            index=2,
        )
        period = PERIOD_OPTIONS[selected_period]
        chart_type = st.radio("チャート", ["ローソク足", "ライン"])
        show_bb = st.checkbox("ボリンジャーバンド", value=False)

    elif page == "₿ 仮想通貨":
        selected_crypto = st.selectbox(
            "銘柄",
            options=list(CRYPTO_SYMBOLS.keys()),
            index=0,
        )
        ticker = CRYPTO_SYMBOLS[selected_crypto]
        display_name = selected_crypto
        selected_interval = st.selectbox(
            "時間足",
            options=list(INTERVAL_OPTIONS.keys()),
            index=5,
        )
        interval = INTERVAL_OPTIONS[selected_interval]
        if interval == "1m":
            period_choices = {"1日": "1d", "2日": "2d", "5日": "5d"}
        elif interval in ["5m", "15m", "30m"]:
            period_choices = {"1日": "1d", "5日": "5d", "1ヶ月": "1mo"}
        elif interval == "1h":
            period_choices = {"5日": "5d", "1ヶ月": "1mo", "3ヶ月": "3mo"}
        else:
            period_choices = PERIOD_OPTIONS
        selected_period = st.selectbox(
            "表示期間",
            options=list(period_choices.keys()),
            index=min(2, len(period_choices) - 1),
        )
        period = period_choices[selected_period]
        chart_type = st.radio("チャート", ["ローソク足", "ライン"])
        show_bb = st.checkbox("ボリンジャーバンド", value=False)

    st.divider()

    # ── 📱 スマホアクセス情報 ──
    with st.expander("📱 iPhone / Web で見る", expanded=False):
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                # 別ロジックでLAN IPを取得
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                except Exception:
                    pass
                finally:
                    s.close()
        except Exception:
            local_ip = "192.168.x.x"

        mobile_url = f"http://{local_ip}:8501"

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0B3D91 0%,#1A2238 100%);color:#fff;padding:12px;border-radius:4px;text-align:center;">
            <div style="font-family:'Hiragino Mincho ProN',serif;color:#C9A961;font-size:0.85rem;letter-spacing:2px;">📱 MOBILE ACCESS</div>
            <div style="font-family:monospace;font-size:0.95rem;font-weight:700;margin:8px 0;color:#fff;background:rgba(255,255,255,0.1);padding:6px;border-radius:3px;word-break:break-all;">
                {mobile_url}
            </div>
            <div style="font-size:0.7rem;color:#C9A961;margin-top:6px;line-height:1.5;">
                スマホ／タブレットを<br>
                <b>同じWi-Fi</b>に接続してアクセス
            </div>
        </div>
        """, unsafe_allow_html=True)

        # QRコード（iframeで生成）
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={mobile_url}&bgcolor=FFFFFF&color=0B3D91"
        st.markdown(f"""
        <div style="text-align:center;margin-top:8px;background:#fff;padding:10px;border:1px solid #C9A961;border-radius:4px;">
            <img src="{qr_url}" width="160" alt="QR Code" style="display:block;margin:0 auto;">
            <div style="font-size:0.7rem;color:#0B3D91;margin-top:6px;">QRコードをスマホで読み取り</div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"💡 Safari で {APP_NAME} を「ホーム画面に追加」するとアプリのように使えます")

    st.markdown(f"""
    <div style="background:linear-gradient(180deg,#FFFBF0 0%,#FAF3DC 100%);border:1px solid #C9A961;border-left:4px solid #C9A961;border-radius:2px;padding:10px 12px;font-size:0.74rem;color:#6B5A2E;line-height:1.6;">
    <b style="color:#8B6914;">◆ ご利用上の注意</b><br>
    {APP_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center;margin-top:14px;color:#4A5568;font-size:0.7rem;line-height:1.7;border-top:1px solid #D5DDE8;padding-top:10px;">
        <div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#0B3D91;letter-spacing:1px;font-size:0.8rem;font-weight:600;">{APP_FOOTER_LINE1}</div>
        <div style="color:#C9A961;font-size:0.62rem;letter-spacing:1px;">{APP_FOOTER_LINE2}</div>
        <div style="margin-top:6px;font-size:0.65rem;">Powered by Yahoo Finance / Google News<br>{APP_FOOTER_COPY}</div>
    </div>
    """, unsafe_allow_html=True)


_layout_mode = st.session_state.get("layout_mode", "auto")
if _layout_mode == "wide":
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 100% !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }
    .miyabi-header, .market-ticker {
        margin-left: -2.5rem !important;
        margin-right: -2.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
elif _layout_mode == "phone":
    st.markdown("""
    <style>
    .main .block-container {
        padding-left: 0.35rem !important;
        padding-right: 0.35rem !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 6px !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        width: 100% !important;
        flex: none !important;
    }
    iframe[title="streamlit_plotly_chart"] {
        min-height: 260px !important;
    }
    </style>
    """, unsafe_allow_html=True)


# 大和証券FXルール参考 — 維持率・価格予測アラーム（全ページ）
try:
    _daiwa_events = check_all_daiwa_alerts()
    if _daiwa_events:
        render_alarm_events(_daiwa_events, play_sound=True)
except Exception:
    pass


# ════════════════════════════════════════════════
#  📊 株価指数先物 総合予測モード
#  日経225・米国D30・S&P500・NASDAQ・DAX・FTSE・ハンセン他
# ════════════════════════════════════════════════
if page == "📊 株価指数先物 総合予測":
    st.title("📊 株価指数先物 総合予測ダッシュボード")
    st.caption("日経225・米国D30・S&P500・NASDAQ・DAX・FTSE・ハンセン・KOSPI・台湾加権 他、世界17銘柄を一括予測")

    tab_scan, tab_detail, tab_region = st.tabs([
        "🌐 全銘柄スコアランキング",
        "🔍 個別銘柄 詳細予測",
        "🌍 地域別マップ",
    ])

    # ─────────── 全銘柄スキャン ───────────
    with tab_scan:
        st.markdown("#### 全17銘柄 強気度スコアランキング")
        st.caption("短期+中期+長期の合計スコアで並び替え。スコア大 = 強気")

        if st.button("🔄 全銘柄スキャン実行（30秒〜1分）", type="primary", key="idx_scan_btn"):
            with st.spinner("世界の指数を一括分析中..."):
                idx_scan = scan_all_index_futures()
            st.session_state["idx_scan"] = idx_scan
            st.success(f"スキャン完了：{len(idx_scan)}銘柄")

        idx_scan = st.session_state.get("idx_scan")
        if idx_scan:
            # サマリー
            bull = [r for r in idx_scan if r["total_score"] >= 2]
            bear = [r for r in idx_scan if r["total_score"] <= -2]
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("総銘柄", len(idx_scan))
            sm2.metric("🟢 強気銘柄", len(bull))
            sm3.metric("🔴 弱気銘柄", len(bear))
            sm4.metric("⚪ 中立", len(idx_scan) - len(bull) - len(bear))

            # 表
            rows = []
            for r in idx_scan:
                rows.append({
                    "判定": r["verdict"],
                    "国": r["country"],
                    "銘柄": r["short_name"],
                    "現在値": r["current_price"],
                    "1日%": f"{r['change_1d']:+.2f}%",
                    "1ヶ月%": f"{r['perf_1m']:+.2f}%",
                    "3ヶ月%": f"{r['perf_3m']:+.2f}%",
                    "RSI": r["rsi"],
                    "短期": r["short_dir"],
                    "中期": r["mid_dir"],
                    "長期": r["long_dir"],
                    "ボラ%": f"{r['volatility']:.1f}%",
                    "総合スコア": r["total_score"],
                })
            df_scan = pd.DataFrame(rows)
            st.dataframe(df_scan, use_container_width=True, hide_index=True, height=500)

            st.divider()
            c_top, c_bot = st.columns(2)
            with c_top:
                st.markdown("##### 🚀 強気TOP3")
                for r in idx_scan[:3]:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#FFF0F0 0%,#FFE5E5 100%);border-left:4px solid #D32030;padding:10px 14px;margin:4px 0;border-radius:0 3px 3px 0;">
                        <b style="color:#D32030;">{r['country']} {r['short_name']}</b>
                        <span style="float:right;color:#D32030;font-weight:700;">スコア {r['total_score']:+d}</span>
                        <div style="font-size:0.85rem;color:#1A2238;margin-top:4px;">
                            現在 {r['current_price']:,.2f} ({r['change_1d']:+.2f}%) ｜ 3ヶ月 {r['perf_3m']:+.2f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            with c_bot:
                st.markdown("##### 📉 弱気TOP3")
                for r in idx_scan[-3:][::-1]:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#F0F4FF 0%,#E5EFFF 100%);border-left:4px solid #1565C0;padding:10px 14px;margin:4px 0;border-radius:0 3px 3px 0;">
                        <b style="color:#1565C0;">{r['country']} {r['short_name']}</b>
                        <span style="float:right;color:#1565C0;font-weight:700;">スコア {r['total_score']:+d}</span>
                        <div style="font-size:0.85rem;color:#1A2238;margin-top:4px;">
                            現在 {r['current_price']:,.2f} ({r['change_1d']:+.2f}%) ｜ 3ヶ月 {r['perf_3m']:+.2f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("「🔄 全銘柄スキャン実行」ボタンを押してください")

    # ─────────── 個別詳細 ───────────
    with tab_detail:
        st.markdown("#### 個別銘柄の詳細予測")

        sel_label = st.selectbox(
            "銘柄を選択",
            options=list(INDEX_FUTURES.keys()),
            format_func=lambda s: f"{INDEX_FUTURES[s]['country']} {INDEX_FUTURES[s]['name']} ({s})",
            key="idx_sel",
        )

        if st.button("🔍 詳細分析", type="primary", key="idx_detail_btn"):
            with st.spinner("分析中..."):
                r = analyze_index_future(sel_label)
            st.session_state["idx_detail"] = r

        r = st.session_state.get("idx_detail")
        if r:
            # ヘッダー
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0B3D91 0%,#1A2238 100%);color:#fff;padding:18px 22px;border-radius:4px;border-left:6px solid {r['verdict_color']};margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-family:'Hiragino Mincho ProN',serif;font-size:1.4rem;font-weight:700;">
                            {r['country']} {r['name']}
                        </div>
                        <div style="color:#C9A961;font-size:0.85rem;letter-spacing:2px;">{r['short_name']} ｜ {r['region']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-family:monospace;font-size:1.6rem;font-weight:700;">{r['current_price']:,.2f}</div>
                        <div style="color:{('#FF6B6B' if r['change_1d']>=0 else '#74C0FC')};font-size:1rem;">{r['change_1d']:+.2f}%</div>
                    </div>
                </div>
                <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(201,169,97,0.3);">
                    <span style="color:{r['verdict_color']};font-size:1.2rem;font-weight:700;">{r['verdict']}</span>
                    <span style="color:#fff;margin-left:14px;">{r['verdict_detail']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 期間別パフォーマンス
            st.markdown("##### 📊 期間別パフォーマンス")
            pc = st.columns(6)
            for i, (label, val) in enumerate([("1日", r["performance"]["1d"]), ("1週", r["performance"]["1w"]),
                                              ("1ヶ月", r["performance"]["1m"]), ("3ヶ月", r["performance"]["3m"]),
                                              ("6ヶ月", r["performance"]["6m"]), ("1年", r["performance"]["1y"])]):
                pc[i].metric(label, f"{val:+.2f}%")

            st.markdown(f"**取引時間 (JST):** {r['trading_hours']}　／　**年率ボラティリティ:** {r['volatility_pct']:.1f}%")

            # マルチタイムフレーム予測
            st.markdown("##### 🎯 マルチタイムフレーム予測")
            tc = st.columns(3)
            for i, (key, label) in enumerate([("short_term", "短期"), ("mid_term", "中期"), ("long_term", "長期")]):
                p = r["predictions"][key]
                color = "#D32030" if "強気" in p["direction"] else ("#1565C0" if "弱気" in p["direction"] else "#FDB813")
                with tc[i]:
                    st.markdown(f"""
                    <div style="background:#fff;border:1px solid #D5DDE8;border-top:4px solid {color};padding:14px;border-radius:3px;height:100%;">
                        <div style="color:#4A5568;font-size:0.8rem;letter-spacing:2px;">{label}（{p['horizon']}）</div>
                        <div style="font-family:'Hiragino Mincho ProN',serif;color:{color};font-weight:700;font-size:1.4rem;margin:6px 0;">
                            {p['icon']} {p['direction']}
                        </div>
                        <div style="color:#0B3D91;font-size:0.85rem;">信頼度 {p['confidence']}%</div>
                        <div style="margin-top:8px;font-size:0.78rem;color:#1A2238;line-height:1.7;">
                            {''.join([f'• {x}<br>' for x in p['reasons']])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            sr = r["support_resistance"]
            one_month_targets = [s["target_1m"] for s in r["scenarios"]]
            idx_range_low = min(sr["support_strong"], min(one_month_targets))
            idx_range_high = max(sr["resistance_strong"], max(one_month_targets))
            idx_base = max(float(r["current_price"]), 1e-9)
            st.markdown("##### 📦 統合予測レンジ（1ヶ月目安）")
            st.info(
                f"現在 {r['current_price']:,.2f} ｜ 予測レンジ {idx_range_low:,.2f} 〜 {idx_range_high:,.2f} "
                f"（{(idx_range_low / idx_base - 1) * 100:+.2f}% 〜 {(idx_range_high / idx_base - 1) * 100:+.2f}%）"
            )
            idx_yf_ticker = INDEX_FUTURES.get(sel_label, {}).get("yf_symbol", sel_label)
            idx_currency = "¥" if "🇯🇵" in r["country"] else "$"
            _render_midlong_range_block(
                ticker_code=idx_yf_ticker,
                currency=idx_currency,
                key_prefix=f"index_midlong_{sel_label}",
                title="奇数週・数年先の予測レンジ（計画/テーマメモ付き）",
                note_title="指数テーマメモ（公開情報ベース）",
            )

            # シナリオ
            st.markdown("##### 🌟 3つのシナリオと確率")
            sc = st.columns(3)
            for i, scen in enumerate(r["scenarios"]):
                with sc[i]:
                    st.markdown(f"""
                    <div style="background:#fff;border:1px solid #D5DDE8;border-top:5px solid {scen['color']};padding:14px;border-radius:3px;height:100%;">
                        <div style="font-family:'Hiragino Mincho ProN',serif;color:{scen['color']};font-weight:700;font-size:1.05rem;">
                            {scen['name']}
                        </div>
                        <div style="font-size:2rem;font-weight:700;color:{scen['color']};margin:8px 0;">
                            {scen['probability']}%
                        </div>
                        <table style="width:100%;font-size:0.83rem;">
                            <tr><td style="color:#4A5568;padding:3px 0;">1ヶ月後目標</td><td style="text-align:right;font-family:monospace;"><b>{scen['target_1m']:,.2f}</b></td></tr>
                            <tr><td style="color:#4A5568;padding:3px 0;">3ヶ月後目標</td><td style="text-align:right;font-family:monospace;"><b>{scen['target_3m']:,.2f}</b></td></tr>
                        </table>
                        <div style="margin-top:8px;font-size:0.78rem;color:#1A2238;line-height:1.6;border-top:1px solid #D5DDE8;padding-top:6px;">
                            <b>トリガー:</b> {scen['trigger']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # サポート・レジスタンス
            st.markdown("##### 📍 重要価格水準")
            sr = r["support_resistance"]
            sr_rows = [
                {"水準": "🔺 強レジスタンス", "価格": sr["resistance_strong"], "距離": f"{(sr['resistance_strong']/r['current_price']-1)*100:+.2f}%"},
                {"水準": "🔻 中レジスタンス", "価格": sr["resistance_mid"], "距離": f"{(sr['resistance_mid']/r['current_price']-1)*100:+.2f}%"},
                {"水準": "⚪ 中立(50%)", "価格": sr["fib_500"], "距離": f"{(sr['fib_500']/r['current_price']-1)*100:+.2f}%"},
                {"水準": "🔻 中サポート", "価格": sr["support_mid"], "距離": f"{(sr['support_mid']/r['current_price']-1)*100:+.2f}%"},
                {"水準": "🔻 強サポート", "価格": sr["support_strong"], "距離": f"{(sr['support_strong']/r['current_price']-1)*100:+.2f}%"},
            ]
            st.dataframe(pd.DataFrame(sr_rows), use_container_width=True, hide_index=True)

            # チャート
            st.markdown("##### 📈 過去1年チャート（サポート・レジスタンス付き）")
            df_chart = r["df"]
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart["Open"], high=df_chart["High"],
                low=df_chart["Low"], close=df_chart["Close"], name="価格",
                increasing_line_color="#D32030", decreasing_line_color="#1565C0",
            ))
            fig.add_hline(y=sr["resistance_strong"], line_dash="dash", line_color="#D32030",
                          annotation_text=f"強レジスタンス {sr['resistance_strong']:,.0f}", annotation_position="right")
            fig.add_hline(y=sr["support_strong"], line_dash="dash", line_color="#1565C0",
                          annotation_text=f"強サポート {sr['support_strong']:,.0f}", annotation_position="right")
            for scen in r["scenarios"]:
                fig.add_hline(y=scen["target_3m"], line_dash="dot", line_color=scen["color"], opacity=0.5,
                              annotation_text=f"{scen['name']} 3M目標", annotation_position="left")
            fig.update_layout(template="plotly_white", height=450,
                              margin=dict(l=0, r=0, t=20, b=0),
                              xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # カタリスト
            st.markdown("##### 🔥 注目カタリスト・材料")
            cat_cols = st.columns(2)
            with cat_cols[0]:
                st.markdown("**📅 主要イベント**")
                for cat in r["catalysts"]:
                    st.markdown(f"- {cat}")
            with cat_cols[1]:
                st.markdown("**💡 主要ドライバー**")
                for d in r["key_drivers"]:
                    st.markdown(f"- {d}")
                st.markdown(f"**🔗 主要相関:** {r['correlation']}")

        else:
            st.info("銘柄を選んで「🔍 詳細分析」を押してください")

    # ─────────── 地域別マップ ───────────
    with tab_region:
        st.markdown("#### 地域別 強弱マップ")
        st.caption("どの地域の指数が強い／弱いかを一目で確認")

        if st.button("🔄 全銘柄分析", key="region_scan_btn") or st.session_state.get("idx_scan"):
            if not st.session_state.get("idx_scan"):
                with st.spinner("分析中..."):
                    st.session_state["idx_scan"] = scan_all_index_futures()
            scan = st.session_state["idx_scan"]

            # 地域別グルーピング
            region_groups = {}
            for r in scan:
                region = INDEX_FUTURES[r["symbol"]]["region"]
                region_groups.setdefault(region, []).append(r)

            for region, items in region_groups.items():
                avg_score = sum(x["total_score"] for x in items) / len(items)
                region_color = ("#D32030" if avg_score >= 1 else
                                "#1565C0" if avg_score <= -1 else "#FDB813")
                st.markdown(f"""
                <div style="background:linear-gradient(90deg,#1A2238 0%,#0B3D91 100%);color:#fff;padding:10px 16px;border-radius:3px 3px 0 0;margin-top:14px;border-bottom:3px solid {region_color};font-family:'Hiragino Mincho ProN',serif;letter-spacing:1.5px;">
                    🌏 {region}　<span style="color:#C9A961;font-size:0.85rem;">平均スコア {avg_score:+.1f}</span>
                </div>
                """, unsafe_allow_html=True)

                cols = st.columns(min(len(items), 4))
                for i, r in enumerate(items):
                    color = "#D32030" if r["total_score"] >= 1 else ("#1565C0" if r["total_score"] <= -1 else "#FDB813")
                    with cols[i % 4]:
                        st.markdown(f"""
                        <div style="background:#fff;border:1px solid #D5DDE8;border-top:4px solid {color};padding:10px 12px;margin:4px 0;border-radius:3px;">
                            <div style="color:#0B3D91;font-weight:700;">{r['country']} {r['short_name']}</div>
                            <div style="font-family:monospace;color:#1A2238;font-size:1rem;">{r['current_price']:,.2f}</div>
                            <div style="color:{color};font-size:0.85rem;">{r['change_1d']:+.2f}% ｜ スコア {r['total_score']:+d}</div>
                            <div style="font-size:0.75rem;color:#4A5568;margin-top:4px;">{r['verdict']}</div>
                        </div>
                        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  原油先物予測モード
# ════════════════════════════════════════════════
if page == "原油先物予測":
    st.title("原油先物 AI予測ダッシュボード")
    st.caption("世界情勢ニュース分析 × テクニカル分析 → 価格方向予測")

    # ─── 最新価格 ───
    latest = get_latest_price(ticker)
    if latest:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                label=selected_future,
                value=f"${latest['price']:.2f}",
                delta=f"{latest['change']:+.2f} ({latest['change_pct']:+.2f}%)",
            )
        with c2:
            st.metric("前日比", f"${latest['change']:+.2f}")
        with c3:
            st.metric("変動率", f"{latest['change_pct']:+.2f}%")
        st.divider()

    # ─── 予測セクション ───
    tab_predict, tab_chart, tab_news, tab_data = st.tabs([
        "予測結果", "チャート", "ニュース分析", "データ",
    ])

    # --- 価格データ取得 ---
    with st.spinner("価格データを取得中..."):
        df = fetch_market_data(ticker, period, interval)

    if df.empty:
        st.error("価格データを取得できませんでした。市場が閉まっている可能性があります。")
        st.info("💡 時間足や期間を変えてお試しください。1分足は市場の営業時間中のみ取得可能です。")
        st.stop()

    df_with_indicators = calculate_technical_indicators(df)

    # --- ニュース分析 ---
    with st.spinner("世界情勢ニュースを分析中..."):
        news_result = fetch_and_analyze_all()

    # --- 予測実行 ---
    with st.spinner("AI予測を実行中..."):
        prediction = train_and_predict(df, news_result["overall_score"])

    # ═══ タブ: 予測結果 ═══
    with tab_predict:
        if prediction:
            if prediction["direction"] == "上昇":
                box_class = "pred-up"
                arrow = "📈"
                color = "#00d26a"
            else:
                box_class = "pred-down"
                arrow = "📉"
                color = "#f92f60"

            st.markdown(f"""
            <div class="prediction-box {box_class}">
                <div style="font-size: 1.2rem; color: #ccc;">AI予測方向</div>
                <div class="score-gauge" style="color: {color};">{arrow} {prediction['direction']}</div>
                <div style="font-size: 1.5rem; color: #fff;">信頼度: {prediction['confidence']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

            oil_current = float(df_with_indicators["終値"].iloc[-1]) if not df_with_indicators.empty else 0.0
            oil_combined = float(prediction.get("combined_score", 0.0))
            oil_vol_pct = (
                float(df_with_indicators["終値"].pct_change().dropna().tail(20).std() * 100)
                if len(df_with_indicators) >= 21 else 0.8
            )
            oil_band_pct = max(0.8, min(8.0, abs(oil_combined) * 3.5 + oil_vol_pct * 0.8))
            oil_shift_pct = oil_combined * 1.5
            oil_low = oil_current * (1 + (oil_shift_pct - oil_band_pct) / 100)
            oil_high = oil_current * (1 + (oil_shift_pct + oil_band_pct) / 100)
            oil_base = max(oil_current, 1e-9)
            st.markdown(
                f"##### 予測レンジ（当面）: {oil_low:,.2f} 〜 {oil_high:,.2f} "
                f"（{(oil_low / oil_base - 1) * 100:+.2f}% 〜 {(oil_high / oil_base - 1) * 100:+.2f}%）"
            )
            _render_midlong_range_block(
                ticker_code=ticker,
                currency="$",
                key_prefix=f"oil_midlong_{ticker}",
                title="奇数週・数年先の予測レンジ（計画/テーマメモ付き）",
                note_title="市場テーマメモ（公開情報ベース）",
            )

            st.write("")

            # スコア内訳
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                ts = prediction["technical_score"]
                st.metric(
                    "テクニカルスコア",
                    f"{ts:+.3f}",
                    delta="上昇寄り" if ts > 0 else "下降寄り",
                )
            with sc2:
                ns = prediction["news_score"]
                st.metric(
                    "ニューススコア",
                    f"{ns:+.3f}",
                    delta="上昇要因" if ns > 0 else "下降要因",
                )
            with sc3:
                cs = prediction["combined_score"]
                st.metric(
                    "統合スコア（テクニカル70% + ニュース30%）",
                    f"{cs:+.3f}",
                )

            # 判断根拠
            st.subheader("判断根拠")
            for factor in prediction["factors"]:
                st.markdown(f'<div class="factor-item">{factor}</div>', unsafe_allow_html=True)

            # ニュース概況
            st.subheader("ニュース概況")
            nc1, nc2, nc3 = st.columns(3)
            with nc1:
                st.metric("上昇要因ニュース", f"{news_result['bullish_count']}件")
            with nc2:
                st.metric("下降要因ニュース", f"{news_result['bearish_count']}件")
            with nc3:
                st.metric("中立ニュース", f"{news_result['neutral_count']}件")
        else:
            st.warning("予測に必要なデータが不足しています。期間を長くするか時間足を変更してください。")

    # ═══ タブ: チャート ═══
    with tab_chart:
        st.subheader(f"{selected_future} {selected_interval}（{selected_period}）")

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=["価格", "RSI", "MACD"],
        )

        # 価格チャート
        if chart_type == "ローソク足":
            fig.add_trace(go.Candlestick(
                x=df_with_indicators["日時"],
                open=df_with_indicators["始値"],
                high=df_with_indicators["高値"],
                low=df_with_indicators["安値"],
                close=df_with_indicators["終値"],
                name="価格",
                increasing_line_color="#D32030",
                decreasing_line_color="#1565C0",
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["終値"],
                mode="lines",
                name="終値",
                line=dict(color="#4da6ff", width=2),
            ), row=1, col=1)

        # 移動平均線
        for col_name, color in [("MA5", "#ffa500"), ("MA25", "#ff6b6b"), ("MA75", "#a855f7")]:
            if col_name in df_with_indicators.columns:
                fig.add_trace(go.Scatter(
                    x=df_with_indicators["日時"],
                    y=df_with_indicators[col_name],
                    mode="lines",
                    name=col_name,
                    line=dict(color=color, width=1, dash="dot"),
                ), row=1, col=1)

        # ボリンジャーバンド
        if show_bb and "BB上限(+2σ)" in df_with_indicators.columns:
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["BB上限(+2σ)"],
                mode="lines", name="BB+2σ",
                line=dict(color="#888", width=1, dash="dash"),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["BB下限(-2σ)"],
                mode="lines", name="BB-2σ",
                line=dict(color="#888", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(136,136,136,0.1)",
            ), row=1, col=1)

        # RSI
        if "RSI" in df_with_indicators.columns:
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["RSI"],
                mode="lines", name="RSI",
                line=dict(color="#e879f9", width=1.5),
            ), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

        # MACD
        if "MACD" in df_with_indicators.columns:
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["MACD"],
                mode="lines", name="MACD",
                line=dict(color="#4da6ff", width=1.5),
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=df_with_indicators["日時"],
                y=df_with_indicators["MACDシグナル"],
                mode="lines", name="Signal",
                line=dict(color="#ffa500", width=1.5),
            ), row=3, col=1)
            if "MACDヒストグラム" in df_with_indicators.columns:
                colors = ["#00d26a" if v >= 0 else "#f92f60"
                          for v in df_with_indicators["MACDヒストグラム"]]
                fig.add_trace(go.Bar(
                    x=df_with_indicators["日時"],
                    y=df_with_indicators["MACDヒストグラム"],
                    name="Histogram",
                    marker_color=colors,
                    opacity=0.5,
                ), row=3, col=1)

        fig.update_layout(
            template="plotly_white",
            height=700,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 基本統計
        with st.expander("基本統計"):
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("期間最高値", f"${df['高値'].max():.2f}")
            with s2:
                st.metric("期間最安値", f"${df['安値'].min():.2f}")
            with s3:
                st.metric("平均終値", f"${df['終値'].mean():.2f}")
            with s4:
                vol = df["終値"].pct_change().std() * 100
                st.metric("ボラティリティ", f"{vol:.3f}%")

    # ═══ タブ: ニュース分析 ═══
    with tab_news:
        st.subheader("世界情勢ニュース分析")

        # カテゴリ別スコア
        if news_result["category_scores"]:
            st.markdown("#### カテゴリ別 原油影響スコア")
            cat_df = pd.DataFrame([
                {"カテゴリ": k, "スコア": v,
                 "判定": "上昇要因" if v > 0.1 else ("下降要因" if v < -0.1 else "中立")}
                for k, v in news_result["category_scores"].items()
            ])

            fig_cat = go.Figure(go.Bar(
                x=cat_df["スコア"],
                y=cat_df["カテゴリ"],
                orientation="h",
                marker_color=["#00d26a" if s > 0.1 else ("#f92f60" if s < -0.1 else "#888")
                              for s in cat_df["スコア"]],
                text=[f"{s:+.3f}" for s in cat_df["スコア"]],
                textposition="auto",
            ))
            fig_cat.update_layout(
                template="plotly_white",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="原油影響スコア（正=上昇要因, 負=下降要因）",
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        # ニュース一覧
        st.markdown("#### 最新ニュース（影響度順）")
        for i, article in enumerate(news_result["articles"][:20]):
            sentiment = article["sentiment"]
            if sentiment["label"] == "上昇要因":
                icon = "🔴"
                badge_color = "#00d26a"
            elif sentiment["label"] == "下降要因":
                icon = "🔵"
                badge_color = "#f92f60"
            else:
                icon = "⚪"
                badge_color = "#888"

            with st.container():
                col_icon, col_text = st.columns([1, 11])
                with col_icon:
                    st.write(icon)
                with col_text:
                    st.markdown(
                        f"**{article['title']}**  \n"
                        f"📰 {article['source']}　"
                        f"🕐 {article['published']}　"
                        f"影響: `{sentiment['oil_impact']:+.3f}` "
                        f"({sentiment['label']})"
                    )

    # ═══ タブ: データ ═══
    with tab_data:
        st.subheader("価格データ")
        display_df = df[["日時", "始値", "高値", "安値", "終値"]].copy()
        display_df = display_df.sort_values("日時", ascending=False)
        for col in ["始値", "高値", "安値", "終値"]:
            display_df[col] = display_df[col].round(4)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════
#  📐 チャートパターン検出（買い/売り 両対応）
# ════════════════════════════════════════════════
elif page == "📐 チャートパターン検出（買い/売り）":
    st.title("📐 チャートパターン検出（買い / 売り）")
    st.caption("大和証券流＋酒田五法｜**参考パターン57種**（包み線・ピンバー対応）※投資助言ではありません")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#F4F7FB 0%,#E8EEF8 100%);border-left:4px solid #C9A961;padding:10px 14px;border-radius:3px;margin-bottom:14px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <div>
        <b style="color:#006837;">🟢 買いパターン 28種</b><br>
        <span style="font-size:0.72rem;color:#4A5568;line-height:1.35;">
        <b>【チャート型 8種】</b><br>
        🆎 ダブルボトム／👤 逆三尊／🚩 上昇フラッグ／📐 上昇三角／🔄 切下レジ→サポ転換／✨ ゴールデンクロス／📍 水平サポ反発／🔼 レジ→サポ転換<br>
        <b>【参考・底値圏パターン 2種】</b><br>
        📈 上げ三法／🚀 被せの上抜き<br>
        <b>【益（酒田 底値圏・継続） 10種】</b><br>
        ✨ 陽の二つ星／🔥 陰線連続後の大陽線／🦅 つばめ返し／🎏 陽のたすき線／🫶 陰の両つつみ／⚔️ 切り込み線／🎣 二本たくり線／🎋 上振れたすき／🤝 <b>陽の包み線</b>／📌 <b>強気ピンバー</b><br>
        <b>【微益（初動・継続弱） 8種】</b><br>
        🤰 はらみ線／🪟 上昇窓／🎖 赤三兵／🧱 三積み上げ／🔝 リバーサルハイ／🏹 スラストアップ／🌟 宴の明星／🚧 赤三兵先詰まり
        </span>
      </div>
      <div>
        <b style="color:#C0392B;">🔴 売りパターン 27種</b><br>
        <span style="font-size:0.74rem;color:#4A5568;line-height:1.35;">
        <b>【チャート型 8種】</b><br>
        🅜 ダブルトップ／👑 三尊天井／🏴 下降フラッグ／📉 下降三角／🔀 切上サポ転換／💀 デッドクロス／📌 水平レジ反落／🔽 サポ→レジ転換<br>
        <b>【酒田・天井圏（今すぐ売り） 14種】</b><br>
        🪢 首吊り線／🐦 三羽鳥／🍡 団子天井／👶 捨て子線／🟩 陽の陽はらみ／🫂 最後の抱き線／⚔ ツタイ打ち返し／🔝 三手放れ寄せ線／☁ 下げ足の被せ／🟥 陽の陰はらみ／🫂 <b>陰の包み線</b>／⭐ <b>弱気ピンバー</b>／🌊 波高い線／🪦 陰線五本<br>
        <b>【酒田・待って売れ（下降継続） 7種】</b><br>
        ⬇ 下放れ二本黒／📉 下げ三法／👻 バケ線／😴 下値遊び／🎀 下放れタスキ／🔻 下放れ並び赤／🗡 入り首
        </span>
      </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    tab_single, tab_scan, tab_guide = st.tabs([
        "🔍 個別銘柄 詳細検出",
        "🌐 複数銘柄 一括スキャン",
        "📖 ローソク足の読み方",
    ])

    # ────────────────────────────────────────────
    # タブ1: 個別銘柄の詳細検出
    # ────────────────────────────────────────────
    with tab_single:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            cp_ticker = st.text_input(
                "ティッカーシンボル（例: 7203.T / AAPL / USDJPY=X / BTC-USD / ^N225）",
                value="AAPL",
                key="cp_ticker",
            ).strip()
        with c2:
            cp_period = st.selectbox("期間", ["3mo", "6mo", "1y", "2y"], index=1, key="cp_period")
        with c3:
            cp_interval = st.selectbox("足種", ["1d", "1h", "30m", "15m"], index=0, key="cp_interval")
        with c4:
            cp_direction_label = st.selectbox("方向", ["🟢🔴 両方", "🟢 買いのみ", "🔴 売りのみ"], index=0, key="cp_direction")
            cp_direction = {"🟢🔴 両方": "ALL", "🟢 買いのみ": "BUY", "🔴 売りのみ": "SELL"}[cp_direction_label]

        if st.button("🔍 パターン検出を実行", type="primary", use_container_width=True, key="cp_run"):
            with st.spinner("57パターンを検出中..."):
                result = analyze_ticker_patterns(cp_ticker, period=cp_period, interval=cp_interval, direction=cp_direction)

            if result is None:
                st.error("❌ データを取得できませんでした。ティッカーを確認してください。")
            else:
                # ─── 総合判定サマリー ───
                verdict = result["verdict"]
                overall = result["overall"]
                cur = result["current_price"]
                patterns = result["patterns"]

                banner_color = {
                    "STRONG_BUY": "linear-gradient(135deg,#006837 0%,#0B6B3A 100%)",
                    "BUY": "linear-gradient(135deg,#0B3D91 0%,#1A4CAB 100%)",
                    "STRONG_SELL": "linear-gradient(135deg,#8B0000 0%,#C0392B 100%)",
                    "SELL": "linear-gradient(135deg,#C0392B 0%,#DC4A3B 100%)",
                    "CONFLICT": "linear-gradient(135deg,#7B2CBF 0%,#9D4EDD 100%)",
                    "WATCH_BUY": "linear-gradient(135deg,#2E7D32 0%,#66BB6A 100%)",
                    "WATCH_SELL": "linear-gradient(135deg,#D84315 0%,#FF7043 100%)",
                    "WATCH": "linear-gradient(135deg,#C9A961 0%,#E0C37A 100%)",
                    "NEUTRAL": "linear-gradient(135deg,#6B7280 0%,#94A3B8 100%)",
                }.get(overall, "linear-gradient(135deg,#6B7280 0%,#94A3B8 100%)")

                st.markdown(f"""
                <div style="background:{banner_color};color:#fff;padding:18px 20px;border-radius:4px;margin:12px 0;border:1px solid #C9A961;">
                <div style="font-size:1.4rem;font-weight:700;letter-spacing:2px;">{verdict}</div>
                <div style="font-size:0.9rem;margin-top:6px;opacity:0.95;">
                    現在値: <b>{cur}</b>　|　検出パターン数: <b>{len(patterns)}</b>　|　ティッカー: <b>{cp_ticker}</b>　|　足種: {cp_interval} / 期間 {cp_period}
                </div>
                </div>
                """, unsafe_allow_html=True)

                if not patterns:
                    st.info("現在、対象パターンは検出されていません。別の銘柄・期間・足種・方向をお試しください。")
                else:
                    # ─── 検出されたパターン一覧 ───
                    st.markdown("### 🎯 検出パターン一覧")

                    summary_rows = []
                    for p in patterns:
                        dir_label = "🟢 買い" if p.get("direction") == "BUY" else "🔴 売り"
                        summary_rows.append({
                            "方向": dir_label,
                            "": p.get("icon", ""),
                            "パターン": p["pattern"],
                            "信頼度": f"{p['confidence']}%",
                            "状態": p["verdict"],
                            "エントリー": p.get("entry_price"),
                            "損切り": p.get("stop_loss"),
                            "目標": p.get("target_price"),
                            "RR比": p.get("risk_reward"),
                        })
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

                    # ─── 各パターンの詳細 ───
                    st.markdown("### 📋 パターン詳細と戦略")
                    for p in patterns:
                        is_buy = p.get("direction") == "BUY"
                        dir_emoji = "🟢" if is_buy else "🔴"
                        header = f"{dir_emoji} {p.get('icon','')} {p['pattern']} — 信頼度 {p['confidence']}%"
                        with st.expander(header, expanded=(p['confidence'] >= 70)):
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            entry = p.get("entry_price", 0)
                            stop = p.get("stop_loss", 0)
                            target = p.get("target_price", 0)
                            stop_pct = round((stop - entry) / max(entry, 1e-9) * 100, 2)
                            target_pct = round((target - entry) / max(entry, 1e-9) * 100, 2)
                            target_sign = "+" if target_pct >= 0 else ""
                            cc1.metric("エントリー", f"{entry}")
                            cc2.metric("損切り", f"{stop}", delta=f"{stop_pct}%")
                            cc3.metric("目標", f"{target}", delta=f"{target_sign}{target_pct}%")
                            cc4.metric("R:R比", f"{p.get('risk_reward')} : 1")

                            st.markdown(f"**📖 解説:** {p.get('description','')}")
                            st.markdown(f"**状態:** {p['verdict']}")

                            # パターン固有の構成要素
                            details_md = ""
                            if "bottom1_price" in p:
                                details_md = f"1つ目の谷: {p['bottom1_price']} / 2つ目の谷: {p['bottom2_price']} / ネックライン: {p['neckline']}"
                            elif "top1_price" in p:
                                details_md = f"1つ目の山: {p['top1_price']} / 2つ目の山: {p['top2_price']} / ネックライン: {p['neckline']}"
                            elif "head" in p and "left_shoulder" in p:
                                details_md = f"左肩: {p['left_shoulder']} / 頭: {p['head']} / 右肩: {p['right_shoulder']} / ネック: {p['neckline']}"
                            elif "pole_gain_pct" in p:
                                details_md = f"ポール上昇率: +{p['pole_gain_pct']}% / フラッグ上限: {p['flag_top']} / フラッグ下限: {p['flag_bottom']}"
                            elif "pole_drop_pct" in p:
                                details_md = f"ポール下落率: {p['pole_drop_pct']}% / フラッグ上限: {p['flag_top']} / フラッグ下限: {p['flag_bottom']}"
                            elif "resistance" in p and "support_slope_pct_per_bar" in p:
                                details_md = f"水平抵抗: {p['resistance']} / 支持線勾配: {p['support_slope_pct_per_bar']}%/bar / タッチ数（高値/安値）: {p['high_touches']}/{p['low_touches']}"
                            elif "support" in p and "resistance_slope_pct_per_bar" in p:
                                details_md = f"水平支持: {p['support']} / 抵抗線勾配: {p['resistance_slope_pct_per_bar']}%/bar / タッチ数（高値/安値）: {p['high_touches']}/{p['low_touches']}"
                            elif "trendline_now" in p:
                                rt = f"（リテスト確認: {p['retest_bars_ago']}本前）" if p.get("retest_confirmed") else "（リテスト未確認）"
                                details_md = f"現在のトレンドライン値: {p['trendline_now']} / 傾き: {p['slope_pct_per_bar']}%/bar {rt}"
                            elif "short_ma_now" in p:
                                cross_ago = p.get("cross_bar_ago", 0)
                                cross_ago_txt = "本日発生" if cross_ago == 0 else f"{cross_ago}本前に発生"
                                details_md = (
                                    f"短期MA: {p['short_ma_now']}（傾き {p['short_slope_pct']:+}%） / "
                                    f"長期MA: {p['long_ma_now']}（傾き {p['long_slope_pct']:+}%） / "
                                    f"クロス: {cross_ago_txt}（@価格 {p['cross_price']}）"
                                )
                            elif "support_price" in p:
                                b_txt = "✅ 反発確認" if p.get("bounce_confirmed") else "⏳ 反発未確認"
                                details_md = (
                                    f"水平サポート: {p['support_price']}（過去 {p['touches']}回タッチ）/ "
                                    f"現在値からの距離: {p['distance_to_support_pct']}% / {b_txt}"
                                )
                            elif "resistance_price" in p:
                                b_txt = "✅ 反落確認" if p.get("rejection_confirmed") else "⏳ 反落未確認"
                                details_md = (
                                    f"水平レジスタンス: {p['resistance_price']}（過去 {p['touches']}回タッチ）/ "
                                    f"現在値からの距離: {p['distance_to_resistance_pct']}% / {b_txt}"
                                )
                            elif "flipped_line_price" in p:
                                orig = p.get("original_touches_as_resistance") or p.get("original_touches_as_support")
                                details_md = (
                                    f"役割反転ライン: {p['flipped_line_price']}（元は {orig}回反応）/ "
                                    f"リテスト確認: {p['bars_since_retest']}本前"
                                )
                            if details_md:
                                st.caption(f"🔢 構成要素: {details_md}")

                    # ─── 価格チャートで可視化 ───
                    st.markdown("### 📈 価格チャート（パターン重ね描き）")
                    df = result["df"]
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                        name="価格",
                        increasing=dict(line=dict(color="#C0392B"), fillcolor="#C0392B"),
                        decreasing=dict(line=dict(color="#1E3A8A"), fillcolor="#1E3A8A"),
                    ))

                    # MA系パターンが含まれるなら MA ラインを重ねる
                    ma_pattern = next((p for p in patterns if "short_ma_now" in p), None)
                    if ma_pattern is not None:
                        import re as _re
                        m = _re.search(r"（(\d+)MA × (\d+)MA）", ma_pattern["pattern"])
                        if m:
                            short_n, long_n = int(m.group(1)), int(m.group(2))
                            sma_short = df["Close"].rolling(short_n).mean()
                            sma_long = df["Close"].rolling(long_n).mean()
                            fig.add_trace(go.Scatter(
                                x=df.index, y=sma_short, mode="lines",
                                name=f"{short_n}MA（短期）",
                                line=dict(color="#E67E22", width=1.6),
                            ))
                            fig.add_trace(go.Scatter(
                                x=df.index, y=sma_long, mode="lines",
                                name=f"{long_n}MA（長期）",
                                line=dict(color="#0B3D91", width=1.6),
                            ))
                            # クロスポイントに★マーカー
                            cross_ago = ma_pattern.get("cross_bar_ago", 0)
                            if cross_ago is not None and 0 <= cross_ago < len(df):
                                cx = df.index[-1 - cross_ago]
                                cy = ma_pattern["cross_price"]
                                sym = "star" if ma_pattern["direction"] == "BUY" else "x"
                                col = "#D4AF37" if ma_pattern["direction"] == "BUY" else "#8B0000"
                                fig.add_trace(go.Scatter(
                                    x=[cx], y=[cy], mode="markers+text",
                                    marker=dict(size=18, color=col, symbol=sym, line=dict(color="#FFFFFF", width=2)),
                                    text=[ma_pattern["icon"]], textposition="top center",
                                    name=f"{ma_pattern['pattern']}",
                                    showlegend=False,
                                ))

                    # パターンごとのライン重ね（買い/売りで色分け）
                    for p in patterns:
                        is_buy = p.get("direction") == "BUY"
                        line_color = "#0B3D91" if is_buy else "#C0392B"
                        if "neckline" in p:
                            fig.add_hline(y=p["neckline"], line=dict(color="#C9A961", dash="dash", width=1.5),
                                          annotation_text=f"{p.get('icon','')} ネック {p['neckline']}", annotation_position="top right")
                        if "flag_top" in p and is_buy:
                            fig.add_hline(y=p["flag_top"], line=dict(color="#006837", dash="dot"),
                                          annotation_text=f"🚩 フラッグ上限 {p['flag_top']}")
                        if "flag_bottom" in p and not is_buy:
                            fig.add_hline(y=p["flag_bottom"], line=dict(color="#C0392B", dash="dot"),
                                          annotation_text=f"🏴 フラッグ下限 {p['flag_bottom']}")
                        if "resistance" in p and "support_slope_pct_per_bar" in p:
                            fig.add_hline(y=p["resistance"], line=dict(color="#0B3D91", dash="dashdot"),
                                          annotation_text=f"📐 水平抵抗 {p['resistance']}")
                        if "support" in p and "resistance_slope_pct_per_bar" in p:
                            fig.add_hline(y=p["support"], line=dict(color="#C0392B", dash="dashdot"),
                                          annotation_text=f"📉 水平支持 {p['support']}")
                        if "support_price" in p:
                            fig.add_hline(y=p["support_price"], line=dict(color="#006837", dash="solid", width=2),
                                          annotation_text=f"📍 水平サポート {p['support_price']} ({p['touches']}回)", annotation_position="top left")
                        if "resistance_price" in p:
                            fig.add_hline(y=p["resistance_price"], line=dict(color="#C0392B", dash="solid", width=2),
                                          annotation_text=f"📌 水平レジスタンス {p['resistance_price']} ({p['touches']}回)", annotation_position="top left")
                        if "flipped_line_price" in p:
                            flip_color = "#0B3D91" if is_buy else "#8B0000"
                            flip_icon = "🔼" if is_buy else "🔽"
                            fig.add_hline(y=p["flipped_line_price"], line=dict(color=flip_color, dash="solid", width=2.5),
                                          annotation_text=f"{flip_icon} 役割反転 {p['flipped_line_price']}", annotation_position="top right")
                        if "target_price" in p:
                            fig.add_hline(y=p["target_price"], line=dict(color="#D4AF37", dash="dot", width=1),
                                          annotation_text=f"🎯 目標 {p['target_price']}", annotation_position="bottom right")
                        if "stop_loss" in p:
                            fig.add_hline(y=p["stop_loss"], line=dict(color="#8B0000", dash="dot", width=1),
                                          annotation_text=f"🛑 損切 {p['stop_loss']}", annotation_position="bottom left")

                    fig.update_layout(
                        template="plotly_white",
                        height=540,
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=30, b=10),
                        paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFBFD",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # トレード計画サマリー
                    top = patterns[0]
                    is_buy_top = top.get("direction") == "BUY"
                    dir_text = "🟢 買い方向（参考）" if is_buy_top else "🔴 売り方向（参考）"
                    plan_msg = f"""
                    **🎯 最有力パターンのトレード計画 — {dir_text}**

                    - パターン: **{top['pattern']}**
                    - エントリー: **{top.get('entry_price')}**（現在値 {cur}）
                    - 損切り（逆指値）: **{top.get('stop_loss')}**
                    - 目標（利確）: **{top.get('target_price')}**
                    - リスクリワード比: **{top.get('risk_reward')} : 1**
                    - 状態: {top['verdict']}
                    """
                    if is_buy_top:
                        st.success(plan_msg)
                    else:
                        st.error(plan_msg)

    # ────────────────────────────────────────────
    # タブ2: 複数銘柄 一括スキャン
    # ────────────────────────────────────────────
    with tab_scan:
        st.markdown("#### 🌐 複数銘柄を一括でパターンスキャン")
        st.caption("リストの銘柄について、現在買いパターンが形成されているものをランキング表示します")

        default_list = "7203.T, 9984.T, 6758.T, 8306.T, 9432.T, AAPL, NVDA, MSFT, TSLA, GOOGL, USDJPY=X, EURJPY=X, ^N225, ^GSPC, BTC-USD, ETH-USD"
        scan_tickers_input = st.text_area(
            "ティッカーをカンマ区切りで入力",
            value=default_list,
            height=80, key="cp_scan_list",
        )

        scan_col1, scan_col2, scan_col3 = st.columns(3)
        with scan_col1:
            scan_period = st.selectbox("期間", ["3mo", "6mo", "1y"], index=1, key="cp_scan_period")
        with scan_col2:
            scan_interval = st.selectbox("足種", ["1d", "1h"], index=0, key="cp_scan_interval")
        with scan_col3:
            scan_direction_label = st.selectbox("方向", ["🟢🔴 両方", "🟢 買いのみ", "🔴 売りのみ"], index=0, key="cp_scan_direction")
            scan_direction = {"🟢🔴 両方": "ALL", "🟢 買いのみ": "BUY", "🔴 売りのみ": "SELL"}[scan_direction_label]

        if st.button("🚀 一括スキャン実行", type="primary", use_container_width=True, key="cp_scan_run"):
            tickers_list = [t.strip() for t in scan_tickers_input.split(",") if t.strip()]
            progress = st.progress(0, text="スキャン中...")
            scan_rows = []
            for idx, tk in enumerate(tickers_list):
                progress.progress((idx + 1) / max(len(tickers_list), 1), text=f"検出中: {tk} ({idx+1}/{len(tickers_list)})")
                r = analyze_ticker_patterns(tk, period=scan_period, interval=scan_interval, direction=scan_direction)
                if r is None or not r["patterns"]:
                    continue
                for p in r["patterns"]:
                    scan_rows.append({
                        "方向": "🟢 買い" if p.get("direction") == "BUY" else "🔴 売り",
                        "ティッカー": tk,
                        "現在値": r["current_price"],
                        "": p.get("icon", ""),
                        "パターン": p["pattern"],
                        "信頼度": p["confidence"],
                        "確定": "✅" if p.get("breakout_confirmed") else "⏳",
                        "エントリー": p.get("entry_price"),
                        "損切り": p.get("stop_loss"),
                        "目標": p.get("target_price"),
                        "RR比": p.get("risk_reward"),
                        "総合判定": r["verdict"],
                    })
            progress.empty()

            if not scan_rows:
                st.warning("対象銘柄でパターンは検出されませんでした。別のリストや期間・方向でお試しください。")
            else:
                df_scan = pd.DataFrame(scan_rows).sort_values("信頼度", ascending=False).reset_index(drop=True)
                buy_count = (df_scan["方向"] == "🟢 買い").sum()
                sell_count = (df_scan["方向"] == "🔴 売り").sum()
                st.success(f"✅ {df_scan['ティッカー'].nunique()}銘柄 / {len(df_scan)}パターン 検出（🟢 買い {buy_count} / 🔴 売り {sell_count}）")

                st.markdown("#### 🏆 信頼度ランキング（高い順）")
                st.dataframe(df_scan, use_container_width=True, hide_index=True)

                confirmed = df_scan[df_scan["確定"] == "✅"]
                if not confirmed.empty:
                    conf_buy = confirmed[confirmed["方向"] == "🟢 買い"]
                    conf_sell = confirmed[confirmed["方向"] == "🔴 売り"]
                    if not conf_buy.empty:
                        st.markdown("#### 🟢 買いパターン確定（参考・自己判断）")
                        st.dataframe(conf_buy, use_container_width=True, hide_index=True)
                    if not conf_sell.empty:
                        st.markdown("#### 🔴 売りパターン確定（参考・自己判断）")
                        st.dataframe(conf_sell, use_container_width=True, hide_index=True)

    with tab_guide:
        render_candlestick_guide()


# ════════════════════════════════════════════════
#  💎 ファンダメンタル売買判断（大和証券流ルール）
# ════════════════════════════════════════════════
elif page == "💎 ファンダメンタル売買判断":
    st.title("💎 ファンダメンタル売買判断")
    st.caption("参考スクリーニング条件｜時価総額・PER・増収率・配当性向（**投資助言ではありません**）")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#F4F7FB 0%,#E8EEF8 100%);border-left:4px solid #C9A961;padding:12px 16px;border-radius:3px;margin-bottom:14px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div>
          <b style="color:#006837;">🟢 買いサイン（4条件）</b>
          <ul style="margin:6px 0 0 0;padding-left:20px;font-size:0.85rem;color:#4A5568;">
            <li>時価総額 <b>{BUY_MARKET_CAP_MAX_JPY/1e8:.0f}億円以下</b>（小型成長余地）</li>
            <li><b>{BUY_CONSEC_GROWTH_YEARS}期以上</b>連続増収（成長企業）</li>
            <li>PER <b>{BUY_PER_MIN:.0f}〜{BUY_PER_MAX:.0f}倍</b>（割安レンジ）</li>
            <li>株価横ばい × 業績好調（割安放置）</li>
          </ul>
        </div>
        <div>
          <b style="color:#C0392B;">🔴 売りサイン（3条件）</b>
          <ul style="margin:6px 0 0 0;padding-left:20px;font-size:0.85rem;color:#4A5568;">
            <li>配当性向 <b>{SELL_PAYOUT_RATIO_MAX*100:.0f}%以上</b>（還元過多）</li>
            <li><b>{SELL_CONSEC_DECLINE_YEARS}期以上</b>連続減収（業績悪化）</li>
            <li>PER <b>{SELL_PER_MIN:.0f}倍以上</b>（割高）</li>
          </ul>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    fund_tab1, fund_tab2 = st.tabs(["🔎 個別銘柄 詳細分析", "🌐 複数銘柄 一括スクリーニング"])

    # ─── 個別銘柄 ───
    with fund_tab1:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            fund_ticker = st.text_input(
                "銘柄ティッカー",
                value="7203.T",
                key="fund_ticker",
                help="例: 7203.T (トヨタ), 9984.T (ソフトバンクG), AAPL (Apple)"
            )
        with col_b:
            st.write("")
            st.write("")
            fund_run = st.button("💎 分析実行", type="primary", use_container_width=True, key="fund_run")

        if fund_run and fund_ticker:
            with st.spinner(f"{fund_ticker} のファンダメンタル分析中..."):
                try:
                    fund = analyze_fundamentals(fund_ticker.strip().upper())
                except Exception as e:
                    st.error(f"分析エラー: {e}")
                    fund = None

            if fund and not fund.get("error"):
                verdict = fund["verdict"]
                vcolors = {
                    "STRONG_BUY": ("#006837", "#E8F5E9"),
                    "BUY": ("#2E7D32", "#F1F8E9"),
                    "WATCH_BUY": ("#FB8C00", "#FFF8E1"),
                    "CONFLICT": ("#795548", "#EFEBE9"),
                    "NEUTRAL": ("#607D8B", "#ECEFF1"),
                    "SELL": ("#C0392B", "#FCE4E4"),
                    "STRONG_SELL": ("#8B0000", "#FDECEC"),
                }
                fg, bg = vcolors.get(verdict, ("#37474F", "#ECEFF1"))

                st.markdown(f"""
                <div style="background:{bg};border-left:6px solid {fg};padding:16px 20px;border-radius:3px;margin:14px 0;">
                  <div style="font-size:0.75rem;color:#666;letter-spacing:2px;">銘柄: {fund['symbol']} ／ {fund['name']}</div>
                  <div style="font-size:1.4rem;font-weight:700;color:{fg};margin-top:4px;">{fund['action']}</div>
                  <div style="font-size:0.85rem;color:#444;margin-top:6px;">
                    買い条件: <b>{len(fund['buy_signals'])}/4</b> ／
                    売り条件: <b>{len(fund['sell_signals'])}/3</b> ／
                    総合スコア: <b>{fund['score']:+d}</b>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # 主要指標
                m1, m2, m3, m4 = st.columns(4)
                mc_jpy = fund.get("market_cap_jpy")
                m1.metric(
                    "時価総額",
                    f"{mc_jpy/1e8:.1f}億円" if mc_jpy else "—",
                    delta="✓ 基準内" if mc_jpy and mc_jpy <= BUY_MARKET_CAP_MAX_JPY else None
                )
                per = fund.get("per")
                m2.metric(
                    "PER",
                    f"{per:.1f}倍" if per else "—",
                    delta=("✓ 割安" if per and BUY_PER_MIN <= per <= BUY_PER_MAX else
                           ("⚠ 割高" if per and per >= SELL_PER_MIN else None))
                )
                payout = fund.get("payout_ratio")
                m3.metric(
                    "配当性向",
                    f"{payout*100:.1f}%" if payout else "—",
                    delta="⚠ 還元過多" if payout and payout >= SELL_PAYOUT_RATIO_MAX else None
                )
                m4.metric(
                    "連続増収",
                    f"{fund['consec_growth_years']}期",
                    delta=f"連続減収 {fund['consec_decline_years']}期" if fund['consec_decline_years'] > 0 else None
                )

                # 買い・売りシグナル詳細
                sig_l, sig_r = st.columns(2)
                with sig_l:
                    st.markdown("##### 🟢 買いシグナル検出")
                    if fund["buy_signals"]:
                        for s in fund["buy_signals"]:
                            st.markdown(f"- {s}")
                    else:
                        st.caption("該当なし")
                with sig_r:
                    st.markdown("##### 🔴 売りシグナル検出")
                    if fund["sell_signals"]:
                        for s in fund["sell_signals"]:
                            st.markdown(f"- {s}")
                    else:
                        st.caption("該当なし")

                # 売上高履歴
                if fund["revenues"]:
                    st.markdown("##### 📊 売上高履歴（新→旧）")
                    rev_df = pd.DataFrame(fund["revenues"], columns=["年度", "売上高"])
                    rev_df["売上高(億)"] = rev_df["売上高"] / 1e8
                    rev_df["前年比%"] = rev_df["売上高"].pct_change(-1) * 100
                    st.dataframe(
                        rev_df[["年度", "売上高(億)", "前年比%"]].round(2),
                        use_container_width=True,
                        hide_index=True
                    )

                st.info(fund["reason"])

            elif fund and fund.get("error"):
                st.error(fund["error"])

    # ─── 一括スクリーニング ───
    with fund_tab2:
        default_list = "\n".join([
            "7203.T", "6758.T", "7974.T", "9984.T", "9983.T",
            "8306.T", "6861.T", "8035.T",
            "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA",
        ])
        tickers_txt = st.text_area(
            "銘柄リスト（1行1銘柄）",
            value=default_list,
            height=180,
            key="fund_batch_list"
        )
        batch_run = st.button("🌐 一括スクリーニング実行", type="primary", use_container_width=True, key="fund_batch_run")

        if batch_run and tickers_txt.strip():
            syms = [s.strip().upper() for s in tickers_txt.splitlines() if s.strip()]
            with st.spinner(f"{len(syms)}銘柄を分析中..."):
                df_batch = batch_screen(syms)

            if not df_batch.empty:
                strong_buy = df_batch[df_batch["判定"].str.contains("強い買い", na=False)]
                buy = df_batch[df_batch["判定"].str.contains("買い推奨", na=False)]
                strong_sell = df_batch[df_batch["判定"].str.contains("強い売り", na=False)]
                sell = df_batch[df_batch["判定"].str.contains("売り推奨", na=False)]

                sm1, sm2, sm3, sm4 = st.columns(4)
                sm1.metric("🟢🟢 強い買い", len(strong_buy))
                sm2.metric("🟢 買い", len(buy))
                sm3.metric("🔴 売り", len(sell))
                sm4.metric("🔴🔴 強い売り", len(strong_sell))

                def _row_style(row):
                    v = str(row.get("判定", ""))
                    if "強い買い" in v:
                        return ["background-color:#E8F5E9"] * len(row)
                    if "買い推奨" in v:
                        return ["background-color:#F1F8E9"] * len(row)
                    if "強い売り" in v:
                        return ["background-color:#FDECEC"] * len(row)
                    if "売り推奨" in v:
                        return ["background-color:#FCE4E4"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    df_batch.style.apply(_row_style, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

                if len(strong_buy) > 0 or len(buy) > 0:
                    st.markdown("#### 🟢 買い候補ピックアップ")
                    st.dataframe(
                        pd.concat([strong_buy, buy]),
                        use_container_width=True,
                        hide_index=True
                    )
                if len(strong_sell) > 0 or len(sell) > 0:
                    st.markdown("#### 🔴 売り候補ピックアップ")
                    st.dataframe(
                        pd.concat([strong_sell, sell]),
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.warning("データを取得できませんでした。")


# ════════════════════════════════════════════════
#  株式ビューアモード（予測・スクリーニング付き）
# ════════════════════════════════════════════════
elif page == "株式ビューア":
    st.title("株式マーケット AI予測")
    st.caption("銘柄スクリーニング × 1分足予測 × テクニカル分析")

    # ─── 最新価格 ───
    latest = get_latest_price(ticker)
    if latest:
        c1, c2, c3 = st.columns(3)
        currency = _currency_for_ticker(ticker)
        is_jpy = currency == "¥"
        decimals = 0 if is_jpy and latest["price"] > 100 else 2

        with c1:
            st.metric(
                display_name,
                f"{currency}{latest['price']:,.{decimals}f}",
                delta=f"{latest['change']:+,.{decimals}f} ({latest['change_pct']:+.2f}%)",
            )
        with c2:
            st.metric("前日比", f"{currency}{latest['change']:+,.{decimals}f}")
        with c3:
            st.metric("変動率", f"{latest['change_pct']:+.2f}%")
        st.divider()

    # ─── データ取得 ───
    with st.spinner("株価データを取得中..."):
        df = fetch_market_data(ticker, period, interval)

    if df.empty:
        st.error("データを取得できませんでした。市場が閉まっている可能性があります。")
        st.stop()

    df = calculate_technical_indicators(df)

    tab_screening, tab_stock_predict, tab_stock_chart, tab_compare, tab_stock_analysis, tab_stock_data = st.tabs([
        "銘柄スクリーニング", "1分足予測", "チャート", "日米比較", "テクニカル分析", "データ",
    ])

    # ═══ タブ: 銘柄スクリーニング ═══
    with tab_screening:
        st.subheader("全銘柄スキャン — リーダー・出遅れ・大変動を検出")
        st.caption("日米30銘柄を横断スキャンし、注目銘柄を自動抽出します")

        with st.spinner("全銘柄をスキャン中...（30銘柄を一括分析）"):
            scan_results = scan_all_stocks()
            top = get_top_movers(scan_results)

        if scan_results:
            # サマリー
            leaders_n = sum(1 for r in scan_results if r["category"] == "リーダー")
            laggards_n = sum(1 for r in scan_results if r["category"] == "出遅れ")
            movers_n = sum(1 for r in scan_results if r["category"] == "大変動")
            up_n = sum(1 for r in scan_results if r["prediction"] == "上昇")
            down_n = sum(1 for r in scan_results if r["prediction"] == "下降")

            sm1, sm2, sm3, sm4, sm5 = st.columns(5)
            with sm1:
                st.metric("リーダー", f"{leaders_n}銘柄")
            with sm2:
                st.metric("出遅れ（反発候補）", f"{laggards_n}銘柄")
            with sm3:
                st.metric("大変動", f"{movers_n}銘柄")
            with sm4:
                st.metric("上昇予測", f"{up_n}銘柄")
            with sm5:
                st.metric("下降予測", f"{down_n}銘柄")

            st.divider()

            # カテゴリ別表示
            cat_filter = st.radio(
                "表示フィルタ",
                ["すべて", "リーダー（上昇牽引）", "出遅れ（反発候補）", "大変動銘柄", "上昇予測のみ"],
                horizontal=True, key="stock_filter",
            )

            show_list = scan_results
            if cat_filter == "リーダー（上昇牽引）":
                show_list = [r for r in scan_results if r["category"] == "リーダー"]
            elif cat_filter == "出遅れ（反発候補）":
                show_list = [r for r in scan_results if r["category"] == "出遅れ"]
            elif cat_filter == "大変動銘柄":
                show_list = [r for r in scan_results if r["category"] == "大変動"]
            elif cat_filter == "上昇予測のみ":
                show_list = [r for r in scan_results if r["prediction"] == "上昇"]

            for stock in show_list:
                cat = stock["category"]
                if cat == "リーダー":
                    cat_icon, cat_color = "👑", "#ffd700"
                elif cat == "出遅れ":
                    cat_icon, cat_color = "🔄", "#4da6ff"
                elif cat == "大変動":
                    cat_icon, cat_color = "⚡", "#f92f60"
                else:
                    cat_icon, cat_color = "📊", "#888"

                pred = stock["prediction"]
                if pred == "上昇":
                    pred_icon, pred_color = "📈", "#00d26a"
                elif pred == "下降":
                    pred_icon, pred_color = "📉", "#f92f60"
                else:
                    pred_icon, pred_color = "➡️", "#888"

                chg = stock["change_pct"]
                chg_color = "#00d26a" if chg > 0 else "#f92f60" if chg < 0 else "#888"
                mkt = "🇯🇵" if stock["market"] == "JP" else "🇺🇸"
                cur = "¥" if stock["market"] == "JP" else "$"

                signals_html = "".join(
                    f'<span style="background:rgba(255,255,255,0.06); border-radius:4px; '
                    f'padding:2px 6px; margin:2px; font-size:0.8rem; color:#ccc;">{s}</span>'
                    for s in stock["signals"][:3]
                )

                st.markdown(f"""
                <div style="border-left:4px solid {cat_color}; background:rgba(255,255,255,0.03);
                            padding:10px 14px; margin:5px 0; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:1.1rem; font-weight:bold; color:#e0e0e0;">
                                {mkt} {stock['name']}
                            </span>
                            <span style="color:#aaa; font-size:0.85rem;">({stock['ticker']})</span>
                            <span style="margin-left:8px; background:{cat_color}; color:#000; font-size:0.75rem;
                                    padding:2px 8px; border-radius:10px; font-weight:bold;">{cat_icon} {cat}</span>
                        </div>
                        <div style="text-align:right;">
                            <span style="font-size:1.2rem; font-weight:bold; color:#fff;">{cur}{stock['price']:,.2f}</span>
                            <span style="color:{chg_color}; font-size:0.95rem; margin-left:8px;">{chg:+.2f}%</span>
                        </div>
                    </div>
                    <div style="margin-top:6px; display:flex; gap:16px; color:#aaa; font-size:0.85rem;">
                        <span>予測: <b style="color:{pred_color};">{pred_icon}{pred}（{stock['confidence']:.0f}%）</b></span>
                        <span>RSI: {stock['rsi']:.0f}</span>
                        <span>出来高倍率: {stock['volume_ratio']:.1f}x</span>
                        <span>モメンタム: {stock['momentum']:+.1f}%</span>
                    </div>
                    <div style="margin-top:4px;">{signals_html}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("銘柄データを取得できませんでした。市場が閉まっている可能性があります。")

    # ═══ タブ: 1分足予測 ═══
    with tab_stock_predict:
        st.subheader(f"{display_name} — 1分足リアルタイム予測")

        with st.spinner("1分足データで予測中..."):
            pred_1m = predict_stock_1min(ticker)

        if pred_1m:
            d = pred_1m["direction"]
            if d == "上昇":
                d_color, d_icon = "#00d26a", "📈"
            elif d == "下降":
                d_color, d_icon = "#f92f60", "📉"
            else:
                d_color, d_icon = "#888", "➡️"

            st.markdown(f"""
            <div style="text-align:center; padding:20px; border-radius:16px;
                        background:linear-gradient(135deg, #1e1e2e, #2d2d44);
                        border:2px solid {d_color}; margin-bottom:16px;">
                <div style="color:#aaa; font-size:1rem;">1分足AI予測</div>
                <div style="color:{d_color}; font-size:2.5rem; font-weight:bold; margin:8px 0;">
                    {d_icon} {d}
                </div>
                <div style="color:#ccc; font-size:1.1rem;">
                    信頼度: {pred_1m['confidence']:.0f}%　|　
                    現在値: {currency}{pred_1m['current_price']:,.2f}
                </div>
                <div style="color:#aaa; font-size:0.9rem; margin-top:4px;">
                    予測レンジ: {currency}{pred_1m['predicted_range'][0]:,.2f} 〜 {currency}{pred_1m['predicted_range'][1]:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### 判断根拠")
            for factor in pred_1m["factors"]:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.04); border-left:3px solid {d_color};'
                    f' padding:6px 12px; margin:3px 0; border-radius:4px; color:#ccc;">{factor}</div>',
                    unsafe_allow_html=True,
                )

            shock = pred_1m.get("shock", {})
            if shock.get("is_shock"):
                st.warning(
                    "⚠️ 突発値動きを検知: "
                    f"1分 {shock.get('move_1m_pct', 0):+.3f}% / "
                    f"3分 {shock.get('move_3m_pct', 0):+.3f}% / "
                    f"z={shock.get('zscore', 0):.2f}。"
                    "予測は通常時よりブレやすいため、理由欄を優先して確認してください。"
                )

            st.markdown("#### 時間軸 × 予測価格グラフ（1/3/5/15/30/60分）")
            stock_horizon_mode = st.selectbox(
                "予測レンジ",
                ["60分", "6時間", "24時間", "3日"],
                index=0,
                key=f"stock_horizon_mode_{ticker}",
            )
            stock_horizons = {
                "60分": [1, 3, 5, 15, 30, 60],
                "6時間": [1, 3, 5, 15, 30, 60, 120, 180, 240, 360],
                "24時間": [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440],
                "3日": [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440, 2880, 4320],
            }[stock_horizon_mode]
            mh = predict_multi_horizon_path(ticker, horizons=stock_horizons)
            if mh and mh.get("points"):
                p_df = pd.DataFrame(mh["points"])
                stock_current_price = float(mh["current_price"])

                monitor_pct = st.select_slider(
                    "到達判定幅（%）",
                    options=[x for x in range(2, 22, 2)],  # 2,4,...,20%
                    value=2,
                    key=f"stock_reach_pct_{ticker}",
                )
                up_trigger = stock_current_price * (1 + monitor_pct / 100)
                down_trigger = stock_current_price * (1 - monitor_pct / 100)
                range_low = float(p_df["price"].min())
                range_high = float(p_df["price"].max())
                up_hits = p_df[p_df["price"] >= up_trigger]
                down_hits = p_df[p_df["price"] <= down_trigger]
                first_up = str(up_hits.iloc[0]["label"]) if not up_hits.empty else None
                first_down = str(down_hits.iloc[0]["label"]) if not down_hits.empty else None

                st.markdown(f"##### ±{monitor_pct}% 先読みレンジ")
                st.info(
                    f"現在 {currency}{stock_current_price:,.2f} / 監視レンジ {currency}{down_trigger:,.2f} 〜 {currency}{up_trigger:,.2f} / "
                    f"今回の予測レンジ {currency}{range_low:,.2f} 〜 {currency}{range_high:,.2f}"
                )
                if first_up or first_down:
                    up_line = f"上方向: {first_up}で +{monitor_pct}%到達見込み" if first_up else "上方向: 未到達"
                    down_line = f"下方向: {first_down}で -{monitor_pct}%到達見込み" if first_down else "下方向: 未到達"
                    st.warning(f"⚠️ {up_line} / {down_line}")
                else:
                    st.success(f"✅ この予測レンジ内では ±{monitor_pct}%は未到達見込みです。")

                st.markdown("##### シミュレーション設定（開始金額ベース）")
                s1, s2, s3 = st.columns([2, 1.6, 1.4])
                with s1:
                    start_amount = st.number_input(
                        "開始金額",
                        min_value=10_000,
                        max_value=1_000_000_000,
                        value=100_000,
                        step=10_000,
                        key=f"stock_start_amount_{ticker}",
                    )
                with s2:
                    side = st.radio("方向", ["買い", "売り"], horizontal=True, key=f"stock_side_{ticker}")
                with s3:
                    if st.button("現在値で開始", key=f"stock_set_entry_{ticker}", use_container_width=True):
                        st.session_state[f"stock_entry_price_{ticker}"] = float(mh["current_price"])
                entry_price = float(st.session_state.get(f"stock_entry_price_{ticker}", mh["current_price"]))
                st.caption(f"開始価格: {currency}{entry_price:,.2f}（クリック時固定）")

                qty = float(start_amount) / max(entry_price, 1e-9)
                if side == "買い":
                    p_df["損益(円)"] = (p_df["price"] - entry_price) * qty
                else:
                    p_df["損益(円)"] = (entry_price - p_df["price"]) * qty
                p_df["想定評価額(円)"] = float(start_amount) + p_df["損益(円)"]

                fig_path = go.Figure()
                fig_path.add_trace(go.Scatter(
                    x=p_df["label"],
                    y=p_df["price"],
                    mode="lines+markers+text",
                    text=[f"{v:+.2f}%" if i > 0 else "0.00%" for i, v in enumerate(p_df["diff_pct"])],
                    textposition="top center",
                    name="予測価格",
                    line=dict(color="#0F52BA", width=3),
                    marker=dict(size=8, color="#C9A961"),
                ))
                fig_path.update_layout(
                    template="plotly_white",
                    height=320,
                    margin=dict(l=0, r=0, t=18, b=0),
                    xaxis_title="予測時間軸",
                    yaxis_title=f"価格 ({currency})",
                )
                fig_path.add_hline(
                    y=up_trigger,
                    line_dash="dot",
                    line_color="#D32030",
                    annotation_text=f"+{monitor_pct}%ライン",
                    annotation_position="top right",
                )
                fig_path.add_hline(
                    y=down_trigger,
                    line_dash="dot",
                    line_color="#1565C0",
                    annotation_text=f"-{monitor_pct}%ライン",
                    annotation_position="bottom right",
                )
                st.plotly_chart(fig_path, use_container_width=True)
                reach_col = f"{monitor_pct}%到達"
                p_df[reach_col] = p_df["price"].apply(
                    lambda px: "到達" if abs((float(px) / max(stock_current_price, 1e-9) - 1) * 100) >= monitor_pct else "未達"
                )
                sim_cols = ["label", "price", "diff_pct", reach_col, "損益(円)", "想定評価額(円)"]
                sim_df = p_df[sim_cols].rename(columns={
                    "label": "時間軸",
                    "price": "予測価格",
                    "diff_pct": "変化率(%)",
                })
                st.dataframe(sim_df, use_container_width=True, hide_index=True)
                st.caption("※ 1分足ベースの推定。3日先は不確実性が高いため、方向感の参考として利用してください。")
                st.markdown("**この予測の原因（根拠）**")
                for reason in mh.get("reasons", []):
                    st.markdown(f"- {reason}")
                _render_midlong_range_block(
                    ticker_code=ticker,
                    currency=currency,
                    key_prefix=f"stock_midlong_{ticker}",
                    title="奇数週・数年先の予測レンジ（企業計画メモ付き）",
                    note_title="各企業の計画内容メモ（公開情報ベース）",
                )
            else:
                st.info("時間軸予測グラフを生成できませんでした。市場時間中に再度お試しください。")

            # 1分足チャート
            st.markdown("#### 1分足チャート（直近）")
            with st.spinner("1分足チャートを生成中..."):
                df_1m = fetch_market_data(ticker, "1d", "1m")

            if not df_1m.empty:
                fig_1m = go.Figure()
                fig_1m.add_trace(go.Candlestick(
                    x=df_1m["日時"], open=df_1m["始値"], high=df_1m["高値"],
                    low=df_1m["安値"], close=df_1m["終値"], name="1分足",
                    increasing_line_color="#D32030", decreasing_line_color="#1565C0",
                ))
                fig_1m.update_layout(
                    template="plotly_white", height=400,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_rangeslider_visible=False,
                )
                st.plotly_chart(fig_1m, use_container_width=True)
            else:
                st.info("1分足データは市場の営業時間中のみ取得可能です。")
        else:
            st.warning("1分足データを取得できませんでした。市場が営業時間中にお試しください。")

    # ═══ タブ: チャート ═══
    with tab_stock_chart:
        st.subheader(f"{display_name}　{selected_interval}（{selected_period}）")

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
            subplot_titles=["価格", "出来高"],
        )

        if chart_type == "ローソク足":
            fig.add_trace(go.Candlestick(
                x=df["日時"], open=df["始値"], high=df["高値"],
                low=df["安値"], close=df["終値"], name="価格",
                increasing_line_color="#D32030", decreasing_line_color="#1565C0",
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["終値"], mode="lines", name="終値",
                line=dict(color="#4da6ff", width=2),
            ), row=1, col=1)

        for col_name, color in [("MA5", "#ffa500"), ("MA25", "#ff6b6b"), ("MA75", "#a855f7")]:
            if col_name in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["日時"], y=df[col_name], mode="lines", name=col_name,
                    line=dict(color=color, width=1, dash="dot"),
                ), row=1, col=1)

        if show_bb and "BB上限(+2σ)" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["BB上限(+2σ)"], mode="lines", name="BB+2σ",
                line=dict(color="#888", width=1, dash="dash"),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["BB下限(-2σ)"], mode="lines", name="BB-2σ",
                line=dict(color="#888", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(136,136,136,0.1)",
            ), row=1, col=1)

        if "出来高" in df.columns and df["出来高"].sum() > 0:
            colors_vol = ["#00d26a" if c >= o else "#f92f60"
                          for c, o in zip(df["終値"], df["始値"])]
            fig.add_trace(go.Bar(
                x=df["日時"], y=df["出来高"], name="出来高",
                marker_color=colors_vol, opacity=0.6,
            ), row=2, col=1)

        fig.update_layout(
            template="plotly_white", height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 基本統計
        with st.expander("基本統計"):
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("期間最高値", f"{currency}{df['高値'].max():,.{decimals}f}")
            with s2:
                st.metric("期間最安値", f"{currency}{df['安値'].min():,.{decimals}f}")
            with s3:
                st.metric("平均終値", f"{currency}{df['終値'].mean():,.{decimals}f}")
            with s4:
                vol = df["終値"].pct_change().std() * 100
                st.metric("ボラティリティ", f"{vol:.3f}%")

    # ═══ タブ: 日米比較 ═══
    with tab_compare:
        st.subheader("日経平均 vs NYダウ 比較チャート")
        st.caption("両指数を正規化（基準日=100）して重ねて表示します")

        compare_period = st.selectbox(
            "比較期間",
            ["1ヶ月", "3ヶ月", "6ヶ月", "1年", "2年"],
            index=2,
            key="compare_period",
        )
        compare_period_val = {"1ヶ月": "1mo", "3ヶ月": "3mo", "6ヶ月": "6mo", "1年": "1y", "2年": "2y"}[compare_period]

        with st.spinner("日米データを取得中..."):
            df_nikkei = fetch_market_data("^N225", compare_period_val, "1d")
            df_dow = fetch_market_data("^DJI", compare_period_val, "1d")
            df_sp500 = fetch_market_data("^GSPC", compare_period_val, "1d")

        if not df_nikkei.empty and not df_dow.empty:
            fig_comp = go.Figure()

            for comp_df, name, color in [
                (df_nikkei, "日経平均", "#f92f60"),
                (df_dow, "NYダウ", "#4da6ff"),
                (df_sp500, "S&P 500", "#00d26a"),
            ]:
                if not comp_df.empty:
                    normalized = (comp_df["終値"] / comp_df["終値"].iloc[0]) * 100
                    fig_comp.add_trace(go.Scatter(
                        x=comp_df["日時"], y=normalized,
                        mode="lines", name=name,
                        line=dict(color=color, width=2),
                    ))

            fig_comp.add_hline(y=100, line_dash="dash", line_color="#666", opacity=0.5)
            fig_comp.update_layout(
                template="plotly_white", height=450,
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis_title="パフォーマンス（基準日=100）",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # パフォーマンス比較テーブル
            st.markdown("#### 期間パフォーマンス")
            perf_data = []
            for comp_df, name in [(df_nikkei, "日経平均"), (df_dow, "NYダウ"), (df_sp500, "S&P 500")]:
                if not comp_df.empty and len(comp_df) >= 2:
                    start_val = comp_df["終値"].iloc[0]
                    end_val = comp_df["終値"].iloc[-1]
                    change_pct = (end_val / start_val - 1) * 100
                    high = comp_df["高値"].max()
                    low = comp_df["安値"].min()
                    perf_data.append({
                        "指数": name,
                        "期間始値": f"{start_val:,.0f}",
                        "現在値": f"{end_val:,.0f}",
                        "騰落率": f"{change_pct:+.2f}%",
                        "期間高値": f"{high:,.0f}",
                        "期間安値": f"{low:,.0f}",
                    })
            if perf_data:
                st.dataframe(pd.DataFrame(perf_data), use_container_width=True, hide_index=True)
        else:
            st.warning("比較データを取得できませんでした。")

    # ═══ タブ: テクニカル分析 ═══
    with tab_stock_analysis:
        st.subheader(f"{display_name} テクニカル分析")

        fig_tech = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.5, 0.25, 0.25],
            subplot_titles=["価格 + 移動平均線", "RSI", "MACD"],
        )

        fig_tech.add_trace(go.Scatter(
            x=df["日時"], y=df["終値"], mode="lines", name="終値",
            line=dict(color="#4da6ff", width=2),
        ), row=1, col=1)

        for col_name, color in [("MA5", "#ffa500"), ("MA25", "#ff6b6b"), ("MA75", "#a855f7")]:
            if col_name in df.columns:
                fig_tech.add_trace(go.Scatter(
                    x=df["日時"], y=df[col_name], mode="lines", name=col_name,
                    line=dict(color=color, width=1),
                ), row=1, col=1)

        if "RSI" in df.columns:
            fig_tech.add_trace(go.Scatter(
                x=df["日時"], y=df["RSI"], mode="lines", name="RSI",
                line=dict(color="#e879f9", width=1.5),
            ), row=2, col=1)
            fig_tech.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig_tech.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

        if "MACD" in df.columns:
            fig_tech.add_trace(go.Scatter(
                x=df["日時"], y=df["MACD"], mode="lines", name="MACD",
                line=dict(color="#4da6ff", width=1.5),
            ), row=3, col=1)
            fig_tech.add_trace(go.Scatter(
                x=df["日時"], y=df["MACDシグナル"], mode="lines", name="Signal",
                line=dict(color="#ffa500", width=1.5),
            ), row=3, col=1)
            if "MACDヒストグラム" in df.columns:
                hist_colors = ["#00d26a" if v >= 0 else "#f92f60"
                               for v in df["MACDヒストグラム"]]
                fig_tech.add_trace(go.Bar(
                    x=df["日時"], y=df["MACDヒストグラム"], name="Histogram",
                    marker_color=hist_colors, opacity=0.5,
                ), row=3, col=1)

        fig_tech.update_layout(
            template="plotly_white", height=650,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_tech, use_container_width=True)

        # テクニカルサマリー
        st.markdown("#### テクニカルサマリー")
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            if "RSI" in df.columns:
                rsi_val = df["RSI"].dropna().iloc[-1] if not df["RSI"].dropna().empty else 50
                if rsi_val > 70:
                    rsi_label = "買われすぎ"
                elif rsi_val < 30:
                    rsi_label = "売られすぎ"
                else:
                    rsi_label = "中立"
                st.metric("RSI (14)", f"{rsi_val:.1f}", delta=rsi_label)
        with tc2:
            if "MACD" in df.columns and "MACDシグナル" in df.columns:
                macd_val = df["MACD"].dropna().iloc[-1] if not df["MACD"].dropna().empty else 0
                sig_val = df["MACDシグナル"].dropna().iloc[-1] if not df["MACDシグナル"].dropna().empty else 0
                macd_label = "買いシグナル" if macd_val > sig_val else "売りシグナル"
                st.metric("MACD", f"{macd_val:.2f}", delta=macd_label)
        with tc3:
            ma5_val = df["MA5"].dropna().iloc[-1] if "MA5" in df.columns and not df["MA5"].dropna().empty else 0
            ma25_val = df["MA25"].dropna().iloc[-1] if "MA25" in df.columns and not df["MA25"].dropna().empty else 0
            if ma5_val > 0 and ma25_val > 0:
                trend_label = "上昇トレンド" if ma5_val > ma25_val else "下降トレンド"
                st.metric("トレンド（MA5 vs MA25）", trend_label)

    # ═══ タブ: データ ═══
    with tab_stock_data:
        st.subheader("価格データ")
        disp_cols = ["日時", "始値", "高値", "安値", "終値"]
        if "出来高" in df.columns:
            disp_cols.append("出来高")
        display_df = df[disp_cols].copy()
        display_df = display_df.sort_values("日時", ascending=False)
        for col in ["始値", "高値", "安値", "終値"]:
            display_df[col] = display_df[col].round(2)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════
#  FXビューアモード（ピーク時刻予測付き）
# ════════════════════════════════════════════════
elif page == "FXビューア":
    st.title("FX Market Viewer")
    st.caption("為替市場ビューア｜円安/円高ピーク時刻予測付き")

    latest = get_latest_price(ticker)
    if latest:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(selected_pair, f"{latest['price']:.4f}",
                      delta=f"{latest['change']:+.4f} ({latest['change_pct']:+.3f}%)")
        with c2:
            st.metric("前日比", f"{latest['change']:+.4f}")
        with c3:
            st.metric("変動率", f"{latest['change_pct']:+.3f}%")
        st.divider()

    with st.spinner("データを取得中..."):
        df = fetch_market_data(ticker, period, interval)

    if df.empty:
        st.error("データを取得できませんでした。")
        st.stop()

    df = calculate_technical_indicators(df)

    # ピーク予測を実行
    with st.spinner("ピーク時刻を分析中..."):
        peak_result = predict_yen_peaks(df, pair_name=selected_pair)

    # 経済指標・要人発言を取得
    with st.spinner("経済指標・要人発言を分析中..."):
        econ_articles = fetch_economic_news()
        econ_summary = get_summary(econ_articles)

    # 軍事・防衛動向を取得
    with st.spinner("軍事・防衛動向を分析中..."):
        mil_articles = fetch_military_news()
        mil_summary = get_military_summary(mil_articles)

    tab_econ, tab_military, tab_peak, tab_chart_fx, tab_schedule, tab_data_fx = st.tabs([
        "経済指標・要人発言", "軍事・防衛動向", "ピーク時刻予測", "チャート", "注目スケジュール", "データ",
    ])

    # ═══ タブ: 経済指標・要人発言 ═══
    with tab_econ:
        st.subheader("経済指標・要人発言 → 円安/円高 即時判定")

        # 総合判定
        es = econ_summary["score"]
        if es > 0.05:
            sum_color = "#f92f60"
            sum_icon = "📈"
            sum_label = "円安圧力"
        elif es < -0.05:
            sum_color = "#00d26a"
            sum_icon = "📉"
            sum_label = "円高圧力"
        else:
            sum_color = "#888"
            sum_icon = "↔️"
            sum_label = "中立"

        st.markdown(f"""
        <div style="text-align:center; padding:16px; border-radius:16px;
                    background:linear-gradient(135deg, #1e1e2e, #2d2d44);
                    border:2px solid {sum_color}; margin-bottom:16px;">
            <div style="color:#aaa; font-size:1rem;">経済指標・要人発言の総合判定</div>
            <div style="color:{sum_color}; font-size:2.5rem; font-weight:bold; margin:8px 0;">
                {sum_icon} {sum_label}
            </div>
            <div style="color:#ccc; font-size:1rem;">
                スコア: {es:+.3f}　|　
                円安要因: {econ_summary['yen_weak']}件　
                円高要因: {econ_summary['yen_strong']}件　
                中立: {econ_summary['neutral']}件
            </div>
        </div>
        """, unsafe_allow_html=True)

        # フェイント警告パネル
        feint_articles = [a for a in econ_articles if a["analysis"]["feint"]["has_feint"]]
        if feint_articles:
            high_feints = [a for a in feint_articles if a["analysis"]["feint"]["feint_level"] in ["高", "中"]]
            st.markdown(f"""
            <div style="text-align:center; padding:12px; border-radius:12px;
                        background:linear-gradient(135deg, #3d2d0a, #5c4a1a);
                        border:2px solid #ffaa00; margin-bottom:16px;">
                <div style="color:#ffaa00; font-size:1.3rem; font-weight:bold;">
                    🎭 フェイント検知: {len(feint_articles)}件（うち警戒レベル中〜高: {len(high_feints)}件）
                </div>
                <div style="color:#ddd; font-size:0.9rem; margin-top:4px;">
                    要人の曖昧表現・観測気球・前言撤回・矛盾表現を検知しました。額面通りに受け取らず裏を読んでください。
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 重要度でフィルタ
        filter_importance = st.radio(
            "表示フィルタ",
            ["すべて", "🎭フェイント検知のみ", "重要度:高のみ", "円安要因のみ", "円高要因のみ"],
            horizontal=True, key="econ_filter",
        )

        filtered = econ_articles
        if filter_importance == "🎭フェイント検知のみ":
            filtered = [a for a in econ_articles if a["analysis"]["feint"]["has_feint"]]
        elif filter_importance == "重要度:高のみ":
            filtered = [a for a in econ_articles if a["analysis"]["importance"] == "高"]
        elif filter_importance == "円安要因のみ":
            filtered = [a for a in econ_articles if a["analysis"]["verdict"] == "円安要因"]
        elif filter_importance == "円高要因のみ":
            filtered = [a for a in econ_articles if a["analysis"]["verdict"] == "円高要因"]

        if not filtered:
            st.info("該当するニュースがありません。")
        else:
            for article in filtered:
                a = article["analysis"]

                if a["verdict"] == "円安要因":
                    badge = "🔴 円安"
                    border_color = "#f92f60"
                    bg = "rgba(249,47,96,0.08)"
                elif a["verdict"] == "円高要因":
                    badge = "🟢 円高"
                    border_color = "#00d26a"
                    bg = "rgba(0,210,106,0.08)"
                else:
                    badge = "⚪ 中立"
                    border_color = "#555"
                    bg = "rgba(255,255,255,0.03)"

                imp_badge = {"高": "🔥高", "中": "⚡中", "低": "・低"}.get(a["importance"], "")
                cat_badge = a["category"]
                person_str = f"👤 {a['person']}　" if a["person"] else ""

                feint = a["feint"]
                feint_badge = ""
                if feint["has_feint"]:
                    fl = feint["feint_level"]
                    feint_badge = f"　|　🎭フェイント:{fl}"

                feint_block = ""
                if feint["has_feint"] and feint["warnings"]:
                    warning_lines = "".join(
                        f'<div style="margin:3px 0; padding:4px 8px; '
                        f'background:rgba(255,170,0,0.1); border-radius:4px; '
                        f'font-size:0.85rem; color:#ffcc44;">{w}</div>'
                        for w in feint["warnings"]
                    )
                    hint = feint.get("true_direction_hint") or ""
                    hint_block = ""
                    if hint:
                        hint_block = (
                            f'<div style="margin-top:4px; padding:6px 8px; '
                            f'background:rgba(255,100,0,0.15); border-radius:4px; '
                            f'font-size:0.9rem; color:#ff8844; font-weight:bold;">'
                            f'🔮 本音推測: {hint}</div>'
                        )
                    feint_block = (
                        f'<div style="margin-top:6px; border-top:1px dashed #ffaa00; padding-top:6px;">'
                        f'{warning_lines}{hint_block}</div>'
                    )

                # 人物コンテキスト
                ctx = a.get("person_context", {})
                person_block = ""
                ctx_lines = []
                for line in ctx.get("profile_insights", []):
                    ctx_lines.append(
                        f'<div style="margin:2px 0; padding:3px 8px; font-size:0.83rem; '
                        f'color:#b8a0d8;">{line}</div>'
                    )
                for line in ctx.get("inner_circle_alerts", []):
                    ctx_lines.append(
                        f'<div style="margin:2px 0; padding:3px 8px; font-size:0.83rem; '
                        f'color:#80c8ff;">{line}</div>'
                    )
                for line in ctx.get("prediction_adjustments", []):
                    ctx_lines.append(
                        f'<div style="margin:2px 0; padding:3px 8px; font-size:0.85rem; '
                        f'color:#ffdd57; font-weight:bold;">{line}</div>'
                    )
                if ctx_lines:
                    person_block = (
                        '<div style="margin-top:6px; border-top:1px dashed #7c5cbf; padding-top:6px;">'
                        + "".join(ctx_lines) + '</div>'
                    )

                st.markdown(f"""
                <div style="border-left:4px solid {border_color}; background:{bg};
                            padding:12px 16px; margin:6px 0; border-radius:8px;">
                    <div style="font-size:1.05rem; font-weight:bold; color:#e0e0e0;">
                        {article['title']}
                    </div>
                    <div style="margin-top:6px; color:#aaa; font-size:0.85rem;">
                        {badge}　|　{imp_badge}　|　📂{cat_badge}　|　{person_str}📰 {article['source']}　🕐 {article['published']}{feint_badge}
                    </div>
                    <div style="margin-top:4px; color:#ccc; font-size:0.9rem;">
                        💡 {a['reason']}　<span style="color:{border_color};">(スコア: {a['score']:+.3f})</span>
                    </div>
                    {feint_block}
                    {person_block}
                </div>
                """, unsafe_allow_html=True)

        # ─── 要人プロファイル一覧 ───
        st.divider()
        st.subheader("要人プロファイル・側近マップ")
        st.caption("性格・意思決定パターン・側近の影響力を把握して発言の裏を先読み")

        profile_keys = list(PROFILES.keys())
        profile_tabs = st.tabs([PROFILES[k]["name"] for k in profile_keys])

        for prof_tab, pkey in zip(profile_tabs, profile_keys):
            with prof_tab:
                pf = get_profile_summary_for_display(pkey)
                if not pf:
                    continue

                st.markdown(f"### {pf['emoji']} {pf['name']}（{pf['title']}）")

                # 性格タイプ
                st.markdown(f"**タイプ: {pf['type']}**")
                st.markdown(f"**意思決定: {pf['decision_style']}**")
                st.markdown(f"**ストレス時: {pf['stress_behavior']}**")
                st.markdown(f"**ブラフ傾向: {pf['bluff_tendency']}**")

                st.markdown("#### 性格特徴")
                for trait in pf["traits"]:
                    st.markdown(f"- {trait}")

                # 側近マップ
                st.markdown("#### 側近・周辺人物")
                for person in pf["inner_circle"]:
                    inf_color = {"極めて高い": "#f92f60", "高い": "#ffa500", "中程度": "#4da6ff"}.get(
                        person["influence"], "#888")
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.04); border-radius:8px;
                                padding:10px 14px; margin:4px 0; border-left:3px solid {inf_color};">
                        <b style="color:#e0e0e0;">{person['name']}</b>
                        <span style="color:#aaa;">（{person['title']}）</span><br>
                        <span style="color:{inf_color};">影響力: {person['influence']}</span>　
                        <span style="color:#ccc;">スタンス: {person['stance']}</span><br>
                        <span style="color:#ffdd57;">🔍 {person['watch']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # 発言パターン
                st.markdown("#### 発言パターン分析")
                for pattern_type, indicators in pf["speech_patterns"].items():
                    if "フェイント" in pattern_type:
                        icon = "🎭"
                        color = "#ffaa00"
                    elif "本気" in pattern_type:
                        icon = "🎯"
                        color = "#00d26a"
                    else:
                        icon = "📌"
                        color = "#4da6ff"

                    st.markdown(f"**{icon} {pattern_type}**")
                    for ind in indicators:
                        st.markdown(
                            f'<div style="margin:2px 0 2px 16px; padding:4px 10px; '
                            f'border-left:2px solid {color}; color:#ccc; font-size:0.9rem;">'
                            f'{ind}</div>',
                            unsafe_allow_html=True,
                        )

    # ═══ タブ: 軍事・防衛動向 ═══
    with tab_military:
        st.subheader("軍事・防衛動向 → 円安/円高 影響分析")
        st.caption("米軍・自衛隊・NATO・中国軍・ロシア軍・中東情勢 等の動きから為替への影響を分析")

        if mil_articles:
            # 総合判定
            ms = mil_summary["score"]
            mt = mil_summary["tension_avg"]
            if ms > 0.05:
                m_color, m_icon, m_label = "#f92f60", "📈", "円安圧力"
            elif ms < -0.05:
                m_color, m_icon, m_label = "#00d26a", "📉", "円高圧力"
            else:
                m_color, m_icon, m_label = "#888", "↔️", "中立"

            # 緊張度メーター
            t_color = "#00d26a" if mt < 0.3 else ("#ffa500" if mt < 0.6 else "#f92f60")
            t_label = "低い" if mt < 0.3 else ("中程度" if mt < 0.6 else "高い")

            st.markdown(f"""
            <div style="text-align:center; padding:16px; border-radius:16px;
                        background:linear-gradient(135deg, #1e1e2e, #2d2d44);
                        border:2px solid {m_color}; margin-bottom:12px;">
                <div style="color:#aaa; font-size:1rem;">軍事情勢の総合判定</div>
                <div style="color:{m_color}; font-size:2.2rem; font-weight:bold; margin:8px 0;">
                    {m_icon} {m_label}
                </div>
                <div style="color:#ccc; font-size:1rem;">
                    円安要因: {mil_summary['yen_weak']}件　
                    円高要因: {mil_summary['yen_strong']}件　
                    中立: {mil_summary['neutral']}件
                </div>
                <div style="margin-top:8px; color:{t_color}; font-size:1.1rem; font-weight:bold;">
                    🌡️ 世界緊張度: {mt:.0%}（{t_label}）
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 最大緊張イベントのピーク時刻
            mte = mil_summary.get("max_tension_event")
            if mte and mte.get("peak_timing"):
                pt = mte["peak_timing"]
                st.markdown(f"""
                <div style="padding:12px; border-radius:12px;
                            background:rgba(249,47,96,0.08); border:1px solid #f92f60;
                            margin-bottom:16px;">
                    <div style="color:#f92f60; font-size:1rem; font-weight:bold;">
                        ⏰ 最も緊張度の高いイベントの為替影響ピーク予測
                    </div>
                    <div style="color:#e0e0e0; font-size:0.95rem; margin-top:6px;">
                        📌 {mte['title']}<br>
                        ⏱️ ピーク時刻: <b>{pt['peak_time']}</b>（{pt['peak_date']}）<br>
                        📊 パターン: {pt['peak_pattern']}
                    </div>
                    <div style="color:#aaa; font-size:0.85rem; margin-top:8px;">
                        直後: {pt['immediate']}<br>
                        短期: {pt['short_term']}<br>
                        中期: {pt['medium_term']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 各ニュース
            for article in mil_articles:
                ma = article["analysis"]
                tension = ma["tension_level"]

                if ma["verdict"] == "円安要因":
                    a_badge = "🔴 円安"
                    a_border = "#f92f60"
                    a_bg = "rgba(249,47,96,0.08)"
                elif ma["verdict"] == "円高要因":
                    a_badge = "🟢 円高"
                    a_border = "#00d26a"
                    a_bg = "rgba(0,210,106,0.08)"
                else:
                    a_badge = "⚪ 中立"
                    a_border = "#555"
                    a_bg = "rgba(255,255,255,0.03)"

                t_bar_color = "#00d26a" if tension < 0.3 else ("#ffa500" if tension < 0.6 else "#f92f60")
                t_bar_width = int(tension * 100)
                entity_names = ", ".join(e["name"] for e in ma["entities"][:3])
                action_names = ", ".join(a_item["action"] for a_item in ma["actions"][:3]) if ma["actions"] else "動向監視"

                peak_info = ""
                if ma["peak_timing"]:
                    p = ma["peak_timing"]
                    peak_info = (
                        f'<div style="margin-top:4px; padding:4px 8px; '
                        f'background:rgba(255,255,255,0.05); border-radius:4px; '
                        f'font-size:0.85rem; color:#80c8ff;">'
                        f'⏰ 影響ピーク: {p["peak_time"]}　|　{p["peak_pattern"]}'
                        f'</div>'
                    )

                st.markdown(f"""
                <div style="border-left:4px solid {a_border}; background:{a_bg};
                            padding:12px 16px; margin:6px 0; border-radius:8px;">
                    <div style="font-size:1.05rem; font-weight:bold; color:#e0e0e0;">
                        {article['title']}
                    </div>
                    <div style="margin-top:6px; color:#aaa; font-size:0.85rem;">
                        {a_badge}　|　🎖️ {entity_names}　|　⚔️ {action_names}
                        　|　📰 {article['source']}　🕐 {article['published']}
                    </div>
                    <div style="margin-top:6px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="color:#aaa; font-size:0.85rem; min-width:60px;">緊張度:</span>
                            <div style="flex:1; background:#333; border-radius:4px; height:8px;">
                                <div style="width:{t_bar_width}%; background:{t_bar_color};
                                            height:100%; border-radius:4px;"></div>
                            </div>
                            <span style="color:{t_bar_color}; font-size:0.85rem;">{tension:.0%}</span>
                        </div>
                    </div>
                    <div style="margin-top:4px; color:#ccc; font-size:0.9rem;">
                        💡 {ma['fx_mechanism']}
                    </div>
                    {peak_info}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("現時点で重要な軍事ニュースは検出されていません。")

    # ═══ タブ: ピーク時刻予測 ═══
    with tab_peak:
        if peak_result:
            # 現在のトレンド
            trend = peak_result["current_trend"]
            if trend == "円安進行中":
                trend_color = "#f92f60"
                trend_icon = "📈"
            elif trend == "円高進行中":
                trend_color = "#00d26a"
                trend_icon = "📉"
            else:
                trend_color = "#888"
                trend_icon = "↔️"

            st.markdown(f"""
            <div style="text-align:center; padding:10px; background:rgba(255,255,255,0.05);
                        border-radius:12px; margin-bottom:16px;">
                <span style="font-size:1.1rem; color:#aaa;">現在のトレンド</span><br>
                <span style="font-size:2rem; font-weight:bold; color:{trend_color};">
                    {trend_icon} {trend}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # 円安ピーク / 円高ピーク の2カラム表示
            col_weak, col_strong = st.columns(2)

            weak = peak_result["yen_weak_peak"]
            strong = peak_result["yen_strong_peak"]

            with col_weak:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #3d0a0a, #5c1a1a);
                            border: 2px solid #f92f60; border-radius:16px;
                            padding:20px; text-align:center;">
                    <div style="color:#f92f60; font-size:1rem;">円安ピーク予測</div>
                    <div style="color:#fff; font-size:2.5rem; font-weight:bold;
                                margin:8px 0;">{weak['hour']:02d}:{weak['minute']:02d}</div>
                    <div style="color:#ccc; font-size:1rem;">
                        予測価格: {weak['estimated_price']:.3f}
                    </div>
                    <div style="color:#aaa; font-size:0.85rem; margin-top:4px;">
                        信頼度: {weak['confidence']:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_strong:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #0a3d0a, #1a5c1a);
                            border: 2px solid #00d26a; border-radius:16px;
                            padding:20px; text-align:center;">
                    <div style="color:#00d26a; font-size:1rem;">円高ピーク予測</div>
                    <div style="color:#fff; font-size:2.5rem; font-weight:bold;
                                margin:8px 0;">{strong['hour']:02d}:{strong['minute']:02d}</div>
                    <div style="color:#ccc; font-size:1rem;">
                        予測価格: {strong['estimated_price']:.3f}
                    </div>
                    <div style="color:#aaa; font-size:0.85rem; margin-top:4px;">
                        信頼度: {strong['confidence']:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")

            # 判断根拠
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("**円安ピークの根拠:**")
                for reason in weak["reasons"]:
                    st.markdown(f'<div style="background:rgba(249,47,96,0.1); border-left:3px solid #f92f60; '
                                f'padding:6px 10px; margin:3px 0; border-radius:4px; font-size:0.9rem;">'
                                f'{reason}</div>', unsafe_allow_html=True)
            with r2:
                st.markdown("**円高ピークの根拠:**")
                for reason in strong["reasons"]:
                    st.markdown(f'<div style="background:rgba(0,210,106,0.1); border-left:3px solid #00d26a; '
                                f'padding:6px 10px; margin:3px 0; border-radius:4px; font-size:0.9rem;">'
                                f'{reason}</div>', unsafe_allow_html=True)

            st.write("")

            # 時間帯別ボラティリティ（棒グラフ）
            hourly = peak_result["hourly_pattern"]
            if hourly:
                st.subheader("時間帯別ボラティリティ")
                st.caption("過去データから各時間帯の値動きの大きさを分析")

                hours = sorted(hourly.keys())
                vols = [hourly[h]["volatility"] for h in hours]
                colors = []
                for h in hours:
                    if h in [weak["hour"]]:
                        colors.append("#f92f60")
                    elif h in [strong["hour"]]:
                        colors.append("#00d26a")
                    else:
                        colors.append("#4da6ff")

                fig_vol = go.Figure(go.Bar(
                    x=[f"{h}:00" for h in hours],
                    y=vols,
                    marker_color=colors,
                    text=[f"{v:.4f}" for v in vols],
                    textposition="auto",
                ))
                fig_vol.update_layout(
                    template="plotly_white",
                    height=280,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="時間帯（日本時間）",
                    yaxis_title="ボラティリティ",
                )
                st.plotly_chart(fig_vol, use_container_width=True)
                st.caption("🔴 = 円安ピーク予測時間帯　🟢 = 円高ピーク予測時間帯　🔵 = その他")

            # 過去のピーク統計
            hist = peak_result["historical_peaks"]
            if hist["high_hours"] or hist["low_hours"]:
                st.subheader("過去のピーク出現統計")
                hc1, hc2 = st.columns(2)
                with hc1:
                    st.markdown("**高値（円安）が出やすい時間:**")
                    for item in hist["high_hours"][:5]:
                        bar_len = int(item["pct"] / 2)
                        st.markdown(f"`{item['hour']:02d}時台` {'█' * bar_len} {item['pct']}%（{item['count']}回）")
                with hc2:
                    st.markdown("**安値（円高）が出やすい時間:**")
                    for item in hist["low_hours"][:5]:
                        bar_len = int(item["pct"] / 2)
                        st.markdown(f"`{item['hour']:02d}時台` {'█' * bar_len} {item['pct']}%（{item['count']}回）")
        else:
            st.warning("ピーク予測に十分なデータがありません。期間を長くするか時間足を小さくしてください。")

    # ═══ タブ: チャート ═══
    with tab_chart_fx:
        fig = go.Figure()
        if chart_type == "ローソク足":
            fig.add_trace(go.Candlestick(
                x=df["日時"], open=df["始値"], high=df["高値"],
                low=df["安値"], close=df["終値"], name="価格",
                increasing_line_color="#D32030", decreasing_line_color="#1565C0",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["終値"], mode="lines", name="終値",
                line=dict(color="#4da6ff", width=2),
            ))

        for col_name, color in [("MA5", "#ffa500"), ("MA25", "#ff6b6b")]:
            if col_name in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["日時"], y=df[col_name], mode="lines", name=col_name,
                    line=dict(color=color, width=1, dash="dot"),
                ))

        if show_bb and "BB上限(+2σ)" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["BB上限(+2σ)"], mode="lines", name="BB+2σ",
                line=dict(color="#888", width=1, dash="dash"),
            ))
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["BB下限(-2σ)"], mode="lines", name="BB-2σ",
                line=dict(color="#888", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(136,136,136,0.1)",
            ))

        fig.update_layout(
            template="plotly_white", height=500,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 時間軸 × 予測価格グラフ（1/3/5/15/30/60分）")
        fx_horizon_mode = st.selectbox(
            "予測レンジ",
            ["60分", "6時間", "24時間", "3日"],
            index=0,
            key=f"fx_horizon_mode_{ticker}",
        )
        fx_horizons = {
            "60分": [1, 3, 5, 15, 30, 60],
            "6時間": [1, 3, 5, 15, 30, 60, 120, 180, 240, 360],
            "24時間": [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440],
            "3日": [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440, 2880, 4320],
        }[fx_horizon_mode]
        fx_mh = predict_multi_horizon_path(ticker, horizons=fx_horizons)
        if fx_mh and fx_mh.get("points"):
            p_df = pd.DataFrame(fx_mh["points"])
            fx_current_price = float(fx_mh["current_price"])

            # JPYクロス向け: 任意幅（小刻み）到達の先読みレンジ表示
            is_jpy_pair = ticker.endswith("JPY=X")
            if is_jpy_pair:
                monitor_width = st.select_slider(
                    "到達判定幅（円）",
                    options=[round(x * 0.1, 1) for x in range(3, 21)],  # 0.3〜2.0円
                    value=2.0,
                    key=f"fx_reach_width_{ticker}",
                )
                up_trigger = fx_current_price + monitor_width
                down_trigger = fx_current_price - monitor_width
                range_low = float(p_df["price"].min())
                range_high = float(p_df["price"].max())
                up_hits = p_df[p_df["price"] >= up_trigger]
                down_hits = p_df[p_df["price"] <= down_trigger]
                first_up = str(up_hits.iloc[0]["label"]) if not up_hits.empty else None
                first_down = str(down_hits.iloc[0]["label"]) if not down_hits.empty else None

                st.markdown(f"##### ±{monitor_width:.1f}円 先読みレンジ（JPYペア）")
                st.info(
                    f"現在 {fx_current_price:,.3f} / 監視レンジ {down_trigger:,.3f} 〜 {up_trigger:,.3f} / "
                    f"今回の予測レンジ {range_low:,.3f} 〜 {range_high:,.3f}"
                )
                if first_up or first_down:
                    up_line = f"上方向: {first_up}で +{monitor_width:.1f}円到達見込み" if first_up else "上方向: 未到達"
                    down_line = f"下方向: {first_down}で -{monitor_width:.1f}円到達見込み" if first_down else "下方向: 未到達"
                    st.warning(f"⚠️ {up_line} / {down_line}")
                else:
                    st.success(f"✅ この予測レンジ内では ±{monitor_width:.1f}円は未到達見込みです。")
            st.markdown("##### シミュレーション設定（開始金額ベース）")
            f1, f2, f3 = st.columns([2, 1.6, 1.4])
            with f1:
                fx_start_amount = st.number_input(
                    "開始金額(円)",
                    min_value=10_000,
                    max_value=1_000_000_000,
                    value=300_000,
                    step=10_000,
                    key=f"fx_start_amount_{ticker}",
                )
            with f2:
                fx_side = st.radio("方向", ["買い", "売り"], horizontal=True, key=f"fx_side_{ticker}")
            with f3:
                if st.button("現在レートで開始", key=f"fx_set_entry_{ticker}", use_container_width=True):
                    st.session_state[f"fx_entry_price_{ticker}"] = float(fx_mh["current_price"])
            fx_entry = float(st.session_state.get(f"fx_entry_price_{ticker}", fx_mh["current_price"]))
            st.caption(f"開始レート: {fx_entry:,.4f}（クリック時固定）")

            # 簡易換算: 開始金額を開始レートで割って保有数量を算出
            fx_qty = float(fx_start_amount) / max(fx_entry, 1e-9)
            if fx_side == "買い":
                p_df["損益(円)"] = (p_df["price"] - fx_entry) * fx_qty
            else:
                p_df["損益(円)"] = (fx_entry - p_df["price"]) * fx_qty
            p_df["想定評価額(円)"] = float(fx_start_amount) + p_df["損益(円)"]

            fig_fx_path = go.Figure()
            fig_fx_path.add_trace(go.Scatter(
                x=p_df["label"],
                y=p_df["price"],
                mode="lines+markers+text",
                text=[f"{v:+.3f}%" if i > 0 else "0.000%" for i, v in enumerate(p_df["diff_pct"])],
                textposition="top center",
                name="予測価格",
                line=dict(color="#0F52BA", width=3),
                marker=dict(size=8, color="#C9A961"),
            ))
            fig_fx_path.update_layout(
                template="plotly_white",
                height=320,
                margin=dict(l=0, r=0, t=18, b=0),
                xaxis_title="予測時間軸",
                yaxis_title=f"{selected_pair} レート",
            )
            if is_jpy_pair:
                fig_fx_path.add_hline(
                    y=up_trigger,
                    line_dash="dot",
                    line_color="#D32030",
                    annotation_text=f"+{monitor_width:.1f}円ライン",
                    annotation_position="top right",
                )
                fig_fx_path.add_hline(
                    y=down_trigger,
                    line_dash="dot",
                    line_color="#1565C0",
                    annotation_text=f"-{monitor_width:.1f}円ライン",
                    annotation_position="bottom right",
                )
            st.plotly_chart(fig_fx_path, use_container_width=True)
            if is_jpy_pair:
                reach_col = f"{monitor_width:.1f}円到達"
                p_df[reach_col] = p_df["price"].apply(
                    lambda px: "到達" if abs(float(px) - fx_current_price) >= monitor_width else "未達"
                )
                display_cols = ["label", "price", "diff_pct", reach_col, "損益(円)", "想定評価額(円)"]
            else:
                display_cols = ["label", "price", "diff_pct", "損益(円)", "想定評価額(円)"]

            fx_sim_df = p_df[display_cols].rename(columns={
                "label": "時間軸",
                "price": "予測レート",
                "diff_pct": "変化率(%)",
            })
            st.dataframe(fx_sim_df, use_container_width=True, hide_index=True)
            st.caption("※ 1分足ベースの推定。3日先は不確実性が高いため、方向感の参考として利用してください。")
            st.markdown("**この予測の原因（根拠）**")
            for reason in fx_mh.get("reasons", []):
                st.markdown(f"- {reason}")
            fx_ccy = "¥" if ticker.endswith("JPY=X") else "$"
            _render_midlong_range_block(
                ticker_code=ticker,
                currency=fx_ccy,
                key_prefix=f"fx_midlong_{ticker}",
                title="奇数週・数年先の予測レンジ（計画/テーマメモ付き）",
                note_title="通貨テーマメモ（公開情報ベース）",
            )
        else:
            st.info("時間軸予測グラフを生成できませんでした。市場時間中に再試行してください。")

    # ═══ タブ: 注目スケジュール ═══
    with tab_schedule:
        st.subheader("今後の注目イベント")
        st.caption("為替レートが大きく動きやすいタイミング")

        if peak_result and peak_result["next_volatile_times"]:
            for event in peak_result["next_volatile_times"]:
                mins = event["minutes_until"]
                if mins < 60:
                    time_str = f"あと {mins}分"
                else:
                    time_str = f"あと {mins // 60}時間{mins % 60}分"

                urgency = "🔴" if mins < 30 else ("🟡" if mins < 120 else "🔵")

                st.markdown(
                    f"{urgency} **{event['time']}** - {event['label']}　（{time_str}）"
                )

        st.write("")
        st.markdown("#### 為替が動きやすい時間帯（日本時間）")
        schedule_info = [
            ("09:55", "東京仲値", "銀行が仲値を決定。ドル買い需要で円安になりやすい"),
            ("15:00", "東京市場クローズ", "ポジション調整で方向転換が起きやすい"),
            ("16:00", "ロンドン市場オープン", "欧州勢参入で大きく動くことが多い"),
            ("21:30", "米国経済指標", "雇用統計・CPI等の発表で急変動"),
            ("22:00", "NY市場オープン", "米国勢参入で再び活発化"),
            ("00:00", "ロンドンフィキシング", "大口の為替取引が集中"),
        ]
        for time, name, desc in schedule_info:
            st.markdown(f"**{time}** - {name}  \n{desc}")

    # ═══ タブ: データ ═══
    with tab_data_fx:
        display_df = df[["日時", "始値", "高値", "安値", "終値"]].copy()
        display_df = display_df.sort_values("日時", ascending=False)
        for col in ["始値", "高値", "安値", "終値"]:
            display_df[col] = display_df[col].round(4)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════
#  ダッシュボード（全体サマリー）
# ════════════════════════════════════════════════
if page == "📊 ダッシュボード":
    st.title("マーケット・ダッシュボード")
    st.caption(f"{APP_NAME} ─ 全市場の動向・アラート・要注目銘柄を一画面でチェック")

    # ════════════════════════════════════════════════
    #  🆕 15分間隔 買値/売値 予測テーブル（最上部）
    # ════════════════════════════════════════════════
    st.markdown("""
    <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A2238 100%);color:#fff;padding:12px 18px;border-radius:4px;border-left:6px solid #C9A961;margin:8px 0 14px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="font-family:'Hiragino Mincho ProN',serif;font-size:1.15rem;font-weight:700;">⏱ FX・原油・CFD　15分先 売値/買値 予測テーブル</span>
                <div style="color:#C9A961;font-size:0.78rem;margin-top:2px;">FX(6) ｜ 原油・商品CFD(5) ｜ 主要指数CFD(8)　— 15分／30分／45分／60分先のbid/ask予想</div>
            </div>
            <div style="color:#fff;font-size:0.78rem;text-align:right;">
                生成時刻: """ + datetime.now().strftime("%H:%M:%S") + """ JST<br>
                <span style="color:#C9A961;">15分ごとに自動更新可</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    @st.cache_data(ttl=900)  # 15分キャッシュ
    def _cached_interval_table():
        return predict_all_intervals_table(), predict_all_intervals_compact(), get_all_reasonings()

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("🔄 再計算", key="dash_predict_refresh"):
            _cached_interval_table.clear()
    with col_btn2:
        view_mode = st.radio("表示", ["📋 コンパクト（15分・60分）", "📊 詳細（15/30/45/60分）"],
                             horizontal=True, label_visibility="collapsed", key="dash_predict_view")

    with st.spinner("19銘柄の15分間隔予測を生成中..."):
        full_tables, compact_tables, reasonings = _cached_interval_table()

    fx_mail_status = check_and_send_fx_move_alerts(compact_tables, reasonings)

    use_tables = compact_tables if "コンパクト" in view_mode else full_tables

    if not use_tables:
        st.warning("予測データの取得に失敗しました。")
    else:
        cat_tabs = st.tabs([f"💴 FX ({len(use_tables.get('FX', []))})",
                            f"🛢 原油・商品CFD ({len(use_tables.get('原油・商品CFD', []))})",
                            f"📈 主要指数CFD ({len(use_tables.get('指数CFD', []))})"])

        for i, cat in enumerate(["FX", "原油・商品CFD", "指数CFD"]):
            with cat_tabs[i]:
                df_cat = use_tables.get(cat)
                if df_cat is None or df_cat.empty:
                    st.info(f"{cat} のデータなし")
                else:
                    st.dataframe(df_cat, use_container_width=True, hide_index=True, height=320)

                # ── 予測根拠（原因）の表示 ──
                cat_reasonings = reasonings.get(cat, [])
                if cat_reasonings:
                    st.markdown(f"""
                    <div style="background:linear-gradient(90deg,#1A2238 0%,#0B3D91 100%);color:#C9A961;padding:8px 14px;border-radius:3px;margin-top:14px;border-left:4px solid #C9A961;font-family:'Hiragino Mincho ProN',serif;letter-spacing:1.5px;font-size:0.95rem;">
                        🔍 上記予測の根拠（なぜそう予測したのか）
                    </div>
                    """, unsafe_allow_html=True)

                    # 根拠サマリ表
                    summary_rows = []
                    for r in cat_reasonings:
                        rsn = r["reasoning"]
                        shock = rsn.get("shock", {})
                        cur = float(r["current_price"])
                        diff_60 = float(r["diff_60min_pct"])
                        vol_pct = float(rsn.get("vol_pct", 0.1))
                        pred_center = cur * (1 + diff_60 / 100)
                        pred_band = cur * (max(vol_pct, 0.05) / 100)
                        range_60 = f"{pred_center - pred_band:,.3f}〜{pred_center + pred_band:,.3f}"
                        summary_rows.append({
                            "銘柄": r["label"],
                            "60分先方向": r["direction_60min"],
                            "60分予想変化%": f"{r['diff_60min_pct']:+.3f}%",
                            "60分予測レンジ": range_60,
                            "突発": "⚠️有" if shock.get("is_shock") else "—",
                            "RSI": rsn["rsi"],
                            "EMA勾配%": f"{rsn['ema_slope_pct']:+.3f}%",
                            "ボラ%": f"{rsn['vol_pct']:.3f}%",
                            "主な原因": rsn["macro_drivers"][:60] + ("…" if len(rsn["macro_drivers"]) > 60 else ""),
                            "リスク": rsn["key_risk"][:40] + ("…" if len(rsn["key_risk"]) > 40 else ""),
                        })
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True, height=min(280, 60 + len(summary_rows) * 36))

                    # 個別カード（折りたたみ）
                    with st.expander(f"📖 {cat} 各銘柄の詳しい根拠を見る（クリックで展開）"):
                        for r in cat_reasonings:
                            rsn = r["reasoning"]
                            shock = rsn.get("shock", {})
                            shock_line = shock.get("reason", "")
                            st.markdown(f"""
                            <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {r['color_60min']};padding:11px 15px;margin:6px 0;border-radius:0 3px 3px 0;">
                                <div style="display:flex;justify-content:space-between;align-items:center;">
                                    <b style="color:#0B3D91;font-family:'Hiragino Mincho ProN',serif;font-size:1rem;">
                                        {r['label']}　
                                        <span style="color:{r['color_60min']};font-size:0.95rem;">{r['direction_60min']}（60分 {r['diff_60min_pct']:+.3f}%）</span>
                                    </b>
                                    <span style="color:#4A5568;font-size:0.78rem;">現在 {r['current_price']}</span>
                                </div>
                                <div style="margin-top:6px;font-size:0.83rem;color:#4A5568;">
                                    <b style="color:#1A2238;">📊 概要:</b> {rsn['summary']}
                                </div>
                                <div style="margin-top:5px;font-size:0.83rem;color:#1A2238;">
                                    <b style="color:#0B3D91;">📈 テクニカル根拠:</b><br>
                                    {''.join(f"&nbsp;&nbsp;• {x}<br>" for x in rsn['technical_reasons'])}
                                </div>
                                <div style="margin-top:5px;font-size:0.83rem;color:#1A2238;">
                                    <b style="color:#D32030;">🌍 {rsn['macro_label']}:</b><br>
                                    &nbsp;&nbsp;{rsn['macro_drivers']}
                                </div>
                                <div style="margin-top:5px;font-size:0.83rem;color:#8B0000;">
                                    {shock_line if shock_line else ""}
                                </div>
                                <div style="margin-top:5px;font-size:0.83rem;color:#8B0000;">
                                    {rsn['key_risk']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        st.caption("💡 売値(Bid)= 売却時の価格、買値(Ask)= 購入時の価格。スプレッドは各銘柄の標準的な参考値で算出。実際の値はFX/CFD業者により異なります。予測根拠はモメンタム・EMA勾配・RSI・ボラティリティ・銘柄固有のマクロ要因を統合したものです。")
        if fx_mail_status.get("sent"):
            st.success(f"📧 FX 0.3円アラートを {len(fx_mail_status['sent'])} 件メール送信しました。")
        elif fx_mail_status.get("candidates") and not fx_mail_status.get("configured"):
            st.info("📧 FX 0.3円アラート候補があります。メール送信には Streamlit Secrets の SMTP設定が必要です。")
        elif fx_mail_status.get("errors"):
            st.warning(f"📧 FXメール送信に失敗しました: {fx_mail_status['errors'][0].get('error', 'unknown error')}")

    st.divider()

    # アラート即時チェック
    triggered = check_all_alerts()
    if triggered:
        st.markdown(f"""
        <div style="background:linear-gradient(90deg,#FFE5E5 0%,#FFF5F5 100%);border-left:5px solid #D32030;padding:12px 16px;border-radius:3px;margin:8px 0;box-shadow:0 2px 6px rgba(211,32,48,0.1);">
            <b style="color:#D32030;font-family:'Hiragino Mincho ProN',serif;letter-spacing:2px;">◆ アラート発火中（{len(triggered)}件）</b>
        </div>
        """, unsafe_allow_html=True)
        for t in triggered[:5]:
            st.markdown(f"""
            <div style="background:linear-gradient(90deg,#FFFBF0 0%,#FFF8E1 100%);border-left:3px solid #C9A961;padding:8px 14px;margin:4px 0;font-size:0.85rem;color:#1A2238;">
                {t["message"]}
            </div>
            """, unsafe_allow_html=True)

    # 主要市場サマリー
    st.subheader("主要マーケット概況")
    market_groups = {
        "為替（FX）": [("USDJPY=X", "ドル/円"), ("EURJPY=X", "ユーロ/円"), ("GBPJPY=X", "ポンド/円"), ("AUDJPY=X", "豪ドル/円")],
        "株式指数（日米）": [("^N225", "日経平均"), ("^TPX", "TOPIX"), ("^DJI", "NYダウ"), ("^GSPC", "S&P500"), ("^IXIC", "NASDAQ"), ("^VIX", "VIX")],
        "コモディティ": [("CL=F", "WTI原油"), ("BZ=F", "ブレント原油"), ("GC=F", "金"), ("SI=F", "銀")],
        "仮想通貨": [("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana"), ("XRP-USD", "XRP")],
    }

    for grp_name, items in market_groups.items():
        st.markdown(f"""
        <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A4FA8 100%);color:#fff;padding:7px 14px;border-radius:3px 3px 0 0;font-weight:600;font-size:0.86rem;margin-top:16px;border-bottom:2px solid #C9A961;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
            <span style="color:#C9A961;">❖</span> {grp_name}
        </div>
        """, unsafe_allow_html=True)
        cols = st.columns(len(items))
        for col, (tk, label) in zip(cols, items):
            with col:
                info = get_latest_price(tk)
                if info:
                    sign = "▲" if info["change_pct"] >= 0 else "▼"
                    color = "#D32030" if info["change_pct"] >= 0 else "#1565C0"
                    st.markdown(f"""
                    <div style="background:#fff;border:1px solid #DDE3E8;border-top:none;padding:10px 12px;border-radius:0 0 3px 3px;">
                        <div style="font-size:0.72rem;color:#555;font-weight:600;">{label}</div>
                        <div style="font-size:1.3rem;font-weight:700;color:#1A1A1A;font-variant-numeric:tabular-nums;">
                            {info["price"]:,.2f}
                        </div>
                        <div style="font-size:0.85rem;color:{color};font-weight:600;font-variant-numeric:tabular-nums;">
                            {sign}{abs(info["change"]):,.2f}　({sign}{abs(info["change_pct"]):.2f}%)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#fff;border:1px solid #DDE3E8;border-top:none;padding:10px 12px;border-radius:0 0 3px 3px;">
                        <div style="font-size:0.72rem;color:#555;font-weight:600;">{label}</div>
                        <div style="font-size:1.3rem;color:#999;">—</div>
                        <div style="font-size:0.78rem;color:#999;">取得不可</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.divider()

    # 二段組: 注目銘柄 / メニュー案内
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A4FA8 100%);color:#fff;padding:7px 14px;border-radius:3px 3px 0 0;font-weight:600;font-size:0.86rem;border-bottom:2px solid #C9A961;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
            <span style="color:#C9A961;">❖</span> 本日の注目テーマ銘柄
        </div>
        <div style="background:#fff;border:1px solid #D5DDE8;border-top:none;padding:16px 18px;border-radius:0 0 3px 3px;box-shadow:0 2px 6px rgba(11,61,145,0.05);">
            <table style="width:100%;font-size:0.86rem;border-collapse:collapse;">
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;width:32%;color:#0B3D91;"><b>🤖 AI・人工知能</b></td><td style="color:#1A2238;">NVDA / PLTR / SMCI / AVGO 他</td></tr>
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;color:#0B3D91;"><b>⚛️ 量子コンピュータ</b></td><td style="color:#1A2238;">IONQ / RGTI / QBTS / IBM</td></tr>
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;color:#0B3D91;"><b>💎 レアアース</b></td><td style="color:#1A2238;">MP / TMC / LAC / 住友金属鉱山</td></tr>
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;color:#0B3D91;"><b>🚀 宇宙・衛星</b></td><td style="color:#1A2238;">RKLB / ASTS / PL / LMT</td></tr>
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;color:#0B3D91;"><b>🔋 次世代エネルギー</b></td><td style="color:#1A2238;">QS / PLUG / TSLA / ENPH</td></tr>
                <tr style="border-bottom:1px solid #D5DDE8;"><td style="padding:7px 0;color:#0B3D91;"><b>🌊 核融合・SMR</b></td><td style="color:#1A2238;">OKLO / SMR / NNE / CCJ</td></tr>
                <tr><td style="padding:7px 0;color:#0B3D91;"><b>💊 GLP-1・肥満治療</b></td><td style="color:#1A2238;">LLY / NVO / VKTX</td></tr>
            </table>
            <div style="margin-top:12px;font-size:0.78rem;color:#4A5568;border-top:1px solid #C9A961;padding-top:8px;">
                ⇒ 詳細は左メニュー「<b style="color:#0B3D91;">🚀 新興・新発掘銘柄</b>」よりご覧いただけます
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A4FA8 100%);color:#fff;padding:7px 14px;border-radius:3px 3px 0 0;font-weight:600;font-size:0.86rem;border-bottom:2px solid #C9A961;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
            <span style="color:#C9A961;">❖</span> サービスご案内（クリックで移動）
        </div>
        <div style="background:#fff;border:1px solid #D5DDE8;border-top:none;padding:12px 14px;border-radius:0 0 3px 3px;box-shadow:0 2px 6px rgba(11,61,145,0.05);">
        """, unsafe_allow_html=True)

        service_links = [
            ("🛢 原油先物予測", "ニュース＋テクニカルでAI予測", "原油先物予測"),
            ("📈 株式ビューア", "日米株式・銘柄スクリーニング", "株式ビューア"),
            ("💱 FXビューア", "円高/円安ピーク時刻予測", "FXビューア"),
            ("🚀 新興・新発掘銘柄", "11テーマ・買い時/売り時提示", "🚀 新興・新発掘銘柄"),
            ("🔔 アラート", "価格・テクニカルで自動通知", "🔔 アラート"),
            ("📈 バックテスト", "5戦略を過去データで検証", "📈 バックテスト"),
        ]

        for i, (title, desc, target_page) in enumerate(service_links):
            c_txt, c_btn = st.columns([4.8, 1.2])
            with c_txt:
                st.markdown(
                    f"<div style='color:#0B3D91;font-weight:700;margin-top:4px;'>{title}</div>"
                    f"<div style='color:#4A5568;font-size:0.82rem;margin-bottom:8px;'>{desc}</div>",
                    unsafe_allow_html=True,
                )
            with c_btn:
                if st.button("開く", key=f"svc_open_{i}", use_container_width=True):
                    st.session_state["_service_nav_target"] = target_page
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  🖥 3画面モニター（FX / 石油 / ドル — PC 3枚 or 1画面3列）
# ════════════════════════════════════════════════
elif page == "🏛 取扱検討株式・市場情報":
    st.title("🏛 取扱検討株式・市場情報")
    st.caption("サファイアブルー基調｜公開メニュー構成を網羅｜最新1分足データを反映")
    render_daiwa_market_board()

elif page == "🏦 FX/CFD ターミナル":
    st.title("🏦 FX/CFD ターミナル")
    st.caption(f"{APP_NAME} — ブローカー風レイアウト（検討用・仮想口座のみ）")
    if require_pro("cfd_terminal", title="Pro Research — CFDターミナル"):
        render_cfd_terminal()

elif page == "🖥 3画面モニター":
    st.title("🖥 3画面モニター")
    st.caption(
        f"{APP_NAME} — 為替・石油・ドル指数を同時監視。"
        "PC 3枚なら下記URLをモニターごとに開いてください。"
    )
    if not require_pro("monitor", title="Pro Research — 3画面モニター"):
        st.stop()

    _panel_filter = st.session_state.get("monitor_panel_filter", "all")
    if _qp_panel in ("fx", "oil", "dollar", "all"):
        _panel_filter = _qp_panel

    _panel_labels = {
        "all": "1画面3列（超ワイド / 3モニター横並び）",
        "fx": "為替のみ（モニター1用）",
        "oil": "石油・商品のみ（モニター2用）",
        "dollar": "ドル・指数のみ（モニター3用）",
    }
    _pf = st.radio(
        "表示パネル",
        options=list(_panel_labels.keys()),
        format_func=lambda k: _panel_labels[k],
        horizontal=True,
        index=list(_panel_labels.keys()).index(_panel_filter) if _panel_filter in _panel_labels else 0,
        key="monitor_panel_filter_ui",
    )
    st.session_state["monitor_panel_filter"] = _pf

    try:
        _base = st.context.url if hasattr(st, "context") else ""
    except Exception:
        _base = "（Streamlit のアプリURL）"
    with st.expander("📺 物理モニター3枚の開き方", expanded=_pf != "all"):
        st.markdown(
            f"""
**同じ Wi‑Fi / 同じアカウントでログインしたうえで**、ブラウザを各モニターに移して次を開きます。

| モニター | 用途 | URL（末尾に付ける） |
|---------|------|---------------------|
| 1 | 為替 | `?panel=fx` |
| 2 | 石油・商品 | `?panel=oil` |
| 3 | ドル・指数 | `?panel=dollar` |

例: `{_base}?panel=fx`（ベースURLは環境により異なります）

サイドバー **表示レイアウト → ワイド（PC全幅）** を選ぶと見やすくなります。
            """
        )

    @st.cache_data(ttl=300)
    def _cached_monitor_tables():
        from interval_predictor import predict_all_intervals_compact
        return predict_all_intervals_compact()

    with st.spinner("市場データを取得中..."):
        _mon_tables = _cached_monitor_tables()

    st.markdown('<div class="monitor-tri-grid">', unsafe_allow_html=True)
    render_tri_monitor(_mon_tables, panel_filter=_pf)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("💡 1画面3列は横幅 1400px 以上推奨。iPhone では縦に積まれます（表示レイアウト → iPhone向け）。")


# ════════════════════════════════════════════════
#  円相場 総合分析モード
#  考えられる全ての円高/円安要因を統合分析
# ════════════════════════════════════════════════
elif page == "💴 円相場 総合分析":
    st.title("円相場 総合ファクター分析")
    st.caption("円高・円安に影響する全要因（金利・原油・株式・地政学・介入リスク等）を統合的に分析")

    if st.button("🔍 全ファクター取得・分析を実行", type="primary"):
        with st.spinner("世界中の市場データを収集・分析中..."):
            yen_analysis = analyze_all_factors()
        st.session_state["yen_analysis"] = yen_analysis

    yen_analysis = st.session_state.get("yen_analysis")

    if not yen_analysis:
        st.markdown("""
        <div style="background:linear-gradient(180deg,#F4F7FB 0%,#E9EFF7 100%);border:1px solid #C9A961;border-radius:4px;padding:20px;text-align:center;color:#0B3D91;">
            <div style="font-family:'Hiragino Mincho ProN',serif;font-size:1.1rem;margin-bottom:8px;">❖ 円相場に影響する <b>11カテゴリ・約45ファクター</b> を統合分析</div>
            <div style="font-size:0.85rem;color:#4A5568;margin-bottom:14px;">
                金利・原油・天然ガス・金・銀・銅・農産物・VIX・株価・クロスレート・暗号資産・地政学リスク・介入水準
            </div>
            <div style="font-size:0.8rem;">👆 上のボタンをクリックして分析を開始してください（約30秒）</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        summary = yen_analysis["summary"]
        current_usdjpy = yen_analysis["current_usdjpy"]

        # ─── 総合判定ボックス ───
        verdict_color = summary["verdict_color"]
        verdict_text = summary["verdict"]
        strength_text = summary["verdict_strength"]
        st.markdown(f"""
        <div class="prediction-box" style="border:3px solid {verdict_color};background:linear-gradient(180deg,#fff 0%,#FAFBFD 100%);">
            <div style="font-family:'Hiragino Mincho ProN',serif;font-size:1rem;color:#4A5568;letter-spacing:2px;">❖ 総合判定 ❖</div>
            <div class="score-gauge" style="color:{verdict_color};">
                {verdict_text}（{strength_text}）
            </div>
            <div style="font-size:1rem;color:#1A2238;margin:6px 0;">
                総合バイアススコア: <b style="font-size:1.4rem;color:{verdict_color};">{summary['total_score']:+.1f}</b>
            </div>
            <div style="font-size:0.85rem;color:#4A5568;">
                円安要因 <b style="color:#D32030;">{summary['weak_factors_count']}</b> ／
                円高要因 <b style="color:#1565C0;">{summary['strong_factors_count']}</b> ／
                中立 <b>{summary['neutral_factors_count']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        spot_ctx = yen_analysis.get("spot_context")
        spot_ctx = spot_ctx if isinstance(spot_ctx, dict) else {}
        recon = yen_analysis.get("reconciliation") or {}
        broker_lens = yen_analysis.get("broker_lens") or {}

        if yen_analysis.get("spot_context") is None:
            st.warning(
                "ドル円の**実勢データを取得できませんでした**（yfinance の一時障害・取得制限など）。"
                "時間をおいて「全ファクター取得・分析」を再実行してください。"
            )

        if spot_ctx:
            c_s1, c_s2, c_s3, c_s4 = st.columns(4)
            with c_s1:
                v1 = spot_ctx.get("change_1h_yen")
                st.metric("実勢: 直近1時間 Δ円", f"{v1:+.3f}" if v1 is not None else "—")
            with c_s2:
                v6 = spot_ctx.get("change_6h_yen")
                st.metric("実勢: 直近6時間 Δ円", f"{v6:+.3f}" if v6 is not None else "—")
            with c_s3:
                v24 = spot_ctx.get("change_24h_yen")
                st.metric("実勢: 約24時間 Δ円", f"{v24:+.3f}" if v24 is not None else "—")
            with c_s4:
                vd = spot_ctx.get("change_prev_day_yen")
                st.metric("実勢: 前営業日 Δ円", f"{vd:+.3f}" if vd is not None else "—")
            if spot_ctx.get("granularity") == "daily":
                st.caption(
                    "※ 実勢は**日足ベース**です（時間足が取得できなかったため）。"
                    "1時間／6時間のΔは — 表示になりますが、24時間・前営業日と乖離判定は動きます。"
                )

        if spot_ctx.get("is_shock"):
            st.error(
                f"⚠️ **短期ショック検知**: {spot_ctx.get('shock_window', '—')} で "
                f"約 **{spot_ctx.get('shock_move_yen', 0):.2f} 円**振れ。"
                "ファクターバイアスは追いつかないことがあります。"
            )

        if recon.get("is_divergent"):
            sev = recon.get("severity", "")
            if sev == "high":
                st.error(f"🚨 **モデル乖離**: {recon.get('message', '')}")
            else:
                st.warning(f"⚠️ **モデル乖離**: {recon.get('message', '')}")

        if broker_lens.get("themes_markdown"):
            with st.expander("📑 証券レポートで一般的な着眼点（参考・一般論）", expanded=False):
                st.caption(broker_lens.get("disclaimer", ""))
                if broker_lens.get("score_context"):
                    st.markdown(broker_lens["score_context"])
                if broker_lens.get("divergence"):
                    st.markdown(broker_lens["divergence"])
                if broker_lens.get("shock"):
                    st.markdown(broker_lens["shock"])
                st.markdown("---")
                for line in broker_lens["themes_markdown"]:
                    st.markdown(f"- {line}")

        # ─── ドル円水準 & 介入リスク ───
        warn = get_intervention_warning(current_usdjpy) if current_usdjpy else None
        spread = calc_us_jp_yield_spread()

        c1, c2, c3 = st.columns(3)
        with c1:
            if current_usdjpy:
                st.metric("USD/JPY 現在値", f"{current_usdjpy:.3f}")
        with c2:
            if warn:
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {warn['color']};padding:10px 14px;border-radius:3px;">
                    <div style="font-size:0.72rem;color:#4A5568;font-weight:600;">介入リスク警戒度</div>
                    <div style="font-size:1.45rem;font-weight:700;color:{warn['color']};">{warn['level']}</div>
                    <div style="font-size:0.72rem;color:#4A5568;">{warn['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        with c3:
            if spread:
                color = "#D32030" if spread["spread_5d_change"] > 0 else "#1565C0"
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {color};padding:10px 14px;border-radius:3px;">
                    <div style="font-size:0.72rem;color:#4A5568;font-weight:600;">米日10年金利差</div>
                    <div style="font-size:1.45rem;font-weight:700;color:#1A2238;">{spread['spread']:.2f}%</div>
                    <div style="font-size:0.72rem;color:{color};">{spread['interpretation']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ─── タブ：詳細表示 ───
        t_factors, t_top, t_geo, t_intv = st.tabs([
            "📊 全ファクター一覧", "🎯 上位影響要因", "🌍 地政学リスク", "🏛 介入水準",
        ])

        # ═══ 全ファクター一覧 ═══
        with t_factors:
            for cat_name, factors in yen_analysis["categories"].items():
                # カテゴリヘッダー
                cat_score = sum(f["bias_info"]["score"] for f in factors)
                cat_color = "#D32030" if cat_score > 1 else ("#1565C0" if cat_score < -1 else "#888")
                st.markdown(f"""
                <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A4FA8 100%);color:#fff;padding:7px 14px;border-radius:3px 3px 0 0;font-weight:600;font-size:0.86rem;border-bottom:2px solid #C9A961;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;margin-top:14px;">
                    <span style="color:#C9A961;">❖</span> {cat_name}
                    <span style="float:right;color:{cat_color};">カテゴリ計: {cat_score:+.1f}</span>
                </div>
                """, unsafe_allow_html=True)

                rows = []
                for f in factors:
                    d = f["data"]
                    bi = f["bias_info"]
                    if d:
                        rows.append({
                            "銘柄": f["name"],
                            "現在値": f"{d['current']:,.4f}",
                            "前日比%": f"{d['change_pct']:+.2f}%",
                            "5日%": f"{d['change_5d']:+.2f}%",
                            "20日%": f"{d['change_20d']:+.2f}%",
                            "トレンド": d["trend"],
                            "JPY影響": "円安↑" if f["impact_type"] == "weak" else ("円高↑" if f["impact_type"] == "strong" else "状況依存"),
                            "重要度": "★" * f["weight"],
                            "現在バイアス": bi["label"],
                        })
                    else:
                        rows.append({
                            "銘柄": f["name"], "現在値": "—", "前日比%": "—",
                            "5日%": "—", "20日%": "—", "トレンド": "—",
                            "JPY影響": "—", "重要度": "★" * f["weight"], "現在バイアス": "データなし",
                        })

                df_cat = pd.DataFrame(rows)

                def _color_bias(val):
                    if "円安" in str(val):
                        return "color: #D32030; font-weight: 600;"
                    if "円高" in str(val):
                        return "color: #1565C0; font-weight: 600;"
                    return ""

                styled = df_cat.style.map(_color_bias, subset=["現在バイアス", "JPY影響"])
                st.dataframe(styled, use_container_width=True, hide_index=True)

        # ═══ 上位影響要因 ═══
        with t_top:
            col_w, col_s = st.columns(2)

            with col_w:
                st.markdown("""
                <div style="background:linear-gradient(90deg,#D32030 0%,#E04D5C 100%);color:#fff;padding:8px 14px;border-radius:3px 3px 0 0;font-weight:600;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
                    🔻 円安方向 寄与 TOP5
                </div>
                """, unsafe_allow_html=True)
                if summary["top_weak_factors"]:
                    for f in summary["top_weak_factors"]:
                        d = f["data"]
                        bi = f["bias_info"]
                        st.markdown(f"""
                        <div style="background:linear-gradient(90deg,#FFF5F5 0%,#fff 100%);border:1px solid #FFD0D0;border-left:4px solid #D32030;padding:10px 14px;margin:4px 0;border-radius:0 3px 3px 0;">
                            <div style="display:flex;justify-content:space-between;">
                                <b style="color:#D32030;">{f['name']}</b>
                                <span style="color:#888;font-size:0.78rem;">★{f['weight']} | {f['ticker']}</span>
                            </div>
                            <div style="font-size:0.85rem;color:#1A2238;margin-top:4px;">
                                {d['current']:,.4f} ／ 5日変動 {d['change_5d']:+.2f}% ／
                                <b style="color:#D32030;">スコア {bi['score']:+.2f}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("円安寄与の強い要因はなし")

            with col_s:
                st.markdown("""
                <div style="background:linear-gradient(90deg,#1565C0 0%,#3A7ECC 100%);color:#fff;padding:8px 14px;border-radius:3px 3px 0 0;font-weight:600;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
                    🔺 円高方向 寄与 TOP5
                </div>
                """, unsafe_allow_html=True)
                if summary["top_strong_factors"]:
                    for f in summary["top_strong_factors"]:
                        d = f["data"]
                        bi = f["bias_info"]
                        st.markdown(f"""
                        <div style="background:linear-gradient(90deg,#F0F5FF 0%,#fff 100%);border:1px solid #C5D7F5;border-left:4px solid #1565C0;padding:10px 14px;margin:4px 0;border-radius:0 3px 3px 0;">
                            <div style="display:flex;justify-content:space-between;">
                                <b style="color:#1565C0;">{f['name']}</b>
                                <span style="color:#888;font-size:0.78rem;">★{f['weight']} | {f['ticker']}</span>
                            </div>
                            <div style="font-size:0.85rem;color:#1A2238;margin-top:4px;">
                                {d['current']:,.4f} ／ 5日変動 {d['change_5d']:+.2f}% ／
                                <b style="color:#1565C0;">スコア {bi['score']:+.2f}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("円高寄与の強い要因はなし")

            # 解説
            st.markdown("""
            <div style="background:#FFFBF0;border:1px solid #C9A961;border-left:4px solid #C9A961;padding:12px 16px;border-radius:3px;margin-top:14px;font-size:0.85rem;color:#1A2238;line-height:1.7;">
                <b style="color:#0B3D91;">📖 スコアの読み方</b><br>
                各ファクターの「5日変動率 × 重要度」から円高/円安への寄与度を算出しています。<br>
                プラス = 円安方向、マイナス = 円高方向。<br>
                総合スコア <b>+8以上</b>: 円安バイアス、<b>-8以下</b>: 円高バイアス、<b>±8以内</b>: 中立（拮抗）。
            </div>
            """, unsafe_allow_html=True)

        # ═══ 地政学リスク ═══
        with t_geo:
            st.markdown("##### 🌍 地政学リスクと円相場への影響")
            for risk in yen_analysis["geopolitical"]:
                if risk["impact"] == "weak":
                    color = "#D32030"
                    icon = "🔻"
                    label = "円安要因"
                elif risk["impact"] == "strong":
                    color = "#1565C0"
                    icon = "🔺"
                    label = "円高要因"
                else:
                    color = "#888"
                    icon = "↔"
                    label = "状況依存"

                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {color};padding:12px 16px;margin:8px 0;border-radius:0 3px 3px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b style="color:#0B3D91;font-size:0.95rem;font-family:'Hiragino Mincho ProN',serif;">
                            {icon} {risk['region']}　<span style="color:#4A5568;font-size:0.8rem;font-weight:400;">— {risk['type']}</span>
                        </b>
                        <span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-size:0.75rem;">{label}</span>
                    </div>
                    <div style="margin-top:6px;color:#1A2238;font-size:0.85rem;">{risk['desc']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            <div style="background:#FFFBF0;border:1px solid #C9A961;padding:12px 16px;border-radius:3px;margin-top:14px;font-size:0.83rem;color:#1A2238;line-height:1.7;">
                <b style="color:#0B3D91;">💡 地政学リスクと円の関係</b><br>
                ・<b>有事の円買い</b>: かつての安全資産神話。リスクオフで円買いが発生しやすい<br>
                ・<b>資源高=円安</b>: 日本はエネルギー・食料の輸入国 → 価格高騰=貿易赤字=円安<br>
                ・<b>アジア有事</b>: 台湾・北朝鮮等は短期的に円買い、長期化なら円売り<br>
                ・<b>米中対立</b>: 人民元安に追随する形で円も売られやすい
            </div>
            """, unsafe_allow_html=True)

        # ═══ 介入水準 ═══
        with t_intv:
            st.markdown("##### 🏛 政府・日銀 介入水準（参考値）")
            for pair, levels in yen_analysis["intervention"].items():
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;padding:14px 18px;border-radius:3px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="font-family:'Hiragino Mincho ProN',serif;font-size:1.1rem;color:#0B3D91;font-weight:700;border-bottom:1px solid #C9A961;padding-bottom:6px;margin-bottom:10px;">
                        {pair}
                    </div>
                    <table style="width:100%;font-size:0.88rem;">
                        <tr><td style="padding:6px 0;color:#4A5568;width:40%;">⚠ 警戒水準</td>
                            <td><b style="color:#FDB813;">{levels['warning']:.2f} 円</b>　<span style="color:#4A5568;font-size:0.8rem;">（口先介入の可能性）</span></td></tr>
                        <tr><td style="padding:6px 0;color:#4A5568;">⛔ 介入水準</td>
                            <td><b style="color:#D32030;">{levels['intervention_likely']:.2f} 円</b>　<span style="color:#4A5568;font-size:0.8rem;">（実弾介入の可能性高）</span></td></tr>
                        {f'<tr><td style="padding:6px 0;color:#4A5568;">📌 過去の介入水準</td><td>{" / ".join(f"{l:.2f}" for l in levels.get("historical_intervention", []))}</td></tr>' if "historical_intervention" in levels else ""}
                        <tr><td style="padding:6px 0;color:#4A5568;vertical-align:top;">📝 備考</td>
                            <td style="font-size:0.83rem;color:#1A2238;">{levels.get('note', '')}</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            <div style="background:#FFE5E5;border:1px solid #D32030;padding:12px 16px;border-radius:3px;margin-top:14px;font-size:0.85rem;color:#1A2238;line-height:1.7;">
                <b style="color:#D32030;">⚠ 介入リスク警告</b><br>
                介入水準に近づくと「ボラティリティ急増」「急激な円高への巻き戻し」が発生します。
                ポジションのリスク管理を厳格に行ってください。<br>
                財務省・日銀・内閣官房長官の発言、為替報告書の文言変化にも注視。
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  ⏰ 転換点・反転予測モード
#  「ずっと円安と思っていたら急に円高」を捉える
# ════════════════════════════════════════════════
elif page == "⏰ 転換点・反転予測":
    st.title("円高 ⇄ 円安 転換点・反転予測")
    st.caption("現在のトレンドがいつまで続くか／いつ急変するか／何がトリガーになるかを統合予測")

    pair_choice = st.selectbox(
        "通貨ペア",
        ["USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"],
        format_func=lambda x: {
            "USDJPY=X": "USD/JPY (米ドル/円)",
            "EURJPY=X": "EUR/JPY (ユーロ/円)",
            "GBPJPY=X": "GBP/JPY (英ポンド/円)",
            "AUDJPY=X": "AUD/JPY (豪ドル/円)",
        }.get(x, x),
    )

    with st.spinner("トレンド分析・反転シグナル検出中..."):
        rev = predict_reversal(pair_choice)

    if rev.get("error"):
        st.error("データ取得に失敗しました")
        st.stop()

    trend = rev["trend_info"]
    keep = rev["keep_period"]
    fatigue = rev["fatigue_score"]

    # ─── 総合判定 ───
    st.markdown(f"""
    <div class="prediction-box" style="border:3px solid {rev['verdict_color']};background:linear-gradient(180deg,#fff 0%,#FAFBFD 100%);">
        <div style="font-family:'Hiragino Mincho ProN',serif;font-size:0.95rem;color:#4A5568;letter-spacing:2px;">❖ 総合判定 ❖</div>
        <div class="score-gauge" style="color:{rev['verdict_color']};">{rev['verdict']}</div>
        <div style="font-size:1rem;color:#1A2238;margin:6px 0;">{rev['verdict_detail']}</div>
        <div style="font-size:0.85rem;color:#4A5568;margin-top:8px;">
            現在トレンド: <b>{trend['trend']}</b>　|　
            連続: <b>{trend['streak_days']}日</b>　|　
            疲労度: <b style="color:{rev['verdict_color']};">{fatigue}%</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── 主要指標 ───
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("現在レート", f"{trend['current_rate']:.3f}")
    m2.metric("RSI", f"{trend['rsi']}")
    m3.metric("BB位置", f"{trend['bb_position']:+.2f}")
    m4.metric("ATR", f"{trend['atr']:.3f}")
    m5.metric("疲労度", f"{fatigue}%")

    rev_center = float(trend["current_rate"])
    rev_atr = max(float(trend.get("atr", 0.3)), 0.15)
    keep_days_raw = keep.get("keep_estimate_days", 1)
    try:
        keep_days = float(keep_days_raw)
    except (TypeError, ValueError):
        keep_days = 1.0
    horizon_scale = min(3.0, max(1.0, keep_days / 2.0))
    rev_band = rev_atr * horizon_scale
    if trend["trend_dir"] == "weak":
        rev_low = rev_center - rev_band * 0.8
        rev_high = rev_center + rev_band * 1.2
    elif trend["trend_dir"] == "strong":
        rev_low = rev_center - rev_band * 1.2
        rev_high = rev_center + rev_band * 0.8
    else:
        rev_low = rev_center - rev_band
        rev_high = rev_center + rev_band
    st.info(
        f"予測レンジ（キープ期間目安）: {rev_low:.3f} 〜 {rev_high:.3f} "
        f"（中心 {rev_center:.3f} / ATR基準 ±{rev_band:.3f}）"
    )

    st.divider()

    # ─── キープ期間予測 ───
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0B3D91 0%,#1A4FA8 100%);color:#fff;padding:8px 14px;border-radius:3px 3px 0 0;font-weight:600;font-size:0.9rem;border-bottom:2px solid #C9A961;letter-spacing:1.5px;font-family:'Hiragino Mincho ProN',serif;">
        <span style="color:#C9A961;">❖</span> このトレンドはいつまでキープできるか？
    </div>
    <div style="background:#fff;border:1px solid #D5DDE8;border-top:none;padding:18px 20px;border-radius:0 0 3px 3px;">
        <div style="display:flex;align-items:center;gap:18px;">
            <div style="font-size:2.6rem;font-weight:700;color:#0B3D91;font-family:'Hiragino Mincho ProN',serif;">
                {keep.get('keep_estimate_days', '?')}<span style="font-size:1.2rem;color:#4A5568;">日</span>
                <span style="font-size:1rem;color:#4A5568;">（約 {keep.get('keep_estimate_hours', '?')}h）</span>
            </div>
            <div style="font-size:0.95rem;color:#1A2238;line-height:1.6;">
                {keep.get('urgency', '')}<br>
                {keep.get('message', '')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # ─── タブ ───
    t_signals, t_scenarios, t_hot, t_events = st.tabs([
        "🚨 反転シグナル", "💥 急変シナリオ", "⏱ 反転ホット時刻", "📅 トリガーイベント",
    ])

    # ═══ 反転シグナル ═══
    with t_signals:
        st.markdown("#### 現在検出されているテクニカル反転シグナル")
        if not rev["reversal_signals"]:
            st.markdown("""
            <div style="background:#F0F5FF;border:1px solid #1565C0;padding:14px;border-radius:3px;color:#1565C0;">
                ✓ 現時点で強い反転シグナルなし。トレンド継続の可能性が高い
            </div>
            """, unsafe_allow_html=True)
        else:
            for s in rev["reversal_signals"]:
                if s["level"] == "extreme":
                    color = "#8B0000"
                    icon = "🔥🔥"
                elif s["level"] == "high":
                    color = "#D32030"
                    icon = "🚨"
                else:
                    color = "#FDB813"
                    icon = "⚠"

                st.markdown(f"""
                <div style="background:linear-gradient(90deg,#FFF5F5 0%,#fff 100%);border:1px solid #D5DDE8;border-left:5px solid {color};padding:12px 16px;margin:8px 0;border-radius:0 3px 3px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b style="color:{color};font-size:0.95rem;">{icon} {s['type']}</b>
                        <span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-size:0.75rem;">
                            ⏱ あと {s['trigger_window_hours']}h以内
                        </span>
                    </div>
                    <div style="margin-top:6px;color:#1A2238;font-size:0.88rem;">{s['msg']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ═══ 急変シナリオ ═══
    with t_scenarios:
        if trend["trend_dir"] == "weak":
            st.markdown("""
            <div style="background:linear-gradient(90deg,#D32030 0%,#B11825 100%);color:#fff;padding:10px 16px;border-radius:3px;margin-bottom:10px;font-family:'Hiragino Mincho ProN',serif;letter-spacing:2px;">
                ⚠ 「ずっと円安だと思っていたら急に円高」になる急変シナリオ
            </div>
            """, unsafe_allow_html=True)
        elif trend["trend_dir"] == "strong":
            st.markdown("""
            <div style="background:linear-gradient(90deg,#1565C0 0%,#0D47A1 100%);color:#fff;padding:10px 16px;border-radius:3px;margin-bottom:10px;font-family:'Hiragino Mincho ProN',serif;letter-spacing:2px;">
                ⚠ 「ずっと円高だと思っていたら急に円安」になる急変シナリオ
            </div>
            """, unsafe_allow_html=True)

        for sc in rev["scenarios"]:
            prob = sc["probability"]
            if "極めて" in prob or "高" in prob:
                p_color = "#D32030"
            elif "中" in prob:
                p_color = "#FDB813"
            else:
                p_color = "#888"

            st.markdown(f"""
            <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {p_color};padding:14px 18px;margin:10px 0;border-radius:0 3px 3px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <b style="color:#0B3D91;font-size:0.98rem;font-family:'Hiragino Mincho ProN',serif;">
                        {sc['icon']} {sc['name']}
                    </b>
                    <span style="background:{p_color};color:#fff;padding:3px 10px;border-radius:3px;font-size:0.78rem;">
                        確率: {prob}
                    </span>
                </div>
                <table style="margin-top:8px;font-size:0.85rem;color:#1A2238;width:100%;">
                    <tr><td style="color:#4A5568;width:18%;padding:3px 0;">🎯 トリガー</td><td>{sc['trigger']}</td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;">📊 想定変動</td><td><b style="color:#D32030;">{sc['expected_move']}</b></td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;">⏱ 持続期間</td><td>{sc['duration']}</td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;">👀 監視ポイント</td><td>{sc['watch']}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

    # ═══ 反転ホット時刻 ═══
    with t_hot:
        st.markdown("#### 1日のうち反転・急変が起きやすい時間帯（日本時間）")
        st.caption("過去パターンから抽出した「方向転換が頻発する時刻」")

        for ht in rev["hot_reversal_times"]:
            if "極大" in ht["type"]:
                color = "#8B0000"
            elif "急変動" in ht["type"]:
                color = "#D32030"
            elif "反転" in ht["type"]:
                color = "#0B3D91"
            else:
                color = "#1565C0"

            st.markdown(f"""
            <div style="background:#fff;border:1px solid #D5DDE8;border-left:5px solid {color};padding:11px 16px;margin:6px 0;border-radius:0 3px 3px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b style="font-family:'Hiragino Mincho ProN',serif;color:#0B3D91;font-size:1rem;">
                            🕐 {ht['time_jst']}
                        </b>
                        <span style="margin-left:10px;color:#1A2238;">{ht['name']}</span>
                    </div>
                    <span style="color:{color};font-weight:600;font-size:0.85rem;">
                        {ht['type']} {ht['freq']}
                    </span>
                </div>
                <div style="margin-top:4px;color:#4A5568;font-size:0.83rem;">{ht['reason']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ═══ トリガーイベント（次の重要発表） ═══
    with t_events:
        st.markdown("#### このトレンドを「壊す」可能性のある今後のイベント")
        events_high = keep.get("high_impact_events", [])
        if not events_high:
            st.info("今後2週間に大きなイベントはありません")
        else:
            for e in events_high:
                lvl = "★" * e["impact_level"]
                t_str = e["scheduled_at"].strftime("%m/%d (%a) %H:%M")
                trend_end_str = e["trend_window_end"].strftime("%m/%d %H:%M")
                color = "#D32030" if e["impact_level"] == 5 else "#FDB813"

                rev_risk = e.get("reversal_risk", "")
                rev_html = f'<div style="margin-top:6px;color:#D32030;font-size:0.83rem;"><b>反転リスク:</b> {rev_risk}</div>' if rev_risk else ""

                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;border-left:5px solid {color};padding:14px 18px;margin:8px 0;border-radius:0 3px 3px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:start;">
                        <div>
                            <b style="font-family:'Hiragino Mincho ProN',serif;color:#0B3D91;font-size:1rem;">
                                {e['country']} {e['name']}
                            </b>
                            <span style="color:{color};margin-left:8px;">{lvl}</span>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1rem;color:#1A2238;font-weight:600;">{t_str}</div>
                            <div style="font-size:0.75rem;color:#4A5568;">あと {e['hours_until']:.0f}時間</div>
                        </div>
                    </div>
                    <div style="margin-top:6px;color:#1A2238;font-size:0.85rem;">{e['description']}</div>
                    <div style="margin-top:6px;color:#4A5568;font-size:0.78rem;">
                        ⏱ 急変動: {e['immediate_volatility_min']}分間　／
                        高ボラ継続: {e['high_volatility_hours']}時間　／
                        トレンド影響: {e['trend_keep_hours']}時間（{trend_end_str} まで）
                    </div>
                    {rev_html}
                </div>
                """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  📅 経済イベント・カレンダー
# ════════════════════════════════════════════════
elif page == "📅 経済イベント・カレンダー":
    st.title("経済指標・要人発言 カレンダー")
    st.caption("日付・時刻・影響時間帯・トレンド継続期間を一覧で確認")

    days = st.slider("表示期間（日）", 3, 60, 14)

    events = get_upcoming_events(days_ahead=days)

    # 重要イベントのサマリー
    crit = [e for e in events if e["impact_level"] >= 4]
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("総イベント数", len(events))
    sc2.metric("最重要 ★4-5", len(crit))
    if crit:
        next_one = crit[0]
        sc3.metric(
            "次の最重要イベント",
            next_one["scheduled_at"].strftime("%m/%d %H:%M"),
            f"あと {next_one['hours_until']:.0f}h"
        )

    st.divider()

    t_table, t_timeline, t_persons = st.tabs(["📊 一覧表（時刻順）", "📋 イベントタイムライン", "👤 要人発言予定"])

    with t_table:
        st.markdown("#### 経済指標 時刻別 一覧表")
        st.caption("円高・円安に切り替わる時間帯と影響継続期間が一目で分かります")
        rows = []
        for e in sorted(events, key=lambda x: x["scheduled_at"]):
            rows.append({
                "日付": e["scheduled_at"].strftime("%m/%d (%a)"),
                "JST時刻": e["scheduled_at"].strftime("%H:%M"),
                "国": e["country"],
                "イベント": e["name"],
                "重要度": "★" * e["impact_level"],
                "高ボラ時間帯": f"{e['scheduled_at'].strftime('%H:%M')}〜{(e['scheduled_at'] + pd.Timedelta(hours=e['high_volatility_hours'])).strftime('%H:%M')}",
                "トレンドキープ目安": f"約 {e['trend_keep_hours']}時間（{e['trend_keep_hours']/24:.1f}日）",
                "あと(時間)": f"{e['hours_until']:.0f}h",
                "反転リスク": e.get("reversal_risk", "—") or "—",
            })
        df_events = pd.DataFrame(rows)
        st.dataframe(df_events, use_container_width=True, hide_index=True, height=500)

        st.markdown("##### 重要度の凡例")
        st.markdown(
            "- ★★★★★ : 即座に1-3円動く可能性（NFP/FOMC/BOJ会合）\n"
            "- ★★★★  : 0.5-1.5円程度の変動（CPI/小売売上高/PCE）\n"
            "- ★★★   : 0.3-0.8円の変動（PMI/中古住宅販売）\n"
            "- ★★    : 短期影響のみ"
        )

    with t_timeline:
        # 日付ごとにグループ化して表示
        from itertools import groupby
        sorted_evs = sorted(events, key=lambda e: e["scheduled_at"])
        for date_str, day_events in groupby(
            sorted_evs, key=lambda e: e["scheduled_at"].strftime("%Y/%m/%d (%a)")
        ):
            day_events = list(day_events)
            st.markdown(f"""
            <div style="background:linear-gradient(90deg,#1A2238 0%,#0B3D91 100%);color:#fff;padding:8px 16px;border-radius:3px 3px 0 0;margin-top:14px;border-bottom:2px solid #C9A961;font-family:'Hiragino Mincho ProN',serif;letter-spacing:1.5px;">
                📅 {date_str}　<span style="color:#C9A961;font-size:0.85rem;">({len(day_events)}件)</span>
            </div>
            """, unsafe_allow_html=True)

            for e in day_events:
                lvl = "★" * e["impact_level"]
                color = ("#8B0000" if e["impact_level"] == 5 else
                         "#D32030" if e["impact_level"] == 4 else
                         "#FDB813" if e["impact_level"] == 3 else "#888")

                rev_html = (
                    f'<div style="margin-top:4px;color:#D32030;font-size:0.78rem;"><b>⚠ 反転リスク:</b> {e["reversal_risk"]}</div>'
                    if e.get("reversal_risk") else ""
                )

                st.markdown(f"""
                <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {color};padding:11px 16px;margin:4px 0;border-radius:0 3px 3px 0;">
                    <div style="display:flex;justify-content:space-between;">
                        <div>
                            <span style="font-family:monospace;color:#0B3D91;font-weight:700;font-size:1rem;">
                                {e['scheduled_at'].strftime('%H:%M')}
                            </span>
                            <span style="margin-left:10px;color:#1A2238;font-weight:600;">
                                {e['country']} {e['name']}
                            </span>
                            <span style="margin-left:8px;color:{color};">{lvl}</span>
                        </div>
                        <div style="font-size:0.78rem;color:#4A5568;">
                            ⏱ {e['high_volatility_hours']}h高ボラ / {e['trend_keep_hours']}hトレンド
                        </div>
                    </div>
                    <div style="margin-top:4px;color:#1A2238;font-size:0.82rem;">{e['description']}</div>
                    {rev_html}
                </div>
                """, unsafe_allow_html=True)

    with t_persons:
        st.markdown("#### 主要 要人発言・講演 予定")
        for p in KEY_PERSON_SCHEDULE:
            color = ("#D32030" if p["impact_level"] == 5 else
                     "#FDB813" if p["impact_level"] == 4 else "#888")
            lvl = "★" * p["impact_level"]
            rev_html = (
                f'<div style="margin-top:4px;color:#D32030;font-size:0.8rem;"><b>⚠ 反転リスク:</b> {p["reversal_risk"]}</div>'
                if p.get("reversal_risk") else ""
            )
            st.markdown(f"""
            <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {color};padding:14px 18px;margin:8px 0;border-radius:0 3px 3px 0;">
                <div style="display:flex;justify-content:space-between;align-items:start;">
                    <b style="font-family:'Hiragino Mincho ProN',serif;color:#0B3D91;font-size:1rem;">
                        {p['country']} {p['name']}
                    </b>
                    <span style="color:{color};">{lvl}</span>
                </div>
                <table style="margin-top:6px;font-size:0.83rem;width:100%;">
                    <tr><td style="color:#4A5568;width:25%;padding:3px 0;">📅 頻度</td><td>{p['frequency']}</td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;">🕐 時間帯</td><td><b>{p['jst_time']}</b></td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;">⏱ トレンド影響</td><td>{p['trend_keep_hours']}時間</td></tr>
                    <tr><td style="color:#4A5568;padding:3px 0;vertical-align:top;">📝 ポイント</td><td>{p['description']}</td></tr>
                </table>
                {rev_html}
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  🚨 要人介入・警戒水準表モード
# ════════════════════════════════════════════════
elif page == "🚨 要人介入・警戒水準表":
    st.title("🚨 要人介入 警戒ポイント・タイミング表")
    st.caption("各要人の介入パターン・警戒価格水準・時間帯・予想変動幅を一覧表で確認")

    tab_persons, tab_levels, tab_times = st.tabs([
        "👤 要人別 介入パターン表",
        "💴 通貨ペア別 警戒水準表",
        "🕐 時間帯別 介入確率表",
    ])

    with tab_persons:
        st.markdown("#### 各要人・機関の介入パターン")
        st.caption("『誰が』『いつ』『どの価格水準で』『どんなキーワードで』介入してくるかを完全網羅")

        intv_table = get_intervention_table()
        rows = []
        for r in intv_table:
            rows.append({
                "区分": r["category"],
                "要人/機関": f"{r['country']} {r['person']}",
                "警戒水準(USD/JPY)": r["watch_levels_usdjpy"],
                "警戒キーワード": r["warning_keywords"],
                "発信時間帯(JST)": r["primary_time_jst"],
                "ピーク時刻": r["peak_intervention_time"],
                "想定変動幅": r["expected_move"],
                "影響継続": r["duration"],
                "優先度": r["trigger_priority"],
            })
        df_intv = pd.DataFrame(rows)
        st.dataframe(df_intv, use_container_width=True, hide_index=True, height=480)

        st.divider()
        st.markdown("#### 詳細・過去事例")
        for r in intv_table:
            color = "#D32030" if "🔥🔥🔥" in r["trigger_priority"] else "#FDB813" if "🔥🔥" in r["trigger_priority"] else "#888"
            st.markdown(f"""
            <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {color};padding:12px 16px;margin:8px 0;border-radius:0 3px 3px 0;">
                <div style="font-family:'Hiragino Mincho ProN',serif;color:#0B3D91;font-weight:700;font-size:1.05rem;">
                    {r['category']} ｜ {r['country']} {r['person']} <span style="color:{color};font-size:0.85rem;margin-left:8px;">{r['trigger_priority']}</span>
                </div>
                <table style="margin-top:6px;font-size:0.85rem;width:100%;border-collapse:collapse;">
                    <tr><td style="padding:4px 0;color:#4A5568;width:22%;">⚠ 警戒水準</td><td><b style="color:#D32030;">{r['watch_levels_usdjpy']}</b></td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;">🔑 警戒キーワード</td><td>{r['warning_keywords']}</td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;">🕐 発信時間帯</td><td>{r['primary_time_jst']}</td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;">🎯 ピーク時刻</td><td><b>{r['peak_intervention_time']}</b></td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;">📉 想定変動幅</td><td>{r['expected_move']}</td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;">⏱ 影響継続期間</td><td>{r['duration']}</td></tr>
                    <tr><td style="padding:4px 0;color:#4A5568;vertical-align:top;">📚 過去事例</td><td style="color:#1A2238;">{r['history']}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

    with tab_levels:
        st.markdown("#### 通貨ペア別 介入警戒水準")
        st.caption("どの価格を超えたら口先介入／実弾介入が出るかの目安")

        levels_table = get_intervention_levels_table()
        rows = []
        for r in levels_table:
            rows.append({
                "通貨ペア": r["pair"],
                "心理的節目": r["psychological_resistance"],
                "口先介入ゾーン": r["verbal_intervention_zone"],
                "実弾介入ゾーン": r["actual_intervention_zone"],
                "過去最高値": r["max_historical"],
                "介入後の戻り(参考)": r["post_intervention_pullback"],
            })
        df_lvl = pd.DataFrame(rows)
        st.dataframe(df_lvl, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("##### 📌 警戒水準の使い方")
        st.markdown("""
        - **口先介入ゾーン到達時** → ポジション縮小、利確検討
        - **実弾介入ゾーン到達時** → 円買い／円ショート決済が安全
        - **過去最高値接近** → 介入確率が指数関数的に上昇
        - **介入直後** → 数時間〜数日で 3-10円の急落リスク → 戻り売り戦略が有効
        """)

    with tab_times:
        st.markdown("#### 時間帯別 介入発生確率マップ")
        st.caption("実弾介入は『流動性の低い時間帯』に集中する傾向（覆面介入）")

        time_table = get_intervention_time_table()
        rows = []
        for r in time_table:
            prob_color = ("🔴" if "極めて高" in r["probability"] else
                          "🟠" if "高" in r["probability"] else
                          "🟡" if "中" in r["probability"] else "⚪")
            rows.append({
                "時間帯(JST)": r["time_jst"],
                "セッション": r["label"],
                "介入確率": f"{prob_color} {r['probability']}",
                "理由": r["reason"],
            })
        df_time = pd.DataFrame(rows)
        st.dataframe(df_time, use_container_width=True, hide_index=True)

        st.markdown("##### 🎯 特に警戒すべきTOP3時間帯")
        st.markdown("""
        1. **21:30 - 22:30 JST** ：米経済指標発表後（NFP/CPIで急変→介入で抑え込み）
        2. **03:00 - 05:00 JST** ：FOMC声明・パウエル会見前後
        3. **05:00 - 07:00 JST** ：早朝薄商い時間帯（覆面介入の常套手段）
        """)


# ════════════════════════════════════════════════
#  💹 FX レバレッジ シミュレーター（25倍・スワップ込み）
# ════════════════════════════════════════════════
elif page == "💹 FX レバレッジ シミュレーター":
    st.title("💹 FX レバレッジ取引 シミュレーター")
    st.caption(f"国内FX上限 レバレッジ {JAPAN_LEVERAGE}倍 / スワップ金利込み / ロスカット計算")

    tab_single, tab_backtest, tab_swap = st.tabs([
        "🎯 トレード単発シミュレーション",
        "📈 期間保有バックテスト",
        "💰 スワップ年利ランキング",
    ])

    # ─────────── 単発トレード ───────────
    with tab_single:
        st.markdown("#### 1回のFXトレードを完全シミュレーション")

        col_l, col_r = st.columns([1, 1])

        with col_l:
            pair_label = st.selectbox(
                "通貨ペア",
                options=[v["label"] for v in SWAP_POINTS.values()],
                key="sim_pair",
            )
            ticker_sim = next(k for k, v in SWAP_POINTS.items() if v["label"] == pair_label)

            side = st.radio("売買", ["買い (Long)", "売り (Short)"], horizontal=True, key="sim_side")
            side_code = "buy" if "買い" in side else "sell"

            capital = st.number_input(
                "預入資金 (円)",
                min_value=10000, max_value=100_000_000, value=300_000, step=10000,
                key="sim_cap",
            )

            lots = st.number_input(
                "ロット数 (1ロット = 1万通貨)",
                min_value=0.1, max_value=100.0, value=1.0, step=0.1,
                key="sim_lots",
            )

        with col_r:
            entry_p = st.number_input(
                "エントリー価格（0で現在値）",
                min_value=0.0, max_value=10000.0, value=0.0, step=0.01,
                key="sim_entry",
            )
            entry_p = None if entry_p == 0 else entry_p

            target_p = st.number_input(
                "利確価格（任意）",
                min_value=0.0, max_value=10000.0, value=0.0, step=0.01,
                key="sim_tgt",
            )
            target_p = None if target_p == 0 else target_p

            stop_p = st.number_input(
                "損切り価格（任意）",
                min_value=0.0, max_value=10000.0, value=0.0, step=0.01,
                key="sim_stop",
            )
            stop_p = None if stop_p == 0 else stop_p

            holding = st.number_input(
                "想定保有日数",
                min_value=1, max_value=730, value=30,
                key="sim_hold",
            )

        if st.button("🚀 シミュレーション実行", type="primary", key="sim_run"):
            with st.spinner("価格取得中..."):
                result = simulate_trade(
                    ticker_sim, side_code, entry_p, lots, capital,
                    JAPAN_LEVERAGE, target_p, stop_p, holding,
                )

            if "error" in result:
                st.error(result["error"])
            else:
                # サマリー
                st.markdown("##### 📊 取引概要")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("取引通貨量", f"{result['trade_units']:,}")
                m2.metric("取引総額", f"{result['notional']:,.0f}円")
                m3.metric("必要証拠金", f"{result['margin_required']:,.0f}円")
                m4.metric("証拠金維持率", f"{result['margin_ratio_pct']:.0f}%")

                # ロスカット警告
                if result['margin_ratio_pct'] < 200:
                    st.error(f"⚠ 証拠金維持率が低い（{result['margin_ratio_pct']:.0f}%）。少しの逆行でロスカットの可能性。")
                elif result['margin_ratio_pct'] < 500:
                    st.warning(f"⚠ 証拠金維持率はやや低め（{result['margin_ratio_pct']:.0f}%）。")

                st.markdown("##### 💰 価格と損益")
                st.dataframe(pd.DataFrame([
                    {"項目": "現在価格", "値": f"{result['current_price']:.4f}"},
                    {"項目": "エントリー価格", "値": f"{result['entry_price']:.4f}"},
                    {"項目": "ロスカット価格 (維持率100%)", "値": f"{result['loss_cut_price']:.4f}"},
                    {"項目": "現在の含み損益", "値": f"{result['current_pnl']:+,.0f} 円"},
                    {"項目": "1pip当たりの損益", "値": f"{result['pip_value_jpy']:,.0f} 円"},
                ]), use_container_width=True, hide_index=True)

                # 利確/損切りシナリオ
                if result.get("target_pnl") is not None or result.get("stop_pnl") is not None:
                    st.markdown("##### 🎯 利確・損切りシナリオ")
                    scen_rows = []
                    if result.get("target_pnl") is not None:
                        scen_rows.append({
                            "シナリオ": "🎯 利確到達",
                            "価格": f"{result['target_price']:.4f}",
                            "価格損益": f"{result['target_pnl']:+,.0f} 円",
                            "+ スワップ": f"{result['swap']['total']:+,.0f} 円",
                            "総損益": f"{result['total_pnl_at_target']:+,.0f} 円",
                            "対資金リターン": f"{result['total_pnl_at_target']/capital*100:+.2f}%",
                        })
                    if result.get("stop_pnl") is not None:
                        scen_rows.append({
                            "シナリオ": "🛑 損切り到達",
                            "価格": f"{result['stop_loss']:.4f}",
                            "価格損益": f"{result['stop_pnl']:+,.0f} 円",
                            "+ スワップ": f"{result['swap']['total']:+,.0f} 円",
                            "総損益": f"{result['total_pnl_at_stop']:+,.0f} 円",
                            "対資金リターン": f"{result['total_pnl_at_stop']/capital*100:+.2f}%",
                        })
                    st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)

                    if result.get("risk_reward"):
                        rr = result["risk_reward"]
                        rr_color = "🟢" if rr >= 2 else "🟡" if rr >= 1 else "🔴"
                        st.info(f"{rr_color} リスクリワード比 = **{rr:.2f}**　（2.0以上が理想）")

                # スワップ
                if result["swap"].get("available"):
                    st.markdown("##### 💴 スワップ金利")
                    s1, s2, s3 = st.columns(3)
                    daily = result["swap"]["daily"]
                    s1.metric("日次スワップ", f"{daily:+,.0f} 円", delta=("受取" if daily > 0 else "支払"))
                    s2.metric(f"{result['holding_days']}日後 累計", f"{result['swap']['total']:+,.0f} 円")
                    annual = daily * 365
                    yield_pct = (annual / capital) * 100
                    s3.metric("年利換算", f"{yield_pct:+.2f}%")
                    st.caption(f"💡 {result['swap']['note']}")
                else:
                    st.info("このペアはスワップデータが未登録です。")

    # ─────────── バックテスト ───────────
    with tab_backtest:
        st.markdown("#### 期間保有 バックテスト")
        st.caption("「もし1年前に買って今もずっと持っていたら？」をシミュレーション")

        col_a, col_b = st.columns(2)
        with col_a:
            bt_pair = st.selectbox(
                "通貨ペア",
                options=[v["label"] for v in SWAP_POINTS.values()],
                key="bt_pair",
            )
            bt_ticker = next(k for k, v in SWAP_POINTS.items() if v["label"] == bt_pair)
            bt_side = st.radio("売買", ["買い (Long)", "売り (Short)"], horizontal=True, key="bt_side")
            bt_side_code = "buy" if "買い" in bt_side else "sell"

        with col_b:
            bt_capital = st.number_input(
                "預入資金 (円)",
                min_value=10000, max_value=100_000_000, value=300_000, step=10000,
                key="bt_cap",
            )
            bt_lots = st.number_input(
                "ロット数",
                min_value=0.1, max_value=100.0, value=1.0, step=0.1,
                key="bt_lots",
            )
            bt_period = st.selectbox(
                "保有期間",
                options=["3mo", "6mo", "1y", "2y", "5y"],
                index=2, key="bt_period",
            )

        if st.button("📈 バックテスト実行", type="primary", key="bt_run"):
            with st.spinner("計算中..."):
                bt_result = backtest_simulation(
                    bt_ticker, bt_side_code, bt_lots, bt_capital, bt_period, JAPAN_LEVERAGE,
                )

            if bt_result is None:
                st.error("データ取得に失敗しました。")
            elif "error" in bt_result:
                st.error(bt_result["error"])
            else:
                # サマリー
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("最終損益(価格)", f"{bt_result['final_price_pnl']:+,.0f}円")
                m2.metric("スワップ累計", f"{bt_result['final_swap_total']:+,.0f}円")
                m3.metric("総損益", f"{bt_result['final_total']:+,.0f}円", delta=f"{bt_result['return_pct']:+.2f}%")
                m4.metric("最大ドローダウン", f"{bt_result['max_drawdown_pct']:.2f}%")

                # ロスカット警告
                if bt_result["loss_cut_triggered"]:
                    st.error(f"🛑 期間中にロスカット発生！（{bt_result['loss_cut_date']}）強制決済されました。")
                else:
                    st.success("✅ 期間中にロスカット発生なし。")

                # 推移グラフ
                import plotly.graph_objects as go
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    row_heights=[0.6, 0.4],
                                    subplot_titles=("含み損益とスワップ累計", "口座残高（資産推移）"))
                fig.add_trace(go.Scatter(x=bt_result["dates"], y=bt_result["pnl_curve"],
                                         name="価格損益", line=dict(color="#0B3D91")), row=1, col=1)
                fig.add_trace(go.Scatter(x=bt_result["dates"], y=bt_result["swap_curve"],
                                         name="スワップ累計", line=dict(color="#C9A961")), row=1, col=1)
                fig.add_trace(go.Scatter(x=bt_result["dates"], y=bt_result["total_curve"],
                                         name="総損益", line=dict(color="#D32030", width=2)), row=1, col=1)
                fig.add_trace(go.Scatter(x=bt_result["dates"], y=bt_result["equity_curve"],
                                         name="口座残高", line=dict(color="#1A2238", width=2),
                                         fill="tozeroy", fillcolor="rgba(11,61,145,0.1)"), row=2, col=1)
                fig.add_hline(y=bt_result["margin_required"], line_dash="dash",
                              line_color="red", row=2, col=1,
                              annotation_text="必要証拠金（割るとロスカット）")
                fig.update_layout(height=600, template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # 詳細テーブル
                st.markdown("##### 📋 取引明細")
                detail_rows = [
                    {"項目": "通貨ペア", "値": bt_result["label"]},
                    {"項目": "売買", "値": "買い" if bt_result["side"] == "buy" else "売り"},
                    {"項目": "エントリー価格", "値": f"{bt_result['entry_price']:.4f}"},
                    {"項目": "最終価格", "値": f"{bt_result['final_price']:.4f}"},
                    {"項目": "ロット数", "値": f"{bt_result['lots']} ロット"},
                    {"項目": "レバレッジ", "値": f"{bt_result['leverage']}倍"},
                    {"項目": "預入資金", "値": f"{bt_result['capital']:,.0f}円"},
                    {"項目": "必要証拠金", "値": f"{bt_result['margin_required']:,.0f}円"},
                    {"項目": "日次スワップ", "値": f"{bt_result['daily_swap']:+,.0f}円"},
                    {"項目": "保有日数", "値": f"{bt_result['holding_days']}日"},
                    {"項目": "最大利益", "値": f"{bt_result['max_profit']:+,.0f}円"},
                    {"項目": "最大損失", "値": f"{bt_result['max_loss']:+,.0f}円"},
                ]
                st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

    # ─────────── スワップ年利ランキング ───────────
    with tab_swap:
        st.markdown("#### 通貨ペア別 スワップ年利ランキング")
        st.caption("レバレッジ25倍を活用した場合の年間スワップ収益（参考値）")

        swap_capital = st.number_input(
            "各ペアに投資する資金 (円)",
            min_value=10000, max_value=10_000_000, value=100_000, step=10000,
            key="swap_cap",
        )

        with st.spinner("各通貨ペアの最新価格取得中..."):
            yield_table = get_swap_yield_table(swap_capital)

        if not yield_table:
            st.warning("データ取得に失敗しました。")
        else:
            rows = []
            for r in yield_table:
                rows.append({
                    "通貨ペア": r["label"],
                    "現在価格": r["current_price"],
                    "推奨ロット": r["safe_lots"],
                    "買いスワップ/日": f"{r['buy_swap_daily']:+,.0f}円",
                    "売りスワップ/日": f"{r['sell_swap_daily']:+,.0f}円",
                    "推奨方向": "買い" if r["better_side"] == "buy" else "売り",
                    "年間スワップ": f"{(r['buy_swap_annual'] if r['better_side']=='buy' else r['sell_swap_annual']):+,.0f}円",
                    "年利%": f"{r['best_annual_yield_pct']:+.2f}%",
                    "備考": r["note"],
                })
            df_swap = pd.DataFrame(rows)
            st.dataframe(df_swap, use_container_width=True, hide_index=True, height=500)

            st.info("""
            💡 **スワップ運用の注意点**
            - スワップポイントは **毎日変動** します（金利差による）
            - 為替差損で**スワップ収益を相殺してしまう可能性**あり
            - **水曜日は3日分（土日含む）** のスワップが付与
            - **トルコリラ・南アランド** などは高金利でも**通貨価値下落リスク**大
            - **レバレッジを上げる**ほど、**ロスカットリスクも増大**
            """)


# ════════════════════════════════════════════════
#  仮想通貨モード
# ════════════════════════════════════════════════
elif page == "₿ 仮想通貨":
    st.title("₿ 仮想通貨ビューア")
    st.caption(f"{display_name}")

    latest = get_latest_price(ticker)
    if latest:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(display_name, f"{latest['price']:,.4f}",
                      delta=f"{latest['change']:+.4f} ({latest['change_pct']:+.2f}%)")
        with c2:
            st.metric("前日比", f"{latest['change']:+.4f}")
        with c3:
            st.metric("変動率", f"{latest['change_pct']:+.2f}%")
        st.divider()

    with st.spinner("価格データ取得中..."):
        df = fetch_market_data(ticker, period, interval)

    if df.empty:
        st.error("データを取得できませんでした。")
        st.stop()

    df = calculate_technical_indicators(df)

    tab_chart_c, tab_pred_c, tab_data_c = st.tabs(["チャート", "1分足予測", "データ"])

    with tab_chart_c:
        fig = go.Figure()
        if chart_type == "ローソク足":
            fig.add_trace(go.Candlestick(
                x=df["日時"], open=df["始値"], high=df["高値"],
                low=df["安値"], close=df["終値"], name="価格",
                increasing_line_color="#D32030", decreasing_line_color="#1565C0",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df["日時"], y=df["終値"], mode="lines", name="終値",
                line=dict(color="#f7931a", width=2),
            ))
        for col_name, color in [("MA5", "#ffa500"), ("MA25", "#ff6b6b")]:
            if col_name in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["日時"], y=df[col_name], mode="lines", name=col_name,
                    line=dict(color=color, width=1, dash="dot"),
                ))
        if show_bb and "BB上限(+2σ)" in df.columns:
            fig.add_trace(go.Scatter(x=df["日時"], y=df["BB上限(+2σ)"], mode="lines",
                                     name="BB+2σ", line=dict(color="#888", dash="dash")))
            fig.add_trace(go.Scatter(x=df["日時"], y=df["BB下限(-2σ)"], mode="lines",
                                     name="BB-2σ", line=dict(color="#888", dash="dash"),
                                     fill="tonexty", fillcolor="rgba(136,136,136,0.1)"))
        fig.update_layout(template="plotly_white", height=550,
                          margin=dict(l=0, r=0, t=30, b=0),
                          xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab_pred_c:
        st.subheader("1分足 短期予測")
        with st.spinner("AI予測中..."):
            pred = predict_stock_1min(ticker)
        if pred:
            arrow = "📈" if pred["direction"] == "上昇" else ("📉" if pred["direction"] == "下落" else "➡️")
            color = "#D32030" if pred["direction"] == "上昇" else ("#1565C0" if pred["direction"] == "下落" else "#888")
            current = pred.get("current_price", 0)
            pred_low, pred_high = pred.get("predicted_range", (current, current))
            mid = (pred_low + pred_high) / 2
            change_pct = ((mid - current) / current * 100) if current else 0
            st.markdown(f"""
            <div class="prediction-box" style="border:2px solid {color};">
              <div style="font-size:2rem;color:{color};">{arrow} {pred['direction']}</div>
              <div style="font-size:1.2rem;">信頼度: {pred['confidence']}%</div>
              <div style="margin-top:8px;">現在値: {current}</div>
              <div>予想レンジ: {pred_low} 〜 {pred_high}</div>
              <div>予想変動: {change_pct:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
            st.write("**判断根拠**")
            for f in pred.get("factors", pred.get("reasons", [])):
                st.markdown(f'<div class="factor-item">{f}</div>', unsafe_allow_html=True)
            s = pred.get("shock", {})
            if s.get("is_shock"):
                st.error(
                    "🚨 突発変動モード: "
                    f"1分 {s.get('move_1m_pct', 0):+.3f}% / "
                    f"3分 {s.get('move_3m_pct', 0):+.3f}% / "
                    f"z={s.get('zscore', 0):.2f}"
                )
        else:
            st.info("予測データが不足しています。")

    with tab_data_c:
        d = df[["日時", "始値", "高値", "安値", "終値"]].sort_values("日時", ascending=False)
        for c in ["始値", "高値", "安値", "終値"]:
            d[c] = d[c].round(4)
        st.dataframe(d, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════
#  新興・新発掘銘柄モード
# ════════════════════════════════════════════════
elif page == "🚀 新興・新発掘銘柄":
    st.title("🚀 新興・新発掘銘柄スクリーナー")
    st.caption("AI・量子・レアアース・宇宙・新エネルギー等のテーマ銘柄を分析し、買い時/売り時を提示")

    tab_now, tab_theme, tab_detail = st.tabs([
        "🎯 今買い時/売り時", "📂 テーマ別一覧", "🔍 個別銘柄詳細",
    ])

    with tab_now:
        st.subheader("全テーマ横断スキャン")
        if st.button("🔄 全銘柄スキャン実行（約30秒〜1分）", type="primary"):
            with st.spinner("全テーマ・全銘柄を分析中..."):
                result = scan_all_emerging()
            st.session_state["emerg_scan"] = result
            st.success(f"スキャン完了：{len(result['all'])}銘柄を分析")

        result = st.session_state.get("emerg_scan")
        if result:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🟢 今が買い時 TOP10")
                if result["buy_now"]:
                    for r in result["buy_now"]:
                        st.markdown(f"""
                        <div style="background:rgba(0,210,106,0.1);padding:10px;border-radius:8px;margin:6px 0;border-left:4px solid #00d26a;">
                          <b>{r['ticker']}</b> ({r['verdict_strength']}) - {r['name']}<br>
                          <small>{r['theme']}｜{r['price']} ({r['change_1d']:+.2f}%)｜RSI={r['rsi']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("現時点で強い買いシグナル銘柄なし")
            with c2:
                st.markdown("### 🔴 今が売り時 TOP10")
                if result["sell_now"]:
                    for r in result["sell_now"]:
                        st.markdown(f"""
                        <div style="background:rgba(249,47,96,0.1);padding:10px;border-radius:8px;margin:6px 0;border-left:4px solid #f92f60;">
                          <b>{r['ticker']}</b> ({r['verdict_strength']}) - {r['name']}<br>
                          <small>{r['theme']}｜{r['price']} ({r['change_1d']:+.2f}%)｜RSI={r['rsi']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("現時点で強い売りシグナル銘柄なし")
        else:
            st.info("👆 上のボタンをクリックしてスキャンを開始してください")

    with tab_theme:
        st.subheader("テーマ別 銘柄一覧")
        theme_choice = st.selectbox("テーマ選択", list(EMERGING_STOCKS.keys()))

        if st.button("このテーマを分析"):
            with st.spinner(f"{theme_choice} を分析中..."):
                results = scan_emerging_by_theme(theme_choice)

            if results:
                df_theme = pd.DataFrame([{
                    "ティッカー": r["ticker"],
                    "銘柄名": r["name"],
                    "判定": f"{r['verdict']}({r['verdict_strength']})",
                    "現在値": r["price"],
                    "1日": f"{r['change_1d']:+.2f}%",
                    "1週": f"{r['change_1w']:+.2f}%",
                    "1月": f"{r['change_1m']:+.2f}%",
                    "RSI": r["rsi"],
                    "買スコア": r["buy_score"],
                    "売スコア": r["sell_score"],
                    "目標価格": r["target_price"],
                    "損切り": r["stop_loss"],
                    "リスクリワード": r["risk_reward"],
                } for r in results])
                st.dataframe(df_theme, use_container_width=True, hide_index=True)
            else:
                st.warning("データを取得できませんでした")
        else:
            stocks = EMERGING_STOCKS.get(theme_choice, {})
            st.markdown(f"**{theme_choice}** の対象銘柄（{len(stocks)}社）")
            for tk, nm in stocks.items():
                st.markdown(f"- `{tk}` - {nm}")

    with tab_detail:
        st.subheader("個別銘柄 詳細分析")
        all_stocks = []
        for theme, stocks in EMERGING_STOCKS.items():
            for tk, nm in stocks.items():
                all_stocks.append((tk, f"{tk} - {nm}"))

        labels = [s[1] for s in all_stocks]
        choice = st.selectbox("銘柄選択", labels)
        chosen_ticker = all_stocks[labels.index(choice)][0]

        if st.button("詳細分析を実行"):
            with st.spinner(f"{chosen_ticker} を分析中..."):
                r = analyze_emerging_stock(chosen_ticker)

            if r:
                if r["verdict"] == "買い時":
                    color = "#00d26a"
                elif r["verdict"] == "売り時":
                    color = "#f92f60"
                else:
                    color = "#888"

                st.markdown(f"""
                <div class="prediction-box" style="border:2px solid {color};">
                  <div style="font-size:1.1rem;">{r['theme']}｜{r['name']}</div>
                  <div style="font-size:2.2rem;color:{color};font-weight:bold;">
                    {r['verdict']} ({r['verdict_strength']})
                  </div>
                  <div>買スコア: {r['buy_score']}　売スコア: {r['sell_score']}</div>
                </div>
                """, unsafe_allow_html=True)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("現在価格", f"{r['price']}", f"{r['change_1d']:+.2f}%")
                m2.metric("RSI", f"{r['rsi']}")
                m3.metric("MA位置", r["ma_label"])
                m4.metric("出来高", r["volume_signal"])

                m5, m6, m7, m8 = st.columns(4)
                m5.metric("推奨エントリー", f"{r['entry_price']}")
                m6.metric("損切り価格", f"{r['stop_loss']}")
                m7.metric("利確目標", f"{r['target_price']}")
                m8.metric("リスクリワード", f"{r['risk_reward']}")

                c_buy, c_sell = st.columns(2)
                with c_buy:
                    st.markdown("#### 🟢 買いシグナル")
                    if r["buy_signals"]:
                        for s in r["buy_signals"]:
                            st.markdown(f'<div class="factor-item">{s}</div>', unsafe_allow_html=True)
                    else:
                        st.caption("該当なし")
                with c_sell:
                    st.markdown("#### 🔴 売りシグナル")
                    if r["sell_signals"]:
                        for s in r["sell_signals"]:
                            st.markdown(f'<div class="factor-item">{s}</div>', unsafe_allow_html=True)
                    else:
                        st.caption("該当なし")

                st.markdown("#### 期間別パフォーマンス")
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("1日", f"{r['change_1d']:+.2f}%")
                pc2.metric("1週間", f"{r['change_1w']:+.2f}%")
                pc3.metric("1ヶ月", f"{r['change_1m']:+.2f}%")
                pc4.metric("3ヶ月", f"{r['change_3m']:+.2f}%")
            else:
                st.error("データ取得に失敗しました")


# ════════════════════════════════════════════════
#  アラートモード
# ════════════════════════════════════════════════
elif page == "🔔 アラート":
    st.title("🔔 アラート設定・通知")
    st.caption("「何が」「どの値を超えたら」発火するか分かりやすく設定できます")

    # ── 発火中のアラート（最上部に大きく表示）──
    triggered_now = check_all_alerts()
    if triggered_now:
        st.markdown(f"""
        <div style="background:linear-gradient(90deg,#D32030 0%,#8B0000 100%);color:#fff;padding:14px 20px;border-radius:4px;border-left:6px solid #C9A961;margin-bottom:10px;">
            <div style="font-size:1.1rem;font-weight:700;">🔔 現在 {len(triggered_now)}件 のアラート発火中</div>
        </div>
        """, unsafe_allow_html=True)
        for t in triggered_now:
            st.warning(t["message"])

    tab_set, tab_list, tab_daiwa, tab_guide, tab_log = st.tabs([
        "⚙️ 新規アラート作成", "📋 設定中アラート", "🏦 大和FXルール参考", "📖 アラート種類ガイド", "📜 通知履歴"
    ])

    with tab_daiwa:
        st.markdown("#### 🏦 大和証券 FX 証拠金アラート（参考・検討用）")
        th = thresholds_for_loss_cut_base(100.0)
        st.markdown(
            f"""
| ステータス | 条件（維持率） | 本アプリの動作 |
|-----------|----------------|----------------|
| 🟡 プレアラート | **{th['pre_alert']:.0f}%** 未満 | お知らせ + 短いビープ |
| 🟠 アラート | **{th['alert']:.0f}%** 未満 | 警告 + ビープ2回 |
| 🔴 ロスカット水準 | **{th['loss_cut']:.0f}%** 未満 | 強警告 + ビープ3回 |

**維持率** = 有効証拠金（預金＋含み損益）÷ 建玉必要証拠金 × 100  
出典: [ダイワFX 利用・取引ルール](https://www.daiwa.jp/products/fx/fx_store/rules_fx.html) を参考（{APP_NAME} は非公式シミュレーション）

1. **🏦 FX/CFD ターミナル** で仮想注文を実行  
2. 相場が逆行して維持率が下がると、画面上部で **アラームが鳴ります**  
3. サイドバー **🔔 アラーム設定** で音 ON/OFF・クールダウンを変更
            """
        )
        if st.button("🔄 今すぐアラーム判定", key="daiwa_check_btn"):
            ev = check_all_daiwa_alerts()
            if ev:
                render_alarm_events(ev, play_sound=True)
            else:
                st.success("現在、発火条件のアラートはありません（仮想建玉がない場合も含む）")

    # ════════════════════════════════════════════════
    #  ガイドタブ：何のアラートが何で発火するかを表で表示
    # ════════════════════════════════════════════════
    with tab_guide:
        st.markdown("#### 📖 全アラートタイプ 一覧表")
        st.caption("どのアラートが、何の値を見て、何を超えると発火するかの早見表")
        guide_rows = []
        for atype, info in ALERT_TYPE_DETAILS.items():
            guide_rows.append({
                "種類": f"{info['icon']} {ALERT_TYPES[atype]}",
                "カテゴリ": info["category"],
                "監視している値": info["watched_value"],
                "発火条件": info["trigger_rule"],
                "意味/使い道": info["use_case"],
                "例": info["example"],
            })
        st.dataframe(pd.DataFrame(guide_rows), use_container_width=True, hide_index=True, height=380)

    # ════════════════════════════════════════════════
    #  新規アラート作成
    # ════════════════════════════════════════════════
    with tab_set:
        st.markdown("#### Step 1: 銘柄を選択")
        all_targets = {}
        for k, v in CURRENCY_PAIRS.items():
            all_targets[f"[FX] {k}"] = v
        for k, v in FUTURES_SYMBOLS.items():
            all_targets[f"[先物] {k}"] = v
        for k, v in STOCK_INDICES.items():
            all_targets[f"[指数] {k}"] = v
        for k, v in JP_STOCKS.items():
            all_targets[f"[日本株] {k}"] = v
        for k, v in US_STOCKS.items():
            all_targets[f"[米国株] {k}"] = v
        for k, v in OVERSEAS_STOCKS.items():
            all_targets[f"[海外株] {k}"] = v
        for k, v in BOND_SYMBOLS.items():
            all_targets[f"[債券] {k}"] = v
        for k, v in CRYPTO_SYMBOLS.items():
            all_targets[f"[仮想通貨] {k}"] = v

        target = st.selectbox("対象銘柄", list(all_targets.keys()), key="al_target")

        st.markdown("#### Step 2: アラートの種類を選択")
        atype_options = [(k, v) for k, v in ALERT_TYPES.items()]
        atype_key = st.selectbox(
            "アラート条件",
            options=[k for k, _ in atype_options],
            format_func=lambda k: f"{ALERT_TYPE_DETAILS[k]['icon']} {ALERT_TYPES[k]}（{ALERT_TYPE_DETAILS[k]['category']}）",
            key="al_type",
        )

        # 選択中のアラートの詳細説明カード
        d = ALERT_TYPE_DETAILS[atype_key]
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#F4F7FB 0%,#E8EFF8 100%);border-left:4px solid #0B3D91;padding:14px 18px;border-radius:0 4px 4px 0;margin:8px 0;">
            <div style="font-family:'Hiragino Mincho ProN',serif;color:#0B3D91;font-weight:700;font-size:1.05rem;">
                {d['icon']} {ALERT_TYPES[atype_key]}
            </div>
            <table style="margin-top:8px;font-size:0.88rem;width:100%;">
                <tr><td style="padding:3px 8px 3px 0;color:#4A5568;width:25%;">📊 監視する値</td><td><b>{d['watched_value']}</b></td></tr>
                <tr><td style="padding:3px 8px 3px 0;color:#4A5568;">⚡ 発火する条件</td><td style="color:#D32030;"><b>{d['trigger_rule']}</b></td></tr>
                <tr><td style="padding:3px 8px 3px 0;color:#4A5568;">💡 意味</td><td>{d['explanation']}</td></tr>
                <tr><td style="padding:3px 8px 3px 0;color:#4A5568;">🎯 使い道</td><td>{d['use_case']}</td></tr>
                <tr><td style="padding:3px 8px 3px 0;color:#4A5568;">📝 設定例</td><td><i>{d['example']}</i></td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Step 3: しきい値を設定")
        if atype_key in ["macd_golden_cross", "macd_dead_cross"]:
            threshold = 0.0
            st.info("📌 MACDクロスは値を指定する必要はありません（クロスした瞬間に発火）")
        else:
            threshold = st.number_input(
                d["threshold_label"],
                value=d["threshold_default"],
                step=d["threshold_step"] if d["threshold_step"] > 0 else 0.01,
                key="al_thresh",
            )

        # ── ライブプレビュー ──
        st.markdown("#### Step 4: 現在の状態を確認（プレビュー）")
        with st.spinner("最新データ取得中..."):
            preview = get_alert_preview(all_targets[target], atype_key, float(threshold))

        if preview:
            triggered_color = "#D32030" if preview["would_trigger"] else "#0B3D91"
            triggered_bg = "#FFF0F0" if preview["would_trigger"] else "#F4F7FB"
            triggered_icon = "🔴 発火中" if preview["would_trigger"] else "🟢 待機中"
            st.markdown(f"""
            <div style="background:{triggered_bg};border:2px solid {triggered_color};border-radius:4px;padding:14px 18px;margin:8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-family:'Hiragino Mincho ProN',serif;color:{triggered_color};font-weight:700;font-size:1.1rem;">
                        {triggered_icon}
                    </div>
                    <div style="color:#4A5568;font-size:0.85rem;">プレビュー判定</div>
                </div>
                <table style="margin-top:8px;font-size:0.92rem;width:100%;">
                    <tr><td style="padding:4px 8px 4px 0;color:#4A5568;width:30%;">監視中の指標</td><td><b>{preview['watched_label']}</b></td></tr>
                    <tr><td style="padding:4px 8px 4px 0;color:#4A5568;">現在値</td><td style="font-family:monospace;font-size:1.1rem;color:#1A2238;"><b>{preview['current_value']}</b></td></tr>
                    <tr><td style="padding:4px 8px 4px 0;color:#4A5568;">しきい値</td><td style="font-family:monospace;color:#0B3D91;"><b>{preview['threshold']}</b></td></tr>
                    <tr><td style="padding:4px 8px 4px 0;color:#4A5568;">発火ルール</td><td style="color:#1A2238;">{preview['rule_text']}</td></tr>
                    <tr><td style="padding:4px 8px 4px 0;color:#4A5568;vertical-align:top;">📍 状況</td><td style="color:{triggered_color};font-weight:600;">{preview['status_message']}</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("プレビュー値の取得に失敗しました（データ未取得）")

        st.markdown("#### Step 5: 作成")
        if st.button("✅ このアラートを作成", type="primary", use_container_width=True, key="al_create"):
            add_alert({
                "name": target,
                "ticker": all_targets[target],
                "type": atype_key,
                "threshold": float(threshold),
            })
            st.success(f"アラートを作成しました：{target} / {ALERT_TYPES[atype_key]} (しきい値: {threshold})")
            st.rerun()

    # ════════════════════════════════════════════════
    #  設定中アラート一覧（プレビュー付き）
    # ════════════════════════════════════════════════
    with tab_list:
        st.markdown("#### 📋 設定中アラート一覧（現在の状態付き）")
        alerts = load_alerts()
        if not alerts:
            st.info("アラートはまだ設定されていません。「⚙️ 新規アラート作成」から作ってください。")
        else:
            # まず一覧表で表示
            list_rows = []
            previews = {}
            for a in alerts:
                d = ALERT_TYPE_DETAILS.get(a["type"], {})
                p = get_alert_preview(a["ticker"], a["type"], a.get("threshold", 0))
                previews[a["id"]] = p
                list_rows.append({
                    "状態": "🟢 ON" if a.get("enabled", True) else "⚫ OFF",
                    "銘柄": a["name"],
                    "アラート": f"{d.get('icon', '')} {ALERT_TYPES.get(a['type'], a['type'])}",
                    "監視値": d.get("watched_value", "-"),
                    "現在値": p["current_value"] if p else "—",
                    "しきい値": a.get("threshold", 0),
                    "判定": ("🔴 発火中" if (p and p["would_trigger"]) else "🟢 待機中") if p else "-",
                    "発火回数": a.get("triggered_count", 0),
                })
            st.dataframe(pd.DataFrame(list_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### 🛠 個別操作（オン/オフ・削除）")

            for a in alerts:
                d = ALERT_TYPE_DETAILS.get(a["type"], {})
                p = previews.get(a["id"])
                status = "🟢 ON" if a.get("enabled", True) else "⚫ OFF"
                triggered_bar = ""
                if p:
                    if p["would_trigger"]:
                        triggered_bar = f'<span style="color:#D32030;font-weight:700;">🔴 発火中</span>'
                    else:
                        triggered_bar = f'<span style="color:#0B3D91;">🟢 待機中</span>'

                with st.container():
                    cols = st.columns([5, 1, 1])
                    with cols[0]:
                        msg = p["status_message"] if p else "（データ取得待ち）"
                        st.markdown(f"""
                        <div style="background:#fff;border:1px solid #D5DDE8;border-left:4px solid {'#D32030' if (p and p['would_trigger']) else '#0B3D91'};padding:10px 14px;border-radius:0 3px 3px 0;margin:4px 0;">
                            <div style="display:flex;justify-content:space-between;">
                                <div>
                                    <b style="color:#0B3D91;">{a['name']}</b>　{d.get('icon','')} {ALERT_TYPES.get(a['type'], a['type'])}
                                </div>
                                <div>{status}　{triggered_bar}</div>
                            </div>
                            <div style="font-size:0.82rem;color:#4A5568;margin-top:4px;">
                                {d.get('trigger_rule','')} ｜ しきい値: <b>{a.get('threshold',0)}</b> ｜ 発火回数: {a.get('triggered_count',0)}
                            </div>
                            <div style="font-size:0.84rem;color:#1A2238;margin-top:4px;">
                                📍 {msg}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    if cols[1].button("ON/OFF", key=f"tg_{a['id']}"):
                        toggle_alert(a["id"])
                        st.rerun()
                    if cols[2].button("🗑 削除", key=f"dl_{a['id']}"):
                        delete_alert(a["id"])
                        st.rerun()

    # ════════════════════════════════════════════════
    #  通知履歴
    # ════════════════════════════════════════════════
    with tab_log:
        st.markdown("#### 📜 過去に発火したアラート履歴")
        log = load_alert_log()
        if not log:
            st.info("通知履歴はまだありません。")
        else:
            if st.button("🗑 履歴をクリア", key="clr_log"):
                clear_alert_log()
                st.rerun()
            log_rows = []
            for entry in reversed(log[-100:]):
                ts = entry.get("triggered_at", "")[:19].replace("T", " ")
                log_rows.append({
                    "発火時刻": ts,
                    "銘柄": entry.get("name", ""),
                    "メッセージ": entry.get("message", ""),
                    "現在値": entry.get("current_price", "-"),
                })
            st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True, height=400)


# ════════════════════════════════════════════════
#  バックテストモード
# ════════════════════════════════════════════════
elif page == "📈 バックテスト":
    st.title("📈 戦略バックテスト")
    st.caption("過去データに対して戦略を検証し、パフォーマンスを評価")

    bt_tab_single, bt_tab_compare = st.tabs(["🎯 単一戦略テスト", "🏆 全戦略比較"])

    all_targets = {}
    for k, v in CURRENCY_PAIRS.items():
        all_targets[f"[FX] {k}"] = v
    for k, v in FUTURES_SYMBOLS.items():
        all_targets[f"[先物] {k}"] = v
    for k, v in STOCK_INDICES.items():
        all_targets[f"[指数] {k}"] = v
    for k, v in JP_STOCKS.items():
        all_targets[f"[日本株] {k}"] = v
    for k, v in US_STOCKS.items():
        all_targets[f"[米国株] {k}"] = v
    for k, v in OVERSEAS_STOCKS.items():
        all_targets[f"[海外株] {k}"] = v
    for k, v in BOND_SYMBOLS.items():
        all_targets[f"[債券] {k}"] = v
    for k, v in CRYPTO_SYMBOLS.items():
        all_targets[f"[仮想通貨] {k}"] = v

    with bt_tab_single:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            target = st.selectbox("銘柄", list(all_targets.keys()), key="bt_single_t")
        with bc2:
            strat = st.selectbox(
                "戦略",
                list(STRATEGIES.keys()),
                format_func=lambda x: STRATEGIES[x],
                key="bt_single_s",
            )
        with bc3:
            period_bt = st.selectbox("期間", ["3mo", "6mo", "1y", "2y", "5y"], index=2, key="bt_single_p")

        capital = st.number_input("初期資金（円・$）", value=1000000, step=100000)

        if st.button("🚀 バックテスト実行", type="primary"):
            with st.spinner("バックテスト実行中..."):
                bt_result = run_backtest(
                    all_targets[target], strat, period=period_bt,
                    initial_capital=float(capital),
                )

            if bt_result:
                st.success("バックテスト完了")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("最終資産", f"{bt_result['final_value']:,.0f}",
                          f"{bt_result['total_return']:+.2f}%")
                m2.metric("バイ&ホールド", f"{bt_result['buy_hold_return']:+.2f}%")
                m3.metric("超過リターン (α)", f"{bt_result['alpha']:+.2f}%")
                m4.metric("シャープレシオ", f"{bt_result['sharpe']}")

                m5, m6, m7, m8 = st.columns(4)
                m5.metric("取引回数", bt_result["trades"])
                m6.metric("勝率", f"{bt_result['win_rate']}%")
                m7.metric("最大ドローダウン", f"{bt_result['max_drawdown']:.2f}%")
                m8.metric("戦略", bt_result["strategy_label"][:14] + "…")

                # 資産推移チャート
                fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
                fig_eq.add_trace(go.Scatter(
                    x=bt_result["dates"], y=bt_result["equity_curve"],
                    name="戦略資産", line=dict(color="#00d26a", width=2),
                ), secondary_y=False)
                fig_eq.add_trace(go.Scatter(
                    x=bt_result["dates"], y=bt_result["price_curve"],
                    name="価格", line=dict(color="#888", width=1, dash="dot"),
                ), secondary_y=True)
                fig_eq.update_layout(template="plotly_white", height=400,
                                     margin=dict(l=0, r=0, t=30, b=0),
                                     legend=dict(orientation="h"))
                fig_eq.update_yaxes(title_text="資産", secondary_y=False)
                fig_eq.update_yaxes(title_text="価格", secondary_y=True)
                st.plotly_chart(fig_eq, use_container_width=True)

                # 取引ログ
                if bt_result["trade_log"]:
                    st.subheader("取引ログ（直近30件）")
                    log_df = pd.DataFrame(bt_result["trade_log"][-30:])
                    st.dataframe(log_df, use_container_width=True, hide_index=True)
            else:
                st.error("バックテストに失敗しました（データ不足の可能性）")

    with bt_tab_compare:
        bc_target = st.selectbox("銘柄", list(all_targets.keys()), key="bt_cmp_t")
        bc_period = st.selectbox("期間", ["6mo", "1y", "2y", "5y"], index=1, key="bt_cmp_p")
        bc_capital = st.number_input("初期資金", value=1000000, step=100000, key="bt_cmp_c")

        if st.button("🏁 全戦略を比較実行", type="primary"):
            with st.spinner("全戦略を比較中..."):
                results = compare_strategies(
                    all_targets[bc_target], period=bc_period,
                    initial_capital=float(bc_capital),
                )

            if results:
                cmp_df = pd.DataFrame([{
                    "順位": i + 1,
                    "戦略": r["strategy_label"],
                    "総リターン": f"{r['total_return']:+.2f}%",
                    "B&H": f"{r['buy_hold_return']:+.2f}%",
                    "α": f"{r['alpha']:+.2f}%",
                    "取引数": r["trades"],
                    "勝率": f"{r['win_rate']}%",
                    "最大DD": f"{r['max_drawdown']:.2f}%",
                    "シャープ": r["sharpe"],
                } for i, r in enumerate(results)])
                st.dataframe(cmp_df, use_container_width=True, hide_index=True)

                # 資産推移比較
                fig_cmp = go.Figure()
                colors = ["#00d26a", "#4da6ff", "#f7931a", "#ff6b6b", "#a78bfa"]
                for i, r in enumerate(results):
                    fig_cmp.add_trace(go.Scatter(
                        x=r["dates"], y=r["equity_curve"],
                        name=r["strategy_label"][:18],
                        line=dict(color=colors[i % len(colors)], width=2),
                    ))
                fig_cmp.update_layout(template="plotly_white", height=400,
                                      margin=dict(l=0, r=0, t=30, b=0),
                                      legend=dict(orientation="h"))
                st.plotly_chart(fig_cmp, use_container_width=True)
            else:
                st.error("比較実行に失敗しました")


elif page == "📜 利用規約・免責":
    render_legal_page()


# ─── フッター ───
st.divider()
st.caption(
    f"⚠️ {APP_DISCLAIMER} "
    "｜メニュー「📜 利用規約・免責」で全文を確認 "
    "｜価格データ: Yahoo Finance｜ニュース: Google News"
)
