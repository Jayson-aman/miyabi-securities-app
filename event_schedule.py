"""
経済指標・要人発言 スケジュール ＆ 影響期間予測モジュール

各イベントについて以下を提供：
1. 開催日時（日付＋日本時間）
2. 影響開始時刻と持続期間（キープできる期間）
3. JPYへの影響方向と振幅
4. 「いつまで現在トレンドが続くか」の目安
"""

from datetime import datetime, timedelta, time
from typing import List, Optional
import calendar


# ════════════════════════════════════════════════
#  定期経済指標カレンダー
#  各イベントは「月内でいつ発生するか」のルールベース定義
#
#  rule type:
#    - "nth_weekday"   : 第n週の曜日（例: 雇用統計=第1金曜）
#    - "fixed_day"     : 毎月固定日
#    - "boj_meeting"   : 日銀金融政策決定会合（年8回・概ね月末）
#    - "fomc_meeting"  : FOMC（年8回・概ね6週ごと）
#    - "ecb_meeting"   : ECB理事会（年8回）
# ════════════════════════════════════════════════

ECONOMIC_EVENTS = [
    # ─── 米国 ───
    {
        "name": "米雇用統計（NFP）",
        "country": "🇺🇸",
        "category": "雇用",
        "rule": "nth_weekday", "nth": 1, "weekday": 4,  # 第1金曜
        "jst_time": "21:30",
        "impact_level": 5,  # 1-5
        "jpy_direction": "depends",
        "immediate_volatility_min": 30,    # 急変動が起きる時間（分）
        "high_volatility_hours": 3,         # 高ボラ継続時間
        "trend_keep_hours": 24,             # トレンド方向が継続する目安
        "description": "非農業部門雇用者数。+25万人超で円安、悪化で円高",
        "reversal_risk": "予想と乖離した結果は逆方向に急変",
    },
    {
        "name": "米CPI（消費者物価指数）",
        "country": "🇺🇸",
        "category": "物価",
        "rule": "fixed_day", "day": 13,  # 概ね月の中旬（10-15日）
        "jst_time": "21:30",
        "impact_level": 5,
        "jpy_direction": "depends",
        "immediate_volatility_min": 30,
        "high_volatility_hours": 4,
        "trend_keep_hours": 48,
        "description": "前年比+2%超で利上げ観測→円安、低下で円高",
        "reversal_risk": "コアCPI注視。総合と逆動きの場合あり",
    },
    {
        "name": "米PPI（生産者物価指数）",
        "country": "🇺🇸",
        "category": "物価",
        "rule": "fixed_day", "day": 14,
        "jst_time": "21:30",
        "impact_level": 3,
        "jpy_direction": "depends",
        "immediate_volatility_min": 20,
        "high_volatility_hours": 2,
        "trend_keep_hours": 12,
        "description": "CPI前哨戦。インフレ動向の先行指標",
    },
    {
        "name": "米PCE価格指数（FRBの目安）",
        "country": "🇺🇸",
        "category": "物価",
        "rule": "fixed_day", "day": 28,
        "jst_time": "22:30",
        "impact_level": 4,
        "jpy_direction": "depends",
        "immediate_volatility_min": 30,
        "high_volatility_hours": 3,
        "trend_keep_hours": 24,
        "description": "FRBが最重視するインフレ指標。コアPCE2%が目標",
    },
    {
        "name": "米GDP速報値",
        "country": "🇺🇸",
        "category": "成長",
        "rule": "fixed_day", "day": 25,
        "jst_time": "21:30",
        "impact_level": 4,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 30,
        "high_volatility_hours": 3,
        "trend_keep_hours": 36,
        "description": "強い数字→円安、景気後退示唆→円高",
    },
    {
        "name": "ISM製造業景況指数",
        "country": "🇺🇸",
        "category": "景況感",
        "rule": "fixed_day", "day": 1,  # 月初第1営業日
        "jst_time": "23:00",
        "impact_level": 3,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 15,
        "high_volatility_hours": 2,
        "trend_keep_hours": 12,
        "description": "50超で景気拡大→円安、50割れで景気後退→円高",
    },
    {
        "name": "ISM非製造業（サービス業）",
        "country": "🇺🇸",
        "category": "景況感",
        "rule": "fixed_day", "day": 3,
        "jst_time": "23:00",
        "impact_level": 3,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 15,
        "high_volatility_hours": 2,
        "trend_keep_hours": 12,
        "description": "米経済の8割を占めるサービス業の景況感",
    },
    {
        "name": "米小売売上高",
        "country": "🇺🇸",
        "category": "消費",
        "rule": "fixed_day", "day": 15,
        "jst_time": "21:30",
        "impact_level": 3,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 20,
        "high_volatility_hours": 2,
        "trend_keep_hours": 12,
        "description": "消費の強さは利上げ余地を示唆",
    },
    {
        "name": "ADP雇用統計",
        "country": "🇺🇸",
        "category": "雇用",
        "rule": "nth_weekday", "nth": 1, "weekday": 2,  # 第1水曜
        "jst_time": "21:15",
        "impact_level": 2,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 15,
        "high_volatility_hours": 1,
        "trend_keep_hours": 6,
        "description": "雇用統計の前哨戦。乖離する場合あり",
    },
    {
        "name": "FOMC（米連邦公開市場委員会）",
        "country": "🇺🇸",
        "category": "金融政策",
        "rule": "fomc_meeting",
        "jst_time": "03:00",  # 翌日午前3時（声明発表）
        "impact_level": 5,
        "jpy_direction": "depends",
        "immediate_volatility_min": 60,
        "high_volatility_hours": 6,
        "trend_keep_hours": 168,  # 1週間
        "description": "政策金利・声明文・ドットチャート・パウエル会見が円相場を決定",
        "reversal_risk": "ハト派サプライズ→急激な円高、タカ派サプライズ→円安加速",
    },

    # ─── 日本 ───
    {
        "name": "日銀金融政策決定会合",
        "country": "🇯🇵",
        "category": "金融政策",
        "rule": "boj_meeting",
        "jst_time": "12:00",
        "impact_level": 5,
        "jpy_direction": "depends",
        "immediate_volatility_min": 60,
        "high_volatility_hours": 8,
        "trend_keep_hours": 240,  # 10日間
        "description": "利上げ・YCC修正観測→急激な円高。緩和維持→円安加速",
        "reversal_risk": "サプライズ修正で1日5円規模の円高もあり得る",
    },
    {
        "name": "日銀総裁記者会見",
        "country": "🇯🇵",
        "category": "要人発言",
        "rule": "boj_meeting",
        "jst_time": "15:30",  # 会合当日
        "impact_level": 5,
        "jpy_direction": "depends",
        "immediate_volatility_min": 90,
        "high_volatility_hours": 6,
        "trend_keep_hours": 72,
        "description": "植田総裁の発言ニュアンスが為替を動かす",
        "reversal_risk": "タカ派発言で円高転換、ハト派維持で円安継続",
    },
    {
        "name": "日本CPI",
        "country": "🇯🇵",
        "category": "物価",
        "rule": "fixed_day", "day": 22,
        "jst_time": "08:30",
        "impact_level": 3,
        "jpy_direction": "strong_if_high",
        "immediate_volatility_min": 30,
        "high_volatility_hours": 3,
        "trend_keep_hours": 12,
        "description": "高インフレは日銀利上げ観測→円高",
    },
    {
        "name": "日銀短観（業況判断DI）",
        "country": "🇯🇵",
        "category": "景況感",
        "rule": "fixed_day", "day": 1,
        "jst_time": "08:50",
        "impact_level": 3,
        "jpy_direction": "strong_if_strong",
        "immediate_volatility_min": 30,
        "high_volatility_hours": 3,
        "trend_keep_hours": 12,
        "description": "四半期1回。日本経済の状況を映す",
    },
    {
        "name": "日本貿易収支",
        "country": "🇯🇵",
        "category": "貿易",
        "rule": "fixed_day", "day": 18,
        "jst_time": "08:50",
        "impact_level": 2,
        "jpy_direction": "strong_if_surplus",
        "immediate_volatility_min": 15,
        "high_volatility_hours": 2,
        "trend_keep_hours": 8,
        "description": "貿易黒字=円高要因、赤字=円安要因",
    },

    # ─── 欧州 ───
    {
        "name": "ECB理事会",
        "country": "🇪🇺",
        "category": "金融政策",
        "rule": "ecb_meeting",
        "jst_time": "21:15",
        "impact_level": 4,
        "jpy_direction": "depends",
        "immediate_volatility_min": 60,
        "high_volatility_hours": 5,
        "trend_keep_hours": 96,
        "description": "EUR/JPY経由でドル円にも波及",
    },
    {
        "name": "ユーロ圏CPI",
        "country": "🇪🇺",
        "category": "物価",
        "rule": "fixed_day", "day": 17,
        "jst_time": "18:00",
        "impact_level": 2,
        "jpy_direction": "depends",
        "immediate_volatility_min": 20,
        "high_volatility_hours": 2,
        "trend_keep_hours": 8,
        "description": "ECB金融政策の根拠となる",
    },

    # ─── 中国 ───
    {
        "name": "中国GDP・小売・鉱工業",
        "country": "🇨🇳",
        "category": "成長",
        "rule": "fixed_day", "day": 16,
        "jst_time": "11:00",
        "impact_level": 3,
        "jpy_direction": "weak_if_strong",
        "immediate_volatility_min": 20,
        "high_volatility_hours": 2,
        "trend_keep_hours": 12,
        "description": "中国減速は人民元安連動で円も売られやすい",
    },
]


