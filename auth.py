"""
パスワード認証モジュール（Streamlit Cloud 対応版）
────────────────────────
- PBKDF2-SHA256 でパスワードをハッシュ化
- クラウド時: st.secrets["auth"] から読込
- ローカル時: auth_config.json から読込（未設定なら初回設定画面）
- セッション管理（Streamlit session_state）
- ログイン失敗5回でロックアウト（15分・メモリ内）
- パスワード変更機能（ローカルのみ）
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets as pysecrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import streamlit as st


# ═══════════════════════════════════════════
# 設定
# ═══════════════════════════════════════════

AUTH_CONFIG_PATH = "auth_config.json"
PBKDF2_ITERATIONS = 200_000
PBKDF2_ALGO = "sha256"
SALT_BYTES = 32
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_MAX_HOURS = 12


# ═══════════════════════════════════════════
# ハッシュ
# ═══════════════════════════════════════════

def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALGO, password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return dk.hex()


def generate_hash(password: str) -> Tuple[str, str]:
    """
    与えたパスワードから (salt_hex, hash_hex) を生成する。
    Streamlit Cloud の secrets 登録に使う。
    """
    salt = pysecrets.token_bytes(SALT_BYTES)
    return salt.hex(), _hash_password(password, salt)


# ═══════════════════════════════════════════
# 設定読込（Cloud優先 → Local fallback）
# ═══════════════════════════════════════════

def _load_from_secrets() -> Optional[dict]:
    """Streamlit secrets に [auth] セクションがあれば読む"""
    try:
        if "auth" in st.secrets:
            s = st.secrets["auth"]
            if "salt" in s and "hash" in s:
                return {
                    "salt": s["salt"],
                    "hash": s["hash"],
                    "source": "secrets",
                }
    except Exception:
        pass
    return None


def _load_from_file() -> Optional[dict]:
    if not os.path.exists(AUTH_CONFIG_PATH):
        return None
    try:
        with open(AUTH_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            cfg["source"] = "file"
            return cfg
    except Exception:
        return None


def load_auth_config() -> Optional[dict]:
    """secrets > file の優先順で認証設定を取得"""
    cfg = _load_from_secrets()
    if cfg:
        return cfg
    return _load_from_file()


def save_auth_config(cfg: dict) -> None:
    """ローカルファイルに保存（Cloudでは使わない）"""
    to_save = {k: v for k, v in cfg.items() if k != "source"}
    with open(AUTH_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(AUTH_CONFIG_PATH, 0o600)
    except Exception:
        pass


def _initialize_password_local(password: str) -> dict:
    salt_hex, hash_hex = generate_hash(password)
    cfg = {
        "salt": salt_hex,
        "hash": hash_hex,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    save_auth_config(cfg)
    cfg["source"] = "file"
    return cfg


# ═══════════════════════════════════════════
# パスワード検証
# ═══════════════════════════════════════════

def verify_password(password: str, cfg: dict) -> bool:
    try:
        salt = bytes.fromhex(cfg["salt"])
        expected = cfg["hash"]
        actual = _hash_password(password, salt)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def change_password(old_password: str, new_password: str) -> Tuple[bool, str]:
    cfg = _load_from_file()
    if cfg is None:
        return False, "クラウドモードではパスワード変更はできません（Secretsで直接書き換えてください）"
    if not verify_password(old_password, cfg):
        return False, "現在のパスワードが一致しません"
    if len(new_password) < 8:
        return False, "新しいパスワードは8文字以上にしてください"

    salt_hex, hash_hex = generate_hash(new_password)
    cfg["salt"] = salt_hex
    cfg["hash"] = hash_hex
    cfg["updated_at"] = datetime.now().isoformat()
    save_auth_config(cfg)
    return True, "パスワードを変更しました"


# ═══════════════════════════════════════════
# ロックアウト（session_state に記録・プロセス単位）
# ═══════════════════════════════════════════

def _get_failures() -> int:
    return int(st.session_state.get("_auth_failed_attempts", 0))


def _get_locked_until() -> Optional[datetime]:
    v = st.session_state.get("_auth_locked_until")
    if v is None:
        return None
    try:
        return datetime.fromisoformat(v) if isinstance(v, str) else v
    except Exception:
        return None


def _is_locked() -> Tuple[bool, Optional[datetime]]:
    until = _get_locked_until()
    if until and datetime.now() < until:
        return True, until
    return False, None


def _register_failure():
    n = _get_failures() + 1
    st.session_state["_auth_failed_attempts"] = n
    if n >= MAX_FAILED_ATTEMPTS:
        st.session_state["_auth_locked_until"] = (
            datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        ).isoformat()


def _reset_failures():
    st.session_state["_auth_failed_attempts"] = 0
    st.session_state["_auth_locked_until"] = None


# ═══════════════════════════════════════════
# Streamlit UI
# ═══════════════════════════════════════════

def is_authenticated() -> bool:
    if not st.session_state.get("auth_ok"):
        return False
    login_at = st.session_state.get("auth_login_at")
    if login_at is None:
        return False
    if datetime.now() - login_at > timedelta(hours=SESSION_MAX_HOURS):
        st.session_state["auth_ok"] = False
        return False
    return True


def _branding_header(subtitle: str):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0B3D91 0%,#1A2D6E 100%);color:#fff;padding:24px;border-radius:6px;text-align:center;border:2px solid #C9A961;margin-bottom:20px;">
      <div style="font-family:'Hiragino Mincho ProN',serif;font-size:2.5rem;font-weight:700;letter-spacing:8px;background:linear-gradient(135deg,#C9A961 0%,#F0D580 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">雅</div>
      <div style="font-size:0.85rem;letter-spacing:6px;color:#C9A961;margin-top:6px;">MIYABI SECURITIES</div>
      <div style="font-size:1rem;margin-top:12px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def _initial_setup_form():
    """初回パスワード設定UI（ローカルのみ）"""
    _branding_header("🔐 初回パスワード設定")
    st.info(
        "初めてのご利用です。管理用パスワードを設定してください（8文字以上）。\n\n"
        "クラウド（Streamlit Cloud）にデプロイする場合は、"
        "この画面で設定せず、Secrets に直接ハッシュを貼り付けてください（DEPLOY.md 参照）。"
    )

    with st.form("initial_setup", clear_on_submit=False):
        pw1 = st.text_input("パスワード", type="password", key="setup_pw1")
        pw2 = st.text_input("パスワード（確認）", type="password", key="setup_pw2")
        submitted = st.form_submit_button("🔐 パスワードを設定する", type="primary", use_container_width=True)

        if submitted:
            if len(pw1) < 8:
                st.error("パスワードは8文字以上にしてください")
            elif pw1 != pw2:
                st.error("パスワードが一致しません")
            else:
                _initialize_password_local(pw1)
                st.success("パスワードを設定しました。もう一度ログインしてください。")
                st.rerun()


def _login_form(cfg: dict):
    _branding_header("🔐 ログイン")

    locked, until = _is_locked()
    if locked and until:
        remaining = until - datetime.now()
        mins = int(remaining.total_seconds() // 60) + 1
        st.error(f"🔒 ロック中（残り約 {mins} 分）")
        st.caption(f"解除予定: {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("パスワード", type="password", key="login_pw")
        submitted = st.form_submit_button("🔐 ログイン", type="primary", use_container_width=True)

        if submitted:
            if verify_password(pw, cfg):
                _reset_failures()
                st.session_state["auth_ok"] = True
                st.session_state["auth_login_at"] = datetime.now()
                st.session_state["auth_source"] = cfg.get("source", "unknown")
                st.success("ログイン成功。画面を読み込みます...")
                st.rerun()
            else:
                _register_failure()
                remaining_attempts = MAX_FAILED_ATTEMPTS - _get_failures()
                if remaining_attempts > 0:
                    st.error(f"❌ パスワードが違います（残り試行回数: {remaining_attempts}）")
                else:
                    st.error(f"🔒 {MAX_FAILED_ATTEMPTS}回失敗したため {LOCKOUT_MINUTES}分 ロックされました")


def require_login():
    """
    ログインを要求するゲート関数。
    app.py の st.set_page_config() 直後に呼ぶだけでアプリ全体を保護する。
    """
    if is_authenticated():
        return

    cfg = load_auth_config()

    _, center, _ = st.columns([1, 2, 1])
    with center:
        if cfg is None:
            _initial_setup_form()
        else:
            _login_form(cfg)

    st.stop()


def render_auth_sidebar():
    """サイドバーの認証UI（ログアウト & パスワード変更）"""
    if not is_authenticated():
        return

    login_at = st.session_state.get("auth_login_at")
    source = st.session_state.get("auth_source", "unknown")
    expires_at = login_at + timedelta(hours=SESSION_MAX_HOURS) if login_at else None

    with st.sidebar:
        with st.expander("🔐 セッション情報", expanded=False):
            src_label = "☁️ クラウド" if source == "secrets" else "💻 ローカル"
            st.caption(f"認証ソース: {src_label}")

            if login_at:
                st.caption(f"ログイン: {login_at.strftime('%Y-%m-%d %H:%M')}")
            if expires_at:
                remaining = expires_at - datetime.now()
                hrs = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                st.caption(f"有効期限まで: {hrs}時間 {mins}分")

            if st.button("🚪 ログアウト", use_container_width=True, key="auth_logout_btn"):
                st.session_state["auth_ok"] = False
                st.session_state["auth_login_at"] = None
                st.rerun()

            if source != "secrets":
                st.markdown("---")
                st.markdown("**🔑 パスワード変更**")
                old = st.text_input("現在のパスワード", type="password", key="auth_old_pw")
                new1 = st.text_input("新しいパスワード", type="password", key="auth_new_pw1")
                new2 = st.text_input("新しいパスワード（確認）", type="password", key="auth_new_pw2")
                if st.button("変更する", use_container_width=True, key="auth_change_btn"):
                    if new1 != new2:
                        st.error("新しいパスワードが一致しません")
                    elif len(new1) < 8:
                        st.error("8文字以上にしてください")
                    else:
                        ok, msg = change_password(old, new1)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
            else:
                st.caption("💡 クラウドモードではパスワード変更はSecrets編集で行ってください")
