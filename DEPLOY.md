# 🌐 雅証券 MIYABI Securities - デプロイ手順書

スマホから24時間どこでもアクセスできる **Streamlit Community Cloud（完全無料）** への公開手順です。
所要時間は合計で約15〜20分です。

---

## 📋 必要なもの（すべて無料）

- ✅ GitHub アカウント（未登録なら [github.com](https://github.com) で作成）
- ✅ Streamlit アカウント（GitHub連携で自動作成）
- ✅ パスワードハッシュ（下記の手順で生成）

---

## 🗺 全体の流れ

```
Step 1: パスワードハッシュ生成（Mac上で1分）
   ↓
Step 2: GitHub アカウント作成（5分）
   ↓
Step 3: コードを GitHub にアップロード（5分）
   ↓
Step 4: Streamlit Cloud でデプロイ（3分）
   ↓
Step 5: スマホでアクセス & ホーム画面に追加（1分）
```

---

## 🔑 Step 1: パスワードハッシュ生成

ターミナルで次のコマンドを実行：

```bash
cd "/Users/masaya.happylife24/雅証券"
source venv/bin/activate
python3 generate_password_hash.py
```

パスワードを2回入力すると、次のような出力が得られます：

```
[auth]
salt = "abc123...（64文字）"
hash = "def456...（64文字）"
```

**この3行を後で使うのでメモ帳などに保存してください。**

⚠ パスワード自体は絶対にメモしないでください（ハッシュだけで十分）。

---

## 🐙 Step 2: GitHub アカウント作成

既にお持ちならスキップ。

1. [github.com/signup](https://github.com/signup) にアクセス
2. メールアドレス・パスワード・ユーザー名を登録
3. メール認証を完了

---

## 📤 Step 3: コードを GitHub にアップロード

### 3-1. 新規リポジトリを作成

1. GitHub にログイン後、右上の「+」→「New repository」
2. 以下を設定：
   - Repository name: `miyabi-securities`（任意）
   - Description: `Miyabi Securities - Financial Dashboard`（任意）
   - **Private**（非公開）を選択 ← 重要！
   - README, .gitignore, license は **何も追加しない**
3. 「Create repository」をクリック

### 3-2. ターミナルでプッシュ

表示される指示の中から「push an existing repository」を使います：

```bash
cd "/Users/masaya.happylife24/雅証券"

# Git初期化
git init
git branch -M main

# 全ファイル追加（.gitignoreで秘密情報は自動除外）
git add .

# ⚠ 確認: 機密ファイルが含まれていないか
git status | grep -E "(secrets\.toml|auth_config\.json|venv|\.env)"
# → 何も表示されなければOK（テンプレート secrets.toml.example は含まれます）

# コミット
git commit -m "Initial commit: Miyabi Securities Terminal"

# GitHubにプッシュ（YOUR_USERNAME を自分のGitHubユーザー名に置換）
git remote add origin https://github.com/YOUR_USERNAME/miyabi-securities.git
git push -u origin main
```

初回プッシュ時に GitHub のユーザー名とパスワード（Personal Access Token）を聞かれます。
パスワードを忘れた場合は、GitHub の Settings → Developer settings → Personal access tokens で作成。

### 3-3. 認証ファイルが含まれていないことを確認

ブラウザでリポジトリを開き、以下のファイルが **含まれていない** ことを確認：

- ❌ `auth_config.json`（含まれていたら今すぐ削除）
- ❌ `.streamlit/secrets.toml`（含まれていたら今すぐ削除）
- ❌ `venv/`（含まれていたら今すぐ削除）

含まれるべきファイル：

- ✅ `app.py`, `auth.py` などのソースコード
- ✅ `requirements.txt`
- ✅ `.gitignore`
- ✅ `.streamlit/config.toml`
- ✅ `.streamlit/secrets.toml.example`（テンプレートのみ）

---

## 🚀 Step 4: Streamlit Cloud でデプロイ

### 4-1. Streamlit Cloud にログイン

1. [share.streamlit.io](https://share.streamlit.io) を開く
2. 「Sign in with GitHub」をクリック
3. 連携を許可

### 4-2. 新規アプリをデプロイ

1. 右上の「**Create app**」→「Deploy a public app from GitHub」
2. 以下を設定：
   - **Repository**: `YOUR_USERNAME/miyabi-securities`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**（カスタム）: 好きな名前（例 `miyabi-yourname`）
3. **「Advanced settings」を必ずクリック** → Secrets 欄に Step 1 で生成したハッシュを貼り付け：

```toml
[auth]
salt = "abc123...（Step 1で生成した値）"
hash = "def456...（Step 1で生成した値）"

[email_alert]
enabled = true
to_addr = "masaya.happylife@gmail.com"
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "送信用Gmailアドレス"
smtp_password = "Googleアカウントのアプリパスワード"
from_addr = "送信用Gmailアドレス"
threshold_yen = 0.3
cooldown_minutes = 60
```

※ メール通知が不要な場合は `[email_alert]` を省略できます。Gmailを使う場合、通常のログインパスワードではなく **Googleのアプリパスワード** を `smtp_password` に設定してください。

4. 「**Save**」→「**Deploy!**」

### 4-3. デプロイ完了まで待機（2〜5分）

画面にログが流れます。以下のようなメッセージが出たら完了：

```
You can now view your Streamlit app in your browser.
URL: https://miyabi-yourname.streamlit.app
```

---

## 📱 Step 5: スマホで使う

### 5-1. iPhone / Safari の場合

1. Safari で URL を開く
2. 下部の「共有」ボタン
3. 「ホーム画面に追加」
4. アイコンを「雅証券」などに変更 → 追加
5. **ホーム画面のアイコンから独立アプリのように起動** できます

### 5-2. Android / Chrome の場合

1. Chrome で URL を開く
2. 右上の「⋮」メニュー
3. 「ホーム画面に追加」
4. 同様にアプリ感覚で使えます

---

## 🔄 アップデート手順

コードを変更したら：

```bash
cd "/Users/masaya.happylife24/雅証券"
git add .
git commit -m "機能追加: ○○"
git push
```

→ Streamlit Cloud が自動的に数分でデプロイし直します。

---

## 🔐 パスワード変更手順

クラウド上のパスワードを変更するには：

1. Mac のターミナルで `python3 generate_password_hash.py` を実行
2. 新しい `salt` と `hash` をコピー
3. [share.streamlit.io](https://share.streamlit.io) でアプリを開く
4. 右上 ⚙ → **Settings** → **Secrets** を開く
5. 古い値を新しい値で上書き → **Save**
6. アプリは数秒で再起動し、新しいパスワードで使えるようになります

---

## ❓ トラブルシューティング

### Q1. デプロイ中に `ModuleNotFoundError` が出る
→ `requirements.txt` にそのモジュールを追記して `git push`

### Q2. ログインできない（パスワード違う）
→ `generate_password_hash.py` で再生成 → Secretsを更新

### Q3. `No such file or directory: 'auth_config.json'` エラー
→ `auth.py` は secrets が設定されていれば使わないので、Secrets が正しく設定されているか確認

### Q4. スマホで文字が小さい
→ Safari の「ぁあ」ボタンで「読みやすい」を選択、または縦横回転

### Q5. GitHub push 時に `Permission denied`
→ Personal Access Token を作成して使う:
   GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic)
   scopes に `repo` をチェック → 生成 → コピー
   git push 時のパスワード欄にそのトークンを貼り付け

### Q6. Streamlit Cloud の無料枠の制限は？
- 1 GB RAM / 1 CPU
- 月 無制限時間（使わない時は自動スリープ、アクセス時に起動）
- Public 1個 + Private 1個まで無料
- このアプリは十分収まります

---

## 🛡 セキュリティチェックリスト

デプロイ前に確認：

- [ ] `auth_config.json` を GitHub に push していない
- [ ] `.streamlit/secrets.toml` を GitHub に push していない（`.example` のみOK）
- [ ] リポジトリを **Private** にしている
- [ ] 強力なパスワード（8文字以上、英数字記号混在）を使っている
- [ ] パスワードは他のサービスと使い回していない

---

## 📞 問い合わせ

問題が発生したら、このファイルの「トラブルシューティング」を参照してください。
