"""
経済指標・要人発言 分析モジュール
最新の経済指標や要人発言を取得し、円安/円高どちらの要因か即時判定する。
要人の「フェイント」（本音と逆の発言、曖昧なヘッジ、観測気球）を検知して警告する。
"""

import feedparser
import re
from textblob import TextBlob
from datetime import datetime
from typing import List, Optional
from person_profiles import analyze_person_context, get_all_tracked_names


# ════════════════════════════════════════════════
#  経済指標の円安/円高判定ルール
# ════════════════════════════════════════════════

US_INDICATORS_BULLISH_USD = {
    "nonfarm payroll": "雇用統計（非農業部門）",
    "non-farm": "雇用統計（非農業部門）",
    "jobs report": "雇用統計",
    "unemployment rate": "失業率",
    "cpi": "消費者物価指数（CPI）",
    "inflation": "インフレ率",
    "gdp": "GDP成長率",
    "retail sales": "小売売上高",
    "ism manufacturing": "ISM製造業景況指数",
    "ism services": "ISMサービス業景況指数",
    "pmi": "購買担当者景気指数（PMI）",
    "consumer confidence": "消費者信頼感指数",
    "durable goods": "耐久財受注",
    "housing starts": "住宅着工件数",
    "trade balance": "貿易収支",
    "industrial production": "鉱工業生産",
}

KEY_PERSONS = {
    "powell": ("パウエル（FRB議長）", "USD"),
    "fed chair": ("FRB議長", "USD"),
    "federal reserve": ("FRB（連邦準備制度）", "USD"),
    "yellen": ("イエレン（米財務長官）", "USD"),
    "trump": ("トランプ大統領", "USD"),
    "biden": ("バイデン", "USD"),
    "ueda": ("植田（日銀総裁）", "JPY"),
    "boj governor": ("日銀総裁", "JPY"),
    "bank of japan": ("日本銀行", "JPY"),
    "kuroda": ("黒田（前日銀総裁）", "JPY"),
    "lagarde": ("ラガルド（ECB総裁）", "EUR"),
    "ecb": ("ECB（欧州中央銀行）", "EUR"),
    "bailey": ("ベイリー（BOE総裁）", "GBP"),
    "bank of england": ("イングランド銀行", "GBP"),
}

HAWKISH_KEYWORDS = [
    "rate hike", "raise rate", "tighten", "hawkish", "higher rate",
    "inflation concern", "strong economy", "robust", "beat expectation",
    "above forecast", "higher than expected", "surge", "accelerat",
    "tapering", "quantitative tightening", "qt",
]

DOVISH_KEYWORDS = [
    "rate cut", "lower rate", "easing", "dovish", "pause",
    "weak", "recession", "slowdown", "miss expectation",
    "below forecast", "lower than expected", "decline", "contraction",
    "stimulus", "quantitative easing", "qe", "accommodate",
]

RISK_OFF_KEYWORDS = [
    "war", "conflict", "sanction", "missile", "attack", "invasion",
    "default", "crisis", "crash", "panic", "bank failure", "collapse",
    "tariff", "trade war", "nuclear",
]

RISK_ON_KEYWORDS = [
    "ceasefire", "peace", "deal", "agreement", "recovery", "rally",
    "record high", "all-time high", "trade deal", "cooperation",
]


# ════════════════════════════════════════════════
#  フェイント検知エンジン
# ════════════════════════════════════════════════

# パターン1: ヘッジ・留保表現（言い切らずに逃げ道を作る）
HEDGE_PHRASES = [
    "data dependent", "data-dependent",
    "if conditions warrant", "if appropriate",
    "at this time", "for now", "at the moment",
    "remain patient", "wait and see",
    "not predetermined", "no preset course",
    "meeting by meeting", "on a case-by-case",
    "optionality", "flexibility", "all options on the table",
    "closely monitor", "carefully assess",
    "balanced approach", "both sides of the mandate",
    "appropriately calibrate",
]

# パターン2: 観測気球・リーク表現（正式発言ではなく市場の反応を探る）
TRIAL_BALLOON_PHRASES = [
    "sources say", "sources familiar",
    "officials discussed", "officials debated",
    "considering", "may consider", "could consider",
    "explore the possibility", "weigh the option",
    "preliminary", "tentative",
    "leaked", "unofficial", "off the record",
    "floating the idea", "testing the water",
    "some officials", "a few members",
    "behind closed doors", "internal discussion",
]

