"""
FX レバレッジ取引シミュレーター
日本の個人投資家向け：レバレッジ25倍上限、スワップ金利込み

機能：
1. 必要証拠金計算（レバレッジ25倍）
2. ロスカット価格計算
3. 損益シミュレーション（含み損益・確定損益）
4. スワップ金利の累積計算
5. 過去データを使ったバックテスト型シミュレーション
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# ════════════════════════════════════════════════
#  日本の FX 制度
# ════════════════════════════════════════════════

JAPAN_LEVERAGE = 25  # 日本の個人FX上限
LOT_SIZE = 10000     # 標準ロット = 1万通貨


# ════════════════════════════════════════════════
#  主要通貨ペア スワップポイント（参考値・1万通貨/1日 単位：円）
#  ※ 各FX会社により実際の値は異なる。日々変動。
#  ※ 高金利通貨買い → プラス、売り → マイナス
# ════════════════════════════════════════════════

SWAP_POINTS = {
    "USDJPY=X": {
        "label": "USD/JPY (米ドル/円)",
        "buy": 220, "sell": -250,
        "note": "米金利高 → 買いスワップ大",
    },
    "EURJPY=X": {
        "label": "EUR/JPY (ユーロ/円)",
        "buy": 165, "sell": -190,
        "note": "ECB金利上昇でスワップ拡大",
    },
    "GBPJPY=X": {
        "label": "GBP/JPY (英ポンド/円)",
        "buy": 230, "sell": -270,
        "note": "BOE金利高でスワップ大。値動きも大",
    },
    "AUDJPY=X": {
        "label": "AUD/JPY (豪ドル/円)",
        "buy": 110, "sell": -135,
        "note": "豪RBA金利。資源国通貨として人気",
    },
    "NZDJPY=X": {
        "label": "NZD/JPY (NZドル/円)",
        "buy": 105, "sell": -130,
        "note": "RBNZ金利。AUDと連動傾向",
    },
    "CADJPY=X": {
        "label": "CAD/JPY (加ドル/円)",
        "buy": 145, "sell": -175,
        "note": "原油価格と相関",
    },
    "CHFJPY=X": {
        "label": "CHF/JPY (スイス/円)",
        "buy": 25, "sell": -45,
        "note": "SNB金利低め。安全通貨",
    },
    "TRYJPY=X": {
        "label": "TRY/JPY (トルコリラ/円)",
        "buy": 30, "sell": -45,
        "note": "高金利だが通貨価値下落リスク",
    },
    "ZARJPY=X": {
        "label": "ZAR/JPY (南アランド/円)",
        "buy": 18, "sell": -25,
        "note": "高金利・コモディティ通貨",
    },
    "MXNJPY=X": {
        "label": "MXN/JPY (メキシコペソ/円)",
        "buy": 25, "sell": -35,
        "note": "高金利・メキシコ中銀",
    },
    "EURUSD=X": {
        "label": "EUR/USD",
        "buy": -180, "sell": 150,
        "note": "ドル高金利のためショートスワップが有利",
    },
    "GBPUSD=X": {
        "label": "GBP/USD",
        "buy": -50, "sell": 30,
        "note": "BOEとFRBの金利差が小さい",
    },
}


# ════════════════════════════════════════════════
#  必要証拠金・ロスカット計算
# ════════════════════════════════════════════════

def calc_margin_required(price: float, lots: float, leverage: int = JAPAN_LEVERAGE) -> float:
    """
    必要証拠金 = (取引金額) ÷ レバレッジ
    取引金額 = 価格 × ロット数 × LOT_SIZE
    """
    notional = price * lots * LOT_SIZE
    return notional / leverage


def calc_loss_cut_price(
    entry_price: float,
    lots: float,
    capital: float,
    side: str = "buy",
    loss_cut_ratio: float = 1.0,
    leverage: int = JAPAN_LEVERAGE,
) -> float:
    """
    ロスカット価格を計算

    一般的な国内FX口座のロスカットルール：
    証拠金維持率 100% を割ると強制ロスカット

    loss_cut_ratio: ロスカット発動の維持率（1.0 = 100%, 0.5 = 50% 等、業者により異なる）
    """
    margin_required = calc_margin_required(entry_price, lots, leverage)
    # 維持証拠金 = 必要証拠金 × loss_cut_ratio
    maintenance = margin_required * loss_cut_ratio
    # 許容損失額 = 預入資金 - 維持証拠金
    max_loss = capital - maintenance
    # 許容変動値 (1通貨あたり)
    max_move_per_unit = max_loss / (lots * LOT_SIZE)

    if side == "buy":
        return round(entry_price - max_move_per_unit, 4)
    else:
        return round(entry_price + max_move_per_unit, 4)


def calc_pnl(
    entry_price: float,
    current_price: float,
    lots: float,
    side: str = "buy",
) -> float:
    """損益（円）= (価格差) × ロット数 × LOT_SIZE"""
    if side == "buy":
        diff = current_price - entry_price
    else:
        diff = entry_price - current_price
    return diff * lots * LOT_SIZE


def calc_swap_total(ticker: str, lots: float, side: str, days: int) -> dict:
    """
    保有日数分のスワップ合計を計算

    Returns: {"daily": 日次, "total": 累計, "annual_yield_pct": 年利換算%}
    """
    if ticker not in SWAP_POINTS:
        return {"daily": 0, "total": 0, "annual_yield_pct": 0, "available": False}

    info = SWAP_POINTS[ticker]
    daily = info["buy"] if side == "buy" else info["sell"]
    daily_total = daily * lots
    total = daily_total * days

    return {
        "daily": daily_total,
        "total": total,
        "available": True,
        "note": info["note"],
        "label": info["label"],
    }


# ════════════════════════════════════════════════
#  単発トレードシミュレーション
# ════════════════════════════════════════════════

def simulate_trade(
    ticker: str,
    side: str = "buy",            # "buy" or "sell"
    entry_price: float = None,    # None なら現在値
    lots: float = 1.0,
    capital: float = 100000,
    leverage: int = JAPAN_LEVERAGE,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    holding_days: int = 30,
) -> dict:
    """
    1回のFXトレードを完全シミュレーション

    Returns: 詳細な結果辞書
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist is None or hist.empty:
            return {"error": "価格データ取得失敗"}
        current = float(hist["Close"].iloc[-1])
    except Exception:
        return {"error": "価格データ取得失敗"}

    if entry_price is None:
        entry_price = current

    margin_req = calc_margin_required(entry_price, lots, leverage)

    if margin_req > capital:
        return {
            "error": f"資金不足：必要証拠金 {margin_req:,.0f}円 > 預入資金 {capital:,.0f}円",
            "margin_required": margin_req,
        }

    notional = entry_price * lots * LOT_SIZE
    loss_cut = calc_loss_cut_price(entry_price, lots, capital, side, 1.0, leverage)

    # 現在の含み損益
    current_pnl = calc_pnl(entry_price, current, lots, side)

    # 利確・損切りシナリオ
    target_pnl = calc_pnl(entry_price, target_price, lots, side) if target_price else None
    stop_pnl = calc_pnl(entry_price, stop_loss, lots, side) if stop_loss else None

    # スワップ
    swap = calc_swap_total(ticker, lots, side, holding_days)

    # トータル収益（利確時）
    total_with_swap_target = (target_pnl or 0) + swap["total"]
    total_with_swap_stop = (stop_pnl or 0) + swap["total"]

    # リスクリワード
    if target_pnl is not None and stop_pnl is not None and stop_pnl != 0:
        rr = abs(target_pnl / stop_pnl)
    else:
        rr = None

    # 1pip相当
    pip_value = 0.01 if "JPY" in ticker else 0.0001
    pip_jpy = pip_value * lots * LOT_SIZE  # 1pip動いた時の損益（円）

    return {
        "ticker": ticker,
        "label": SWAP_POINTS.get(ticker, {}).get("label", ticker),
        "side": side,
        "entry_price": entry_price,
        "current_price": current,
        "lots": lots,
        "trade_units": int(lots * LOT_SIZE),
        "leverage": leverage,
        "notional": notional,
        "margin_required": margin_req,
        "margin_ratio_pct": (capital / margin_req) * 100 if margin_req > 0 else 0,
        "capital": capital,
        "loss_cut_price": loss_cut,
        "current_pnl": current_pnl,
        "target_price": target_price,
        "target_pnl": target_pnl,
        "stop_loss": stop_loss,
        "stop_pnl": stop_pnl,
        "risk_reward": rr,
        "swap": swap,
        "holding_days": holding_days,
        "total_pnl_at_target": total_with_swap_target,
        "total_pnl_at_stop": total_with_swap_stop,
        "pip_value_jpy": pip_jpy,
        "expected_max_loss": stop_pnl if stop_pnl else -capital,
    }


