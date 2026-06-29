"""
ローソク足の読み方ガイド — 表形式の解説と利確タイミングのヒント

検討・学習用。投資助言ではありません。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from candlestick_patterns import _candle_metrics, _is_top_zone, _is_bottom_zone, _is_uptrend_zone, _is_downtrend_zone


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """data_fetcher 日本語列 → candlestick_patterns 用英語列"""
    if df is None or df.empty:
        return df
    if "Open" in df.columns:
        return df
    mapping = {"始値": "Open", "高値": "High", "安値": "Low", "終値": "Close", "出来高": "Volume"}
    out = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    return out


# ── 静的リファレンス表 ──────────────────────────────

BASIC_PARTS = pd.DataFrame([
    {"部位": "始値（Open）", "意味": "その足の最初の取引価格", "見方": "足の左端（実体の端）"},
    {"部位": "終値（Close）", "意味": "その足の最後の取引価格", "見方": "足の右端（実体の端）"},
    {"部位": "高値（High）", "意味": "その足の中で最も高い価格", "見方": "上ヒゲの先端"},
    {"部位": "安値（Low）", "意味": "その足の中で最も低い価格", "見方": "下ヒゲの先端"},
    {"部位": "実体", "意味": "始値と終値の差（白/緑＝陽線、黒/赤＝陰線）", "見方": "太い部分。勢いの強さを示す"},
    {"部位": "上ヒゲ", "意味": "高値 − max(始値, 終値)", "見方": "長い＝上値で売りに遭った"},
    {"部位": "下ヒゲ", "意味": "min(始値, 終値) − 安値", "見方": "長い＝下値で買い支えが入った"},
])

CANDLE_TYPES = pd.DataFrame([
    {"形": "🟩 大陽線", "条件": "終値≫始値、実体が長い", "意味": "買い優勢・上昇の勢い", "注意": "天井圏の大陽線は「飛びつき」注意"},
    {"形": "🟥 大陰線", "条件": "始値≫終値、実体が長い", "意味": "売り優勢・下落の勢い", "注意": "底値圏では「売り尽くし」反発の可能性"},
    {"形": "➖ 十字線", "条件": "始値≒終値、実体が極小", "意味": "方向感なし・転換の兆し", "注意": "天井/底値圏で出ると特に重要"},
    {"形": "🔨 ハンマー", "条件": "小実体＋長い下ヒゲ（底付近）", "意味": "下値で買い支え・反発の初動", "注意": "翌足で陽線確認してからエントリー"},
    {"形": "🪢 首吊り線", "条件": "小実体＋長い下ヒゲ（天井付近）", "意味": "上昇失速・反落の兆し", "注意": "ロング保有なら利確検討"},
    {"形": "☁ 上影線（トウ引き）", "条件": "長い上ヒゲ＋小実体", "意味": "高値で売り圧力", "注意": "利確・部分決済のサイン"},
    {"形": "🌊 波高い線", "条件": "上下ヒゲとも長い", "意味": "相場の迷い・ボラ拡大", "注意": "新規より様子見・利確優先"},
    {"形": "🤰 はらみ線", "条件": "前足の実体内に小さく収まる", "意味": "勢いの減退・転換の前兆", "注意": "トレンド継続中なら利確早め"},
])

ENGULFING_PINBAR = pd.DataFrame([
    {
        "パターン": "🤝 陽の包み線",
        "英名": "Bullish Engulfing",
        "条件": "前日陰線 → 当日陽線が前日実体を完全に包む",
        "場所": "底値圏・押し目",
        "意味": "売り終了 → 買い優勢",
        "利確ヒント": "目標=包み足実体の1.5〜2倍 / 損切=包み足安値下",
    },
    {
        "パターン": "🫂 陰の包み線",
        "英名": "Bearish Engulfing",
        "条件": "前日陽線 → 当日陰線が前日実体を完全に包む",
        "場所": "天井圏・戻り高値",
        "意味": "買い終了 → 売り優勢",
        "利確ヒント": "ロングは即〜部分利確 / ショート目標=実体1.5〜2倍",
    },
    {
        "パターン": "📌 強気ピンバー",
        "英名": "Bullish Pinbar",
        "条件": "小実体＋下ヒゲ≥実体2倍＋上ヒゲ短い",
        "場所": "底値圏・支持線",
        "意味": "下値で買い支え・反発",
        "利確ヒント": "翌足陽線確認後エントリー / 損切=ピンバー安値",
    },
    {
        "パターン": "⭐ 弱気ピンバー",
        "英名": "Bearish Pinbar / 流れ星",
        "条件": "小実体＋上ヒゲ≥実体2倍＋下ヒゲ短い",
        "場所": "天井圏・抵抗線",
        "意味": "高値で拒否・反落",
        "利確ヒント": "ロングは終値付近で利確 / ショート損切=高値上",
    },
    {
        "パターン": "🫶 陰の両つつみ",
        "英名": "Double Bullish Engulfing",
        "条件": "陰線2本を1本の大陽線が同時に包む",
        "場所": "底値圏",
        "意味": "強力な買い転換",
        "利確ヒント": "大陽線実体の2倍を目標",
    },
    {
        "パターン": "🫂 最後の抱き線",
        "英名": "Last Engulfing Top",
        "条件": "陰→陽包み→翌陰で騙し確定",
        "場所": "天井圏",
        "意味": "買い誘いの失敗",
        "利確ヒント": "ロング全利確 / 戻り売り検討",
    },
])

# ── その他の読み方（表） ──────────────────────────────

HARAMI_PATTERNS = pd.DataFrame([
    {"パターン": "🤰 陰のはらみ（強気）", "条件": "大陰線の実体内に小陽線", "場所": "底値圏", "意味": "売り圧力の減退", "アクション": "反転初動・損切=大陰線安値下"},
    {"パターン": "🟥 陽の陰はらみ", "条件": "大陽線の実体内に小陰線", "場所": "天井圏", "意味": "買い失速・反転の兆し", "アクション": "ロング部分利確"},
    {"パターン": "🟩 陽の陽はらみ", "条件": "大陽線の実体内に小陽線", "場所": "天井圏", "意味": "上昇の失速", "アクション": "追い玉禁止・利確検討"},
    {"パターン": "🟦 陰の陰はらみ", "条件": "大陰線の実体内に小陰線", "場所": "底値圏", "意味": "下落の失速", "アクション": "ショート利確・底固め観察"},
])

STAR_THREE_PATTERNS = pd.DataFrame([
    {"パターン": "🌟 宴の明星（Morning Star）", "条件": "大陰→小星→大陽（陰実体半分以上回復）", "場所": "底値圏", "意味": "底打ち反転", "アクション": "3本目確定後ロング / 損切=星の安値"},
    {"パターン": "🌙 宵の明星（Evening Star）", "条件": "大陽→小星→大陰（陽実体半分以上下落）", "場所": "天井圏", "意味": "天井反転", "アクション": "ロング全利確 / ショート損切=星の高値"},
    {"パターン": "🎖 赤三兵", "条件": "3本連続陽線・終値切り上げ", "場所": "底値〜上昇中", "意味": "順調な買い上げ", "アクション": "ロング継続 / 4本目陰線で利確"},
    {"パターン": "🐦 三羽鳥", "条件": "3本連続陰線・終値切り下げ", "場所": "天井〜下降中", "意味": "順調な売り下げ", "アクション": "ロング即利確 / 戻り売り"},
    {"パターン": "🪦 陰線五本", "条件": "5本連続陰線", "場所": "天井圏", "意味": "下降トレンド確定", "アクション": "ロング撤退・戻り売り優勢"},
    {"パターン": "👶 捨て子線", "条件": "ギャップアップ→十字→ギャップダウン", "場所": "天井", "意味": "最強級の反転", "アクション": "ロング全決済"},
])

PIERCING_COVER = pd.DataFrame([
    {"パターン": "⚔️ 切り込み線", "条件": "陰線の翌日、安値割れ始値から陰実体50%以上回復する陽線", "場所": "底値圏", "意味": "売り方の降参", "アクション": "ロング / 損切=陽線安値"},
    {"パターン": "☁ 下げ足の被せ", "条件": "陽線の翌日、高値超え始値から陽実体50%以上食い込む陰線", "場所": "天井圏", "意味": "買い失敗", "アクション": "ロング利確 / ショート検討"},
    {"パターン": "🚀 被せの上抜き", "条件": "被せ線の後、高値を陽線で上抜き", "場所": "任意", "意味": "被せはダマシ→再上昇", "アクション": "ロング / 損切=被せ安値"},
    {"パターン": "🦅 つばめ返し", "条件": "底値圏で前日陰線始値を一気に上抜く長陽線", "場所": "底値圏", "意味": "急反発", "アクション": "ロング / 損切=長陽線安値"},
    {"パターン": "⚔ ツタイ打ち返し", "条件": "ギャップアップ始値→前日終値付近まで長陰線", "場所": "天井圏", "意味": "売り方の反撃", "アクション": "ロング利確"},
])

GAP_WINDOW = pd.DataFrame([
    {"パターン": "🪟 上昇窓", "条件": "前日高値を上回って始まる（ギャップアップ）", "意味": "買い意欲・上昇継続", "注意": "窓埋めでトレンド弱体化"},
    {"パターン": "⬇ 下降窓", "条件": "前日安値を下回って始まる（ギャップダウン）", "意味": "売り意欲・下降継続", "注意": "窓埋めで反発の可能性"},
    {"パターン": "🎏 陽のたすき", "条件": "ギャップアップ後の小陰線がギャップを埋めない", "意味": "上昇トレンド継続", "アクション": "押し目買い"},
    {"パターン": "🎀 下放れタスキ", "条件": "ギャップダウン後の小陽線がギャップを埋めない", "意味": "下降トレンド継続", "アクション": "戻り売り"},
    {"パターン": "🔻 下放れ並び赤", "条件": "ギャップダウン後に弱い陽線2本並び", "意味": "戻り弱く下落継続", "アクション": "ショート維持"},
])

CONTINUATION_PATTERNS = pd.DataFrame([
    {"パターン": "📈 上げ三法", "条件": "大陽→小休止3本（陽実体内）→大陽で上抜け", "意味": "上昇継続確定", "アクション": "ロング追加 / 損切=最初の大陽始値"},
    {"パターン": "📉 下げ三法", "条件": "大陰→小休止3本（陰実体内）→大陰で下抜け", "意味": "下降継続確定", "アクション": "ショート維持"},
    {"パターン": "🧱 三積み上げ", "条件": "3陽線で高値・安値とも切り上げ", "意味": "安定上昇", "アクション": "トレンドフォロー"},
    {"パターン": "🍡 団子天井", "条件": "同じ高値に数本の頭抑え→陰線反落", "意味": "上値抵抗・天井", "アクション": "ロング利確"},
    {"パターン": "😴 下値遊び", "条件": "下落後の狭レンジ持ち合い", "意味": "休憩後のさらなる下落", "アクション": "ショート準備"},
    {"パターン": "👻 バケ線", "条件": "小動き続き→突然の巨大陰線", "意味": "急落開始", "アクション": "ロング撤退"},
])

SEQUENCE_READING = pd.DataFrame([
    {"読み方": "終値の位置", "見方": "足の上1/3で引け＝強い / 下1/3＝弱い", "活用": "同じ陽線でも引け位置で信頼度が変わる"},
    {"読み方": "実体の大きさ", "見方": "前足比150%以上＝勢い増 / 50%以下＝失速", "活用": "包み線・はらみの判断材料"},
    {"読み方": "ヒゲの長さ", "見方": "ヒゲ＝その価格帯は拒否された", "活用": "ピンバー・トウ引き・首吊りの判断"},
    {"読み方": "2本の組み合わせ", "見方": "2本目が1本目を否定するか継続するか", "活用": "包み・はらみ・切込み・被せ"},
    {"読み方": "3本の組み合わせ", "見方": "明星・三兵・三法は3本セット", "活用": "3本目確定後にエントリー"},
    {"読み方": "連続同色", "見方": "3本以上同方向＝トレンド / 5本以上＝過熱", "活用": "5本目以降は利確・反転警戒"},
    {"読み方": "高安の切り上げ", "見方": "高値・安値とも上昇＝上昇トレンド", "活用": "三積み上げ・押し目買い"},
    {"読み方": "出来高（参考）", "見方": "ブレイク時に出来高増＝本物", "活用": "リバーサルハイの信頼度UP"},
])

CONTEXT_READING = pd.DataFrame([
    {"位置": "📈 上昇トレンド中", "陽線の意味": "押し目終了・継続", "陰線の意味": "一時調整（浅ければ買い）", "利確": "高値更新失敗・上ヒゲ長い"},
    {"位置": "📉 下降トレンド中", "陽線の意味": "戻り（売りチャンス）", "陰線の意味": "下落継続", "利確": "ショートは安値付近"},
    {"位置": "🔝 天井圏", "陽線の意味": "飛びつき・警戒", "陰線の意味": "反転初動", "利確": "ロング優先・追い玉禁止"},
    {"位置": "🔻 底値圏", "陽線の意味": "反転初動", "陰線の意味": "売り尽くしの可能性", "利確": "ショート優先・底値掴み注意"},
    {"位置": "↔️ レンジ", "陽線の意味": "レンジ上限付近で売り", "陰線の意味": "レンジ下限付近で買い", "利確": "レンジ反対側"},
    {"位置": "📊 MA乖離大", "意味": "平均回帰しやすい", "アクション": "順張りより利確・逆張り慎重"},
])

# ライブ検出は scan_live_patterns() で candlestick_patterns と連携


def scan_live_patterns(df: pd.DataFrame) -> list[dict]:
    """直近足で成立している代表パターンを検出（candlestick_patterns 連携）"""
    if df is None or len(df) < 30:
        return []
    from candlestick_patterns import (
        detect_bearish_engulfing,
        detect_bearish_pinbar,
        detect_bullish_engulfing,
        detect_bullish_harami,
        detect_dark_cloud_cover,
        detect_falling_three_methods,
        detect_hanging_man,
        detect_kirikomi_sen,
        detect_morning_star,
        detect_rising_three_methods,
        detect_three_black_crows,
        detect_three_white_soldiers,
        detect_tsubame_gaeshi,
        detect_upper_pinbar,
        detect_yang_yin_harami,
    )
    detectors = [
        detect_bullish_engulfing,
        detect_bearish_engulfing,
        detect_upper_pinbar,
        detect_bearish_pinbar,
        detect_morning_star,
        detect_kirikomi_sen,
        detect_dark_cloud_cover,
        detect_tsubame_gaeshi,
        detect_three_white_soldiers,
        detect_three_black_crows,
        detect_bullish_harami,
        detect_yang_yin_harami,
        detect_hanging_man,
        detect_rising_three_methods,
        detect_falling_three_methods,
    ]
    found: list[dict] = []
    for fn in detectors:
        try:
            r = fn(df)
            if r:
                found.append({
                    "pattern": r["pattern"],
                    "verdict": r.get("verdict", ""),
                    "direction": r.get("direction", ""),
                    "confidence": r.get("confidence", 0),
                })
        except Exception:
            continue
    found.sort(key=lambda x: x["confidence"], reverse=True)
    return found


def _evening_star_hint(df: pd.DataFrame) -> Optional[str]:
    """宵の明星（3本・簡易判定）"""
    if len(df) < 30 or not _is_top_zone(df):
        return None
    c1 = _candle_metrics(df.iloc[-3])
    c2 = _candle_metrics(df.iloc[-2])
    c3 = _candle_metrics(df.iloc[-1])
    if not c1["is_bull"] or c1["body_ratio"] < 0.5:
        return None
    if c2["body"] > c1["body"] * 0.45:
        return None
    if not c3["is_bear"] or c3["body_ratio"] < 0.5:
        return None
    mid = (c1["o"] + c1["c"]) / 2
    if c3["c"] > mid:
        return None
    return "🌙 宵の明星型 → 天井圏の3本反転（ロング利確）"


PROFIT_HINTS_LONG = pd.DataFrame([
    {"状況": "📈 上昇トレンド中", "利確の目安": "直近高値・前日高値・抵抗線", "タイミング": "大陽線の翌日に陰線が出たら部分利確", "理由": "高値圏で勢いが止まることが多い"},
    {"状況": "🎯 目標到達", "利確の目安": "RR比1:2以上の目標価格", "タイミング": "目標に到達したら半分利確、残りは損切上げ", "理由": "利益を確保しつつ伸びを取る"},
    {"状況": "☁ 上影線・首吊り", "利確の目安": "その足の終値付近", "タイミング": "上ヒゲが実体の2倍以上で出たら", "理由": "天井圏の売り圧力サイン"},
    {"状況": "🐦 三羽鳥・陰線連続", "利確の目安": "即時〜翌足", "タイミング": "3本連続陰線が出たら全利確", "理由": "トレンド転換の典型"},
    {"状況": "🟩→🟥 陽の陰はらみ", "利確の目安": "はらみ足の安値割れ前", "タイミング": "天井圏で小陰線が大陽線内に収まったら", "理由": "買い失速・反転初動"},
    {"状況": "📊 乖離（RSI/MA）", "利確の目安": "25日線から+3%以上乖離", "タイミング": "短期線から大きく離れた大陽線", "理由": "平均回帰で押し戻されることが多い"},
    {"状況": "🌙 夜間/週末前", "利確の目安": "イベント前の終値", "タイミング": "雇用統計・FOMC・週末前", "理由": "ギャップリスク回避"},
])

PROFIT_HINTS_SHORT = pd.DataFrame([
    {"状況": "📉 下降トレンド中", "利確の目安": "直近安値・前日安値・支持線", "タイミング": "大陰線の翌日に陽線が出たら部分利確", "理由": "底値圏で踏み上げが起きやすい"},
    {"状況": "🎯 目標到達", "利確の目安": "RR比1:2以上の目標価格", "タイミング": "目標到達で半分利確", "理由": "下落も途中で反発しやすい"},
    {"状況": "🔨 ハンマー・下ヒゲ", "利確の目安": "その足の安値付近", "タイミング": "底値圏で長い下ヒゲが出たら", "理由": "売り尽くし・買い戻しの兆し"},
    {"状況": "🎖 赤三兵・陽線連続", "利確の目安": "即時〜翌足", "タイミング": "3本連続陽線で全利確", "理由": "下降トレンドの反転初動"},
    {"状況": "🌟 宴の明星", "利確の目安": "明星3本目の終値付近", "タイミング": "大陰→小星→大陽が完成したら", "理由": "底打ち反転の典型"},
    {"状況": "📊 乖離（RSI/MA）", "利確の目安": "25日線から−3%以上乖離", "タイミング": "短期線から大きく離れた大陰線", "理由": "平均回帰で戻りやすい"},
    {"状況": "🌙 夜間/週末前", "利確の目安": "イベント前の終値", "タイミング": "重要指標・週末前", "理由": "ギャップリスク回避"},
])

WHEN_TO_ACT = pd.DataFrame([
    {"優先度": "🔴 今すぐ", "シグナル": "三羽鳥・陰線五本・捨て子線", "アクション": "ロング全利確 / ショート新規は慎重", "根拠": "強い反転・下降確定"},
    {"優先度": "🟠 早めに", "シグナル": "首吊り線・被せ線・弱気ピンバー・陰の包み線", "アクション": "ロングは50%以上利確", "根拠": "天井圏の売り圧力"},
    {"優先度": "🟡 部分利確", "シグナル": "はらみ線・十字線・団子天井", "アクション": "利益の30〜50%確保", "根拠": "勢い減退・方向感喪失"},
    {"優先度": "🟢 伸ばす", "シグナル": "上げ三法・たすき線・陽の包み線・強気ピンバー", "アクション": "損切りを建値に移動、利確は目標まで", "根拠": "トレンド継続・底値反転"},
    {"優先度": "⏸ 様子見", "シグナル": "レンジ内の小動き", "アクション": "新規せず保有は狭い損切", "根拠": "方向不明・ノイズ"},
])


def _ma_distance_pct(df: pd.DataFrame, period: int = 25) -> Optional[float]:
    if len(df) < period + 1:
        return None
    ma = float(df["Close"].rolling(period).mean().iloc[-1])
    close = float(df["Close"].iloc[-1])
    return (close - ma) / ma * 100


def analyze_live_candle_hint(df: pd.DataFrame, symbol: str = "") -> dict:
    """直近ローソクから利確・損切ヒントを生成"""
    df = _normalize_ohlc(df)
    if df is None or len(df) < 10:
        return {"ok": False, "message": "データ不足（10本以上必要）"}

    last = _candle_metrics(df.iloc[-1])
    prev = _candle_metrics(df.iloc[-2])
    close = last["c"]

    hints: list[str] = []
    actions: list[str] = []
    urgency = "🟢 通常"
    detected: list[dict] = []

    # 足の形
    if last["body_ratio"] < 0.12:
        hints.append("十字線に近い形 → 方向転換の可能性")
        actions.append("新規は控え、保有中なら部分利確を検討")
        urgency = "🟡 注意"

    if last["upper"] > last["body"] * 2 and last["upper"] > last["lower"]:
        hints.append("長い上ヒゲ → 高値で売りに遭った")
        actions.append("ロング: 終値付近で部分〜全利確")
        urgency = "🟠 利確検討"

    if last["lower"] > last["body"] * 2 and last["lower"] > last["upper"]:
        if _is_bottom_zone(df):
            hints.append("底値圏の長い下ヒゲ → 買い支え")
            actions.append("ショート: 利確検討 / ロング: 反発狙いは損切厳守")
        elif _is_top_zone(df):
            hints.append("天井圏の長い下ヒゲ（首吊り線型）→ 反落警戒")
            actions.append("ロング: 早めの利確")
            urgency = "🟠 利確検討"
        else:
            hints.append("長い下ヒゲ → 下値で攻防")
            actions.append("保有方向の逆に動いたら損切")

    if last["is_bull"] and last["body_ratio"] > 0.65:
        hints.append("大陽線 → 買い優勢")
        if _is_top_zone(df):
            actions.append("天井圏の大陽線 → 翌足陰線で利確")
            urgency = "🟡 注意"
        else:
            actions.append("ロング: 損切を前足安値下に / ショート: 損切")

    if last["is_bear"] and last["body_ratio"] > 0.65:
        hints.append("大陰線 → 売り優勢")
        if _is_bottom_zone(df):
            actions.append("底値圏の大陰線 → ショートは利確、ロングは慎重")
            urgency = "🟡 注意"
        else:
            actions.append("ショート: 損切を前足高値上に / ロング: 損切")

    # はらみ
    if prev["is_bull"] and last["body"] < prev["body"] * 0.5:
        if prev["o"] < last["h"] and last["l"] > prev["o"]:
            hints.append("陽のはらみ → 上昇失速")
            actions.append("ロング: 30〜50%利確")
            urgency = "🟡 注意"

    # 包み線（2本足）
    if prev["is_bear"] and last["is_bull"]:
        if last["o"] <= prev["c"] and last["c"] >= prev["o"] and last["body"] >= prev["body"] * 1.1:
            hints.append("🤝 陽の包み線 → 前日陰線を陽線が飲み込み（買い転換）")
            actions.append("底値圏ならロング検討 / 損切=包み足安値下")
            if _is_bottom_zone(df):
                urgency = "🟢 通常" if urgency == "🟢 通常" else urgency

    if prev["is_bull"] and last["is_bear"]:
        if last["o"] >= prev["c"] and last["c"] <= prev["o"] and last["body"] >= prev["body"] * 1.1:
            hints.append("🫂 陰の包み線 → 前日陽線を陰線が飲み込み（売り転換）")
            actions.append("ロング: 部分〜全利確 / 天井圏ならショート検討")
            urgency = "🟠 利確検討"

    # ピンバー（1本足）
    if last["body_ratio"] <= 0.35:
        if last["lower"] >= last["body"] * 2 and last["lower"] > last["upper"] * 1.5:
            hints.append("📌 強気ピンバー（長い下ヒゲ）→ 下値で買い支え")
            actions.append("底値圏: 翌足確認後ロング / 損切=安値下")
        if last["upper"] >= last["body"] * 2 and last["upper"] > last["lower"] * 1.5:
            hints.append("⭐ 弱気ピンバー（長い上ヒゲ・流れ星）→ 高値で拒否")
            actions.append("ロング: 利確検討 / 損切=高値上")
            urgency = "🟠 利確検討"

    # 切り込み・被せ（2本足）
    if prev["is_bear"] and last["is_bull"] and prev["body_ratio"] > 0.4:
        mid = (prev["o"] + prev["c"]) / 2
        if last["o"] < prev["l"] and last["c"] >= mid and last["c"] < prev["o"]:
            hints.append("⚔️ 切り込み線型 → 陰線の半分以上を陽線が回復")
            actions.append("底値圏ならロング / 損切=切り込み足安値")
    if prev["is_bull"] and last["is_bear"] and prev["body_ratio"] > 0.4:
        if last["o"] > prev["h"]:
            mid = (prev["o"] + prev["c"]) / 2
            if last["c"] < mid and last["c"] > prev["o"]:
                hints.append("☁ 被せ線型 → 陽線の半分以上を陰線が食い込み")
                actions.append("ロング: 部分〜全利確")
                urgency = "🟠 利確検討"

    # はらみ（陰→陽 / 陽→陰）
    if prev["is_bear"] and last["is_bull"] and last["body"] < prev["body"] * 0.6:
        if prev["c"] <= last["o"] and last["c"] <= prev["o"]:
            hints.append("🤰 陰のはらみ型 → 売り勢いの減退")
            actions.append("底値圏: 反転狙い / 損切=大陰線安値")
    if prev["is_bull"] and last["is_bear"] and last["body"] < prev["body"] * 0.6:
        if prev["o"] <= last["c"] and last["o"] <= prev["c"]:
            hints.append("🟥 陽の陰はらみ型 → 買い勢いの減退")
            actions.append("ロング: 30〜50%利確")
            urgency = "🟡 注意"

    # 連続足
    if len(df) >= 3:
        m2 = _candle_metrics(df.iloc[-3])
        if m2["is_bear"] and prev["is_bear"] and last["is_bear"]:
            if prev["c"] < m2["c"] and last["c"] < prev["c"]:
                hints.append("🐦 3本連続陰線 → 売り優勢")
                actions.append("ロング: 利確検討")
                urgency = "🟠 利確検討"
        if m2["is_bull"] and prev["is_bull"] and last["is_bull"]:
            if prev["c"] > m2["c"] and last["c"] > prev["c"]:
                hints.append("🎖 3本連続陽線 → 買い優勢")
                actions.append("ショート: 利確 / ロング: 損切上げ")

    # ギャップ（窓）
    if last["l"] > prev["h"] * 1.001:
        hints.append("🪟 上昇窓（ギャップアップ）→ 買い意欲")
        actions.append("ロング: 窓下限を損切に / 窓埋めで弱体化")
    elif last["h"] < prev["l"] * 0.999:
        hints.append("⬇ 下降窓（ギャップダウン）→ 売り意欲")
        actions.append("ショート: 窓上限を損切に / 窓埋めで反発警戒")

    # 明星（3本）
    ev = _evening_star_hint(df)
    if ev:
        hints.append(ev)
        urgency = "🟠 利確検討"
    if len(df) >= 30 and _is_bottom_zone(df):
        c1 = _candle_metrics(df.iloc[-3])
        c2 = _candle_metrics(df.iloc[-2])
        c3 = _candle_metrics(df.iloc[-1])
        if c1["is_bear"] and c2["body"] < c1["body"] * 0.4 and c3["is_bull"]:
            mid = (c1["o"] + c1["c"]) / 2
            if c3["c"] >= mid:
                hints.append("🌟 宴の明星型 → 底打ち3本反転")
                actions.append("ロング検討 / 損切=明星の安値")

    # パターン検出エンジン連携
    detected = scan_live_patterns(df)
    for p in detected[:3]:
        tag = "🟢" if p["direction"] == "BUY" else "🔴" if p["direction"] == "SELL" else ""
        hints.append(f"{tag} 検出: {p['pattern']}（信頼度{p['confidence']}%）")

    # トレンド
    if _is_uptrend_zone(df):
        hints.append("上昇トレンド中")
        actions.append("ロング: 押し目まで保有 / 高値更新失敗で利確")
    elif _is_downtrend_zone(df):
        hints.append("下降トレンド中")
        actions.append("ショート: 戻り売り / ロングは短期利確")

    if _is_top_zone(df):
        hints.append("天井圏（高値付近）")
        actions.append("ロングは利確優先、追い玉は避ける")
        if urgency == "🟢 通常":
            urgency = "🟡 注意"

    if _is_bottom_zone(df):
        hints.append("底値圏（安値付近）")
        actions.append("ショートは利確優先、新規売りは慎重")

    # MA乖離
    ma_dist = _ma_distance_pct(df)
    if ma_dist is not None:
        if ma_dist > 3:
            hints.append(f"25日線より +{ma_dist:.1f}% 乖離（買われ過ぎ気味）")
            actions.append("ロング: 部分利確を推奨")
            urgency = "🟠 利確検討"
        elif ma_dist < -3:
            hints.append(f"25日線より {ma_dist:.1f}% 乖離（売られ過ぎ気味）")
            actions.append("ショート: 部分利確を推奨")
            urgency = "🟠 利確検討"

    # 直近高安
    lookback = min(20, len(df) - 1)
    seg = df.iloc[-lookback:]
    high = float(seg["High"].max())
    low = float(seg["Low"].min())
    dist_high = (high - close) / high * 100
    dist_low = (close - low) / low * 100

    candle_label = "陽線" if last["is_bull"] else "陰線" if last["is_bear"] else "十字付近"
    body_pct = round(last["body_ratio"] * 100, 1)

    return {
        "ok": True,
        "symbol": symbol,
        "candle_label": candle_label,
        "body_pct": body_pct,
        "close": round(close, 4),
        "dist_high_pct": round(dist_high, 2),
        "dist_low_pct": round(dist_low, 2),
        "ma_dist_pct": round(ma_dist, 2) if ma_dist is not None else None,
        "urgency": urgency,
        "hints": hints or ["特筆すべき形状なし — 「その他の読み方」タブを参照"],
        "actions": list(dict.fromkeys(actions))[:6],
        "detected_patterns": detected,
    }


def render_candlestick_guide(
    live_df: Optional[pd.DataFrame] = None,
    symbol: str = "",
    key_prefix: str = "csg",
) -> None:
    """ローソク足読み方ガイド UI"""
    st.markdown("### 📖 ローソク足の読み方と利確ヒント")
    st.caption("検討・学習用。投資助言ではありません。")

    tab_basic, tab_engulf, tab_other, tab_long, tab_short, tab_when, tab_live = st.tabs([
        "🔤 基本",
        "🤝 包み・ピン",
        "📚 その他",
        "🟢 ロング利確",
        "🔴 ショート利確",
        "⏰ いつ動くか",
        "📡 今の足",
    ])

    with tab_basic:
        st.markdown("#### ローソク足の構成")
        st.dataframe(BASIC_PARTS, use_container_width=True, hide_index=True)
        st.markdown("#### 代表的な形と意味")
        st.dataframe(CANDLE_TYPES, use_container_width=True, hide_index=True)
        st.info(
            "**覚え方**: 実体＝勢い、ヒゲ＝拒否された価格。"
            " 陽線は買い、陰線は売り。**どこで出るか**（天井/底/トレンド中）が同じ形でも意味を変える。"
        )

    with tab_engulf:
        st.markdown("#### 包み線・ピンバー一覧（検出対象）")
        st.dataframe(ENGULFING_PINBAR, use_container_width=True, hide_index=True)
        st.markdown(
            "**包み線** = 前の足の実体を次の足が丸ごと飲み込む形。"
            " **ピンバー** = 小さな実体＋長いヒゲ（拒否された価格）。"
            " どちらも **出現位置**（天井/底）で意味が変わります。"
        )

    with tab_other:
        o1, o2, o3, o4, o5, o6, o7 = st.tabs([
            "はらみ", "明星・三兵", "切込・被せ", "窓・ギャップ", "継続足", "連続の読み方", "位置の読み方",
        ])
        with o1:
            st.dataframe(HARAMI_PATTERNS, use_container_width=True, hide_index=True)
        with o2:
            st.dataframe(STAR_THREE_PATTERNS, use_container_width=True, hide_index=True)
        with o3:
            st.dataframe(PIERCING_COVER, use_container_width=True, hide_index=True)
        with o4:
            st.dataframe(GAP_WINDOW, use_container_width=True, hide_index=True)
        with o5:
            st.dataframe(CONTINUATION_PATTERNS, use_container_width=True, hide_index=True)
        with o6:
            st.dataframe(SEQUENCE_READING, use_container_width=True, hide_index=True)
        with o7:
            st.dataframe(CONTEXT_READING, use_container_width=True, hide_index=True)
        st.caption(
            "📐 **チャートパターン検出** ページでは上記を含む57種を自動検出できます。"
            " 表は学習用、検出は銘柄・足種を指定して実行してください。"
        )

    with tab_long:
        st.markdown("#### ロング（買い）保有時 — いつ利確するか")
        st.dataframe(PROFIT_HINTS_LONG, use_container_width=True, hide_index=True)
        st.markdown(
            "**基本ルール**: ① 目標到達で半分利確 ② 逆方向の強い足で残り決済 "
            "③ 損切りは建値または前足安値の下"
        )

    with tab_short:
        st.markdown("#### ショート（売り）保有時 — いつ利確するか")
        st.dataframe(PROFIT_HINTS_SHORT, use_container_width=True, hide_index=True)

    with tab_when:
        st.markdown("#### 優先度別 — 今すぐ動くべきサイン")
        st.dataframe(WHEN_TO_ACT, use_container_width=True, hide_index=True)

    with tab_live:
        if live_df is not None and len(live_df) >= 10:
            result = analyze_live_candle_hint(live_df, symbol)
            if result["ok"]:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("直近足", result["candle_label"])
                c2.metric("実体比率", f"{result['body_pct']}%")
                c3.metric("高値から", f"{result['dist_high_pct']}%")
                c4.metric("安値から", f"{result['dist_low_pct']}%")

                st.markdown(f"**総合判断**: {result['urgency']}")
                if result.get("ma_dist_pct") is not None:
                    st.caption(f"25日移動平均との乖離: {result['ma_dist_pct']:+.2f}%")

                st.markdown("**読み取り**")
                for h in result["hints"]:
                    st.markdown(f"- {h}")

                st.markdown("**利確・損切のヒント**")
                for a in result["actions"]:
                    st.markdown(f"- ✅ {a}")

                if result.get("detected_patterns"):
                    st.markdown("**自動検出パターン**")
                    rows = [
                        {
                            "パターン": p["pattern"],
                            "判定": p["verdict"],
                            "信頼度": f"{p['confidence']}%",
                        }
                        for p in result["detected_patterns"]
                    ]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning(result.get("message", "分析できません"))
        else:
            st.info("チャートデータがある画面（FXターミナル等）では、直近足を自動分析します。")
            st.markdown("手動で銘柄を選んで分析:")
            manual_ticker = st.text_input("ティッカー", value=symbol or "USDJPY=X", key=f"{key_prefix}_manual_ticker")
            manual_period = st.selectbox("期間", ["1mo", "3mo", "6mo"], index=0, key=f"{key_prefix}_period")
            if st.button("直近足を分析", key=f"{key_prefix}_analyze_btn"):
                try:
                    from data_fetcher import fetch_market_data
                    raw = fetch_market_data(manual_ticker.strip(), period=manual_period, interval="1d")
                    if raw is not None and len(raw) >= 10:
                        result = analyze_live_candle_hint(raw, manual_ticker)
                        if result["ok"]:
                            st.success(f"**{result['urgency']}** — {result['candle_label']}（実体{result['body_pct']}%）")
                            for h in result["hints"]:
                                st.markdown(f"- {h}")
                            for a in result["actions"]:
                                st.markdown(f"- ✅ {a}")
                    else:
                        st.error("データを取得できませんでした")
                except Exception as e:
                    st.error(f"取得エラー: {e}")
