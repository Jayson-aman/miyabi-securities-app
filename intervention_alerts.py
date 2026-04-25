"""
要人介入 注意ポイント表

各要人・機関の介入パターンを「警戒すべき価格水準・時間帯・キーワード」とともに表形式で提供
"""

INTERVENTION_TABLE = [
    # ─── 日本 ───
    {
        "category": "🏛 日本財務省",
        "person": "財務官（神田氏／財務省国際局長）",
        "country": "🇯🇵",
        "watch_levels_usdjpy": "152円〜155円",
        "warning_keywords": "「過度な変動」「あらゆる手段」「断固たる措置」「投機的な動き」「為替介入を否定しない」",
        "primary_time_jst": "07:00 - 22:00 (随時)",
        "peak_intervention_time": "08:30 / 10:00 / 17:00 / 22:00 (NYクローズ前)",
        "expected_move": "口先介入：30分で 0.5-1円　／実弾介入：1時間で 3-5円急落",
        "duration": "効果は 24-48時間。その後再度円安に戻りやすい",
        "history": "2022年9月22日(145.90円)、10月21日(151.95円)、2024年4月29日(160.20円)、5月1日(157.55円)",
        "trigger_priority": "🔥🔥🔥",
    },
    {
        "category": "🏛 日本財務省",
        "person": "財務大臣",
        "country": "🇯🇵",
        "watch_levels_usdjpy": "150円超",
        "warning_keywords": "「行き過ぎた動き」「適切に対応」「投機的」",
        "primary_time_jst": "閣議後会見 09:00-10:30 / 国会答弁 13:00-17:00",
        "peak_intervention_time": "閣議後会見直後",
        "expected_move": "口先介入のみ：0.3-0.8円",
        "duration": "数時間-1日",
        "history": "週2回の閣議後会見が定例",
        "trigger_priority": "🔥🔥",
    },
    {
        "category": "🏛 日本政府",
        "person": "官房長官・内閣総理大臣",
        "country": "🇯🇵",
        "watch_levels_usdjpy": "心理的節目（150/155/160円）",
        "warning_keywords": "「注視」「適切な対応」「市場動向を高い緊張感を持って」",
        "primary_time_jst": "11:00 / 16:00 (官房長官定例会見)",
        "peak_intervention_time": "16:00 会見直後",
        "expected_move": "0.2-0.5円",
        "duration": "数時間",
        "history": "毎日2回の定例記者会見あり",
        "trigger_priority": "🔥",
    },
    {
        "category": "🏦 日本銀行",
        "person": "植田 和男 総裁",
        "country": "🇯🇵",
        "watch_levels_usdjpy": "—（金利政策で円高方向に作用）",
        "warning_keywords": "「正常化」「利上げ」「YCC修正」「物価目標達成」「賃上げ加速」",
        "primary_time_jst": "金融政策決定会合 11:30-12:00 (発表) / 15:30 (会見)",
        "peak_intervention_time": "会見の Q&A 後半 (16:00-17:00)",
        "expected_move": "サプライズ利上げ：1日 2-4円の円高　／会見トーン変化：1-2円",
        "duration": "数日-2週間",
        "history": "2024年3月マイナス金利解除(151円→149円)、2024年7月利上げ(155円→145円)",
        "trigger_priority": "🔥🔥🔥",
    },
    {
        "category": "🏦 日本銀行",
        "person": "副総裁・審議委員",
        "country": "🇯🇵",
        "watch_levels_usdjpy": "—",
        "warning_keywords": "「タカ派」「ハト派」発言の偏り",
        "primary_time_jst": "講演 10:30-15:00 / 記者会見 16:30-",
        "peak_intervention_time": "発言途中・要旨配信時",
        "expected_move": "0.5-1.5円",
        "duration": "1-3日",
        "history": "週1-2回の講演・会見",
        "trigger_priority": "🔥🔥",
    },

    # ─── 米国 ───
    {
        "category": "🏦 FRB（米中銀）",
        "person": "パウエル FRB議長",
        "country": "🇺🇸",
        "watch_levels_usdjpy": "—（金利方針が直接影響）",
        "warning_keywords": "「忍耐強く」「データ次第」「インフレ目標」「利下げの時期は近い／遠い」",
        "primary_time_jst": "FOMC会見 03:30-04:30 / 議会証言 23:00-翌02:00 / ジャクソンホール 23:00頃",
        "peak_intervention_time": "FOMC会見 Q&A 04:00-04:30",
        "expected_move": "ハト派サプライズ：1時間で 2-3円円高　／タカ派：2-3円円安",
        "duration": "1週間〜1ヶ月",
        "history": "毎FOMC後の会見が最重要。ジャクソンホール(8月下旬)も同等",
        "trigger_priority": "🔥🔥🔥",
    },
    {
        "category": "🏦 FRB高官",
        "person": "ウォラー / ウィリアムズ / ボウマン / クグラー他",
        "country": "🇺🇸",
        "watch_levels_usdjpy": "—",
        "warning_keywords": "「タカ派」（インフレ警戒）／「ハト派」（利下げ示唆）",
        "primary_time_jst": "23:00 - 翌03:00",
        "peak_intervention_time": "発言要旨配信時 (Bloomberg/Reuters速報)",
        "expected_move": "0.3-1.0円",
        "duration": "数時間-1日",
        "history": "週数回の発言。タカ派・ハト派ローテーション",
        "trigger_priority": "🔥",
    },
    {
        "category": "🏛 米財務省",
        "person": "イエレン財務長官 / 財務副長官",
        "country": "🇺🇸",
        "watch_levels_usdjpy": "急激な円安時の協調観測",
        "warning_keywords": "「為替介入を支持」「日米連携」「過度な変動」",
        "primary_time_jst": "G7/G20財務相会合時 / 議会証言",
        "peak_intervention_time": "声明発表時",
        "expected_move": "1-3円（協調介入示唆時）",
        "duration": "1-3日",
        "history": "2024年4月にG20で日本の介入容認示唆",
        "trigger_priority": "🔥🔥",
    },

    # ─── 欧州 ───
    {
        "category": "🏦 ECB（欧州中銀）",
        "person": "ラガルド ECB総裁",
        "country": "🇪🇺",
        "watch_levels_usdjpy": "EUR/JPY経由でドル円に波及",
        "warning_keywords": "「利下げの可能性」「インフレ圧力低下」",
        "primary_time_jst": "ECB理事会会見 21:45-22:30",
        "peak_intervention_time": "会見 Q&A 22:00-22:30",
        "expected_move": "EUR/JPY: 1-2円　ドル円: 0.5-1円波及",
        "duration": "数日",
        "history": "月1回の理事会会見",
        "trigger_priority": "🔥🔥",
    },

    # ─── 中国 ───
    {
        "category": "🏦 中国人民銀行",
        "person": "PBOC（中国人民銀行）",
        "country": "🇨🇳",
        "watch_levels_usdjpy": "USD/CNH連動で円安方向に影響",
        "warning_keywords": "「人民元基準値」「中間値」「LPR金利」",
        "primary_time_jst": "中間値発表 10:15 / LPR発表 10:15 (毎月20日前後)",
        "peak_intervention_time": "中間値発表時",
        "expected_move": "ドル円 0.3-0.8円波及",
        "duration": "数時間-1日",
        "history": "中間値の方向で人民元相場をコントロール",
        "trigger_priority": "🔥",
    },
]


