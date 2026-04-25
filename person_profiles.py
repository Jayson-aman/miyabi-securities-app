"""
要人プロファイル・側近マッピング モジュール
要人の性格・意思決定の癖・側近の影響力を分析し、発言の裏を読む
"""

from typing import Optional


# ════════════════════════════════════════════════
#  要人 詳細プロファイル
# ════════════════════════════════════════════════

PROFILES = {
    "powell": {
        "name": "ジェローム・パウエル",
        "title": "FRB議長",
        "country": "USD",
        "photo_emoji": "🇺🇸",

        # 性格・意思決定の傾向
        "personality": {
            "type": "慎重な合意形成型",
            "traits": [
                "法律家出身で経済学者ではない → データの解釈を側近に依存しやすい",
                "リスク回避型 → 大胆な決定を避け、段階的に動く傾向",
                "市場との対話を重視 → サプライズを嫌い、事前にシグナルを出す",
                "政治的圧力に敏感だが、独立性を強く意識して逆に動くこともある",
                "記者会見で言葉を慎重に選ぶが、アドリブで本音が漏れることがある",
            ],
            "decision_style": "コンセンサス重視。FOMC内の多数派に寄り添う傾向が強い",
            "stress_behavior": "圧力を受けると「data dependent」を繰り返し時間を稼ぐ",
            "bluff_tendency": "中（ハト派トーンで語りつつタカ派行動を取るパターンあり）",
        },

        # 側近・周辺人物
        "inner_circle": [
            {
                "name": "ジョン・ウィリアムズ",
                "title": "NY連銀総裁（FOMC副議長）",
                "influence": "極めて高い",
                "stance": "パウエルと歩調を合わせるが、やや慎重寄り",
                "watch": "ウィリアムズの発言はパウエルの考えを先取りしていることが多い",
            },
            {
                "name": "クリストファー・ウォーラー",
                "title": "FRB理事",
                "influence": "高い",
                "stance": "タカ派寄り。インフレ抑制を最優先",
                "watch": "ウォーラーが軟化した時はFRB全体のハト派転換のサイン",
            },
            {
                "name": "リサ・クック",
                "title": "FRB理事",
                "influence": "中程度",
                "stance": "ハト派寄り。雇用市場を重視",
                "watch": "クックがタカ派発言をした時は引き締め強化の地ならし",
            },
            {
                "name": "フィリップ・ジェファーソン",
                "title": "FRB副議長",
                "influence": "高い",
                "stance": "中立〜ややハト派",
                "watch": "パウエルの右腕。ジェファーソンの講演はFRBの方向性を示唆",
            },
        ],

        # 発言パターン分析
        "speech_patterns": {
            "本気のタカ派": [
                "「インフレは受け入れられない」と感情的な強調がある時",
                "具体的な数字や時期に言及した時",
                "「必要なら追加措置を取る」と明言した時",
            ],
            "フェイントのタカ派": [
                "「データ次第」を何度も繰り返す時",
                "「ある時点で」「いずれ」など時期を曖昧にする時",
                "質疑応答で同じ質問に違うニュアンスで答える時",
            ],
            "本気のハト派": [
                "「労働市場の冷え込みを注視」と雇用に言及する時",
                "「リスクはバランスしている」から「下方リスク」に表現が変わった時",
            ],
            "フェイントのハト派": [
                "「緩和的な姿勢」と言いつつ具体的な時期を示さない時",
                "「慎重に」「段階的に」と付け加えて行動を遅らせる時",
            ],
        },
    },

    "ueda": {
        "name": "植田和男",
        "title": "日銀総裁",
        "country": "JPY",
        "photo_emoji": "🇯🇵",

        "personality": {
            "type": "学者型・超慎重派",
            "traits": [
                "経済学者出身 → 理論的だがマーケットの心理を読むのが苦手な面がある",
                "極めて慎重 → 明確な結論を避け、多角的に論じる傾向",
                "前任の黒田総裁と真逆のスタイル → サプライズを極力避ける",
                "記者会見で長い前置きをした後に核心部分を薄める癖がある",
                "学術用語を多用して一般人には真意が伝わりにくい",
            ],
            "decision_style": "データ重視の学者型。理論的な裏付けがないと動かない",
            "stress_behavior": "曖昧な二重否定や条件付き表現が増える",
            "bluff_tendency": "高（「緩和を続ける」と言いつつ出口を模索する傾向が強い）",
        },

        "inner_circle": [
            {
                "name": "氷見野良三",
                "title": "日銀副総裁",
                "influence": "高い",
                "stance": "金融システム安定重視。正常化にやや前向き",
                "watch": "氷見野の講演で正常化に言及した時は植田の布石の可能性",
            },
            {
                "name": "内田眞一",
                "title": "日銀副総裁",
                "influence": "極めて高い",
                "stance": "実務派。市場との対話を重視",
                "watch": "内田の発言はオペレーション面の本音。市場急変時に火消し役を担う",
            },
            {
                "name": "中村豊明",
                "title": "日銀審議委員",
                "influence": "中程度",
                "stance": "ハト派。利上げに慎重",
                "watch": "中村が賛成に回った時は全会一致の演出 → 既定路線の証",
            },
            {
                "name": "田村直樹",
                "title": "日銀審議委員",
                "influence": "中程度",
                "stance": "タカ派寄り。正常化推進派",
                "watch": "田村の発言が先鋭化する時は利上げが近い可能性",
            },
        ],

        "speech_patterns": {
            "本気のタカ派（正常化）": [
                "「物価目標の実現が見通せる」と断言に近い表現をした時",
                "「副作用」「金融仲介機能」に繰り返し言及する時",
                "「適切なタイミングで」が「近い将来」に変わった時",
            ],
            "フェイントのタカ派": [
                "「出口の議論は時期尚早」と言いつつ具体的な条件を並べる時",
                "「仮に」「もし」を多用して正常化シナリオを語る時 → 市場の反応テスト",
            ],
            "本気のハト派（緩和継続）": [
                "「不確実性が高い」を強く繰り返す時",
                "海外リスクに多くの時間を割く時",
            ],
            "フェイントのハト派": [
                "「粘り強く緩和を継続」と言いつつYCC（金利操作）の柔軟化に言及する時",
                "結論は緩和維持だが、審議委員の「異なる意見」を長く紹介する時",
            ],
        },
    },

    "lagarde": {
        "name": "クリスティーヌ・ラガルド",
        "title": "ECB総裁",
        "country": "EUR",
        "photo_emoji": "🇪🇺",

        "personality": {
            "type": "政治家型・カリスマ派",
            "traits": [
                "IMF出身の政治家 → 経済理論より政治的判断を優先する傾向",
                "カリスマ性が高く、断定的な表現を好む",
                "しかし断定した方向と逆に動くことが多い（最大の特徴）",
                "プレゼンテーション能力が高く、市場をコントロールしようとする意識が強い",
                "フランス的なレトリック（美辞麗句の裏に本音を隠す）",
            ],
            "decision_style": "トップダウン型。自分のビジョンに理事会を引っ張る",
            "stress_behavior": "「私を信じて」的な感情に訴える表現が増える",
            "bluff_tendency": "極めて高い（「利上げは当面ない」→ 翌月利上げ の前科あり）",
        },

        "inner_circle": [
            {
                "name": "ルイス・デギンドス",
                "title": "ECB副総裁",
                "influence": "高い",
                "stance": "ラガルドを補佐しつつやや慎重",
                "watch": "デギンドスが楽観的になった時は、ECBの方向転換が近い",
            },
            {
                "name": "イザベル・シュナーベル",
                "title": "ECB理事",
                "influence": "極めて高い",
                "stance": "タカ派の理論的支柱。インフレに厳格",
                "watch": "シュナーベルの論文や講演はECBの理論的方向性を先取り",
            },
            {
                "name": "フィリップ・レーン",
                "title": "ECBチーフエコノミスト",
                "influence": "極めて高い",
                "stance": "データ重視の中立派",
                "watch": "レーンの経済見通し修正はECBの次の一手を直接示す",
            },
        ],

        "speech_patterns": {
            "本気のタカ派": [
                "具体的な利上げ幅に言及した時（珍しいので本気度が高い）",
                "「インフレは受け入れられない」と感情を込めた時",
            ],
            "フェイントのタカ派": [
                "「断固たる姿勢」と言いつつ時期を明示しない時（常套手段）",
                "シュナーベルに先にタカ派発言させてから自分は中立的にまとめる時",
            ],
            "本気のハト派": [
                "「景気下振れリスク」を冒頭で強調した時",
                "南欧経済への配慮を繰り返す時",
            ],
            "フェイントのハト派": [
                "「段階的に」「柔軟に」と言いつつ実際は大幅利上げした前歴あり",
            ],
        },
    },

    "trump": {
        "name": "ドナルド・トランプ",
        "title": "米大統領",
        "country": "USD",
        "photo_emoji": "🇺🇸",

        "personality": {
            "type": "ディールメーカー型・攪乱者",
            "traits": [
                "不動産ビジネス出身 → 全てを交渉のカードとして使う",
                "極端な発言→譲歩→ディール成立 のパターンを繰り返す",
                "SNS（Truth Social等）での突発的発言で市場を意図的に動かす",
                "FRBへの利下げ圧力を公然とかける（金融政策の独立性を軽視）",
                "関税を交渉ツールとして多用。実際に全て実行するとは限らない",
            ],
            "decision_style": "直感型・ディール型。アドバイザーの意見より自分の勘を信じる",
            "stress_behavior": "攻撃的な発言が増え、スケープゴートを作る",
            "bluff_tendency": "極めて高い（関税・制裁の脅しは交渉カード）",
        },

        "inner_circle": [
            {
                "name": "スコット・ベッセント",
                "title": "財務長官",
                "influence": "極めて高い",
                "stance": "ウォール街出身。市場フレンドリーだがトランプに忠実",
                "watch": "ベッセントがドル安容認発言をした時は政権の為替政策転換",
            },
            {
                "name": "ピーター・ナバロ",
                "title": "通商政策顧問",
                "influence": "高い（通商面）",
                "stance": "超強硬派。中国との対立を推進",
                "watch": "ナバロが表に出てくる時は関税強化・貿易戦争激化の前兆",
            },
            {
                "name": "イーロン・マスク",
                "title": "DOGE（政府効率化部門）",
                "influence": "高い（財政面）",
                "stance": "政府支出削減推進。テック企業寄り",
                "watch": "マスクの政策関与発言はテック株・ドルに影響",
            },
            {
                "name": "ジェイミー・ダイモン",
                "title": "JPモルガンCEO（非公式アドバイザー）",
                "influence": "中程度（非公式）",
                "stance": "ウォール街の代弁者。金融規制緩和推進",
                "watch": "ダイモンの経済見通しはトランプ政権の経済認識に影響",
            },
        ],

        "speech_patterns": {
            "本気の強硬策": [
                "大統領令に署名した時（発言ではなく行動）",
                "具体的な国名・品目・税率を明示した時",
                "議会と連携して法案を進めている時",
            ],
            "フェイントの強硬策": [
                "SNSで突発的に脅した時（交渉カードの可能性大）",
                "「最大の」「史上最悪の」など最上級表現を連発する時 → ディール交渉中",
                "相手国を名指しで批判した直後に「素晴らしい関係」と言う時",
            ],
            "本気の融和策": [
                "首脳会談で具体的な合意文書に署名した時",
                "関税の段階的撤廃スケジュールを発表した時",
            ],
            "フェイントの融和策": [
                "「検討中」「良い方向に進んでいる」と曖昧に語る時 → 交渉が難航中",
                "「ディールは近い」を繰り返す時 → 実際はまだ遠い",
            ],
        },
    },
}


