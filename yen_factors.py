"""
円相場 総合ファクター分析モジュール

円高/円安に影響を与える「考えられるすべての要因」を統合的に取得・分析し、
各ファクターの現在のバイアス（円高/円安方向への寄与）と総合判定を出力する。

【影響要因のカテゴリー】
1. 金融政策・金利差    : FF金利、長短国債利回り差、日銀政策
2. 米ドル指数 (DXY)
3. 資源・エネルギー    : 原油WTI/ブレント、天然ガス、LNG（日本は輸入国）
4. 貴金属・コモディティ: 金、銀、銅、プラチナ
5. 食料・農産物        : 小麦、大豆、コーン、コーヒー
6. リスクセンチメント  : VIX、SKEW、米株（S&P/NASDAQ/ダウ）
7. 株式市場            : 日経225、TOPIX、上海総合
8. クロスレート        : EUR/USD、GBP/USD、AUD/USD、USD/CNH
9. 暗号資産            : Bitcoin（リスク資産バロメーター）
10. 貿易関連          : 海運運賃指数、米中貿易リスク
11. 地政学            : 中東・ウクライナ・台湾海峡・北朝鮮
12. 政府・中銀介入    : 介入実績／介入観測ライン
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional


# ════════════════════════════════════════════════
#  円相場に影響するすべての因子定義
#  jpy_impact: そのファクターが「上昇」したときに JPY に与える影響
#    "weak"  = 円安方向
#    "strong" = 円高方向
#    "depends" = 状況依存（個別ロジックで判定）
# ════════════════════════════════════════════════

YEN_FACTORS = {
    # ─── 1. 金利・国債利回り ─────────────────────────
    "金利・国債": {
        "^TNX":  {"name": "米国10年債利回り",     "jpy_impact": "weak",  "weight": 5, "unit": "%"},
        "^FVX":  {"name": "米国 5年債利回り",     "jpy_impact": "weak",  "weight": 4, "unit": "%"},
        "^IRX":  {"name": "米国13週TB利回り",     "jpy_impact": "weak",  "weight": 3, "unit": "%"},
        "^TYX":  {"name": "米国30年債利回り",     "jpy_impact": "weak",  "weight": 4, "unit": "%"},
    },

    # ─── 2. 米ドル指数 ─────────────────────────────
    "米ドル指数": {
        "DX-Y.NYB": {"name": "ドルインデックス (DXY)", "jpy_impact": "weak",  "weight": 5, "unit": ""},
    },

    # ─── 3. 資源・エネルギー（日本は輸入国 → 高騰=貿易赤字=円安） ─
    "資源・エネルギー": {
        "CL=F":  {"name": "WTI原油先物",          "jpy_impact": "weak",  "weight": 5, "unit": "$"},
        "BZ=F":  {"name": "ブレント原油先物",     "jpy_impact": "weak",  "weight": 5, "unit": "$"},
        "NG=F":  {"name": "天然ガス先物",         "jpy_impact": "weak",  "weight": 4, "unit": "$"},
        "HO=F":  {"name": "ヒーティングオイル",   "jpy_impact": "weak",  "weight": 2, "unit": "$"},
        "RB=F":  {"name": "ガソリン先物",         "jpy_impact": "weak",  "weight": 2, "unit": "$"},
    },

    # ─── 4. 貴金属（安全資産=円高方向と相関） ──────
    "貴金属・コモディティ": {
        "GC=F":  {"name": "金（ゴールド）",       "jpy_impact": "strong", "weight": 4, "unit": "$"},
        "SI=F":  {"name": "銀（シルバー）",       "jpy_impact": "strong", "weight": 2, "unit": "$"},
        "PL=F":  {"name": "プラチナ",             "jpy_impact": "depends", "weight": 2, "unit": "$"},
        "HG=F":  {"name": "銅（ドクターカッパー）", "jpy_impact": "weak",  "weight": 3, "unit": "$"},
    },

    # ─── 5. 食料・農産物（輸入インフレ要因） ───────
    "食料・農産物": {
        "ZW=F":  {"name": "小麦",                 "jpy_impact": "weak",  "weight": 2, "unit": "¢"},
        "ZS=F":  {"name": "大豆",                 "jpy_impact": "weak",  "weight": 2, "unit": "¢"},
        "ZC=F":  {"name": "とうもろこし",         "jpy_impact": "weak",  "weight": 2, "unit": "¢"},
        "KC=F":  {"name": "コーヒー",             "jpy_impact": "weak",  "weight": 1, "unit": "¢"},
        "SB=F":  {"name": "砂糖",                 "jpy_impact": "weak",  "weight": 1, "unit": "¢"},
    },

    # ─── 6. リスクセンチメント（リスクオフ=円高） ──
    "リスクセンチメント": {
        "^VIX":  {"name": "VIX (恐怖指数)",       "jpy_impact": "strong", "weight": 5, "unit": ""},
        "^MOVE": {"name": "MOVE指数 (債券ボラ)",  "jpy_impact": "strong", "weight": 3, "unit": ""},
        "^SKEW": {"name": "SKEW指数",             "jpy_impact": "strong", "weight": 2, "unit": ""},
    },

    # ─── 7. 株式市場（リスクオン/オフ判定） ─────────
    "株式市場": {
        "^GSPC": {"name": "S&P 500",              "jpy_impact": "weak",  "weight": 4, "unit": ""},
        "^IXIC": {"name": "NASDAQ総合",           "jpy_impact": "weak",  "weight": 3, "unit": ""},
        "^DJI":  {"name": "NYダウ",               "jpy_impact": "weak",  "weight": 3, "unit": ""},
        "^N225": {"name": "日経平均",             "jpy_impact": "weak",  "weight": 4, "unit": "¥"},
        "^TPX":  {"name": "TOPIX",                "jpy_impact": "weak",  "weight": 3, "unit": "¥"},
        "^HSI":  {"name": "ハンセン指数",         "jpy_impact": "weak",  "weight": 2, "unit": ""},
        "000001.SS": {"name": "上海総合指数",     "jpy_impact": "weak",  "weight": 2, "unit": "¥"},
    },

    # ─── 8. クロスレート ────────────────────────────
    "クロスレート（FX）": {
        "EURUSD=X": {"name": "EUR/USD",           "jpy_impact": "depends", "weight": 3, "unit": ""},
        "GBPUSD=X": {"name": "GBP/USD",           "jpy_impact": "depends", "weight": 2, "unit": ""},
        "AUDUSD=X": {"name": "AUD/USD",           "jpy_impact": "weak",    "weight": 3, "unit": ""},
        "NZDUSD=X": {"name": "NZD/USD",           "jpy_impact": "weak",    "weight": 2, "unit": ""},
        "USDCNH=X": {"name": "USD/CNH (人民元)",  "jpy_impact": "weak",    "weight": 4, "unit": "¥"},
        "USDKRW=X": {"name": "USD/KRW (ウォン)",  "jpy_impact": "weak",    "weight": 2, "unit": "₩"},
        "USDCHF=X": {"name": "USD/CHF (スイス)",  "jpy_impact": "weak",    "weight": 2, "unit": ""},
    },

    # ─── 9. 暗号資産（リスク資産バロメーター） ──────
    "暗号資産": {
        "BTC-USD": {"name": "Bitcoin",            "jpy_impact": "weak",  "weight": 3, "unit": "$"},
        "ETH-USD": {"name": "Ethereum",           "jpy_impact": "weak",  "weight": 2, "unit": "$"},
    },

    # ─── 10. 海運・輸送・実体経済 ───────────────────
    "海運・実体経済": {
        # ※ Baltic Dry Index は yfinance で取得できないため代替指標
        "FXI":  {"name": "中国大型株ETF",         "jpy_impact": "weak",  "weight": 2, "unit": "$"},
        "EEM":  {"name": "新興国株ETF",           "jpy_impact": "weak",  "weight": 2, "unit": "$"},
        "XLE":  {"name": "エネルギーセクターETF", "jpy_impact": "weak",  "weight": 2, "unit": "$"},
    },
}


# ════════════════════════════════════════════════
#  地政学・介入リスク（数値化されないがバイアスに加算）
# ════════════════════════════════════════════════

GEOPOLITICAL_RISKS = [
    {"region": "中東", "type": "原油供給リスク",
     "impact": "weak", "desc": "ホルムズ海峡封鎖懸念→原油急騰→円安要因"},
    {"region": "ウクライナ", "type": "エネルギー価格",
     "impact": "weak", "desc": "天然ガス・小麦上昇→輸入インフレ→円安"},
    {"region": "台湾海峡", "type": "リスクオフ",
     "impact": "strong", "desc": "緊急時はアジア圏通貨売り→安全資産の円買い"},
    {"region": "北朝鮮", "type": "短期リスクオフ",
     "impact": "strong", "desc": "ミサイル発射→一時的に円買い"},
    {"region": "米中貿易", "type": "貿易摩擦",
     "impact": "depends", "desc": "報復関税→人民元安→円も連動売り or リスクオフ円買い"},
]


# ════════════════════════════════════════════════
#  日銀・FRB介入ライン（参考値）
# ════════════════════════════════════════════════

INTERVENTION_LEVELS = {
    "USDJPY": {
        "warning": 152.00,
        "intervention_likely": 155.00,
        "historical_intervention": [151.95, 155.20, 160.20],
        "note": "150円超で財務省口先介入、155円超で実弾介入の歴史"
    },
    "EURJPY": {
        "warning": 165.00,
        "intervention_likely": 170.00,
        "note": "クロス円も同時に介入対象となる"
    },
}


# ════════════════════════════════════════════════
#  ファクター取得＆分析エンジン
# ════════════════════════════════════════════════

def _fetch_factor(ticker: str) -> Optional[dict]:
    """単一ファクターの最新値・変動率・トレンドを取得"""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="3mo", interval="1d")
        if df is None or df.empty or len(df) < 5:
            return None

        close = df["Close"]
        current = close.iloc[-1]
        prev = close.iloc[-2]
        change = current - prev
        change_pct = (change / prev) * 100 if prev != 0 else 0

        # 各期間の変動率
        def chg(periods):
            if len(close) > periods:
                return (current / close.iloc[-1 - periods] - 1) * 100
            return 0.0

        ch_5d = chg(5)
        ch_20d = chg(20)
        ch_60d = chg(60)

        # 短期トレンド判定
        ma5 = close.tail(5).mean()
        ma20 = close.tail(20).mean()
        if current > ma5 > ma20:
            trend = "上昇"
        elif current < ma5 < ma20:
            trend = "下降"
        else:
            trend = "横ばい"

        return {
            "current": round(float(current), 4),
            "change": round(float(change), 4),
            "change_pct": round(float(change_pct), 2),
            "change_5d": round(float(ch_5d), 2),
            "change_20d": round(float(ch_20d), 2),
            "change_60d": round(float(ch_60d), 2),
            "trend": trend,
        }
    except Exception:
        return None


def _calc_factor_bias(factor_meta: dict, factor_data: dict) -> dict:
    """
    ファクターの現在の状態から円高/円安バイアススコアを算出

    Returns: {"bias": "weak" | "strong" | "neutral", "score": -3 ~ +3, "label": 文字列}
    """
    if factor_data is None:
        return {"bias": "neutral", "score": 0, "label": "データなし", "color": "#999"}

    impact = factor_meta["jpy_impact"]
    ch_5d = factor_data["change_5d"]
    weight = factor_meta["weight"]

    # 「上昇」したときに円安方向(weak)に効く因子と、円高方向(strong)に効く因子で符号を変える
    if impact == "weak":
        # 上昇 → 円安バイアス +
        raw = ch_5d / 2.0  # 5日変動率の半分をスコア化
    elif impact == "strong":
        # 上昇 → 円高バイアス +（スコアは円安基準で表現するためマイナスに）
        raw = -ch_5d / 2.0
    else:  # depends
        raw = 0

    # 重み加味して -3 〜 +3 に正規化
    score = max(-3, min(3, raw * (weight / 5)))

    if score > 1.0:
        bias = "weak"
        label = f"円安方向 (+{score:.1f})"
        color = "#D32030"
    elif score < -1.0:
        bias = "strong"
        label = f"円高方向 ({score:.1f})"
        color = "#1565C0"
    else:
        bias = "neutral"
        label = f"中立 ({score:+.1f})"
        color = "#888"

    return {
        "bias": bias,
        "score": round(score, 2),
        "label": label,
        "color": color,
        "weight": weight,
        "impact_type": impact,
    }


def fetch_usdjpy_spot_context() -> Optional[dict]:
    """
    ドル円の短期実勢（主に1時間足）を取得。
    ファクター総合（数日スパンの加重）とは独立して「今・直近がどう動いたか」を把握する。
    """
    try:
        t = yf.Ticker("USDJPY=X")
        df_h = t.history(period="12d", interval="1h")
        df_d = t.history(period="40d", interval="1d")
        if df_h is None or df_h.empty or len(df_h) < 3:
            return None
        close = df_h["Close"].dropna()
        cur = float(close.iloc[-1])
        ch_1h = float(close.iloc[-1] - close.iloc[-2]) if len(close) >= 2 else 0.0
        ch_6h = float(close.iloc[-1] - close.iloc[-7]) if len(close) >= 7 else None
        ch_24h = float(close.iloc[-1] - close.iloc[-25]) if len(close) >= 25 else None

        prev_daily_move = None
        if df_d is not None and not df_d.empty and len(df_d) >= 2:
            prev_daily_move = float(df_d["Close"].iloc[-1] - df_d["Close"].iloc[-2])

        shock_move = abs(ch_1h)
        shock_window = None
        is_shock = shock_move >= 1.0
        if is_shock:
            shock_window = "1時間"
        elif ch_24h is not None and abs(ch_24h) >= 2.0:
            is_shock = True
            shock_move = abs(ch_24h)
            shock_window = "約24時間"
        elif prev_daily_move is not None and abs(prev_daily_move) >= 2.5:
            is_shock = True
            shock_move = abs(prev_daily_move)
            shock_window = "直近営業日（日足）"

        return {
            "current": round(cur, 3),
            "change_1h_yen": round(ch_1h, 3),
            "change_6h_yen": round(ch_6h, 3) if ch_6h is not None else None,
            "change_24h_yen": round(ch_24h, 3) if ch_24h is not None else None,
            "change_prev_day_yen": round(prev_daily_move, 3) if prev_daily_move is not None else None,
            "is_shock": is_shock,
            "shock_move_yen": round(shock_move, 3),
            "shock_window": shock_window,
        }
    except Exception:
        return None


def reconcile_factor_verdict_with_spot(summary: dict, spot: Optional[dict]) -> dict:
    """
    ファクター総合判定と短期ドル円実勢の符号が大きくズレたときに警告（乖離検知）。
    """
    if not spot:
        return {"is_divergent": False, "message": "", "severity": "none"}

    verdict = summary.get("verdict", "")
    ch1 = float(spot.get("change_1h_yen") or 0.0)
    ch6 = spot.get("change_6h_yen")
    ch24 = spot.get("change_24h_yen")
    d1 = spot.get("change_prev_day_yen")

    diverge = False
    msg = ""
    severity = "none"

    def _set(m: str, s: str):
        nonlocal diverge, msg, severity
        diverge = True
        msg = m
        severity = s

    if "円安" in verdict:
        if ch1 <= -0.35:
            _set(
                f"ファクターは円安寄りだが、直近1時間でドル円は {ch1:+.3f} 円（円高＝下落方向）と逆行。",
                "high" if ch1 <= -0.8 else "medium",
            )
        elif ch6 is not None and ch6 <= -0.6:
            _set(
                f"ファクターは円安寄りだが、直近6時間でドル円は {ch6:+.3f} 円と円高方向。",
                "medium",
            )
        elif ch24 is not None and ch24 <= -1.0:
            _set(
                f"ファクターは円安寄りだが、約24時間でドル円は {ch24:+.3f} 円と円高が優勢。",
                "high" if ch24 <= -2.0 else "medium",
            )
        elif d1 is not None and d1 <= -1.5:
            _set(
                f"ファクターは円安寄りだが、直近営業日の日足では {d1:+.3f} 円下落（急円高）。",
                "high" if d1 <= -3.0 else "medium",
            )

    elif "円高" in verdict:
        if ch1 >= 0.35:
            _set(
                f"ファクターは円高寄りだが、直近1時間でドル円は {ch1:+.3f} 円（円安＝上昇方向）と逆行。",
                "high" if ch1 >= 0.8 else "medium",
            )
        elif ch6 is not None and ch6 >= 0.6:
            _set(
                f"ファクターは円高寄りだが、直近6時間でドル円は {ch6:+.3f} 円と円安方向。",
                "medium",
            )
        elif ch24 is not None and ch24 >= 1.0:
            _set(
                f"ファクターは円高寄りだが、約24時間でドル円は {ch24:+.3f} 円と円安が優勢。",
                "high" if ch24 >= 2.0 else "medium",
            )
        elif d1 is not None and d1 >= 1.5:
            _set(
                f"ファクターは円高寄りだが、直近営業日の日足では {d1:+.3f} 円上昇（急円安）。",
                "high" if d1 >= 3.0 else "medium",
            )

    elif verdict.startswith("中立"):
        if d1 is not None and abs(d1) >= 2.0:
            _set(
                f"ファクター総合は中立だが、直近営業日の日足でドル円は {d1:+.3f} 円と**大きく変動**。"
                "ファクターモデルは数日スケールの拮抗を示している一方、**短期フローが上書き**している可能性。",
                "high" if abs(d1) >= 4.0 else "medium",
            )
        elif ch24 is not None and abs(ch24) >= 2.0:
            _set(
                f"ファクター総合は中立だが、約24時間でドル円は {ch24:+.3f} 円の振れ。"
                "ポジション調整・イベント・流動性要因を優先的に確認してください。",
                "medium",
            )

    return {
        "is_divergent": diverge,
        "message": msg,
        "severity": severity,
    }


def analyze_all_factors() -> dict:
    """
    全ての円相場ファクターを取得＆分析し、総合判定を返す

    Returns:
        {
            "categories": {
                "金利・国債": [{"ticker", "name", "data", "bias_info"}, ...],
                ...
            },
            "summary": {
                "total_score": 加重合計スコア,
                "verdict": "円安バイアス" | "円高バイアス" | "中立",
                "verdict_strength": "強" | "中" | "弱",
                "weak_factors_count": 円安要因数,
                "strong_factors_count": 円高要因数,
                "neutral_factors_count": 中立数,
                "top_weak_factors": [円安TOP3],
                "top_strong_factors": [円高TOP3],
            },
            "geopolitical": GEOPOLITICAL_RISKS,
            "intervention": INTERVENTION_LEVELS,
            "current_usdjpy": 現在のドル円レート,
        }
    """
    categories = {}
    all_results = []

    for cat_name, factors in YEN_FACTORS.items():
        cat_results = []
        for ticker, meta in factors.items():
            data = _fetch_factor(ticker)
            bias_info = _calc_factor_bias(meta, data)

            entry = {
                "ticker": ticker,
                "name": meta["name"],
                "weight": meta["weight"],
                "unit": meta["unit"],
                "impact_type": meta["jpy_impact"],
                "data": data,
                "bias_info": bias_info,
            }
            cat_results.append(entry)
            all_results.append(entry)
        categories[cat_name] = cat_results

    # 総合スコア集計
    total_score = sum(r["bias_info"]["score"] for r in all_results)
    weak_count = len([r for r in all_results if r["bias_info"]["bias"] == "weak"])
    strong_count = len([r for r in all_results if r["bias_info"]["bias"] == "strong"])
    neutral_count = len([r for r in all_results if r["bias_info"]["bias"] == "neutral"])

    if total_score > 8:
        verdict = "円安バイアス"
        verdict_color = "#D32030"
        if total_score > 20:
            strength = "強"
        elif total_score > 14:
            strength = "中"
        else:
            strength = "弱"
    elif total_score < -8:
        verdict = "円高バイアス"
        verdict_color = "#1565C0"
        if total_score < -20:
            strength = "強"
        elif total_score < -14:
            strength = "中"
        else:
            strength = "弱"
    else:
        verdict = "中立（拮抗）"
        verdict_color = "#888"
        strength = "弱"

    # TOP要因
    weak_top = sorted(
        [r for r in all_results if r["bias_info"]["bias"] == "weak"],
        key=lambda r: r["bias_info"]["score"], reverse=True
    )[:5]
    strong_top = sorted(
        [r for r in all_results if r["bias_info"]["bias"] == "strong"],
        key=lambda r: r["bias_info"]["score"]
    )[:5]

    # 現在のドル円
    usdjpy_data = _fetch_factor("USDJPY=X")
    current_usdjpy = usdjpy_data["current"] if usdjpy_data else None

    spot_ctx = fetch_usdjpy_spot_context()
    reconciliation = reconcile_factor_verdict_with_spot(
        {
            "verdict": verdict,
            "total_score": round(total_score, 1),
            "verdict_strength": strength,
        },
        spot_ctx,
    )

    try:
        from yen_broker_lens import synthesize_broker_lens

        broker_lens = synthesize_broker_lens(
            summary={
                "verdict": verdict,
                "total_score": round(total_score, 1),
                "verdict_strength": strength,
            },
            spot_ctx=spot_ctx,
            reconciliation=reconciliation,
        )
    except Exception:
        broker_lens = {}

    return {
        "categories": categories,
        "summary": {
            "total_score": round(total_score, 1),
            "verdict": verdict,
            "verdict_strength": strength,
            "verdict_color": verdict_color,
            "weak_factors_count": weak_count,
            "strong_factors_count": strong_count,
            "neutral_factors_count": neutral_count,
            "top_weak_factors": weak_top,
            "top_strong_factors": strong_top,
        },
        "geopolitical": GEOPOLITICAL_RISKS,
        "intervention": INTERVENTION_LEVELS,
        "current_usdjpy": current_usdjpy,
        "spot_context": spot_ctx,
        "reconciliation": reconciliation,
        "broker_lens": broker_lens,
        "analyzed_at": datetime.now().isoformat(),
    }


def get_intervention_warning(usdjpy: float) -> Optional[dict]:
    """ドル円レベルから介入リスク警戒度を返す"""
    if usdjpy is None:
        return None
    levels = INTERVENTION_LEVELS["USDJPY"]
    if usdjpy >= levels["intervention_likely"]:
        return {
            "level": "高",
            "color": "#D32030",
            "message": f"⚠ {levels['intervention_likely']}円超 → 実弾介入の可能性極めて高い",
            "advice": "急激な円高への巻き戻しに注意"
        }
    elif usdjpy >= levels["warning"]:
        return {
            "level": "中",
            "color": "#FDB813",
            "message": f"⚠ {levels['warning']}円超 → 財務省・口先介入リスク",
            "advice": "要人発言・介入観測報道に警戒"
        }
    else:
        return {
            "level": "低",
            "color": "#1565C0",
            "message": f"介入水準（{levels['warning']}円）まで余裕あり",
            "advice": "—"
        }


# ════════════════════════════════════════════════
#  eBay輸出：利益計算エンジン
# ════════════════════════════════════════════════

# eBay / 受取手数料のデフォルト（2026年時点の一般的な値）
# Final Value Fee はカテゴリで多少変動する。ブランド時計等は一部異なる。
DEFAULT_EBAY_FEE_RATE = 0.1325       # eBay Final Value Fee 13.25%
DEFAULT_PAYONEER_FEE_RATE = 0.02     # Payoneer 受取・出金手数料目安 2%
DEFAULT_INTL_FEE_RATE = 0.0165       # International fee 1.65%（海外販売時）


# ════════════════════════════════════════════════
#  仕入れ先プリセット
#  name: 表示名, typical_margin: 標準的な利益率目安(%),
#  notes: 特徴・注意点
# ════════════════════════════════════════════════

SOURCES = {
    "yahoo_auction": {
        "name": "Yahoo!オークション",
        "url": "https://auctions.yahoo.co.jp/",
        "typical_margin": "40〜80%（骨董・絶版で100%超も）",
        "strengths": "骨董・中古カメラ・古銭・レトロゲームの宝庫",
        "notes": "古物商許可証ほぼ必須。偽物に注意（特に刀剣・陶磁器）。",
    },
    "yahoo_shopping": {
        "name": "Yahoo!ショッピング",
        "url": "https://shopping.yahoo.co.jp/",
        "typical_margin": "20〜40%",
        "strengths": "5のつく日＋LYPプレミアムで15%超還元",
        "notes": "在庫が薄いジャンルあり。",
    },
    "rakuten": {
        "name": "楽天市場",
        "url": "https://www.rakuten.co.jp/",
        "typical_margin": "20〜40%",
        "strengths": "SPU＋お買い物マラソンで実質15〜20%OFF",
        "notes": "楽天カードで還元率最大化。",
    },
    "amazon_jp": {
        "name": "Amazon.co.jp",
        "url": "https://www.amazon.co.jp/",
        "typical_margin": "15〜35%",
        "strengths": "Prime配送が速い。価格比較が容易。",
        "notes": "Amazon米国の並行輸入で日本の方が高い場合もあり。",
    },
    "mercari": {
        "name": "メルカリ",
        "url": "https://jp.mercari.com/",
        "typical_margin": "30〜70%",
        "strengths": "個人出品の掘り出し物が多い",
        "notes": "中古はノンクレノンリターンが基本。古物商許可推奨。",
    },
    "surugaya": {
        "name": "駿河屋",
        "url": "https://www.suruga-ya.jp/",
        "typical_margin": "40〜80%",
        "strengths": "ホビー・ゲーム・トレカが最安値圏",
        "notes": "納期遅い、キャンセル発生率高め。",
    },
    "fanvi_terauchi": {
        "name": "ファンビ寺内",
        "url": "https://www.fanvi.co.jp/",
        "typical_margin": "40〜60%",
        "strengths": "ブランド服（コムデギャルソン、イッセイミヤケ等）の卸",
        "notes": "業者登録必須。現金決済中心。",
    },
    "superdelivery": {
        "name": "スーパーデリバリー",
        "url": "https://www.superdelivery.com/",
        "typical_margin": "30〜60%",
        "strengths": "アパレル・雑貨・食品の卸サイト",
        "notes": "月額2,200円、法人/個人事業主登録必要。",
    },
    "kosendo": {
        "name": "古書店・骨董市（実店舗＋オンライン）",
        "url": "",
        "typical_margin": "50〜200%",
        "strengths": "目利きで激安掘り出し物。eBay化で大化けする",
        "notes": "目利き力が収益を左右。古物商許可必須。",
    },
}


# ════════════════════════════════════════════════
#  商品カテゴリプリセット（骨董品を含む）
#  typical_margin: eBay等に海外販売した場合の利益率目安
# ════════════════════════════════════════════════

CATEGORIES = {
    # ─── 骨董品・日本文化系（欧米コレクター人気・高利益） ─
    "骨董品・浮世絵": {
        "typical_margin": "50〜200%",
        "examples": "歌川広重・葛飾北斎・月岡芳年など木版画、摺物",
        "hot_markets": "アメリカ、フランス、ドイツ",
        "risk": "真贋判定が難しい。昭和期の復刻版に注意。",
    },
    "骨董品・刀剣": {
        "typical_margin": "60〜150%",
        "examples": "脇差、短刀、鐔(つば)、拵え、模造刀は不可",
        "hot_markets": "アメリカ、イギリス、フランス",
        "risk": "真剣は銃砲刀剣類登録証必須、輸出は許可必要。",
    },
    "骨董品・陶磁器": {
        "typical_margin": "40〜120%",
        "examples": "九谷焼、有田焼、萩焼、志野、織部、備前",
        "hot_markets": "アメリカ、ヨーロッパ、台湾",
        "risk": "破損リスク→厳重梱包必須。贋作に注意。",
    },
    "骨董品・茶道具": {
        "typical_margin": "50〜150%",
        "examples": "茶碗、茶筅、棗、水指、釜、掛け軸",
        "hot_markets": "アメリカ、ヨーロッパ、中国、台湾",
        "risk": "共箱・箱書きの有無で価値が10倍変わる。",
    },
    "骨董品・仏像・仏具": {
        "typical_margin": "60〜200%",
        "examples": "木彫仏像、銅製仏具、念珠、経典",
        "hot_markets": "欧米の仏教徒、東南アジア",
        "risk": "宗教的配慮が必要。輸出規制品あり。",
    },
    "骨董品・着物・帯": {
        "typical_margin": "40〜100%",
        "examples": "アンティーク着物、大島紬、西陣帯、刺繍羽織",
        "hot_markets": "アメリカ、オーストラリア、ヨーロッパ",
        "risk": "シミ・虫食いに要注意。素材で価格大差。",
    },
    "骨董品・古銭・切手": {
        "typical_margin": "30〜300%",
        "examples": "大判小判、寛永通宝、明治銀貨、戦前切手",
        "hot_markets": "世界中のコレクター",
        "risk": "贋作多数。グレーディング推奨。",
    },
    "骨董品・漆器・蒔絵": {
        "typical_margin": "50〜150%",
        "examples": "輪島塗、春慶塗、蒔絵硯箱・重箱、印籠、根付",
        "hot_markets": "欧米、中東",
        "risk": "ひび・剥離に注意。",
    },
    "骨董品・古書・浮世絵本": {
        "typical_margin": "30〜150%",
        "examples": "和装本、絵本、古地図、絵入本",
        "hot_markets": "欧米の大学図書館・研究者",
        "risk": "状態とサインで価格大差。",
    },

    # ─── ホビー系 ─
    "ホビー・ポケモンカード": {"typical_margin": "40〜100%",
                              "hot_markets": "世界中"},
    "ホビー・フィギュア": {"typical_margin": "30〜60%",
                          "hot_markets": "アメリカ、ヨーロッパ、東南アジア"},
    "ホビー・ガンプラ": {"typical_margin": "30〜80%",
                       "hot_markets": "世界中"},

    # ─── カメラ・時計・楽器 ─
    "カメラ・レンズ": {"typical_margin": "30〜70%",
                     "hot_markets": "アメリカ、ヨーロッパ"},
    "時計": {"typical_margin": "30〜60%",
            "hot_markets": "アジア、欧米"},
    "楽器": {"typical_margin": "40〜80%",
            "hot_markets": "アメリカ、ヨーロッパ"},

    # ─── その他 ─
    "ファッション": {"typical_margin": "40〜60%",
                    "hot_markets": "欧米、東南アジア"},
    "ゲーム": {"typical_margin": "40〜100%",
              "hot_markets": "世界中"},
    "包丁・キッチン": {"typical_margin": "50%〜",
                     "hot_markets": "欧米シェフ"},
    "化粧品": {"typical_margin": "20〜40%",
              "hot_markets": "中国、東南アジア、北米"},
}


def list_sources() -> str:
    """仕入れ先プリセット一覧を整形して返す"""
    lines = ["━━━ 仕入れ先プリセット ━━━"]
    for key, s in SOURCES.items():
        lines.append(f"\n[{key}] {s['name']}")
        lines.append(f"  URL       : {s['url'] or '—'}")
        lines.append(f"  想定利益率: {s['typical_margin']}")
        lines.append(f"  強み      : {s['strengths']}")
        lines.append(f"  注意点    : {s['notes']}")
    return "\n".join(lines)


def list_categories(keyword: str = "") -> str:
    """商品カテゴリ一覧を整形して返す（keywordでフィルタ可）"""
    lines = ["━━━ 商品カテゴリ（海外販売の利益率目安） ━━━"]
    for name, c in CATEGORIES.items():
        if keyword and keyword not in name:
            continue
        lines.append(f"\n● {name}")
        lines.append(f"  利益率目安: {c.get('typical_margin', '—')}")
        if "examples" in c:
            lines.append(f"  主な品目  : {c['examples']}")
        if "hot_markets" in c:
            lines.append(f"  人気国    : {c['hot_markets']}")
        if "risk" in c:
            lines.append(f"  リスク    : {c['risk']}")
    return "\n".join(lines)


def calc_ebay_profit(
    cost_jpy: float,
    sell_price_usd: float,
    product_name: str = "",
    sku: str = "",
    category: str = "",
    source: str = "",
    shipping_usd: float = 0.0,
    shipping_cost_jpy: float = 0.0,
    extra_cost_jpy: float = 0.0,
    ebay_fee_rate: float = DEFAULT_EBAY_FEE_RATE,
    payoneer_fee_rate: float = DEFAULT_PAYONEER_FEE_RATE,
    intl_fee_rate: float = DEFAULT_INTL_FEE_RATE,
    usdjpy: Optional[float] = None,
    include_yen_analysis: bool = False,
) -> dict:
    """
    eBay 輸出の利益を、現在の為替レート＆円相場バイアスを加味して計算する。

    Args:
        cost_jpy: 仕入れ値（円、税込）
        sell_price_usd: eBay での販売価格（ドル）
        product_name: 商品名（レポート表示用、任意）
        sku: 自分の管理用SKU（任意）
        category: カテゴリ（例: カメラ / 骨董品・陶磁器 など、任意）
        source: 仕入れ先キー or 名前（例: "yahoo_auction" / "楽天" など、任意）
        shipping_usd: 買い手から受け取る送料（ドル、送料込み価格なら0）
        shipping_cost_jpy: 実際にかかる国際発送コスト（円）
        extra_cost_jpy: 梱包材・国内送料などその他経費（円）
        ebay_fee_rate: eBay Final Value Fee（デフォルト13.25%）
        payoneer_fee_rate: Payoneer受取手数料（デフォルト2%）
        intl_fee_rate: 海外販売追加手数料（デフォルト1.65%）
        usdjpy: ドル円レート。Noneなら yfinance から取得
        include_yen_analysis: True なら全ファクター分析（時間がかかる）も含める

    Returns:
        {
          "usdjpy": 現在のドル円,
          "revenue_usd": eBay総売上（$）,
          "fee_usd": 各種手数料合計（$）,
          "net_usd": 手取り（$）,
          "revenue_jpy": 円換算売上,
          "cost_total_jpy": 総コスト（仕入れ＋発送＋その他）,
          "profit_jpy": 純利益（円）,
          "margin_pct": 利益率（売上ベース %）,
          "roi_pct": 投資対利益率（コストベース %）,
          "timing": 売却タイミング判定文字列,
          "intervention_risk": 介入リスク辞書 or None,
          "yen_verdict": 円相場バイアス（全分析した場合のみ詳細）,
          "judge": "GO" | "HOLD" | "STOP" の3値判定,
        }
    """
    # ── ドル円レート取得
    if usdjpy is None:
        usdjpy_data = _fetch_factor("USDJPY=X")
        if usdjpy_data is None:
            raise RuntimeError("USD/JPY レート取得失敗。引数 usdjpy を指定してください。")
        usdjpy = usdjpy_data["current"]

    # ── 売上・手数料の計算（USDベース）
    gross_usd = sell_price_usd + shipping_usd
    total_fee_rate = ebay_fee_rate + payoneer_fee_rate + intl_fee_rate
    fee_usd = gross_usd * total_fee_rate
    net_usd = gross_usd - fee_usd

    # ── 円換算
    revenue_jpy = net_usd * usdjpy
    cost_total_jpy = cost_jpy + shipping_cost_jpy + extra_cost_jpy
    profit_jpy = revenue_jpy - cost_total_jpy

    margin = (profit_jpy / revenue_jpy * 100) if revenue_jpy > 0 else 0
    roi = (profit_jpy / cost_total_jpy * 100) if cost_total_jpy > 0 else 0

    # ── 介入リスク
    intervention = get_intervention_warning(usdjpy)

    # ── 円相場バイアス（任意・重い処理なのでオプション）
    yen_verdict = None
    timing = "為替分析スキップ"
    if include_yen_analysis:
        analysis = analyze_all_factors()
        yen_verdict = {
            "verdict": analysis["summary"]["verdict"],
            "strength": analysis["summary"]["verdict_strength"],
            "total_score": analysis["summary"]["total_score"],
        }
        v = analysis["summary"]["verdict"]
        if v == "円安バイアス":
            timing = "売り時（円安で円換算利益が伸びている）"
        elif v == "円高バイアス":
            timing = "売却待機 or 値上げ出品を検討（円高で目減り）"
        else:
            timing = "中立：通常運転"
    else:
        # 簡易タイミング：介入リスクだけでざっくり判定
        if intervention and intervention["level"] == "高":
            timing = "介入警戒：在庫を早めに売却推奨"
        elif usdjpy and usdjpy >= 150:
            timing = "円安圏：販売有利"
        else:
            timing = "通常水準"

    # ── GO / HOLD / STOP 判定
    if profit_jpy <= 0:
        judge = "STOP"
    elif roi >= 30:
        judge = "GO"
    elif roi >= 15:
        judge = "HOLD"
    else:
        judge = "STOP"

    # ── 仕入れ先表示名の解決（プリセットキーなら日本語名へ）
    source_display = SOURCES[source]["name"] if source in SOURCES else source

    return {
        "product_name": product_name,
        "sku": sku,
        "category": category,
        "source": source_display,
        "usdjpy": round(usdjpy, 3),
        "revenue_usd": round(gross_usd, 2),
        "fee_usd": round(fee_usd, 2),
        "net_usd": round(net_usd, 2),
        "revenue_jpy": round(revenue_jpy),
        "cost_total_jpy": round(cost_total_jpy),
        "profit_jpy": round(profit_jpy),
        "margin_pct": round(margin, 1),
        "roi_pct": round(roi, 1),
        "timing": timing,
        "intervention_risk": intervention,
        "yen_verdict": yen_verdict,
        "judge": judge,
    }


def format_ebay_profit_report(result: dict) -> str:
    """calc_ebay_profit の結果を日本語レポート文字列に整形"""
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("  eBay 輸出 利益シミュレーション")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if result.get("product_name"):
        lines.append(f"  商品名            : {result['product_name']}")
    if result.get("sku"):
        lines.append(f"  SKU               : {result['sku']}")
    if result.get("category"):
        lines.append(f"  カテゴリ          : {result['category']}")
    if result.get("source"):
        lines.append(f"  仕入れ先          : {result['source']}")
    if any(result.get(k) for k in ("product_name", "sku", "category", "source")):
        lines.append("  ─────────────────────────")
    lines.append(f"  現在のUSD/JPY     : {result['usdjpy']} 円")
    lines.append(f"  eBay売上（総額）  : ${result['revenue_usd']:.2f}")
    lines.append(f"  手数料合計        : ${result['fee_usd']:.2f}")
    lines.append(f"  手取り            : ${result['net_usd']:.2f}")
    lines.append("  ─────────────────────────")
    lines.append(f"  円換算売上        : ¥{result['revenue_jpy']:,}")
    lines.append(f"  総コスト          : ¥{result['cost_total_jpy']:,}")
    lines.append(f"  純利益            : ¥{result['profit_jpy']:,}")
    lines.append(f"  利益率（売上比）  : {result['margin_pct']}%")
    lines.append(f"  ROI（投下資金比） : {result['roi_pct']}%")
    lines.append("  ─────────────────────────")

    judge_mark = {"GO": "[GO] 仕入れ推奨", "HOLD": "[HOLD] 要検討",
                  "STOP": "[STOP] 見送り"}
    lines.append(f"  判定              : {judge_mark.get(result['judge'], result['judge'])}")
    lines.append(f"  タイミング        : {result['timing']}")

    if result["intervention_risk"]:
        ir = result["intervention_risk"]
        lines.append(f"  介入リスク        : {ir['level']} - {ir['message']}")

    if result["yen_verdict"]:
        yv = result["yen_verdict"]
        lines.append(
            f"  円相場バイアス    : {yv['verdict']}（{yv['strength']}） "
            f"score={yv['total_score']}"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def calc_us_jp_yield_spread() -> Optional[dict]:
    """米日金利差（10年債）を算出 - 円相場との相関が強い"""
    us10y = _fetch_factor("^TNX")
    if us10y is None:
        return None
    # 日本の10年債はyfinanceで取れないため、目安として0.7%（2025年想定）
    jp10y_proxy = 0.7
    spread = us10y["current"] - jp10y_proxy
    return {
        "us10y": us10y["current"],
        "jp10y_estimate": jp10y_proxy,
        "spread": round(spread, 2),
        "spread_5d_change": round(us10y["change_5d"], 2),
        "interpretation": (
            "金利差拡大 → 円安方向" if us10y["change_5d"] > 0
            else "金利差縮小 → 円高方向"
        ),
    }


# ════════════════════════════════════════════════
#  CLI: python yen_factors.py を直接叩くとデモ実行
# ════════════════════════════════════════════════

if __name__ == "__main__":
    # サンプル1：Yahoo!オークション仕入れの骨董品（九谷焼）
    antique = calc_ebay_profit(
        product_name="九谷焼 赤絵金彩 花瓶 明治期 共箱付",
        sku="ANT-KUT-001",
        category="骨董品・陶磁器",
        source="yahoo_auction",
        cost_jpy=12000,
        sell_price_usd=280,
        shipping_usd=45,
        shipping_cost_jpy=5500,
        extra_cost_jpy=800,  # 梱包材（陶磁器は厳重梱包）
    )
    print(format_ebay_profit_report(antique))

    # サンプル2：Yahoo!オークション仕入れのカメラ
    camera = calc_ebay_profit(
        product_name="Nikon AI-s 50mm f/1.4 レンズ 中古美品",
        sku="CAM-NIK-001",
        category="カメラ・レンズ",
        source="yahoo_auction",
        cost_jpy=15000,
        sell_price_usd=180,
        shipping_usd=25,
        shipping_cost_jpy=3500,
        extra_cost_jpy=300,
    )
    print(format_ebay_profit_report(camera))

    # 骨董品カテゴリ一覧も表示
    print()
    print(list_categories(keyword="骨董品"))