# パターン3: 前言撤回・トーン反転（以前の発言を覆す）
REVERSAL_PHRASES = [
    "walk back", "walked back", "backtrack",
    "reverse", "reversed course", "u-turn", "U-turn",
    "shift", "shifted stance", "pivot", "pivoted",
    "reconsider", "reconsidering",
    "revise", "revised", "reassess",
    "clarify", "clarified", "correct", "corrected",
    "contrary to earlier", "despite previous",
    "change tone", "changed tone", "soften", "softened",
    "no longer", "abandon", "dropped",
]

# パターン4: 矛盾・両面表現（タカ派とハト派を同時に匂わせる）
CONTRADICTION_PATTERNS = [
    ("strong", "but"), ("robust", "however"), ("growth", "but risk"),
    ("rate hike", "pause"), ("tighten", "flexible"),
    ("inflation", "transitory"), ("inflation", "temporary"),
    ("hawkish", "dovish"), ("optimistic", "cautious"),
    ("raise", "cut"), ("strong", "uncertain"),
    ("confident", "risk"), ("progress", "challenge"),
]

# パターン5: 意図的に市場を動かす強い断定（過剰な確信表現 → 裏を読め）
OVERCONFIDENCE_PHRASES = [
    "absolutely", "no doubt", "certain", "definitely",
    "guarantee", "promise", "committed to",
    "whatever it takes", "by all means",
    "ruled out", "off the table", "impossible",
    "never", "always", "without question",
]

# パターン6: 時間稼ぎ・先延ばし表現（決定を遅らせて市場を不安定にする）
STALLING_PHRASES = [
    "more time", "need more data", "premature",
    "too early to", "too soon to",
    "not yet ready", "not the right time",
    "upcoming data will", "future meetings",
    "evolving situation", "fluid", "in flux",
    "uncharted territory", "unprecedented",
]

# 要人別の過去フェイントパターン（癖・傾向）
PERSON_FEINT_HISTORY = {
    "powell": {
        "known_pattern": "ハト派トーンで語った直後にタカ派行動を取る傾向",
        "typical_feint": "「利上げは急がない」→ 実際は利上げ実施",
        "watch_for": "patience/data-dependent と言いつつ行動は決まっている",
    },
    "ueda": {
        "known_pattern": "極めて慎重な表現で本音を隠す傾向",
        "typical_feint": "「緩和を粘り強く続ける」→ 実際は出口戦略を模索中",
        "watch_for": "二重否定や曖昧表現が増えた時は政策変更の前兆",
    },
    "lagarde": {
        "known_pattern": "強い決意を表明した後に方針転換する傾向",
        "typical_feint": "「利上げは当面ない」→ 翌月に利上げ",
        "watch_for": "断定的な否定表現は逆シグナルの可能性",
    },
    "trump": {
        "known_pattern": "市場を揺さぶる極端な発言の後に交渉材料として使う",
        "typical_feint": "「関税を引き上げる」→ 実際はディール交渉のカード",
        "watch_for": "SNS等での突発的発言は交渉戦術の一環",
    },
}


