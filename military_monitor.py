"""
軍事・防衛動向モニターモジュール
米軍・自衛隊・NATO・中国軍・ロシア軍 等の動きと、各国防衛省/国防総省の発表を追跡し、
為替（円安/円高）への影響と、影響がピークになる時間帯を予測する
"""

import feedparser
import re
from textblob import TextBlob
from datetime import datetime, timedelta
from typing import List, Optional


# ════════════════════════════════════════════════
#  追跡対象: 軍事組織・防衛機関
# ════════════════════════════════════════════════

MILITARY_ENTITIES = {
    # 米国
    "pentagon": {"name": "ペンタゴン（米国防総省）", "country": "US", "weight": 1.0},
    "department of defense": {"name": "米国防総省", "country": "US", "weight": 1.0},
    "us military": {"name": "米軍", "country": "US", "weight": 0.9},
    "us army": {"name": "米陸軍", "country": "US", "weight": 0.8},
    "us navy": {"name": "米海軍", "country": "US", "weight": 0.9},
    "us air force": {"name": "米空軍", "country": "US", "weight": 0.8},
    "us marines": {"name": "米海兵隊", "country": "US", "weight": 0.8},
    "indo-pacific command": {"name": "米インド太平洋軍", "country": "US", "weight": 0.9},
    "centcom": {"name": "米中央軍（CENTCOM）", "country": "US", "weight": 0.9},
    "carrier strike group": {"name": "空母打撃群", "country": "US", "weight": 0.9},
    "aircraft carrier": {"name": "航空母艦", "country": "US", "weight": 0.8},
    "lloyd austin": {"name": "オースティン国防長官", "country": "US", "weight": 1.0},
    "defense secretary": {"name": "国防長官", "country": "US", "weight": 1.0},

    # 日本
    "japan self-defense": {"name": "自衛隊", "country": "JP", "weight": 0.8},
    "jsdf": {"name": "自衛隊（JSDF）", "country": "JP", "weight": 0.8},
    "japan defense": {"name": "日本防衛省", "country": "JP", "weight": 0.9},
    "japan military": {"name": "日本軍事", "country": "JP", "weight": 0.8},
    "japan coast guard": {"name": "海上保安庁", "country": "JP", "weight": 0.7},

    # NATO・欧州
    "nato": {"name": "NATO（北大西洋条約機構）", "country": "EU", "weight": 0.9},
    "nato alliance": {"name": "NATO同盟", "country": "EU", "weight": 0.9},
    "european defense": {"name": "欧州防衛", "country": "EU", "weight": 0.7},

    # 中国
    "china military": {"name": "中国人民解放軍", "country": "CN", "weight": 1.0},
    "pla": {"name": "人民解放軍（PLA）", "country": "CN", "weight": 1.0},
    "chinese navy": {"name": "中国海軍", "country": "CN", "weight": 0.9},
    "chinese air force": {"name": "中国空軍", "country": "CN", "weight": 0.8},
    "taiwan strait": {"name": "台湾海峡", "country": "CN", "weight": 1.0},
    "south china sea": {"name": "南シナ海", "country": "CN", "weight": 0.9},
    "east china sea": {"name": "東シナ海", "country": "CN", "weight": 0.9},
    "senkaku": {"name": "尖閣諸島", "country": "CN", "weight": 1.0},

    # ロシア
    "russian military": {"name": "ロシア軍", "country": "RU", "weight": 0.9},
    "russian forces": {"name": "ロシア軍", "country": "RU", "weight": 0.9},
    "russia ukraine": {"name": "ロシア・ウクライナ", "country": "RU", "weight": 1.0},
    "ukraine war": {"name": "ウクライナ戦争", "country": "RU", "weight": 1.0},
    "nuclear threat": {"name": "核の脅威", "country": "RU", "weight": 1.0},

    # 中東
    "iran military": {"name": "イラン軍", "country": "ME", "weight": 0.9},
    "israel military": {"name": "イスラエル軍（IDF）", "country": "ME", "weight": 0.9},
    "idf": {"name": "イスラエル国防軍", "country": "ME", "weight": 0.9},
    "houthi": {"name": "フーシ派", "country": "ME", "weight": 0.8},
    "hezbollah": {"name": "ヒズボラ", "country": "ME", "weight": 0.8},
    "hamas": {"name": "ハマス", "country": "ME", "weight": 0.8},
    "strait of hormuz": {"name": "ホルムズ海峡", "country": "ME", "weight": 1.0},
    "red sea": {"name": "紅海", "country": "ME", "weight": 0.8},
    "persian gulf": {"name": "ペルシャ湾", "country": "ME", "weight": 0.8},

    # 北朝鮮
    "north korea missile": {"name": "北朝鮮ミサイル", "country": "NK", "weight": 1.0},
    "north korea nuclear": {"name": "北朝鮮核", "country": "NK", "weight": 1.0},
    "icbm": {"name": "大陸間弾道ミサイル（ICBM）", "country": "NK", "weight": 1.0},
    "pyongyang": {"name": "平壌", "country": "NK", "weight": 0.7},
}