# 介入 警戒水準テーブル
INTERVENTION_LEVELS_DETAIL = [
    {
        "pair": "USD/JPY",
        "psychological_resistance": "150.00 / 155.00 / 160.00 円",
        "verbal_intervention_zone": "150-152 円",
        "actual_intervention_zone": "155-160 円",
        "max_historical": "161.95 円 (2024年7月)",
        "post_intervention_pullback": "通常 3-5円 / 最大 10円 (2024年5月実例)",
    },
    {
        "pair": "EUR/JPY",
        "psychological_resistance": "165 / 170 円",
        "verbal_intervention_zone": "165-168 円",
        "actual_intervention_zone": "170-175 円",
        "max_historical": "175.43 円 (2024年7月)",
        "post_intervention_pullback": "5-8円",
    },
    {
        "pair": "GBP/JPY",
        "psychological_resistance": "190 / 200 円",
        "verbal_intervention_zone": "195-200 円",
        "actual_intervention_zone": "200円超で警戒",
        "max_historical": "208.10 円 (2024年7月)",
        "post_intervention_pullback": "5-10円",
    },
]


# 時間帯別 介入発生確率マップ
INTERVENTION_TIME_PROBABILITY = [
    {"time_jst": "07:00-08:00", "label": "オセアニア寄り付き", "probability": "中", "reason": "薄商いを狙ったステルス介入"},
    {"time_jst": "08:30-09:30", "label": "東京寄り前", "probability": "高", "reason": "閣議後会見・要人発言と連動"},
    {"time_jst": "09:55-10:00", "label": "東京仲値", "probability": "中", "reason": "実需フローと組み合わせ"},
    {"time_jst": "10:30-11:30", "label": "東京日中", "probability": "低", "reason": "通常時間帯"},
    {"time_jst": "13:00-15:00", "label": "東京午後", "probability": "中", "reason": "国会答弁時"},
    {"time_jst": "15:00-16:00", "label": "東京クローズ", "probability": "中", "reason": "ポジション調整局面"},
    {"time_jst": "16:00-17:00", "label": "ロンドン寄り", "probability": "高", "reason": "欧州勢にインパクト"},
    {"time_jst": "21:30-22:30", "label": "米経済指標", "probability": "極めて高", "reason": "発表後の急変動を抑制"},
    {"time_jst": "22:30-24:00", "label": "NY寄り後", "probability": "高", "reason": "米市場参加者にメッセージ"},
    {"time_jst": "00:00-02:00", "label": "ロンドン・フィキシング後", "probability": "中", "reason": "大口決済後の薄商い"},
    {"time_jst": "03:00-05:00", "label": "FOMC前後", "probability": "極めて高", "reason": "FOMC声明・会見時"},
    {"time_jst": "05:00-07:00", "label": "深夜薄商い", "probability": "高", "reason": "流動性低下時の効果大（覆面介入）"},
]


def get_intervention_table() -> list:
    return INTERVENTION_TABLE


def get_intervention_levels_table() -> list:
    return INTERVENTION_LEVELS_DETAIL


def get_intervention_time_table() -> list:
    return INTERVENTION_TIME_PROBABILITY
