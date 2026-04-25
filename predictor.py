"""
価格予測モジュール
テクニカル指標 + ニュース感情分析を組み合わせて原油先物の方向性を予測する
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from typing import Optional


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    価格データからML用の特徴量を作成する
    """
    if df.empty or "終値" not in df.columns or len(df) < 30:
        return pd.DataFrame()

    feat = pd.DataFrame(index=df.index)
    close = df["終値"]

    # 価格変化率（複数タイムスパン）
    for n in [1, 3, 5, 10, 15]:
        feat[f"return_{n}"] = close.pct_change(n)

    # 移動平均との乖離率
    for n in [5, 10, 25]:
        ma = close.rolling(n).mean()
        feat[f"ma_gap_{n}"] = (close - ma) / ma

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    feat["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    feat["macd"] = ema12 - ema26
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()

    # ボラティリティ
    feat["volatility_5"] = close.pct_change().rolling(5).std()
    feat["volatility_15"] = close.pct_change().rolling(15).std()

    # 高値-安値レンジ
    if "高値" in df.columns and "安値" in df.columns:
        feat["range_pct"] = (df["高値"] - df["安値"]) / close

    # 出来高の変化率
    if "出来高" in df.columns and df["出来高"].sum() > 0:
        feat["volume_change"] = df["出来高"].pct_change()
        feat["volume_ma_ratio"] = df["出来高"] / df["出来高"].rolling(10).mean()

    # ターゲット: 次の足が上昇(1)か下降(0)か
    feat["target"] = (close.shift(-1) > close).astype(int)

    feat = feat.replace([np.inf, -np.inf], np.nan)

    return feat


def train_and_predict(
    df: pd.DataFrame,
    news_score: float = 0.0,
    lookahead: int = 5,
) -> Optional[dict]:
    """
    過去データでモデルを訓練し、直近の価格方向を予測する

    Args:
        df: 価格データ（テクニカル指標計算済みでなくてよい）
        news_score: ニュース感情スコア (-1.0〜1.0)
        lookahead: 何本先を予測するか

    Returns:
        {
            "direction": "上昇" or "下降",
            "confidence": 信頼度 (0〜100%),
            "technical_score": テクニカルスコア (-1.0〜1.0),
            "news_score": ニューススコア (-1.0〜1.0),
            "combined_score": 統合スコア (-1.0〜1.0),
            "factors": [判断根拠リスト],
        }
    """
    features = prepare_features(df)
    if features.empty or len(features) < 60:
        return _simple_prediction(df, news_score)

    feature_cols = [c for c in features.columns if c != "target"]
    clean = features.replace([np.inf, -np.inf], np.nan).dropna()

    if len(clean) < 40:
        return _simple_prediction(df, news_score)

    X = clean[feature_cols].values
    y = clean["target"].values

    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]
    X_recent = X[-1:]

    scaler = StandardScaler()
    try:
        X_train_scaled = scaler.fit_transform(X_train)
        X_recent_scaled = scaler.transform(X_recent)
    except ValueError:
        return _simple_prediction(df, news_score)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train_scaled, y_train)

    prob = model.predict_proba(X_recent_scaled)[0]
    tech_up_prob = prob[1] if len(prob) > 1 else 0.5

    # テクニカルスコア: 0.5を中心に -1〜1 に変換
    technical_score = (tech_up_prob - 0.5) * 2

    # 統合スコア: テクニカル70% + ニュース30%
    combined_score = (technical_score * 0.7) + (news_score * 0.3)
    combined_score = max(-1.0, min(1.0, combined_score))

    if combined_score > 0:
        direction = "上昇"
        confidence = min(95, 50 + abs(combined_score) * 45)
    else:
        direction = "下降"
        confidence = min(95, 50 + abs(combined_score) * 45)

    factors = _analyze_factors(df, features, news_score, technical_score)

    return {
        "direction": direction,
        "confidence": round(confidence, 1),
        "technical_score": round(technical_score, 3),
        "news_score": round(news_score, 3),
        "combined_score": round(combined_score, 3),
        "factors": factors,
    }


def _simple_prediction(df: pd.DataFrame, news_score: float) -> Optional[dict]:
    """データが少ない場合のシンプルな予測（移動平均ベース）"""
    if df.empty or "終値" not in df.columns or len(df) < 5:
        return None

    close = df["終値"]
    current = close.iloc[-1]
    ma5 = close.tail(5).mean()

    technical_score = 0.0
    factors = []

    if current > ma5:
        technical_score += 0.3
        factors.append("現在値が短期移動平均を上回っている（上昇傾向）")
    else:
        technical_score -= 0.3
        factors.append("現在値が短期移動平均を下回っている（下降傾向）")

    recent_returns = close.pct_change().tail(5).mean()
    if recent_returns > 0:
        technical_score += 0.2
        factors.append("直近5本で上昇基調")
    else:
        technical_score -= 0.2
        factors.append("直近5本で下降基調")

    combined_score = (technical_score * 0.7) + (news_score * 0.3)
    combined_score = max(-1.0, min(1.0, combined_score))

    if news_score > 0.1:
        factors.append(f"ニュース感情: 原油上昇要因が多い (スコア: {news_score:+.2f})")
    elif news_score < -0.1:
        factors.append(f"ニュース感情: 原油下降要因が多い (スコア: {news_score:+.2f})")

    direction = "上昇" if combined_score > 0 else "下降"
    confidence = min(85, 50 + abs(combined_score) * 35)

    return {
        "direction": direction,
        "confidence": round(confidence, 1),
        "technical_score": round(technical_score, 3),
        "news_score": round(news_score, 3),
        "combined_score": round(combined_score, 3),
        "factors": factors,
    }


def _analyze_factors(
    df: pd.DataFrame,
    features: pd.DataFrame,
    news_score: float,
    technical_score: float,
) -> list:
    """予測の根拠を日本語で列挙する"""
    factors = []
    close = df["終値"]
    latest = features.iloc[-1] if not features.empty else None

    if latest is not None:
        rsi = latest.get("rsi", 50)
        if not np.isnan(rsi):
            if rsi > 70:
                factors.append(f"RSI = {rsi:.1f}（買われすぎ → 反落の可能性）")
            elif rsi < 30:
                factors.append(f"RSI = {rsi:.1f}（売られすぎ → 反発の可能性）")
            else:
                factors.append(f"RSI = {rsi:.1f}（中立圏）")

        macd = latest.get("macd", 0)
        macd_sig = latest.get("macd_signal", 0)
        if not (np.isnan(macd) or np.isnan(macd_sig)):
            if macd > macd_sig:
                factors.append("MACD がシグナルを上回っている（買いシグナル）")
            else:
                factors.append("MACD がシグナルを下回っている（売りシグナル）")

    ma5 = close.tail(5).mean()
    ma25 = close.tail(25).mean() if len(close) >= 25 else ma5
    if ma5 > ma25:
        factors.append("短期MA > 中期MA（ゴールデンクロス傾向）")
    elif len(close) >= 25:
        factors.append("短期MA < 中期MA（デッドクロス傾向）")

    if news_score > 0.1:
        factors.append(f"ニュース感情: 原油上昇要因が優勢 (スコア: {news_score:+.3f})")
    elif news_score < -0.1:
        factors.append(f"ニュース感情: 原油下降要因が優勢 (スコア: {news_score:+.3f})")
    else:
        factors.append(f"ニュース感情: 中立 (スコア: {news_score:+.3f})")

    return factors