# 軍事行動の種類 → 緊張度
ESCALATION_KEYWORDS = {
    "deploy": ("部隊展開", 0.6),
    "deployment": ("部隊配備", 0.6),
    "mobilize": ("動員", 0.7),
    "exercise": ("軍事演習", 0.5),
    "drill": ("演習", 0.5),
    "joint exercise": ("合同演習", 0.4),
    "missile launch": ("ミサイル発射", 0.9),
    "missile test": ("ミサイル実験", 0.8),
    "ballistic missile": ("弾道ミサイル", 0.9),
    "cruise missile": ("巡航ミサイル", 0.8),
    "hypersonic": ("極超音速兵器", 0.9),
    "nuclear test": ("核実験", 1.0),
    "nuclear weapon": ("核兵器", 0.9),
    "airstrike": ("空爆", 0.9),
    "air strike": ("空爆", 0.9),
    "bombing": ("爆撃", 0.9),
    "invasion": ("侵攻", 1.0),
    "incursion": ("侵入", 0.8),
    "blockade": ("封鎖", 0.9),
    "naval blockade": ("海上封鎖", 1.0),
    "no-fly zone": ("飛行禁止区域", 0.8),
    "cyber attack": ("サイバー攻撃", 0.7),
    "cyberattack": ("サイバー攻撃", 0.7),
    "assassination": ("暗殺", 0.9),
    "coup": ("クーデター", 0.9),
    "martial law": ("戒厳令", 1.0),
    "emergency": ("非常事態", 0.7),
    "intercept": ("迎撃・傍受", 0.6),
    "scramble": ("緊急発進（スクランブル）", 0.6),
    "provocation": ("挑発", 0.6),
    "confrontation": ("対峙・衝突", 0.7),
    "retaliation": ("報復", 0.8),
    "escalation": ("エスカレーション", 0.8),
    "standoff": ("にらみ合い", 0.6),
    "arms deal": ("武器取引", 0.5),
    "arms sale": ("武器売却", 0.5),
    "defense budget": ("防衛予算", 0.4),
    "military spending": ("軍事支出", 0.4),
    "conscription": ("徴兵", 0.7),
}

DE_ESCALATION_KEYWORDS = {
    "ceasefire": ("停戦", -0.7),
    "peace talk": ("和平交渉", -0.6),
    "peace deal": ("和平合意", -0.8),
    "withdrawal": ("撤退", -0.6),
    "pullout": ("撤収", -0.6),
    "de-escalation": ("緊張緩和", -0.7),
    "de-escalate": ("緊張緩和", -0.7),
    "diplomatic": ("外交的解決", -0.4),
    "negotiate": ("交渉", -0.3),
    "truce": ("休戦", -0.7),
    "armistice": ("休戦協定", -0.8),
    "disarmament": ("軍縮", -0.6),
    "demilitarize": ("非武装化", -0.6),
    "humanitarian corridor": ("人道回廊", -0.5),
    "prisoner exchange": ("捕虜交換", -0.4),
}

