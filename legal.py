"""
Zaibase.Economic Research — 利用規約・プライバシー・免責事項

法的助言ではありません。必要に応じて弁護士等の確認を推奨します。
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from brand import APP_NAME, APP_DISCLAIMER, APP_FOOTER_COPY

TERMS_VERSION = "2026-06-01-v1"

LEGAL_SUMMARY = (
    "本サービスは **学習・研究目的** の市場情報ツールです。"
    " **投資助言・投資勧誘・金融商品取引の媒介・取引執行・口座開設は一切行いません。**"
    " 大和証券・GMOクリック証券等の **公式サービスではなく、提携・後援もありません。**"
)


def _legal_cfg() -> dict[str, Any]:
    try:
        return dict(st.secrets.get("legal", {}))
    except Exception:
        return {}


def _truthy(val) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "on")


def operator_name() -> str:
    return str(_legal_cfg().get("operator_name") or "南條 雅哉（Zaibase.Economic Research）")


def contact_email() -> str:
    return str(_legal_cfg().get("contact_email") or "info@zaibase.group")


def operator_address() -> str:
    """Secrets のみ。Git / 画面にはデフォルトで出さない。"""
    return str(_legal_cfg().get("address") or "").strip()


def may_show_private_legal_fields() -> bool:
    """住所等 — 非公開運用中は画面に表示しない。"""
    try:
        from auth import is_closed_until_notice
        if is_closed_until_notice():
            return False
    except Exception:
        pass
    return bool(_legal_cfg().get("show_address", False)) or _truthy(_legal_cfg().get("public_legal_details"))


def terms_accepted() -> bool:
    return st.session_state.get("terms_accepted_version") == TERMS_VERSION


def require_terms_acceptance() -> None:
    """初回・規約改定時に同意を取得。未同意ならここで停止。"""
    if terms_accepted():
        return

    st.markdown(f"## 📜 {APP_NAME} — ご利用前の確認")
    st.warning(LEGAL_SUMMARY)

    with st.expander("利用規約（全文）", expanded=False):
        _render_terms_full()

    with st.expander("プライバシーポリシー（全文）", expanded=False):
        _render_privacy_full()

    with st.expander("リスク・免責事項（全文）", expanded=False):
        _render_risk_full()

    st.markdown("---")
    agree_terms = st.checkbox("**利用規約**に同意します", key="legal_agree_terms")
    agree_risk = st.checkbox(
        "**リスク・免責事項**を理解し、表示内容が投資助言ではないことを確認しました",
        key="legal_agree_risk",
    )
    agree_no_broker = st.checkbox(
        "**本サービスが証券会社・FX会社の公式アプリではない**ことを理解しました",
        key="legal_agree_no_broker",
    )

    if st.button("同意して利用を開始", type="primary", use_container_width=True, key="legal_accept_btn"):
        if agree_terms and agree_risk and agree_no_broker:
            st.session_state["terms_accepted_version"] = TERMS_VERSION
            st.session_state["terms_accepted_at"] = __import__("datetime").datetime.now().isoformat()
            st.rerun()
        else:
            st.error("すべてのチェック項目に同意してください。")

    st.caption(f"規約バージョン: {TERMS_VERSION} ｜ 運営: {operator_name()}")
    st.stop()


def render_legal_banner() -> None:
    """全ページ上部に表示する短い免責バー。"""
    st.markdown(
        f"""
        <div style="background:#FFF8E1;border:1px solid #C9A961;border-left:4px solid #8B6914;
            padding:8px 12px;font-size:0.72rem;color:#5D4E37;line-height:1.55;margin-bottom:10px;border-radius:2px;">
        <b>免責</b> — {APP_DISCLAIMER}
        表示の「買い/売り」「パターン」は自動検出の参考情報であり、特定銘柄の推奨ではありません。
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_legal_page() -> None:
    """利用規約・免責の専用ページ。"""
    st.title("📜 利用規約・プライバシー・免責")
    st.caption(f"運営: {operator_name()} ｜ お問い合わせ: {contact_email()} ｜ 版: {TERMS_VERSION}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "利用規約",
        "プライバシーポリシー",
        "リスク・免責",
        "有料プラン・返金",
    ])

    with tab1:
        _render_terms_full()
    with tab2:
        _render_privacy_full()
    with tab3:
        _render_risk_full()
    with tab4:
        _render_billing_legal()

    st.divider()
    if not terms_accepted():
        st.info("利用規約への同意が必要です。サイドバーから再度アクセスしてください。")
    else:
        st.success(f"同意済み（{TERMS_VERSION}）")


