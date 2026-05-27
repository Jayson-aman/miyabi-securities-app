"""
Streamlit Cloud の Secrets に貼り付ける [auth] セクション用の
パスワードハッシュを生成するユーティリティ。

使い方:
    python3 generate_password_hash.py

パスワードを対話的に入力すると、Streamlit Cloud の
Secrets 画面にコピペ可能な TOML 形式で出力されます。
"""

from __future__ import annotations
import getpass
import sys

from auth import generate_hash


def main():
    print("=" * 60)
    print("  🌐 雅証券 | Streamlit Cloud 用パスワードハッシュ生成")
    print("=" * 60)
    print()

    pw1 = getpass.getpass("パスワードを入力 (8文字以上): ")
    if len(pw1) < 8:
        print("❌ パスワードは8文字以上にしてください")
        sys.exit(1)

    pw2 = getpass.getpass("パスワードをもう一度入力: ")
    if pw1 != pw2:
        print("❌ パスワードが一致しません")
        sys.exit(1)

    salt_hex, hash_hex = generate_hash(pw1)

    print()
    print("✅ 生成完了！以下を Streamlit Cloud の Secrets に貼り付けてください：")
    print()
    print("─" * 60)
    print("[auth]")
    print(f'salt = "{salt_hex}"')
    print(f'hash = "{hash_hex}"')
    print("─" * 60)
    print()
    print("📋 Streamlit Cloud での設定方法:")
    print("  1. https://share.streamlit.io でアプリを開く")
    print("  2. ⚙ Settings → Secrets を開く")
    print("  3. 上記の3行を貼り付けて Save")
    print()
    print("⚠  salt と hash は絶対にGitHubに公開しないでください")
    print("⚠  同じパスワードのままなら hash を作り直さないでください（Secrets と不一致になりログインできなくなります）")
    print()


if __name__ == "__main__":
    main()
