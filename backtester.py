"""
バックテストエンジン
複数の取引戦略を過去データに対して検証し、パフォーマンス指標を算出する
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional


# ════════════════════════════════════════════════
#  戦略定義
# ════════════════════════════════════════════════

STRATEGIES = {
    "ma_cross": "移動平均クロス（MA20とMA50のゴールデン/デッドクロス）",
    "rsi_reversal": "RSI逆張り（30以下で買い、70以上で売り）",
    "macd_signal": "MACDシグナルクロス",
    "bollinger_band": "ボリンジャーバンド逆張り（±2σ）",
    "breakout": "ブレイクアウト（直近20日高値/安値ブレイク）",
}


def _generate_signals(df: pd.DataFrame, strategy: str, params: dict) -> pd.Series:
    """戦略に応じた売買シグナル生成（1=買い保有, 0=現金, -1=売り保有）"""
    close = df["Close"]
    signal = pd.Series(0, index=df.index)

    if strategy == "ma_cross":
        short = params.get("short", 20)
        long_ = params.get("long", 50)
        ma_s = close.rolling(short).mean()
        ma_l = close.rolling(long_).mean()
        signal[ma_s > ma_l] = 1
        signal[ma_s < ma_l] = -1 if params.get("allow_short", False) else 0

    elif strategy == "rsi_reversal":
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        position = 0
        positions = []
        for r in rsi:
            if pd.isna(r):
                positions.append(0)
                continue
            if r < oversold:
                position = 1
            elif r > overbought:
                position = 0
            positions.append(position)
        signal = pd.Series(positions, index=df.index)

    elif strategy == "macd_signal":
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        sig = macd.ewm(span=9, adjust=False).mean()
        signal[macd > sig] = 1
        signal[macd < sig] = 0

    elif strategy == "bollinger_band":
        n = params.get("period", 20)
        std_n = params.get("std", 2)
        mid = close.rolling(n).mean()
        std = close.rolling(n).std()
        upper = mid + std * std_n
        lower = mid - std * std_n
        position = 0
        positions = []
        for c, u, l in zip(close, upper, lower):
            if pd.isna(u):
                positions.append(0)
                continue
            if c < l:
                position = 1
            elif c > u:
                position = 0
            positions.append(position)
        signal = pd.Series(positions, index=df.index)

    elif strategy == "breakout":
        n = params.get("period", 20)
        high_n = df["High"].rolling(n).max().shift(1)
        low_n = df["Low"].rolling(n).min().shift(1)
        position = 0
        positions = []
        for c, h, l in zip(close, high_n, low_n):
            if pd.isna(h):
                positions.append(0)
                continue
            if c > h:
                position = 1
            elif c < l:
                position = 0
            positions.append(position)
        signal = pd.Series(positions, index=df.index)

    return signal


def run_backtest(
    ticker: str,
    strategy: str,
    period: str = "1y",
    interval: str = "1d",
    initial_capital: float = 1_000_000,
    commission: float = 0.001,
    params: Optional[dict] = None,
) -> Optional[dict]:
    """
    バックテストを実行

    Returns:
        {
            "ticker": ティッカー,
            "strategy": 戦略名,
            "initial_capital": 初期資金,
            "final_value": 最終資産,
            "total_return": 総リターン (%),
            "buy_hold_return": バイ&ホールドのリターン (%),
            "alpha": 戦略 - バイ&ホールド,
            "trades": 取引回数,
            "win_rate": 勝率 (%),
            "max_drawdown": 最大ドローダウン (%),
            "sharpe": シャープレシオ,
            "equity_curve": [資産推移リスト],
            "dates": [日付リスト],
            "signals": [シグナル変化リスト],
            "trade_log": [取引ログ],
        }
    """
    if params is None:
        params = {}

    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df is None or df.empty or len(df) < 50:
            return None
    except Exception:
        return None

    df = df.dropna(subset=["Close"])
    signals = _generate_signals(df, strategy, params)

    cash = initial_capital
    shares = 0
    equity = []
    trade_log = []
    position = 0
    entry_price = 0

    for i, (date, row) in enumerate(df.iterrows()):
        price = row["Close"]
        sig = signals.iloc[i] if i < len(signals) else 0

        if sig == 1 and position == 0:
            shares = (cash * (1 - commission)) / price
            cash = 0
            position = 1
            entry_price = price
            trade_log.append({
                "date": str(date)[:10],
                "action": "BUY",
                "price": round(price, 4),
                "shares": round(shares, 4),
            })
        elif sig != 1 and position == 1:
            cash = shares * price * (1 - commission)
            pnl = (price / entry_price - 1) * 100
            trade_log.append({
                "date": str(date)[:10],
                "action": "SELL",
                "price": round(price, 4),
                "shares": round(shares, 4),
                "pnl_pct": round(pnl, 2),
            })
            shares = 0
            position = 0

        equity.append(cash + shares * price)

    final_value = equity[-1] if equity else initial_capital
    total_return = (final_value / initial_capital - 1) * 100

    buy_hold_return = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100

    eq_series = pd.Series(equity)
    returns = eq_series.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        # 年率換算（日足前提だが粗い目安）
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe = 0

    rolling_max = eq_series.cummax()
    drawdown = (eq_series - rolling_max) / rolling_max
    max_dd = drawdown.min() * 100 if len(drawdown) > 0 else 0

    sells = [t for t in trade_log if t["action"] == "SELL"]
    wins = [t for t in sells if t.get("pnl_pct", 0) > 0]
    win_rate = (len(wins) / len(sells) * 100) if sells else 0

    return {
        "ticker": ticker,
        "strategy": strategy,
        "strategy_label": STRATEGIES.get(strategy, strategy),
        "initial_capital": initial_capital,
        "final_value": round(final_value, 0),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(buy_hold_return, 2),
        "alpha": round(total_return - buy_hold_return, 2),
        "trades": len(sells),
        "win_rate": round(win_rate, 1),
        "max_drawdown": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "equity_curve": equity,
        "dates": [str(d)[:10] for d in df.index],
        "trade_log": trade_log,
        "price_curve": df["Close"].tolist(),
    }


def compare_strategies(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    initial_capital: float = 1_000_000,
) -> list:
    """全戦略を比較"""
    results = []
    for strat in STRATEGIES:
        r = run_backtest(ticker, strat, period, interval, initial_capital)
        if r:
            results.append(r)
    results.sort(key=lambda x: x["total_return"], reverse=True)
    return results
