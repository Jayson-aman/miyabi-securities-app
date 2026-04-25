"""
15分間隔 買値/売値予測モジュール
FX・原油・主要CFD（指数CFD）について
今後 15分／30分／45分／60分の bid/ask 予想値を生成
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# ════════════════════════════════════════════════
#  対象銘柄定義 ＋ 標準スプレッド（参考値）
#  spread: 1単位あたりの bid と ask の差
# ════════════════════════════════════════════════

INTERVAL_TARGETS = {
    # ─── FX ───
    "USDJPY=X": {
        "label": "USD/JPY", "category": "FX", "spread": 0.003, "decimals": 3, "unit": "円",
    },
    "EURJPY=X": {
        "label": "EUR/JPY", "category": "FX", "spread": 0.005, "decimals": 3, "unit": "円",
    },
    "GBPJPY=X": {
        "label": "GBP/JPY", "category": "FX", "spread": 0.010, "decimals": 3, "unit": "円",
    },
    "AUDJPY=X": {
        "label": "AUD/JPY", "category": "FX", "spread": 0.006, "decimals": 3, "unit": "円",
    },
    "EURUSD=X": {
        "label": "EUR/USD", "category": "FX", "spread": 0.00005, "decimals": 5, "unit": "$",
    },
    "GBPUSD=X": {
        "label": "GBP/USD", "category": "FX", "spread": 0.00010, "decimals": 5, "unit": "$",
    },

    # ─── 原油 / コモディティ CFD ───
    "CL=F": {
        "label": "WTI原油", "category": "原油・商品CFD", "spread": 0.04, "decimals": 2, "unit": "$",
    },
    "BZ=F": {
        "label": "ブレント原油", "category": "原油・商品CFD", "spread": 0.04, "decimals": 2, "unit": "$",
    },
    "NG=F": {
        "label": "天然ガス", "category": "原油・商品CFD", "spread": 0.005, "decimals": 3, "unit": "$",
    },
    "GC=F": {
        "label": "金（ゴールド）", "category": "原油・商品CFD", "spread": 0.30, "decimals": 2, "unit": "$",
    },
    "SI=F": {
        "label": "銀（シルバー）", "category": "原油・商品CFD", "spread": 0.020, "decimals": 3, "unit": "$",
    },

    # ─── 主要指数 CFD ───
    "^N225": {
        "label": "日経225 CFD", "category": "指数CFD", "spread": 7, "decimals": 0, "unit": "円",
    },
    "^DJI": {
        "label": "米国D30 (ダウ)", "category": "指数CFD", "spread": 2.5, "decimals": 1, "unit": "$",
    },
    "^GSPC": {
        "label": "S&P 500", "category": "指数CFD", "spread": 0.5, "decimals": 2, "unit": "$",
    },
    "^IXIC": {
        "label": "NASDAQ総合", "category": "指数CFD", "spread": 2.0, "decimals": 2, "unit": "$",
    },
    "^NDX": {
        "label": "NASDAQ100", "category": "指数CFD", "spread": 1.5, "decimals": 2, "unit": "$",
    },
    "^GDAXI": {
        "label": "独DAX", "category": "指数CFD", "spread": 1.0, "decimals": 1, "unit": "€",
    },
    "^FTSE": {
        "label": "英FTSE100", "category": "指数CFD", "spread": 1.0, "decimals": 1, "unit": "£",
    },
    "^HSI": {
        "label": "香港ハンセン", "category": "指数CFD", "spread": 5, "decimals": 0, "unit": "HKD",
    },
}


# ════════════════════════════════════════════════
#  予測ロジック：15分間隔 × 4ステップ
# ════════════════════════════════════════════════

def _momentum_prediction(closes: pd.Series, steps: int = 4) -> tuple:
    """
    モメンタム＋EMA勾配を組み合わせた短期予測
    Returns: (predicted_prices[], confidence_pcts[])
    """
    if len(closes) < 10:
        last = float(closes.iloc[-1])
        return [last] * steps, [50] * steps

    # 最近5本の平均変化
    recent_diffs = closes.diff().tail(5).dropna()
    avg_change = float(recent_diffs.mean())

    # EMA勾配（最近10本）
    ema = closes.ewm(span=10, adjust=False).mean()
    ema_slope = (float(ema.iloc[-1]) - float(ema.iloc[-5])) / 5 if len(ema) >= 5 else 0

    # ボラティリティ
    vol = float(closes.diff().tail(20).std()) if len(closes) >= 20 else abs(avg_change) * 2

    # 加重平均（モメンタム7割、EMA勾配3割）
    expected_step = avg_change * 0.7 + ema_slope * 0.3

    last = float(closes.iloc[-1])
    predicted = []
    confidences = []
    for i in range(1, steps + 1):
        # 時間が長いほど不確実性増す（モメンタム減衰）
        decay = 0.85 ** (i - 1)
        p = last + expected_step * i * decay
        predicted.append(p)

        # 信頼度（ボラ大なら下がる）
        if vol > 0:
            error_pct = (vol * np.sqrt(i)) / abs(last) * 100
            conf = max(35, min(85, 80 - error_pct * 8))
        else:
            conf = 60
        confidences.append(round(conf))
    return predicted, confidences


# ════════════════════════════════════════════════
#  銘柄別「マクロ要因」テンプレート
#  上昇/下落どちらに動いた時、典型的に何が原因かを返す
# ════════════════════════════════════════════════

MACRO_DRIVERS = {
    "USDJPY=X": {
        "up": "米金利上昇 / 米株高 / リスクオン / 日米金利差拡大 / 介入後の戻り",
        "down": "米金利低下 / リスクオフ / 日銀タカ派 / 政府/財務省介入 / 米景気減速懸念",
    },
    "EURJPY=X": {
        "up": "ECBタカ派 / ユーロ圏景気回復 / 欧州株高 / 円全面安",
        "down": "ECBハト派 / ユーロ圏景気減速 / リスクオフ / 円買戻し",
    },
    "GBPJPY=X": {
        "up": "BOE利上げ観測 / 英CPI高止まり / 英株高 / リスクオン",
        "down": "BOE利下げ観測 / 英景気不安 / リスクオフ / 介入観測",
    },
    "AUDJPY=X": {
        "up": "資源価格高騰 / 中国景気回復 / リスクオン / RBAタカ派",
        "down": "鉄鉱石・銅安 / 中国景気不安 / リスクオフ / RBAハト派",
    },
    "EURUSD=X": {
        "up": "ドル安(米金利低下) / ECBタカ派 / 欧米金利差縮小",
        "down": "ドル高(米金利上昇) / ECBハト派 / 欧州景気不安 / 米経済の独歩高",
    },
    "GBPUSD=X": {
        "up": "ドル安 / BOEタカ派 / 英CPI高止まり",
        "down": "ドル高 / BOEハト派 / 英景気不安",
    },
    "CL=F": {
        "up": "中東情勢悪化 / OPEC+減産観測 / 米在庫減少 / ドル安 / 中国需要回復",
        "down": "OPEC+増産 / 米在庫急増 / 中国需要鈍化 / ドル高 / 景気後退懸念",
    },
    "BZ=F": {
        "up": "ホルムズ海峡リスク / OPEC+減産 / 欧州冬季需要 / 在庫減",
        "down": "中東緊張緩和 / OPEC+増産 / 欧州景気不安",
    },
    "NG=F": {
        "up": "寒波予報 / 米在庫減 / LNG輸出増 / 欧州供給不安",
        "down": "暖冬 / 米在庫過剰 / 需要減 / 風力/太陽光好調",
    },
    "GC=F": {
        "up": "実質金利低下 / ドル安 / 地政学リスク / インフレ懸念 / 中銀買い増し",
        "down": "実質金利上昇 / ドル高 / リスクオン / FRBタカ派",
    },
    "SI=F": {
        "up": "金高に連動 / 産業需要回復 / ソーラー需要 / ドル安",
        "down": "金安 / 製造業PMI悪化 / 産業需要減",
    },
    "^N225": {
        "up": "米株高 / 円安進行 / 半導体株上昇 / 海外勢買い / 日銀緩和継続観測",
        "down": "米株安 / 円高進行 / 海外勢売り / 日銀タカ派観測 / 中国不振",
    },
    "^DJI": {
        "up": "シクリカル株好調 / 金利低下 / 好決算 / 原油高(エネルギー比重高)",
        "down": "金利上昇 / リセッション懸念 / 工業株不振 / 原油安",
    },
    "^GSPC": {
        "up": "FRBハト派 / 好決算 / 金利低下 / メガテック上昇 / VIX低下",
        "down": "FRBタカ派 / 決算ミス / 金利急騰 / VIX急騰 / 地政学リスク",
    },
    "^IXIC": {
        "up": "AI/半導体ブーム / 金利低下 / メガテック決算 / 成長期待",
        "down": "金利上昇 / グロース売り / 規制懸念 / 決算失望",
    },
    "^NDX": {
        "up": "AI/半導体株主導 / 金利低下 / NVIDIA高 / クラウド/AI関連好決算",
        "down": "金利上昇 / グロース売り / 大型テック決算ミス",
    },
    "^GDAXI": {
        "up": "ECBハト派観測 / 中国景気回復 / ドイツ製造業PMI改善 / ユーロ安(輸出有利)",
        "down": "ECBタカ派 / 中国不振 / 製造業PMI悪化 / ロシア情勢悪化",
    },
    "^FTSE": {
        "up": "原油高(エネルギー比重高) / コモディティ株高 / ポンド安(輸出有利)",
        "down": "原油安 / 中国景気不安 / ポンド高",
    },
    "^HSI": {
        "up": "中国景気刺激策 / テック規制緩和 / アリババ/テンセント好決算 / 米中緊張緩和",
        "down": "中国景気不安 / 不動産危機 / 米中対立激化 / テック規制強化",
    },
}


def _direction_label(pred_price: float, current: float) -> tuple:
    """方向ラベル＆色"""
    diff_pct = (pred_price / current - 1) * 100 if current else 0
    if diff_pct > 0.05:
        return "📈 上昇", "#D32030", diff_pct
    elif diff_pct < -0.05:
        return "📉 下落", "#1565C0", diff_pct
    else:
        return "➡️ 横ばい", "#888", diff_pct


# ════════════════════════════════════════════════
#  メインAPI：単一銘柄の15分予測
# ════════════════════════════════════════════════

def _build_reasoning(ticker: str, closes: pd.Series, predicted_60min: float, current: float) -> dict:
    """
    なぜそう予測したかの根拠を構造化して返す
    """
    if len(closes) < 20:
        return {
            "summary": "データ不足",
            "technical_reasons": [],
            "macro_drivers": [],
            "key_risk": "—",
        }

    # ── テクニカル根拠 ──
    tech = []

    # モメンタム
    last5_diff = float(closes.diff().tail(5).sum())
    if last5_diff > 0:
        tech.append(f"📈 直近5本(75分)で {last5_diff:+.4f} 上昇（上昇モメンタム）")
    else:
        tech.append(f"📉 直近5本(75分)で {last5_diff:+.4f} 下落（下降モメンタム）")

    # EMA勾配
    ema = closes.ewm(span=10, adjust=False).mean()
    ema_slope_pct = (float(ema.iloc[-1]) / float(ema.iloc[-5]) - 1) * 100 if len(ema) >= 5 else 0
    if ema_slope_pct > 0.05:
        tech.append(f"📊 10本EMA勾配 +{ema_slope_pct:.3f}% → 短期トレンドは上向き")
    elif ema_slope_pct < -0.05:
        tech.append(f"📊 10本EMA勾配 {ema_slope_pct:.3f}% → 短期トレンドは下向き")
    else:
        tech.append(f"📊 10本EMA勾配 {ema_slope_pct:+.3f}% → ほぼフラット")

    # RSI
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if len(closes) >= 14 else 50
    if rsi >= 70:
        tech.append(f"🔺 RSI={rsi:.0f}（買われすぎ → 反落リスク）")
    elif rsi <= 30:
        tech.append(f"🔻 RSI={rsi:.0f}（売られすぎ → 反発期待）")
    else:
        tech.append(f"⚖️ RSI={rsi:.0f}（中立圏）")

    # ボラティリティ
    vol = float(closes.diff().tail(20).std())
    vol_pct = (vol / current * 100) if current else 0
    if vol_pct > 0.3:
        tech.append(f"⚡ 15分足ボラ高め({vol_pct:.2f}%) → 値動き急激")
    else:
        tech.append(f"💧 15分足ボラ落ち着き({vol_pct:.2f}%) → 安定推移")

    # ── マクロ要因 ──
    diff_pct = (predicted_60min / current - 1) * 100 if current else 0
    drivers = MACRO_DRIVERS.get(ticker, {})
    if diff_pct > 0:
        macro = drivers.get("up", "上昇要因が優勢")
        direction_label = "上昇シナリオの主な原因"
    elif diff_pct < 0:
        macro = drivers.get("down", "下落要因が優勢")
        direction_label = "下落シナリオの主な原因"
    else:
        macro = "明確な方向感なし — レンジ相場"
        direction_label = "レンジ要因"

    # ── 重要リスク（反転材料）──
    key_risk = ""
    if rsi >= 70 and diff_pct > 0:
        key_risk = "🚨 RSI過熱中の上昇予測 → 急反落リスクに注意"
    elif rsi <= 30 and diff_pct < 0:
        key_risk = "🚨 RSI低下中の下落予測 → 急反発リスクに注意"
    elif vol_pct > 0.5:
        key_risk = "🚨 ボラティリティ高 → 予測レンジを大きく外れる可能性"
    elif abs(diff_pct) < 0.05:
        key_risk = "💡 値動き乏しい → イベント待ち・突発材料待ち"
    else:
        key_risk = "✅ 標準的な相場環境 → 予測に沿いやすい"

    summary = f"{ema_slope_pct:+.2f}%の勾配・RSI{rsi:.0f}・ボラ{vol_pct:.2f}%から、60分先 {diff_pct:+.3f}% を予測"

    return {
        "summary": summary,
        "technical_reasons": tech,
        "macro_label": direction_label,
        "macro_drivers": macro,
        "key_risk": key_risk,
        "rsi": round(rsi, 1),
        "ema_slope_pct": round(ema_slope_pct, 3),
        "vol_pct": round(vol_pct, 3),
        "predicted_60min_pct": round(diff_pct, 3),
    }


def predict_intervals(ticker: str, steps: int = 4) -> Optional[dict]:
    """
    15分間隔で steps 回先までの bid/ask を予測

    Returns:
        {
          "ticker", "label", "category", "current_price", "current_bid", "current_ask",
          "intervals": [
            {"step": 1, "time_offset": "+15分", "predicted": 159.32, "bid": 159.318, "ask": 159.322,
             "direction": "📈 上昇", "diff_pct": +0.05, "confidence": 72},
            ...
          ]
        }
    """
    if ticker not in INTERVAL_TARGETS:
        return None
    info = INTERVAL_TARGETS[ticker]

    try:
        t = yf.Ticker(ticker)
        # 過去5日分の15分足
        df = t.history(period="5d", interval="15m")
        if df is None or df.empty or len(df) < 10:
            # 5分足にフォールバック
            df = t.history(period="2d", interval="5m")
            if df is None or df.empty or len(df) < 10:
                return None
    except Exception:
        return None

    closes = df["Close"].dropna()
    if closes.empty:
        return None
    current = float(closes.iloc[-1])
    spread = info["spread"]
    half_sp = spread / 2

    current_bid = round(current - half_sp, info["decimals"] + 1)
    current_ask = round(current + half_sp, info["decimals"] + 1)

    preds, confs = _momentum_prediction(closes, steps)
    now = datetime.now()
    intervals = []
    for i, (p, c) in enumerate(zip(preds, confs), start=1):
        bid = round(p - half_sp, info["decimals"] + 1)
        ask = round(p + half_sp, info["decimals"] + 1)
        direction, color, diff_pct = _direction_label(p, current)
        target_time = (now + timedelta(minutes=15 * i)).strftime("%H:%M")
        intervals.append({
            "step": i,
            "time_offset": f"+{15*i}分",
            "target_time": target_time,
            "predicted": round(p, info["decimals"] + 1),
            "bid": bid,
            "ask": ask,
            "direction": direction,
            "color": color,
            "diff_pct": round(diff_pct, 3),
            "confidence": c,
        })

    reasoning = _build_reasoning(ticker, closes, preds[-1] if preds else current, current)

    return {
        "ticker": ticker,
        "label": info["label"],
        "category": info["category"],
        "unit": info["unit"],
        "spread": spread,
        "current_price": round(current, info["decimals"] + 1),
        "current_bid": current_bid,
        "current_ask": current_ask,
        "intervals": intervals,
        "decimals": info["decimals"],
        "reasoning": reasoning,
    }


def get_all_reasonings() -> dict:
    """全銘柄の根拠を取得（カテゴリ別）"""
    out = {"FX": [], "原油・商品CFD": [], "指数CFD": []}
    for ticker in INTERVAL_TARGETS.keys():
        try:
            r = predict_intervals(ticker, steps=4)
            if r is None:
                continue
            iv1 = r["intervals"][0]
            iv4 = r["intervals"][3]
            out[r["category"]].append({
                "ticker": ticker,
                "label": r["label"],
                "current_price": r["current_price"],
                "direction_15min": iv1["direction"],
                "direction_60min": iv4["direction"],
                "diff_60min_pct": iv4["diff_pct"],
                "color_60min": iv4["color"],
                "reasoning": r["reasoning"],
            })
        except Exception:
            continue
    return out


# ════════════════════════════════════════════════
#  全銘柄を一括予測 → ダッシュボード用テーブル
# ════════════════════════════════════════════════

def predict_all_intervals_table() -> dict:
    """
    全銘柄を予測しカテゴリ別の DataFrame を返す
    Returns: {"FX": df, "原油・商品CFD": df, "指数CFD": df}
    """
    results = {"FX": [], "原油・商品CFD": [], "指数CFD": []}

    for ticker in INTERVAL_TARGETS.keys():
        try:
            r = predict_intervals(ticker, steps=4)
            if r is None:
                continue

            row = {
                "銘柄": r["label"],
                "現在 売値(Bid)": r["current_bid"],
                "現在 買値(Ask)": r["current_ask"],
            }
            # 4ステップ分を列展開
            for iv in r["intervals"]:
                t = iv["time_offset"]
                row[f"{t} 売値"] = iv["bid"]
                row[f"{t} 買値"] = iv["ask"]
                row[f"{t} 方向"] = iv["direction"]
                row[f"{t} 信頼度"] = f"{iv['confidence']}%"

            results[r["category"]].append(row)
        except Exception:
            continue

    out = {}
    for cat, rows in results.items():
        if rows:
            out[cat] = pd.DataFrame(rows)
    return out


def predict_all_intervals_compact() -> dict:
    """
    コンパクト版：方向・15分先予想・60分先予想だけのシンプル表
    """
    results = {"FX": [], "原油・商品CFD": [], "指数CFD": []}

    for ticker in INTERVAL_TARGETS.keys():
        try:
            r = predict_intervals(ticker, steps=4)
            if r is None:
                continue

            iv1 = r["intervals"][0]
            iv4 = r["intervals"][3]

            row = {
                "銘柄": r["label"],
                "現在値": r["current_price"],
                "現在 売値": r["current_bid"],
                "現在 買値": r["current_ask"],
                "15分後 予想": iv1["predicted"],
                "15分後 売値": iv1["bid"],
                "15分後 買値": iv1["ask"],
                "15分 方向": iv1["direction"],
                "15分 変化%": f"{iv1['diff_pct']:+.3f}%",
                "60分後 予想": iv4["predicted"],
                "60分後 売値": iv4["bid"],
                "60分後 買値": iv4["ask"],
                "60分 方向": iv4["direction"],
                "60分 変化%": f"{iv4['diff_pct']:+.3f}%",
                "信頼度(15)": f"{iv1['confidence']}%",
            }
            results[r["category"]].append(row)
        except Exception:
            continue

    out = {}
    for cat, rows in results.items():
        if rows:
            out[cat] = pd.DataFrame(rows)
    return out
