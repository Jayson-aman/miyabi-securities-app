"""
ファンダメンタル・スクリーナー
────────────────────────────
大和証券流 売買判断基準:

【買いサイン】
  1) 時価総額100億円以下（小型株で急成長余地あり）
  2) 3期以上連続増収（成長企業）
  3) PER 10〜15倍（割安レンジ）
  4) 株価横ばいかつ業績好調（割安放置銘柄）

【売りサイン】
  1) 配当性向 80%以上（還元しすぎ = 成長投資余力が枯渇）
  2) 3期以上連続減収（業績悪化）
  3) PER 20倍以上（割高）
"""

from __future__ import annotations
import math
from typing import Optional, List, Dict
import yfinance as yf
import pandas as pd
import numpy as np


# ═══════════════════════════════════════════
# 設定値
# ═══════════════════════════════════════════

BUY_MARKET_CAP_MAX_JPY = 10_000_000_000   # 100億円
BUY_PER_MIN = 10.0
BUY_PER_MAX = 15.0
BUY_CONSEC_GROWTH_YEARS = 3

SELL_PAYOUT_RATIO_MAX = 0.80              # 80%
SELL_CONSEC_DECLINE_YEARS = 3
SELL_PER_MIN = 20.0

SIDEWAYS_RANGE_PCT = 0.15                 # 1年で±15%以内
EARNINGS_STRONG_GROWTH = 0.10             # 10%以上増収


# ═══════════════════════════════════════════
# ユーティリティ
# ═══════════════════════════════════════════

def _to_jpy(amount: Optional[float], currency: str, usdjpy: float = 155.0) -> Optional[float]:
    """通貨別市場キャピタルを円換算"""
    if amount is None or not math.isfinite(amount):
        return None
    currency = (currency or "").upper()
    if currency == "JPY":
        return float(amount)
    if currency == "USD":
        return float(amount) * usdjpy
    if currency == "EUR":
        return float(amount) * usdjpy * 1.08
    if currency == "GBP":
        return float(amount) * usdjpy * 1.27
    return float(amount) * usdjpy  # 不明通貨は USD 換算で代用


def _fetch_usdjpy() -> float:
    try:
        t = yf.Ticker("USDJPY=X")
        px = t.history(period="5d")
        if len(px) > 0:
            return float(px["Close"].iloc[-1])
    except Exception:
        pass
    return 155.0


def _revenue_history(ticker: yf.Ticker) -> Optional[pd.Series]:
    """年次売上高を新しい順で取得"""
    for attr in ("financials", "income_stmt"):
        try:
            fin = getattr(ticker, attr, None)
            if fin is None or fin.empty:
                continue
            for row_name in ("Total Revenue", "TotalRevenue", "Revenue",
                             "Operating Revenue", "OperatingRevenue"):
                if row_name in fin.index:
                    series = fin.loc[row_name].dropna()
                    if len(series) >= 2:
                        # 列はおおむね新しい期が先頭（yfinance の仕様）
                        return series.astype(float)
        except Exception:
            continue
    return None


def _consecutive_growth(revenues: pd.Series) -> int:
    """直近から遡って連続増収年数をカウント（revenues は新→旧順）"""
    if revenues is None or len(revenues) < 2:
        return 0
    vals = list(revenues.values)
    count = 0
    for i in range(len(vals) - 1):
        newer = vals[i]
        older = vals[i + 1]
        if newer is not None and older is not None and newer > older > 0:
            count += 1
        else:
            break
    return count


def _consecutive_decline(revenues: pd.Series) -> int:
    """直近から遡って連続減収年数をカウント"""
    if revenues is None or len(revenues) < 2:
        return 0
    vals = list(revenues.values)
    count = 0
    for i in range(len(vals) - 1):
        newer = vals[i]
        older = vals[i + 1]
        if newer is not None and older is not None and 0 < newer < older:
            count += 1
        else:
            break
    return count