# 地域別の為替影響パターン
REGION_FX_IMPACT = {
    "US": {
        "escalation": "米軍事行動 → 有事のドル買い → 短期的に円安、ただし長期化すれば財政懸念でドル安",
        "de_escalation": "緊張緩和 → リスクオン → 円売り → 円安",
    },
    "JP": {
        "escalation": "日本周辺の脅威 → 安全資産の円買い → 円高（逆説的だが歴史的パターン）",
        "de_escalation": "脅威後退 → リスクオン → 円売り → 円安",
    },
    "CN": {
        "escalation": "米中対立激化 → サプライチェーン不安 → リスクオフ → 円高",
        "de_escalation": "米中関係改善 → 世界経済楽観 → リスクオン → 円安",
    },
    "RU": {
        "escalation": "ロシアの軍事行動 → エネルギー不安 → 欧州経済打撃 → 円高",
        "de_escalation": "ウクライナ停戦 → エネルギー安定 → リスクオン → 円安",
    },
    "ME": {
        "escalation": "中東緊張 → 原油高騰 → 日本は輸入国なので貿易赤字拡大 → 円安",
        "de_escalation": "中東安定 → 原油安定 → 貿易赤字縮小 → やや円高",
    },
    "NK": {
        "escalation": "北朝鮮挑発 → 地政学リスク → 安全資産の円買い → 円高",
        "de_escalation": "北朝鮮対話 → リスク後退 → 円安",
    },
    "EU": {
        "escalation": "NATO軍事強化 → 欧州防衛支出増 → ユーロ圏財政懸念 → 円高",
        "de_escalation": "NATO安定 → ユーロ回復 → 対ユーロで円安",
    },
}

# 時間帯別: 軍事ニュースが為替に波及するタイミング
IMPACT_TIMING = {
    "missile_launch": {
        "label": "ミサイル発射",
        "immediate": "発生直後〜30分: パニック的な円買い（円高）",
        "short_term": "1〜3時間: 各国政府の反応で方向性が決まる",
        "medium_term": "4〜24時間: 報復・追加行動の有無で大きく変動",
        "peak_pattern": "発生直後が最大の円高ピーク。その後反発で円安方向へ",
        "peak_offset_minutes": 15,
    },
    "military_conflict": {
        "label": "軍事衝突・紛争",
        "immediate": "発生直後〜1時間: リスクオフで円高",
        "short_term": "2〜6時間: 規模の確認で追加の円買いか反発か",
        "medium_term": "1〜3日: 原油・エネルギー市場の反応が波及",
        "peak_pattern": "衝突拡大懸念がピークの時が円高ピーク（通常6〜12時間後）",
        "peak_offset_minutes": 360,
    },
    "deployment": {
        "label": "部隊展開・配備",
        "immediate": "発表直後: 限定的な反応",
        "short_term": "数時間〜1日: 意図の分析が進み、方向性が固まる",
        "medium_term": "数日: 実際の軍事行動に発展するか注視",
        "peak_pattern": "展開の意図が判明した時がピーク（通常翌日の東京市場オープン）",
        "peak_offset_minutes": 720,
    },
    "exercise": {
        "label": "軍事演習",
        "immediate": "限定的な影響",
        "short_term": "演習の規模・場所による。台湾海峡なら大きい",
        "medium_term": "演習終了まで不透明感が続く",
        "peak_pattern": "演習開始日のアジア市場オープン（9:00 JST）前後",
        "peak_offset_minutes": 60,
    },
    "ceasefire": {
        "label": "停戦・和平",
        "immediate": "発表直後: リスクオンで円安（大きく動く）",
        "short_term": "数時間: 合意の信頼性で調整",
        "medium_term": "数日: 実際の履行状況で持続性を判断",
        "peak_pattern": "発表直後が円安ピーク。その後「本当か？」で戻す",
        "peak_offset_minutes": 30,
    },
    "nuclear": {
        "label": "核関連（実験・脅威）",
        "immediate": "発生直後: 世界的パニック → 急激な円高",
        "short_term": "数時間: 各国の対応声明で追加動向",
        "medium_term": "数日〜数週間: 制裁・対抗措置で長期トレンド形成",
        "peak_pattern": "円高の最大ピークは発生後1〜2時間。その後は情報戦",
        "peak_offset_minutes": 90,
    },
}