def _render_terms_full() -> None:
    op = operator_name()
    st.markdown(f"""
### 第1条（サービスの性質）
1. {APP_NAME}（以下「本サービス」）は、{op}が提供する **学習・研究目的** の市場情報表示ツールです。
2. 本サービスは **金融商品取引業、金融商品取引法上の投資助言・代理業、銀行業、資金移転業に該当するものではありません**。
3. 本サービスは **口座開設、注文執行、資金の預託・受入、決済代行を行いません**。

### 第2条（非公式・非提携）
1. 本サービスに表示される UI や用語（例: 証拠金維持率、Bid/Ask、ロスカット等）は、業界慣行・公開情報を **参考にしたシミュレーション** です。
2. **大和証券、GMOクリック証券その他の金融機関の公式アプリ・公式サービスではありません。** 商標・ロゴ・社名の表示は識別・説明目的の参考であり、提携・後援・推奨を意味しません。

### 第3条（情報の限界）
1. チャート、パターン検出、AI 予測、アラート等は **自動計算・参考情報** です。正確性、完全性、最新性、有用性を保証しません。
2. 「買い」「売り」「ロング」「ショート」「爆益」等の表示は **テクニカルパターンのラベル** であり、特定の金融商品の売買を推奨するものではありません。
3. データ源（Yahoo Finance 等）の障害・遅延・誤差により、表示が実勢と異なる場合があります。

### 第4条（ユーザーの責任）
1. 投資・取引に関する一切の判断は **ユーザー自身の責任** で行ってください。
2. 本サービスを唯一の根拠として投資判断しないでください。必要に応じて licensed の専門家に相談してください。
3. 仮想注文・シミュレーション結果は **過去・仮定に基づくもの** で、将来の成果を示唆しません。

### 第5条（禁止事項）
1. 本サービスの表示を **投資助言・勧誘** として第三者に提供すること
2. 本サービスを **証券会社・FX 会社の公式サービス** と誤認させる宣伝
3. 不正アクセス、過度な負荷、スクレイピング、リバースエンジニアリング
4. 法令・公序良俗に反する利用

### 第6条（知的財産）
本サービスのプログラム・デザイン・文案の権利は運営者に帰属します。無断複製・再配布を禁じます。

### 第7条（サービスの変更・停止）
運営者は、事前通知なく本サービスの全部または一部を変更・中断・終了できます。

### 第8条（免責）
運営者は、本サービスの利用により生じた **損害（投資損失を含む）** について、法令上許容される範囲で責任を負いません。

### 第9条（規約の変更）
本規約は必要に応じて改定します。改定後は改定版への同意を求める場合があります。

### 第10条（準拠法・管轄）
本規約は日本法に準拠します。紛争については、運営者所在地を管轄する裁判所を第一審の専属的合意管轄とします。

---
{APP_FOOTER_COPY} ｜ 運営: {op}
""")