# ════════════════════════════════════════════════
#  過去データを使った長期シミュレーション
# ════════════════════════════════════════════════

def backtest_simulation(
    ticker: str,
    side: str = "buy",
    lots: float = 1.0,
    capital: float = 100000,
    period: str = "1y",
    leverage: int = JAPAN_LEVERAGE,
) -> Optional[dict]:
    """
    指定期間、ずっと保有したらどうなったかをシミュレーション
    （日次の含み損益＋スワップ累積）
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d")
        if df is None or df.empty or len(df) < 5:
            return None
    except Exception:
        return None

    df = df.dropna(subset=["Close"]).reset_index()
    entry_price = float(df["Close"].iloc[0])
    margin_req = calc_margin_required(entry_price, lots, leverage)

    if margin_req > capital:
        return {
            "error": f"資金不足：必要証拠金 {margin_req:,.0f}円 > 預入資金 {capital:,.0f}円",
            "margin_required": margin_req,
        }

    swap_info = SWAP_POINTS.get(ticker, {})
    daily_swap = (swap_info.get("buy", 0) if side == "buy" else swap_info.get("sell", 0)) * lots

    dates = []
    pnls = []
    swaps_cumulative = []
    totals = []
    equity_curve = []
    loss_cut_triggered = False
    loss_cut_date = None
    final_close = entry_price

    for i, row in df.iterrows():
        price = float(row["Close"])
        d = row.get("Date") or row.get("Datetime") or row.get(0)
        d_str = str(d)[:10]

        pnl = calc_pnl(entry_price, price, lots, side)
        cum_swap = daily_swap * (i + 1)
        total = pnl + cum_swap
        equity = capital + total

        # ロスカット判定（証拠金維持率100%）
        if equity < margin_req and not loss_cut_triggered:
            loss_cut_triggered = True
            loss_cut_date = d_str
            final_close = price

        dates.append(d_str)
        pnls.append(pnl)
        swaps_cumulative.append(cum_swap)
        totals.append(total)
        equity_curve.append(equity)

    final_pnl = pnls[-1]
    final_swap = swaps_cumulative[-1]
    final_total = totals[-1]
    final_equity = equity_curve[-1]
    return_pct = (final_total / capital) * 100

    max_pnl = max(totals)
    min_pnl = min(totals)
    max_dd_pct = ((min(equity_curve) - capital) / capital) * 100

    return {
        "ticker": ticker,
        "label": SWAP_POINTS.get(ticker, {}).get("label", ticker),
        "side": side,
        "lots": lots,
        "leverage": leverage,
        "capital": capital,
        "entry_price": round(entry_price, 4),
        "final_price": round(float(df["Close"].iloc[-1]), 4),
        "margin_required": round(margin_req, 0),
        "daily_swap": round(daily_swap, 0),
        "holding_days": len(df),
        "final_price_pnl": round(final_pnl, 0),
        "final_swap_total": round(final_swap, 0),
        "final_total": round(final_total, 0),
        "final_equity": round(final_equity, 0),
        "return_pct": round(return_pct, 2),
        "max_profit": round(max_pnl, 0),
        "max_loss": round(min_pnl, 0),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "loss_cut_triggered": loss_cut_triggered,
        "loss_cut_date": loss_cut_date,
        "dates": dates,
        "pnl_curve": pnls,
        "swap_curve": swaps_cumulative,
        "total_curve": totals,
        "equity_curve": equity_curve,
    }


# ════════════════════════════════════════════════
#  通貨ペア別 スワップ年利ランキング
# ════════════════════════════════════════════════

def get_swap_yield_table(capital_per_pair: float = 100000) -> list:
    """
    全通貨ペアのスワップ収益を計算した一覧表

    capital_per_pair: 各ペアに投資する資金（円）
    各ペアで「資金を最大限使う最大ロット」を計算してスワップ年利を出す
    """
    out = []
    for ticker, info in SWAP_POINTS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if hist is None or hist.empty:
                continue
            price = float(hist["Close"].iloc[-1])
        except Exception:
            continue

        # 最大ロット = 資金×レバレッジ ÷ (価格×LOT_SIZE)
        max_lots = (capital_per_pair * JAPAN_LEVERAGE) / (price * LOT_SIZE)
        # 安全のため0.7倍にする（ロスカット余裕）
        safe_lots = round(max_lots * 0.7, 1)

        buy_daily = info["buy"] * safe_lots
        sell_daily = info["sell"] * safe_lots
        buy_annual = buy_daily * 365
        sell_annual = sell_daily * 365

        better_side = "buy" if buy_annual > abs(sell_annual) else "sell"
        better_annual = buy_annual if better_side == "buy" else sell_annual
        annual_yield_pct = (better_annual / capital_per_pair) * 100

        out.append({
            "ticker": ticker,
            "label": info["label"],
            "current_price": round(price, 4),
            "safe_lots": safe_lots,
            "buy_swap_daily": round(buy_daily, 0),
            "sell_swap_daily": round(sell_daily, 0),
            "buy_swap_annual": round(buy_annual, 0),
            "sell_swap_annual": round(sell_annual, 0),
            "better_side": better_side,
            "best_annual_yield_pct": round(annual_yield_pct, 2),
            "note": info["note"],
        })

    out.sort(key=lambda x: x["best_annual_yield_pct"], reverse=True)
    return out