def fetch_military_news() -> List[dict]:
    """軍事・防衛関連ニュースを取得"""
    queries = [
        "US military deployment",
        "pentagon defense",
        "NATO military",
        "China military Taiwan",
        "Russia Ukraine war",
        "North Korea missile",
        "Middle East military conflict",
        "Japan defense security",
        "Iran Israel military",
        "Red Sea Houthi attack",
        "South China Sea",
        "nuclear threat",
    ]

    all_articles = []
    seen_titles = set()

    for query in queries:
        encoded = query.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
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
            analysis = analyze_military_impact(title)

            if analysis["relevance"] > 0:
                all_articles.append({
                    "title": title,
                    "link": entry.link,
                    "published": published,
                    "source": source,
                    "analysis": analysis,
                })

    all_articles.sort(key=lambda x: x["analysis"]["tension_level"], reverse=True)
    return all_articles


def analyze_military_impact(text: str) -> dict:
    """
    軍事ニュースの為替への影響を分析

    Returns:
        {
            "verdict": "円安要因" / "円高要因" / "中立",
            "score": -1.0〜1.0,
            "tension_level": 緊張度 0〜1.0,
            "entities": [検出された軍事組織],
            "actions": [検出された軍事行動],
            "region": 主要関連地域,
            "fx_mechanism": 為替への波及メカニズム説明,
            "peak_timing": ピーク時刻予測,
            "relevance": 関連度 0〜1.0,
        }
    """
    text_lower = text.lower()

    # 軍事組織の検出
    entities = []
    regions = []
    max_weight = 0
    for keyword, info in MILITARY_ENTITIES.items():
        if keyword in text_lower:
            entities.append(info)
            regions.append(info["country"])
            max_weight = max(max_weight, info["weight"])

    if not entities:
        return {"relevance": 0, "verdict": "中立", "score": 0, "tension_level": 0,
                "entities": [], "actions": [], "region": "", "fx_mechanism": "",
                "peak_timing": None}

    # 軍事行動の検出
    esc_score = 0.0
    actions = []
    event_type = "deployment"

    for keyword, (label, tension) in ESCALATION_KEYWORDS.items():
        if keyword in text_lower:
            esc_score += tension
            actions.append({"action": label, "tension": tension, "direction": "escalation"})
            if tension >= 0.9:
                if "nuclear" in keyword:
                    event_type = "nuclear"
                elif "missile" in keyword:
                    event_type = "missile_launch"
                else:
                    event_type = "military_conflict"
            elif tension >= 0.5 and event_type == "deployment":
                if "exercise" in keyword or "drill" in keyword:
                    event_type = "exercise"

    for keyword, (label, tension) in DE_ESCALATION_KEYWORDS.items():
        if keyword in text_lower:
            esc_score += tension
            actions.append({"action": label, "tension": tension, "direction": "de_escalation"})
            if abs(tension) >= 0.6:
                event_type = "ceasefire"

    # 緊張度 (0〜1)
    tension = min(1.0, max(0.0, esc_score / 2))

    # 主要地域
    primary_region = max(set(regions), key=regions.count) if regions else "US"

    # 為替スコア計算
    region_info = REGION_FX_IMPACT.get(primary_region, REGION_FX_IMPACT["US"])
    if esc_score > 0:
        fx_mechanism = region_info["escalation"]
    elif esc_score < 0:
        fx_mechanism = region_info["de_escalation"]
    else:
        fx_mechanism = "影響は限定的"

    # 地域別の円安/円高スコア
    fx_score = _calculate_fx_score(primary_region, esc_score, tension)

    if fx_score > 0.08:
        verdict = "円安要因"
    elif fx_score < -0.08:
        verdict = "円高要因"
    else:
        verdict = "中立"

    # ピーク時刻予測
    peak_timing = _predict_impact_peak(event_type, tension)

    return {
        "verdict": verdict,
        "score": round(fx_score, 3),
        "tension_level": round(tension, 2),
        "entities": entities,
        "actions": actions,
        "region": primary_region,
        "fx_mechanism": fx_mechanism,
        "peak_timing": peak_timing,
        "event_type": event_type,
        "relevance": min(1.0, max_weight * (0.5 + tension)),
    }