def detect_feint(text: str, person_key: Optional[str] = None) -> dict:
    """
    要人発言のフェイント（ミスリード、曖昧さ、観測気球）を検知する

    Returns:
        {
            "has_feint": True/False,
            "feint_level": "高" / "中" / "低" / "なし",
            "feint_types": [検知されたフェイントの種類],
            "warnings": [警告メッセージ],
            "true_direction_hint": "本音は円安寄りか" / "本音は円高寄りか" / None,
            "person_history": 過去のフェイントパターン or None,
        }
    """
    text_lower = text.lower()
    feint_types = []
    warnings = []
    feint_score = 0

    # 1) ヘッジ表現の検知
    hedge_hits = [p for p in HEDGE_PHRASES if p in text_lower]
    if hedge_hits:
        feint_types.append("ヘッジ表現")
        feint_score += len(hedge_hits) * 1.5
        warnings.append(
            f"🛡️ ヘッジ表現検知（{', '.join(hedge_hits[:3])}）→ "
            "言い切らずに逃げ道を確保。実際の行動は発言と異なる可能性"
        )

    # 2) 観測気球・リーク
    trial_hits = [p for p in TRIAL_BALLOON_PHRASES if p in text_lower]
    if trial_hits:
        feint_types.append("観測気球")
        feint_score += len(trial_hits) * 2
        warnings.append(
            f"🎈 観測気球の可能性（{', '.join(trial_hits[:3])}）→ "
            "市場の反応を見て本決定を下す布石。反応次第で方針が変わる"
        )

    # 3) 前言撤回・トーン反転
    reversal_hits = [p for p in REVERSAL_PHRASES if p in text_lower]
    if reversal_hits:
        feint_types.append("前言撤回")
        feint_score += len(reversal_hits) * 2.5
        warnings.append(
            f"🔄 前言撤回シグナル（{', '.join(reversal_hits[:3])}）→ "
            "以前の発言と矛盾する方向転換。表面の言葉より行動を見るべき"
        )

    # 4) 矛盾・両面表現
    contradiction_hits = []
    for word_a, word_b in CONTRADICTION_PATTERNS:
        if word_a in text_lower and word_b in text_lower:
            contradiction_hits.append(f"{word_a}+{word_b}")
    if contradiction_hits:
        feint_types.append("矛盾表現")
        feint_score += len(contradiction_hits) * 2
        warnings.append(
            f"⚡ 矛盾する表現を同時使用（{', '.join(contradiction_hits[:3])}）→ "
            "タカ派とハト派の両面を匂わせて市場を混乱させる意図の可能性"
        )

    # 5) 過剰な確信表現
    overconf_hits = [p for p in OVERCONFIDENCE_PHRASES if p in text_lower]
    if overconf_hits:
        feint_types.append("過剰断定")
        feint_score += len(overconf_hits) * 1.5
        warnings.append(
            f"⚠️ 過度に断定的な表現（{', '.join(overconf_hits[:3])}）→ "
            "「絶対にしない」は裏を返せば検討中の証拠。逆方向を警戒"
        )

    # 6) 時間稼ぎ
    stall_hits = [p for p in STALLING_PHRASES if p in text_lower]
    if stall_hits:
        feint_types.append("時間稼ぎ")
        feint_score += len(stall_hits) * 1
        warnings.append(
            f"⏳ 時間稼ぎ表現（{', '.join(stall_hits[:3])}）→ "
            "判断先送りは不確実性を高め、ボラティリティ拡大要因"
        )

    # 7) 要人の過去フェイント傾向
    person_history = None
    if person_key and person_key in PERSON_FEINT_HISTORY:
        person_history = PERSON_FEINT_HISTORY[person_key]
        if feint_score > 0:
            warnings.append(
                f"📋 この要人の過去パターン: {person_history['known_pattern']}。"
                f"注意: {person_history['watch_for']}"
            )

    # 本音の方向推測
    true_direction = _guess_true_direction(text_lower, feint_types)

    # フェイントレベル判定
    if feint_score >= 5:
        feint_level = "高"
    elif feint_score >= 2.5:
        feint_level = "中"
    elif feint_score > 0:
        feint_level = "低"
    else:
        feint_level = "なし"

    return {
        "has_feint": feint_score > 0,
        "feint_level": feint_level,
        "feint_score": round(feint_score, 1),
        "feint_types": feint_types,
        "warnings": warnings,
        "true_direction_hint": true_direction,
        "person_history": person_history,
    }


def _guess_true_direction(text_lower: str, feint_types: list) -> Optional[str]:
    """フェイントを踏まえて本音の方向を推測する"""
    hawk = sum(1 for kw in HAWKISH_KEYWORDS if kw in text_lower)
    dove = sum(1 for kw in DOVISH_KEYWORDS if kw in text_lower)

    if not feint_types:
        return None

    if "過剰断定" in feint_types or "前言撤回" in feint_types:
        if hawk > dove:
            return "表面はタカ派だが、本音はハト派（円高）寄りの可能性"
        elif dove > hawk:
            return "表面はハト派だが、本音はタカ派（円安）寄りの可能性"

    if "矛盾表現" in feint_types:
        return "意図的に曖昧化 → 次の行動で真意が判明するまで両方向に警戒"

    if "観測気球" in feint_types:
        if hawk > dove:
            return "タカ派方向の地ならし → 利上げ・引き締めへの布石の可能性（円安）"
        elif dove > hawk:
            return "ハト派方向の地ならし → 利下げ・緩和への布石の可能性（円高）"

    if "ヘッジ表現" in feint_types:
        return "公式見解と実際の行動にズレが生じやすい。行動ベースで判断を"

    return None