# ════════════════════════════════════════════════
#  要人発言（定期スケジュール枠 + 注意人物）
# ════════════════════════════════════════════════

KEY_PERSON_SCHEDULE = [
    {
        "name": "FRB議長講演（パウエル）",
        "person": "パウエル",
        "country": "🇺🇸",
        "frequency": "不定期 / FOMC前後 / ジャクソンホール（8月下旬）",
        "jst_time": "深夜 22:00-翌02:00",
        "impact_level": 5,
        "trend_keep_hours": 72,
        "description": "ハト派 → 円高、タカ派 → 円安。会見の語尾とフォワードガイダンス重視",
        "reversal_risk": "事前期待と異なる発言で急反転"
    },
    {
        "name": "FRB高官 公演（ウォラー/ボウマン/ウィリアムズ等）",
        "person": "FRB高官",
        "country": "🇺🇸",
        "frequency": "週数回",
        "jst_time": "23:00 - 翌03:00",
        "impact_level": 3,
        "trend_keep_hours": 24,
        "description": "高官の発言で短期トレンド形成。タカ派発言＝円安、ハト派＝円高",
    },
    {
        "name": "日銀総裁発言（植田）",
        "person": "植田",
        "country": "🇯🇵",
        "frequency": "不定期 / 国会答弁 / 講演",
        "jst_time": "08:00-17:00",
        "impact_level": 5,
        "trend_keep_hours": 96,
        "description": "正常化加速示唆 → 急激な円高、緩和継続 → 円安加速",
        "reversal_risk": "想定外のタカ派化で1円以上の円高に振れる"
    },
    {
        "name": "財務官・神田氏（介入関係者）",
        "person": "財務官",
        "country": "🇯🇵",
        "frequency": "円安加速時に増加",
        "jst_time": "07:00-22:00（随時）",
        "impact_level": 5,
        "trend_keep_hours": 48,
        "description": "口先介入から実弾介入まで。「あらゆる手段」「断固たる措置」がキーワード",
        "reversal_risk": "実弾介入で1時間で5円超の円高転換あり"
    },
    {
        "name": "ECB総裁（ラガルド）",
        "person": "ラガルド",
        "country": "🇪🇺",
        "frequency": "ECB理事会後 / 月例講演",
        "jst_time": "21:30-23:00",
        "impact_level": 4,
        "trend_keep_hours": 48,
        "description": "ユーロ円経由でドル円に波及"
    },
    {
        "name": "日本財務大臣・首相",
        "person": "財務大臣",
        "country": "🇯🇵",
        "frequency": "閣議後会見・国会",
        "jst_time": "09:00-18:00",
        "impact_level": 4,
        "trend_keep_hours": 24,
        "description": "「過度な変動は好ましくない」「行き過ぎた動きには適切に対応」が警戒語",
    },
]