def _calculate_fx_score(region: str, esc_score: float, tension: float) -> float:
    """地域と軍事行動からFXスコアを算出"""
    score = 0.0

    if esc_score > 0:
        if region in ["NK", "JP", "CN", "RU", "EU"]:
            score = -tension * 0.5  # リスクオフ → 円高
        elif region == "ME":
            score = tension * 0.4  # 原油高 → 貿易赤字 → 円安
        elif region == "US":
            score = tension * 0.2  # 有事のドル買い → 円安（短期）
    elif esc_score < 0:
        score = abs(esc_score) * 0.3  # 緊張緩和 → リスクオン → 円安

    return max(-1.0, min(1.0, score))


def _predict_impact_peak(event_type: str, tension: float) -> dict:
    """軍事イベントの為替影響ピーク時刻を予測"""
    now = datetime.now()
    timing = IMPACT_TIMING.get(event_type, IMPACT_TIMING["deployment"])

    offset = timing["peak_offset_minutes"]
    if tension > 0.8:
        offset = int(offset * 0.5)  # 高緊張度は早くピーク到達

    peak_time = now + timedelta(minutes=offset)

    # 市場時間に調整
    peak_hour = peak_time.hour
    if 7 <= peak_hour < 9:
        peak_time = peak_time.replace(hour=9, minute=0)
    elif 3 <= peak_hour < 7:
        peak_time = peak_time.replace(hour=9, minute=0)

    return {
        "event_label": timing["label"],
        "peak_time": peak_time.strftime("%H:%M"),
        "peak_date": peak_time.strftime("%Y-%m-%d"),
        "immediate": timing["immediate"],
        "short_term": timing["short_term"],
        "medium_term": timing["medium_term"],
        "peak_pattern": timing["peak_pattern"],
    }


def get_military_summary(articles: List[dict]) -> dict:
    """軍事ニュース全体の集計"""
    if not articles:
        return {"verdict": "軍事ニュースなし", "score": 0, "tension_avg": 0,
                "yen_weak": 0, "yen_strong": 0, "neutral": 0, "max_tension_event": None}

    scores = [a["analysis"]["score"] for a in articles]
    tensions = [a["analysis"]["tension_level"] for a in articles]
    avg_score = sum(scores) / len(scores)
    avg_tension = sum(tensions) / len(tensions)

    yen_weak = sum(1 for a in articles if a["analysis"]["verdict"] == "円安要因")
    yen_strong = sum(1 for a in articles if a["analysis"]["verdict"] == "円高要因")
    neutral = sum(1 for a in articles if a["analysis"]["verdict"] == "中立")

    max_tension_article = max(articles, key=lambda x: x["analysis"]["tension_level"])

    if avg_score > 0.05:
        verdict = "軍事面: 円安圧力"
    elif avg_score < -0.05:
        verdict = "軍事面: 円高圧力"
    else:
        verdict = "軍事面: 中立"

    return {
        "verdict": verdict,
        "score": round(avg_score, 3),
        "tension_avg": round(avg_tension, 2),
        "yen_weak": yen_weak,
        "yen_strong": yen_strong,
        "neutral": neutral,
        "max_tension_event": {
            "title": max_tension_article["title"],
            "tension": max_tension_article["analysis"]["tension_level"],
            "peak_timing": max_tension_article["analysis"]["peak_timing"],
        },
    }


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
