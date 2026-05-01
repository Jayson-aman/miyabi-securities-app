"""
円相場: 証券会社レポートで一般的に用いられる着眼点の「参考フレーム」

個別証券の公式レポートや見解を転載するものではなく、
国内・海外のマクロレポートで繰り返し語られる論点の整理用テキストを返す。
"""

from __future__ import annotations

from typing import Any, Optional


def synthesize_broker_lens(
    *,
    summary: dict[str, Any],
    spot_ctx: Optional[dict[str, Any]],
    reconciliation: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """証券レポート風の着眼点（一般論）＋現在のスコアに応じた注意を返す。"""

    verdict = summary.get("verdict", "—")
    total = summary.get("total_score", 0.0)
    strength = summary.get("verdict_strength", "—")

    themes: list[str] = [
        "**金利差・実質金利** — 米長期金利・日米10年スプレッドはドル円の中軸。指標・要人発言で一気にリプライスされやすい。",
        "**リスクオン／オフ** — 株・クレジット・VIXの動きでクロス円と連動。リスクオフ時は円買いが入りやすい（ただしドル単独の流動性要因でズレることがある）。",
        "**実需・フロー** — 輸出企業の売却タイミング、決済フロー、SQ・月末による実需は「ファクター表に現れない」動きを作る。",
        "**投機・ポジション調整** — COT等は遅行だが、積み上がったドルロングの巻き戻しは数円規模の急円高になりうる（モデル乖離の典型）。",
        "**流動性・時間帯** — 欧米早朝／指標直後はスプレッド拡大・ストップ狩りで実勢が跳ねやすい。",
        "**オプション・ガンマ** — 大量のストライク集中で、市場が「磁力」的に価格を引き寄せたあと急反転することがある。",
        "**当局・介入観測** — 口先と実弾のギャップ、報道フローだけでもボラが膨らむ。",
    ]

    score_note = (
        f"現在のファクター総合は **{verdict}（強さ:{strength}）** 、スコア **{total:+.1f}** 。"
        "これは主に各資産の**数日スパンの方向感**から積み上げたバイアスであり、"
        "**当日の急変（数円）を説明する主要指標ではない**点に注意してください。"
    )

    div_note = ""
    if reconciliation and reconciliation.get("is_divergent"):
        div_note = (
            f"**乖離アラート**: {reconciliation.get('message', '')} "
            "— 多くの際は**ポジション解体・オプション・流動性ショック・未計測フロー**が絡みます。"
        )

    shock_note = ""
    if spot_ctx and spot_ctx.get("is_shock"):
        shock_note = (
            f"**短期ボラ異常**: 直近{spot_ctx.get('shock_window', '—')}で "
            f"**{abs(spot_ctx.get('shock_move_yen', 0) or 0):.2f}円**相当の変化。 "
            "イベント前後の薄商い・ストップ連鎖を疑うべき水準です。"
        )

    return {
        "disclaimer": (
            "以下は**一般的なマクロ・FXレポートの論点整理（参考）**です。"
            "特定の証券会社の公式見解・目標レート・投資判断の引用ではありません。"
        ),
        "score_context": score_note,
        "divergence": div_note,
        "shock": shock_note,
        "themes_markdown": themes,
    }
