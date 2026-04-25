"""
ニュース取得・感情分析モジュール
Google News RSS を使って原油・エネルギー関連ニュースを取得し、
テキスト感情分析で市場への影響度を算出する
"""

import feedparser
from textblob import TextBlob
from datetime import datetime
from typing import List
import re


# 原油・エネルギー市場に影響するキーワード（検索用）
SEARCH_QUERIES = {
    "原油全般": "crude oil price",
    "OPEC動向": "OPEC production",
    "中東情勢": "middle east oil conflict",
    "米国経済": "US economy oil demand",
    "中国経済": "China economy oil demand",
    "地政学リスク": "geopolitical risk energy",
    "原油在庫": "crude oil inventory stockpile",
    "制裁・規制": "oil sanctions embargo",
}

# 価格上昇を示唆するキーワード（重み付け用）
BULLISH_KEYWORDS = [
    "surge", "rally", "rise", "jump", "soar", "high", "demand",
    "shortage", "cut", "reduce production", "sanctions", "conflict",
    "war", "tension", "supply disruption", "hurricane", "outage",
    "bullish", "upbeat", "growth", "recovery",
]

# 価格下降を示唆するキーワード（重み付け用）
BEARISH_KEYWORDS = [
    "fall", "drop", "decline", "plunge", "crash", "low", "surplus",
    "oversupply", "increase production", "weak demand", "recession",
    "slowdown", "bearish", "slump", "glut", "ceasefire", "peace",
    "deal", "agreement", "ease", "stable",
]


def fetch_news(query: str = "crude oil price", max_results: int = 15) -> List[dict]:
    """
    Google News RSS から関連ニュースを取得する（APIキー不要）
    """
    encoded_query = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en&gl=US&ceid=US:en"

    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:max_results]:
        published = ""
        if hasattr(entry, "published"):
            try:
                dt = datetime(*entry.published_parsed[:6])
                published = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                published = entry.published

        articles.append({
            "title": _clean_html(entry.title),
            "link": entry.link,
            "published": published,
            "source": entry.get("source", {}).get("title", "不明"),
        })

    return articles


def analyze_sentiment(text: str) -> dict:
    """
    テキストの感情分析を行う

    Returns:
        {
            "polarity": -1.0〜1.0 (負=ネガティブ, 正=ポジティブ),
            "subjectivity": 0.0〜1.0 (0=客観的, 1=主観的),
            "oil_impact": -1.0〜1.0 (負=原油下落要因, 正=原油上昇要因),
            "label": "上昇要因" / "下降要因" / "中立"
        }
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    oil_impact = _calculate_oil_impact(text, polarity)

    if oil_impact > 0.15:
        label = "上昇要因"
    elif oil_impact < -0.15:
        label = "下降要因"
    else:
        label = "中立"

    return {
        "polarity": round(polarity, 3),
        "subjectivity": round(subjectivity, 3),
        "oil_impact": round(oil_impact, 3),
        "label": label,
    }


def fetch_and_analyze_all() -> dict:
    """
    全カテゴリのニュースを取得し、感情分析した統合結果を返す

    Returns:
        {
            "articles": [記事リスト（感情分析付き）],
            "overall_score": 総合スコア (-1.0〜1.0),
            "overall_label": "上昇圧力" / "下降圧力" / "中立",
            "category_scores": {カテゴリ: スコア},
            "bullish_count": 上昇要因の記事数,
            "bearish_count": 下降要因の記事数,
            "neutral_count": 中立の記事数,
        }
    """
    all_articles = []
    category_scores = {}

    for category, query in SEARCH_QUERIES.items():
        articles = fetch_news(query, max_results=8)
        scores = []

        for article in articles:
            sentiment = analyze_sentiment(article["title"])
            article["sentiment"] = sentiment
            article["category"] = category
            scores.append(sentiment["oil_impact"])

        all_articles.extend(articles)
        if scores:
            category_scores[category] = round(sum(scores) / len(scores), 3)

    bullish = sum(1 for a in all_articles if a["sentiment"]["label"] == "上昇要因")
    bearish = sum(1 for a in all_articles if a["sentiment"]["label"] == "下降要因")
    neutral = sum(1 for a in all_articles if a["sentiment"]["label"] == "中立")

    if all_articles:
        impacts = [a["sentiment"]["oil_impact"] for a in all_articles]
        overall_score = round(sum(impacts) / len(impacts), 3)
    else:
        overall_score = 0.0

    if overall_score > 0.1:
        overall_label = "上昇圧力"
    elif overall_score < -0.1:
        overall_label = "下降圧力"
    else:
        overall_label = "中立"

    all_articles.sort(key=lambda x: abs(x["sentiment"]["oil_impact"]), reverse=True)

    return {
        "articles": all_articles,
        "overall_score": overall_score,
        "overall_label": overall_label,
        "category_scores": category_scores,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
    }


def _calculate_oil_impact(text: str, base_polarity: float) -> float:
    """原油市場への影響スコアを計算する"""
    text_lower = text.lower()
    bullish_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bearish_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

    keyword_score = (bullish_hits - bearish_hits) * 0.15
    combined = (base_polarity * 0.4) + (keyword_score * 0.6)

    return max(-1.0, min(1.0, combined))


def _clean_html(text: str) -> str:
    """HTMLタグを除去する"""
    return re.sub(r"<[^>]+>", "", text)