def _render_privacy_full() -> None:
    op = operator_name()
    email = contact_email()
    st.markdown(f"""
### 1. 基本方針
{op}（以下「当方」）は、{APP_NAME} 利用に伴い取得する情報を、本ポリシーに従い適切に取り扱います。

### 2. 取得する情報
| 種類 | 内容 | 目的 |
|------|------|------|
| 認証情報 | パスワードハッシュ（平文は保存しません） | アクセス制御 |
| セッション | ログイン状態、UI 設定、規約同意版 | サービス提供 |
| 利用設定 | アラート設定、仮想建玉（端末セッション内） | 機能提供 |
| 課金 | Stripe 等の決済は **決済事業者が処理**（当方はカード番号を保持しません） | 有料プラン |
| ログ | サーバーアクセスログ（ホスト・時刻等） | 障害対応・セキュリティ |
| メール通知（任意） | Secrets 設定時のみ、通知先アドレス | FX 変動通知（オプション） |

### 3. 第三者提供
法令に基づく場合を除き、本人の同意なく第三者に個人情報を提供しません。
データ取得先（Yahoo Finance、Google News 等）へのリクエストは、各提供者の規約に従います。

### 4. 保管期間
セッション情報はセッション終了まで。ログは必要な期間保管後、削除します。

### 5. 安全管理
アクセス制限、Secrets による機密管理、HTTPS 通信（ホスティング環境依存）等の措置を講じます。

### 6. 開示・訂正・削除
ご本人からの請求には、合理的な範囲で対応します。お問い合わせ: {email}

### 7. 改定
本ポリシーは改定することがあります。重要な変更はサービス内で告知します。
""")


def _render_risk_full() -> None:
    st.markdown(f"""
### 投資リスクに関する重要事項

1. **元本割れのリスク** — FX、CFD、株式、仮想通貨、商品先物等には価格変動リスクがあり、損失が生じるおそれがあります。レバレッジ取引では **損失が預託金を超える** 場合があります（口座契約に依存）。

2. **情報の非保証** — 本サービスの予測・シグナル・パターンは **過去データとモデルに基づく参考表示** で、将来の相場を保証しません。

3. **シミュレーションの限界** — 仮想注文、証拠金アラーム、スワップ表示等は **実取引環境（スプレッド、約定、滑り、サーバー障害）を再現しません**。

4. **アラーム・通知** — ブラウザ音・画面表示・メールは **到達・即時性を保証しません**。取引判断の唯一の手段にしないでください。

5. **外部データ** — ニュース・カレンダー・要人発言等は自動収集であり、誤訳・欠落・遅延があり得ます。

6. **AI・機械学習** — モデルは過学習・ドリフト・異常値に弱く、極端な相場で機能しない場合があります。

### 免責（再掲）
{APP_DISCLAIMER}

{LEGAL_SUMMARY}
""")


def _render_billing_legal() -> None:
    op = operator_name()
    email = contact_email()
    addr_row = ""
    if may_show_private_legal_fields():
        addr = operator_address()
        if addr:
            addr_row = f"| 所在地 | {addr} |\n"

    st.markdown(f"""
### 有料プラン（Pro Research）について

| 項目 | 内容 |
|------|------|
| 販売者 | {op} |
| お問い合わせ | {email} |
{addr_row}| 販売価格 | 各決済ページ（Stripe）に表示（例: ¥1,980/月・税込表示は決済画面に準拠） |
| 商品の性質 | **ソフトウェア機能へのアクセス権**（調査・分析ツール）。金融商品ではありません |
| 引渡し時期 | 決済確認後、ライセンスキー入力により **直ちに** 機能解放 |
| 動作環境 | 最新の Web ブラウザ、インターネット接続 |
| 支払方法 | クレジットカード等（Stripe が処理） |

### 返金・キャンセル
1. デジタルコンテンツの性質上、**決済完了後の返金は原則お受けできません**（法令上必要な場合を除く）。
2. サブスクリプションの解約は Stripe の顧客ポータルまたは決済メールの手順に従ってください。
3. 重大な不具合でサービスが利用不能な場合は、個別にご相談ください。

### 注意
Pro プランは **投資成果・利益を保証するものではありません**。機能追加のみを提供します。
""")