# ════════════════════════════════════════════════
#  日付計算ユーティリティ
# ════════════════════════════════════════════════

def _nth_weekday_of_month(year: int, month: int, nth: int, weekday: int) -> datetime:
    """ある月の第n曜日（0=月, 4=金）を返す"""
    first = datetime(year, month, 1)
    first_weekday = first.weekday()
    days_ahead = (weekday - first_weekday) % 7
    day = 1 + days_ahead + (nth - 1) * 7
    return datetime(year, month, day)


def _get_next_fomc_dates() -> List[datetime]:
    """直近のFOMC日程（参考値・概算）"""
    # 概ね6週ごと、年8回
    base = datetime(2026, 1, 28)
    dates = []
    for i in range(8):
        d = base + timedelta(weeks=6 * i)
        dates.append(d)
    return dates


def _get_next_boj_dates() -> List[datetime]:
    """日銀会合の概算日程"""
    base = datetime(2026, 1, 23)
    dates = []
    for i in range(8):
        d = base + timedelta(weeks=6 * i)
        dates.append(d)
    return dates


def _get_next_ecb_dates() -> List[datetime]:
    base = datetime(2026, 1, 22)
    dates = []
    for i in range(8):
        d = base + timedelta(weeks=6 * i)
        dates.append(d)
    return dates


