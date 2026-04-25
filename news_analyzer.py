"""
ニュース取得・感情分析モジュール（Step 2）
RSSフィードから金融ニュースを取得し、感情スコアを算出する
APIキー不要
"""

import feedparser
from textblob import TextBlob
from datetime import datetime
from typing import List
import re
import html


# 金融・為替関連のRSSフィード
NEWS_FEEDS = {
    "Reuters (Markets)": "https://www.rss.app/feeds/ts3VoAcJqIsMKPwL.xml",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "FX Street": "https://www.fxstreet.com/rss",
    "Google News (Forex)": "https://news.google.com/rss/search?q=forex+OR+%E7%82%BA%E6%9B%BF+OR+FX&hl=en",
    "Google News (Economy)": "https://news.google.com/rss/search?q=economy+OR+interest+rate+OR+central+bank&hl=en",
}

# 通貨ペアに関連するキーワード
CURRENCY_KEYWORDS = {
    "USD/JPY": ["usdjpy", "dollar yen", "usd jpy", "ドル円", "ドル/円", "米ドル"],
    "EUR/JPY": ["eurjpy", "euro yen", "eur jpy", "ユーロ円", "ユーロ/円"],
    "GBP/JPY": ["gbpjpy", "pound yen", "gbp jpy", "ポンド円", "ポンド/円"],
    "AUD/JPY": ["audjpy", "aussie yen", "aud jpy", "豪ドル円"],
    "EUR/USD": ["eurusd", "euro dollar", "eur usd", "ユーロドル"],
    "GBP/USD": ["gbpusd", "pound dollar", "gbp usd", "ポンドドル"],
}

# 市場に影響を与える重要キーワード
MARKET_KEYWORDS = {
    "利上げ・タカ派": ["rate hike", "hawkish", "tightening", "利上げ", "タカ派", "引き締め"],
    "利下げ・ハト派": ["rate cut", "dovish", "easing", "利下げ", "ハト派", "緩和"],
    "インフレ": ["inflation", "cpi", "consumer price", "インフレ", "物価上昇"],
    "雇用": ["employment", "jobs", "nonfarm", "unemployment", "雇用", "失業"],
    "GDP": ["gdp", "gross domestic", "economic growth", "経済成長"],
    "地政学リスク": ["war", "conflict", "sanctions", "tariff", "戦争", "制裁", "関税"],
    "中央銀行": ["fed", "ecb", "boj", "bank of japan", "federal reserve", "日銀", "中央銀行"],
}


def clean_html(raw_html: str) -> str:
    """HTMLタグを除去してプレーンテキストにする"""
    clean = re.sub(r"<.*?>", "", raw_html)
    return html.unescape(clean).strip()


def analyze_sentiment(text: str) -> dict:
    """
    テキストの感情分析を行う

    Returns:
        {
            "score": -1.0〜1.0 の感情スコア,
            "label": "ポジティブ" / "ネガティブ" / "ニュートラル",
            "subjectivity": 0〜1 の主観性スコア
        }
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    if polarity > 0.1:
        label = "ポジティブ"
    elif polarity < -0.1:
        label = "ネガティブ"
    else:
        label = "ニュートラル"

    return {
        "score": round(polarity, 3),
        "label": label,
        "subjectivity": round(subjectivity, 3),
    }


def detect_market_topics(text: str) -> List[str]:
    """記事から市場関連トピックを検出する"""
    text_lower = text.lower()
    detected = []
    for topic, keywords in MARKET_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(topic)
    return detected


def detect_currency_relevance(text: str) -> List[str]:
    """記事に関連する通貨ペアを検出する"""
    text_lower = text.lower()
    relevant = []
    for pair, keywords in CURRENCY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            relevant.append(pair)
    return relevant


def fetch_news(feed_names: List[str] = None, max_articles: int = 30) -> List[dict]:
    """
    RSSフィードからニュースを取得し、感情分析を付与する

    Args:
        feed_names: 取得するフィード名のリスト（Noneなら全て）
        max_articles: 最大記事数

    Returns:
        記事情報のリスト（日時降順）
    """
    if feed_names is None:
        feed_names = list(NEWS_FEEDS.keys())

    articles = []

    for name in feed_names:
        url = NEWS_FEEDS.get(name)
        if not url:
            continue

        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                summary = clean_html(entry.get("summary", entry.get("description", "")))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                pub_date = None
                if published:
                    try:
                        from email.utils import parsedate_to_datetime
                        pub_date = parsedate_to_datetime(published)
                        pub_date = pub_date.replace(tzinfo=None)
                    except Exception:
                        pub_date = None

                full_text = f"{title} {summary}"
                sentiment = analyze_sentiment(full_text)
                topics = detect_market_topics(full_text)
                currencies = detect_currency_relevance(full_text)

                articles.append({
                    "source": name,
                    "title": title,
                    "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                    "link": link,
                    "published": pub_date,
                    "sentiment_score": sentiment["score"],
                    "sentiment_label": sentiment["label"],
                    "subjectivity": sentiment["subjectivity"],
                    "topics": topics,
                    "currencies": currencies,
                })
        except Exception:
            continue

    articles.sort(key=lambda x: x["published"] or datetime.min, reverse=True)
    return articles[:max_articles]


def compute_market_sentiment(articles: List[dict]) -> dict:
    """
    取得した記事群から市場全体の感情サマリーを算出する

    Returns:
        {
            "overall_score": 全体スコア,
            "overall_label": ラベル,
            "positive_count": ポジティブ記事数,
            "negative_count": ネガティブ記事数,
            "neutral_count": ニュートラル記事数,
            "topic_sentiment": トピック別スコア,
            "currency_sentiment": 通貨ペア別スコア
        }
    """
    if not articles:
        return {
            "overall_score": 0,
            "overall_label": "データなし",
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "topic_sentiment": {},
            "currency_sentiment": {},
        }

    scores = [a["sentiment_score"] for a in articles]
    overall = sum(scores) / len(scores)

    if overall > 0.1:
        label = "ポジティブ（楽観的）"
    elif overall < -0.1:
        label = "ネガティブ（悲観的）"
    else:
        label = "ニュートラル（様子見）"

    pos = sum(1 for s in scores if s > 0.1)
    neg = sum(1 for s in scores if s < -0.1)
    neu = len(scores) - pos - neg

    topic_scores = {}
    for article in articles:
        for topic in article["topics"]:
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(article["sentiment_score"])
    topic_sentiment = {
        t: round(sum(s) / len(s), 3) for t, s in topic_scores.items()
    }

    currency_scores = {}
    for article in articles:
        for cur in article["currencies"]:
            if cur not in currency_scores:
                currency_scores[cur] = []
            currency_scores[cur].append(article["sentiment_score"])
    currency_sentiment = {
        c: round(sum(s) / len(s), 3) for c, s in currency_scores.items()
    }

    return {
        "overall_score": round(overall, 3),
        "overall_label": label,
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "topic_sentiment": topic_sentiment,
        "currency_sentiment": currency_sentiment,
    }