# ════════════════════════════════════════════════
#  メイン分析関数
# ════════════════════════════════════════════════

def fetch_economic_news() -> List[dict]:
    """経済指標・要人発言関連ニュースを取得"""
    queries = [
        "fed interest rate decision",
        "bank of japan policy",
        "us economic data",
        "japan economic indicator",
        "central bank speech",
        "forex market today",
        "us inflation cpi",
        "nonfarm payroll jobs",
        "geopolitical risk market",
        "powell speech remarks",
        "ueda boj statement",
        "trump tariff trade",
    ]

    all_articles = []
    seen_titles = set()

    for query in queries:
        encoded = query.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for entry in feed.entries[:6]:
            title = _clean_html(entry.title)
            if title in seen_titles:
                continue
            seen_titles.add(title)

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    dt = datetime(*entry.published_parsed[:6])
                    published = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    published = getattr(entry, "published", "")

            source = entry.get("source", {}).get("title", "")
            analysis = analyze_impact(title)

            all_articles.append({
                "title": title,
                "link": entry.link,
                "published": published,
                "source": source,
                "analysis": analysis,
            })

    all_articles.sort(key=lambda x: abs(x["analysis"]["score"]), reverse=True)
    return all_articles


def analyze_impact(text: str) -> dict:
    """
    テキストから円安/円高への影響を即時判定 + フェイント検知

    Returns:
        通常の判定結果に加えて feint 情報を含む
    """
    text_lower = text.lower()
    score = 0.0
    reasons = []
    category = "その他"
    importance = "低"
    person_name = None
    person_key = None

    # 1) 要人発言チェック
    for keyword, (name, currency) in KEY_PERSONS.items():
        if keyword in text_lower:
            person_name = name
            person_key = keyword
            category = "要人発言"
            importance = "高"

            hawk_hits = sum(1 for kw in HAWKISH_KEYWORDS if kw in text_lower)
            dove_hits = sum(1 for kw in DOVISH_KEYWORDS if kw in text_lower)

            if currency == "USD":
                score += (hawk_hits - dove_hits) * 0.2
                if hawk_hits > dove_hits:
                    reasons.append(f"{name}のタカ派発言 → 米金利上昇期待 → 円安")
                elif dove_hits > hawk_hits:
                    reasons.append(f"{name}のハト派発言 → 米金利低下期待 → 円高")
                else:
                    reasons.append(f"{name}関連ニュース")
            elif currency == "JPY":
                score -= (hawk_hits - dove_hits) * 0.2
                if hawk_hits > dove_hits:
                    reasons.append(f"{name}のタカ派発言 → 日本金利上昇期待 → 円高")
                elif dove_hits > hawk_hits:
                    reasons.append(f"{name}のハト派発言 → 日本金利低下期待 → 円安")
                else:
                    reasons.append(f"{name}関連ニュース")
            break

    # 2) 経済指標チェック
    for keyword, indicator_name in US_INDICATORS_BULLISH_USD.items():
        if keyword in text_lower:
            category = "経済指標"
            importance = "高" if keyword in ["nonfarm", "cpi", "gdp", "non-farm"] else "中"

            strong_hits = sum(1 for kw in ["beat", "strong", "surge", "above", "higher", "rise", "jump", "robust"]
                             if kw in text_lower)
            weak_hits = sum(1 for kw in ["miss", "weak", "below", "lower", "fall", "drop", "decline", "disappoint"]
                           if kw in text_lower)

            indicator_score = (strong_hits - weak_hits) * 0.2
            score += indicator_score

            if indicator_score > 0:
                reasons.append(f"{indicator_name}が予想を上回る → ドル高 → 円安")
            elif indicator_score < 0:
                reasons.append(f"{indicator_name}が予想を下回る → ドル安 → 円高")
            else:
                reasons.append(f"{indicator_name}関連ニュース")
            break

    # 3) 金融政策チェック
    if not reasons:
        hawk = sum(1 for kw in HAWKISH_KEYWORDS if kw in text_lower)
        dove = sum(1 for kw in DOVISH_KEYWORDS if kw in text_lower)

        if hawk + dove >= 2:
            category = "金融政策"
            importance = "高"
            policy_score = (hawk - dove) * 0.15

            if "japan" in text_lower or "boj" in text_lower or "yen" in text_lower:
                score -= policy_score
                if policy_score > 0:
                    reasons.append("日本の金融引き締め示唆 → 円高")
                elif policy_score < 0:
                    reasons.append("日本の金融緩和継続 → 円安")
            else:
                score += policy_score
                if policy_score > 0:
                    reasons.append("米欧のタカ派姿勢 → ドル高 → 円安")
                elif policy_score < 0:
                    reasons.append("米欧のハト派姿勢 → ドル安 → 円高")

    # 4) 地政学リスクチェック
    risk_off = sum(1 for kw in RISK_OFF_KEYWORDS if kw in text_lower)
    risk_on = sum(1 for kw in RISK_ON_KEYWORDS if kw in text_lower)

    if risk_off > risk_on and risk_off >= 1:
        category = "地政学"
        importance = "高" if risk_off >= 2 else "中"
        score -= risk_off * 0.1
        reasons.append("地政学リスク上昇 → 安全資産の円に資金流入 → 円高")
    elif risk_on > risk_off and risk_on >= 1:
        category = "地政学"
        importance = "中"
        score += risk_on * 0.1
        reasons.append("リスクオン（楽観ムード） → 円売り → 円安")

    # 5) TextBlobの感情分析で補完
    if not reasons:
        blob = TextBlob(text)
        pol = blob.sentiment.polarity
        if "yen" in text_lower or "japan" in text_lower:
            score -= pol * 0.15
        elif "dollar" in text_lower or "usd" in text_lower:
            score += pol * 0.15

    score = max(-1.0, min(1.0, score))

    if score > 0.08:
        verdict = "円安要因"
    elif score < -0.08:
        verdict = "円高要因"
    else:
        verdict = "中立"

    if not reasons:
        reasons.append("直接的な為替影響は限定的")
        importance = "低"

    # ─── フェイント検知 ───
    feint = detect_feint(text, person_key)

    if feint["has_feint"] and feint["feint_level"] in ["高", "中"]:
        if feint["true_direction_hint"]:
            reasons.append(f"⚠️ フェイント警告: {feint['true_direction_hint']}")

    # ─── 人物プロファイル分析 ───
    person_context = analyze_person_context(text)

    return {
        "verdict": verdict,
        "score": round(score, 3),
        "reason": reasons[0] if reasons else "",
        "all_reasons": reasons,
        "category": category,
        "importance": importance,
        "person": person_name,
        "person_key": person_key,
        "feint": feint,
        "person_context": person_context,
    }