def _calc_next_event_date(event: dict, after: datetime) -> Optional[datetime]:
    """イベントの次回開催予定日時を計算"""
    rule = event["rule"]
    jst_time_str = event["jst_time"]
    try:
        h, m = jst_time_str.split(":")
        h, m = int(h), int(m)
    except Exception:
        h, m = 22, 0

    if rule == "nth_weekday":
        nth, wd = event["nth"], event["weekday"]
        for offset in range(0, 12):
            target_month = after.month + offset
            year = after.year + (target_month - 1) // 12
            month = ((target_month - 1) % 12) + 1
            try:
                d = _nth_weekday_of_month(year, month, nth, wd)
                d = d.replace(hour=h, minute=m)
                if d > after:
                    return d
            except Exception:
                continue

    elif rule == "fixed_day":
        day = event["day"]
        for offset in range(0, 6):
            target_month = after.month + offset
            year = after.year + (target_month - 1) // 12
            month = ((target_month - 1) % 12) + 1
            try:
                d = datetime(year, month, min(day, calendar.monthrange(year, month)[1]),
                             h, m)
                if d > after:
                    return d
            except Exception:
                continue

    elif rule == "fomc_meeting":
        for d in _get_next_fomc_dates():
            d = d.replace(hour=h, minute=m)
            if d > after:
                return d

    elif rule == "boj_meeting":
        for d in _get_next_boj_dates():
            d = d.replace(hour=h, minute=m)
            if d > after:
                return d

    elif rule == "ecb_meeting":
        for d in _get_next_ecb_dates():
            d = d.replace(hour=h, minute=m)
            if d > after:
                return d

    return None


# ════════════════════════════════════════════════
#  公開API
# ════════════════════════════════════════════════

def get_upcoming_events(days_ahead: int = 30) -> List[dict]:
    """
    今後N日間に発生する経済指標を時系列でリスト化

    各イベントに以下を付与：
    - scheduled_at: 開催予定日時
    - impact_window_end: 高ボラ終了予測時刻
    - trend_window_end: トレンド継続終了予測時刻
    - hours_until: 開始までの残り時間（時）
    """
    now = datetime.now()
    cutoff = now + timedelta(days=days_ahead)
    events = []

    for ev in ECONOMIC_EVENTS:
        nxt = _calc_next_event_date(ev, now)
        if nxt is None or nxt > cutoff:
            continue

        impact_end = nxt + timedelta(hours=ev["high_volatility_hours"])
        trend_end = nxt + timedelta(hours=ev["trend_keep_hours"])
        hours_until = (nxt - now).total_seconds() / 3600

        events.append({
            **ev,
            "scheduled_at": nxt,
            "impact_window_end": impact_end,
            "trend_window_end": trend_end,
            "hours_until": round(hours_until, 1),
        })

    events.sort(key=lambda e: e["scheduled_at"])
    return events


def get_critical_events_today_tomorrow() -> List[dict]:
    """今日・明日の重要イベント（impact_level >= 4）"""
    events = get_upcoming_events(days_ahead=2)
    return [e for e in events if e["impact_level"] >= 4]


def get_event_calendar_text(days: int = 14) -> str:
    """テキスト形式のカレンダー（デバッグ用）"""
    events = get_upcoming_events(days)
    lines = []
    for e in events:
        lines.append(
            f"{e['scheduled_at'].strftime('%m/%d (%a) %H:%M')}　"
            f"[{e['country']}] {e['name']} "
            f"(影響★{e['impact_level']} / 高ボラ{e['high_volatility_hours']}h / トレンド{e['trend_keep_hours']}h)"
        )
    return "\n".join(lines)


def estimate_keep_period_for_current_trend(direction: str = "weak") -> dict:
    """
    現在のトレンドが「いつまでキープできるか」推定

    direction: "weak" (円安継続中) / "strong" (円高継続中)

    今後の重要イベントから、トレンドが転換されうるタイミングを抽出
    """
    events = get_upcoming_events(days_ahead=14)
    high_impact = [e for e in events if e["impact_level"] >= 4]

    # 次の高インパクト イベント = 次の転換候補
    next_pivot = high_impact[0] if high_impact else None

    if next_pivot is None:
        return {
            "keep_estimate_hours": 168,
            "next_pivot": None,
            "message": "今後2週間は大きなイベントなし。テクニカル要因のみで推移",
            "high_impact_events": [],
        }

    hours_to_next = next_pivot["hours_until"]

    if hours_to_next < 6:
        urgency = "🔴 直近"
    elif hours_to_next < 24:
        urgency = "🟡 24時間以内"
    elif hours_to_next < 72:
        urgency = "🟢 3日以内"
    else:
        urgency = "🔵 余裕あり"

    return {
        "keep_estimate_hours": round(hours_to_next, 1),
        "keep_estimate_days": round(hours_to_next / 24, 1),
        "next_pivot": next_pivot,
        "urgency": urgency,
        "message": (
            f"次の転換候補は <b>{next_pivot['scheduled_at'].strftime('%m/%d %H:%M')}</b> の"
            f" <b>{next_pivot['name']}</b>。"
            f"あと <b>{hours_to_next:.0f}時間</b> はテクニカル主導の可能性"
        ),
        "high_impact_events": high_impact[:5],
    }