def get_profile(person_key: str) -> Optional[dict]:
    """要人のプロファイルを取得"""
    return PROFILES.get(person_key)


def get_all_tracked_names() -> dict:
    """全ての追跡対象者名（要人+側近）とキーワードマッピングを返す"""
    name_map = {}

    for key, profile in PROFILES.items():
        name_map[key] = {
            "name": profile["name"],
            "role": "要人",
            "title": profile["title"],
        }
        for person in profile.get("inner_circle", []):
            name_lower = person["name"].lower().split()[-1]
            name_map[name_lower] = {
                "name": person["name"],
                "role": "側近",
                "title": person["title"],
                "parent": profile["name"],
                "parent_key": key,
                "influence": person["influence"],
                "stance": person["stance"],
                "watch": person["watch"],
            }

    return name_map


def analyze_person_context(text: str) -> dict:
    """
    テキストに登場する要人・側近を特定し、性格・側近情報から予測を立てる

    Returns:
        {
            "detected_persons": [検出された人物リスト],
            "profile_insights": [プロファイルに基づく洞察],
            "inner_circle_alerts": [側近発言からの先読みアラート],
            "prediction_adjustments": [予測の調整理由],
        }
    """
    text_lower = text.lower()
    detected = []
    insights = []
    circle_alerts = []
    adjustments = []

    tracked = get_all_tracked_names()

    for keyword, info in tracked.items():
        if keyword in text_lower:
            detected.append(info)

            if info["role"] == "要人":
                profile = PROFILES.get(keyword)
                if profile:
                    p = profile["personality"]
                    insights.append(
                        f"👤 {info['name']}（{p['type']}）: {p['decision_style']}"
                    )
                    insights.append(
                        f"   ブラフ傾向: {p['bluff_tendency']}"
                    )

                    # 発言パターンとの照合
                    patterns = profile.get("speech_patterns", {})
                    for pattern_type, indicators in patterns.items():
                        for indicator in indicators:
                            check_words = [w.lower() for w in indicator.split() if len(w) > 4]
                            matches = sum(1 for w in check_words if w in text_lower)
                            if matches >= 2:
                                insights.append(
                                    f"   📎 パターン一致「{pattern_type}」: {indicator}"
                                )

            elif info["role"] == "側近":
                parent_profile = PROFILES.get(info.get("parent_key", ""))
                circle_alerts.append(
                    f"🔍 側近検知: {info['name']}（{info['title']}）"
                    f"　影響力: {info['influence']}　スタンス: {info['stance']}"
                )
                circle_alerts.append(
                    f"   → 注目ポイント: {info['watch']}"
                )

                if parent_profile:
                    adjustments.append(
                        f"💡 {info['name']}は{info['parent']}の側近。"
                        f"この発言は{info['parent']}の方針を先取りしている可能性がある"
                    )

    return {
        "detected_persons": detected,
        "profile_insights": insights,
        "inner_circle_alerts": circle_alerts,
        "prediction_adjustments": adjustments,
    }


def get_profile_summary_for_display(person_key: str) -> Optional[dict]:
    """画面表示用にプロファイル情報を整形"""
    profile = PROFILES.get(person_key)
    if not profile:
        return None

    p = profile["personality"]
    return {
        "name": profile["name"],
        "title": profile["title"],
        "emoji": profile["photo_emoji"],
        "type": p["type"],
        "traits": p["traits"],
        "decision_style": p["decision_style"],
        "stress_behavior": p["stress_behavior"],
        "bluff_tendency": p["bluff_tendency"],
        "inner_circle": profile.get("inner_circle", []),
        "speech_patterns": profile.get("speech_patterns", {}),
    }