def get_summary(articles: List[dict]) -> dict:
    """全記事を集計して総合判定"""
    if not articles:
        return {
            "verdict": "データなし", "score": 0,
            "yen_weak": 0, "yen_strong": 0, "neutral": 0,
            "feint_count": 0,
        }

    scores = [a["analysis"]["score"] for a in articles]
    avg = sum(scores) / len(scores)

    yen_weak = sum(1 for a in articles if a["analysis"]["verdict"] == "円安要因")
    yen_strong = sum(1 for a in articles if a["analysis"]["verdict"] == "円高要因")
    neutral = sum(1 for a in articles if a["analysis"]["verdict"] == "中立")

    feint_count = sum(1 for a in articles if a["analysis"]["feint"]["has_feint"])

    high_impact = [a for a in articles if a["analysis"]["importance"] == "高"]
    if high_impact:
        high_scores = [a["analysis"]["score"] for a in high_impact]
        weighted_avg = sum(high_scores) / len(high_scores)
        final = avg * 0.4 + weighted_avg * 0.6
    else:
        final = avg

    if final > 0.05:
        verdict = "総合: 円安圧力"
    elif final < -0.05:
        verdict = "総合: 円高圧力"
    else:
        verdict = "総合: 中立"

    return {
        "verdict": verdict,
        "score": round(final, 3),
        "yen_weak": yen_weak,
        "yen_strong": yen_strong,
        "neutral": neutral,
        "feint_count": feint_count,
    }


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