def _sideways_check(ticker: yf.Ticker) -> bool:
    """直近12ヶ月の終値レンジが SIDEWAYS_RANGE_PCT 以内"""
    try:
        hist = ticker.history(period="1y")
        if len(hist) < 60:
            return False
        hi = float(hist["Close"].max())
        lo = float(hist["Close"].min())
        rng = (hi - lo) / max(lo, 1e-9)
        return rng <= SIDEWAYS_RANGE_PCT
    except Exception:
        return False


def _recent_revenue_growth_pct(revenues: pd.Series) -> Optional[float]:
    if revenues is None or len(revenues) < 2:
        return None
    newer = float(revenues.iloc[0])
    older = float(revenues.iloc[1])
    if older <= 0:
        return None
    return (newer - older) / older


# ═══════════════════════════════════════════
# メイン解析関数
# ═══════════════════════════════════════════

def analyze_fundamentals(symbol: str, usdjpy: Optional[float] = None) -> Dict:
    """
    指定銘柄のファンダメンタル分析を実施して売買判断を返す
    """
    if usdjpy is None:
        usdjpy = _fetch_usdjpy()

    result: Dict = {
        "symbol": symbol,
        "name": symbol,
        "currency": "USD",
        "market_cap": None,
        "market_cap_jpy": None,
        "per": None,
        "forward_per": None,
        "payout_ratio": None,
        "dividend_yield": None,
        "revenue_growth_pct": None,
        "consec_growth_years": 0,
        "consec_decline_years": 0,
        "is_sideways": False,
        "revenues": [],
        "buy_signals": [],
        "sell_signals": [],
        "score": 0,
        "verdict": "NEUTRAL",
        "action": "中立（様子見）",
        "reason": "",
        "error": None,
    }

    try:
        tk = yf.Ticker(symbol)
        info = tk.info or {}
    except Exception as e:
        result["error"] = f"データ取得失敗: {e}"
        return result

    name = info.get("longName") or info.get("shortName") or symbol
    currency = (info.get("currency") or "USD").upper()
    market_cap = info.get("marketCap")
    per = info.get("trailingPE")
    forward_per = info.get("forwardPE")
    payout = info.get("payoutRatio")
    div_yield = info.get("dividendYield")

    market_cap_jpy = _to_jpy(market_cap, currency, usdjpy)

    result.update({
        "name": name,
        "currency": currency,
        "market_cap": market_cap,
        "market_cap_jpy": market_cap_jpy,
        "per": per,
        "forward_per": forward_per,
        "payout_ratio": payout,
        "dividend_yield": div_yield,
    })

    # 売上履歴
    revenues = _revenue_history(tk)
    if revenues is not None:
        result["revenues"] = [(str(ix.year) if hasattr(ix, "year") else str(ix), float(v))
                              for ix, v in revenues.items()]
        result["consec_growth_years"] = _consecutive_growth(revenues)
        result["consec_decline_years"] = _consecutive_decline(revenues)
        result["revenue_growth_pct"] = _recent_revenue_growth_pct(revenues)

    result["is_sideways"] = _sideways_check(tk)

    # ─── 買いシグナル判定 ───
    buy_sigs = []
    if market_cap_jpy is not None and market_cap_jpy <= BUY_MARKET_CAP_MAX_JPY:
        buy_sigs.append(f"✅ 時価総額 {market_cap_jpy/1e8:.1f}億円（≤100億円＝小型株）")
    if result["consec_growth_years"] >= BUY_CONSEC_GROWTH_YEARS:
        buy_sigs.append(f"✅ {result['consec_growth_years']}期連続増収（成長企業）")
    if per is not None and BUY_PER_MIN <= per <= BUY_PER_MAX:
        buy_sigs.append(f"✅ PER {per:.1f}倍（10〜15倍の割安レンジ）")
    if result["is_sideways"] and result["revenue_growth_pct"] is not None \
       and result["revenue_growth_pct"] >= EARNINGS_STRONG_GROWTH:
        buy_sigs.append(
            f"✅ 株価横ばい（±15%以内）× 増収 {result['revenue_growth_pct']*100:.1f}%（割安放置）"
        )

    # ─── 売りシグナル判定 ───
    sell_sigs = []
    if payout is not None and payout >= SELL_PAYOUT_RATIO_MAX:
        sell_sigs.append(f"❌ 配当性向 {payout*100:.1f}%（≥80% 還元過多）")
    if result["consec_decline_years"] >= SELL_CONSEC_DECLINE_YEARS:
        sell_sigs.append(f"❌ {result['consec_decline_years']}期連続減収（業績悪化）")
    if per is not None and per >= SELL_PER_MIN:
        sell_sigs.append(f"❌ PER {per:.1f}倍（≥20倍 割高）")

    result["buy_signals"] = buy_sigs
    result["sell_signals"] = sell_sigs

    # ─── 総合判定 ───
    score = len(buy_sigs) - len(sell_sigs)
    result["score"] = score

    if len(buy_sigs) >= 3 and len(sell_sigs) == 0:
        result["verdict"] = "STRONG_BUY"
        result["action"] = "🟢🟢 強い買い（買い条件3つ以上）"
    elif len(buy_sigs) >= 2 and len(sell_sigs) == 0:
        result["verdict"] = "BUY"
        result["action"] = "🟢 買い推奨"
    elif len(sell_sigs) >= 2:
        result["verdict"] = "STRONG_SELL"
        result["action"] = "🔴🔴 強い売り（売り条件2つ以上）"
    elif len(sell_sigs) >= 1 and len(buy_sigs) == 0:
        result["verdict"] = "SELL"
        result["action"] = "🔴 売り推奨"
    elif len(buy_sigs) >= 1 and len(sell_sigs) >= 1:
        result["verdict"] = "CONFLICT"
        result["action"] = "⚠️ 買い売り混在（要注意）"
    elif len(buy_sigs) >= 1:
        result["verdict"] = "WATCH_BUY"
        result["action"] = "🟡 買い監視（条件1つのみ）"
    else:
        result["verdict"] = "NEUTRAL"
        result["action"] = "⚪ 中立（基準外）"

    reason_parts: List[str] = []
    if buy_sigs:
        reason_parts.append("【買い材料】" + " / ".join(buy_sigs))
    if sell_sigs:
        reason_parts.append("【売り材料】" + " / ".join(sell_sigs))
    result["reason"] = "\n".join(reason_parts) if reason_parts else "基準該当なし"

    return result


def batch_screen(symbols: List[str], usdjpy: Optional[float] = None) -> pd.DataFrame:
    """
    複数銘柄をまとめてスクリーニング
    """
    if usdjpy is None:
        usdjpy = _fetch_usdjpy()

    rows: List[Dict] = []
    for sym in symbols:
        r = analyze_fundamentals(sym, usdjpy=usdjpy)
        rows.append({
            "銘柄": sym,
            "名称": r.get("name", sym),
            "判定": r.get("action", ""),
            "スコア": r.get("score", 0),
            "時価総額(億円)": round(r["market_cap_jpy"] / 1e8, 1) if r.get("market_cap_jpy") else None,
            "PER": round(r["per"], 2) if r.get("per") else None,
            "配当性向%": round(r["payout_ratio"] * 100, 1) if r.get("payout_ratio") else None,
            "連続増収": r.get("consec_growth_years", 0),
            "連続減収": r.get("consec_decline_years", 0),
            "横ばい": "○" if r.get("is_sideways") else "",
            "買い条件": len(r.get("buy_signals", [])),
            "売り条件": len(r.get("sell_signals", [])),
        })

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df = df.sort_values("スコア", ascending=False).reset_index(drop=True)
    return df
