"""
パスワードハッシュ生成（画面表示版）
getpass でうまく入力できない場合のシンプルな代替版。
パスワードがそのまま画面に表示されるので、周囲に注意してください。
"""

from auth import generate_hash


def main():
    print("=" * 60)
    print("  🌐 雅証券 | パスワードハッシュ生成（画面表示版）")
    print("=" * 60)
    print()
    print("⚠ 注意: パスワードがそのまま画面に表示されます")
    print("   周囲に人がいない場所で実行してください")
    print()

    pw1 = input("パスワード (8文字以上): ").strip()
    if len(pw1) < 8:
        print("❌ パスワードは8文字以上にしてください")
        return

    pw2 = input("もう一度入力: ").strip()
    if pw1 != pw2:
        print("❌ パスワードが一致しません")
        return

    salt_hex, hash_hex = generate_hash(pw1)

    print()
    print("✅ 生成完了！以下の3行を Streamlit Cloud の Secrets に貼り付け:")
    print()
    print("=" * 60)
    print("[auth]")
    print(f'salt = "{salt_hex}"')
    print(f'hash = "{hash_hex}"')
    print("=" * 60)
    print()
    print("📝 上の3行をコピーしてメモ帳などに保存してください")
    print("⚠ salt と hash は GitHub にアップロードしないでください")
    print()
    # ターミナル履歴からパスワードを消すヒント
    print("💡 セキュリティのため、ターミナルを閉じるかクリアしてください:")
    print("   clear        （画面クリア）")
    print("   history -c   （履歴削除・zsh）")


if __name__ == "__main__":
    main()
