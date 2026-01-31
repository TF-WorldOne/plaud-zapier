# Plaud → Zapier → Notion 連携システム

Plaudで録音した音声メモを自動的にNotionにカテゴリ分けして記録するシステムです。

## システム構成

```
Plaud (音声録音 + 文字起こし)
  ↓ Webhook
Webhook Server (このアプリ)
  ↓ OpenAI GPT でカテゴリ自動判定
  ↓ Webhook
Zapier
  ↓
Notion (カテゴリ分けして保存)
```

## 機能

- PlaudからのWebhookを受信
- OpenAI GPT-4を使った自動カテゴリ分類
- Zapier経由でNotionに送信
- 以下のカテゴリに自動分類:
  - 仕事
  - プライベート
  - アイデア
  - TODO
  - メモ
  - 会議
  - 学習
  - その他

## セットアップ手順（Renderで無料ホスティング）

### 1. 必要なもの

- GitHubアカウント
- Renderアカウント（無料）
- OpenAI API Key
- Zapier アカウント
- Notion アカウント
- Plaud デバイス

### 2. GitHubにコードをプッシュ

```bash
# 現在のディレクトリで実行（既にGit初期化済み）
git add .
git commit -m "Initial commit: Plaud to Notion webhook server"

# GitHubで新しいリポジトリを作成してから実行
git remote add origin https://github.com/YOUR_USERNAME/plaud-zapier.git
git branch -M main
git push -u origin main
```

### 3. Renderでデプロイ

1. [Render](https://render.com) にアクセスしてサインアップ/ログイン
2. ダッシュボードで「New +」→「Web Service」を選択
3. GitHubアカウントを連携
4. 先ほど作成したリポジトリを選択
5. 以下の設定を入力:
   - **Name**: `plaud-zapier-webhook` (任意)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -b 0.0.0.0:$PORT webhook_server:app`
   - **Plan**: `Free`

6. 「Advanced」を開いて環境変数を追加:
   - `OPENAI_API_KEY`: あなたのOpenAI API Key
   - `ZAPIER_WEBHOOK_URL`: 後で設定（一旦空でOK）

7. 「Create Web Service」をクリック

8. デプロイが完了したら、URLが表示されます（例: `https://plaud-zapier-webhook.onrender.com`）

### 4. Zapier の設定

1. [Zapier](https://zapier.com) にログイン
2. 新しいZap(自動化ワークフロー)を作成
3. **トリガー**を設定:
   - アプリ: "Webhooks by Zapier" を選択
   - イベント: "Catch Hook" を選択
   - Webhook URLをコピーして `.env` ファイルの `ZAPIER_WEBHOOK_URL` に設定

4. **アクション**を設定:
   - アプリ: "Notion" を選択
   - イベント: "Create Database Item" を選択
   - Notionアカウントを接続
   - データベースを選択
   - フィールドをマッピング:
     - `text` → メモ内容
     - `category` → カテゴリ
     - `timestamp` → 作成日時
     - `audio_url` → 音声ファイルURL(オプション)

5. Zapをオンにする

### 5. Notion の準備

Notionでメモ用のデータベースを作成し、以下のプロパティを追加:

| プロパティ名 | タイプ | 説明 |
|------------|--------|------|
| タイトル | タイトル | メモのタイトル(最初の50文字など) |
| 内容 | テキスト | メモの本文 |
| カテゴリ | セレクト | カテゴリ(仕事、プライベート、アイデア、TODO、メモ、会議、学習、その他) |
| 作成日時 | 日付 | メモの作成日時 |
| 音声URL | URL | 音声ファイルのURL(オプション) |

### 6. Plaud の設定

1. Plaudアプリを開く
2. 設定 → Webhook設定を開く
3. Webhook URLに以下を設定:
   ```
   https://your-render-app.onrender.com/webhook/plaud
   ```
   ※ `your-render-app` の部分はRenderで作成したサービスのURLに置き換えてください

4. Webhookを有効化

### 7. 動作確認

1. Renderのサービスページで「Logs」タブを開く
2. Plaudで音声メモを録音
3. Renderのログにリクエストが表示されることを確認
4. Notionのデータベースに新しいエントリが追加されることを確認

## テスト

### ヘルスチェック

```bash
curl http://localhost:5000/health
```

### カテゴリ分類のテスト

```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{"text": "明日の会議の資料を準備する必要がある"}'
```

### Webhook のテスト

```bash
curl -X POST http://localhost:5000/webhook/plaud \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "今日のミーティングで新しいプロジェクトについて話し合った",
    "timestamp": "2024-01-31T10:00:00",
    "duration": 120
  }'
```

## カスタマイズ

### カテゴリの変更

[webhook_server.py](webhook_server.py) の `CATEGORIES` リストを編集してカテゴリをカスタマイズできます:

```python
CATEGORIES = [
    "仕事",
    "プライベート",
    "アイデア",
    "TODO",
    "メモ",
    "会議",
    "学習",
    "その他"
]
```

### AIモデルの変更

OpenAI APIのモデルを変更する場合は、[webhook_server.py:36](webhook_server.py#L36) の `model` パラメータを変更してください:

```python
model="gpt-4o-mini",  # gpt-4, gpt-4-turbo 等に変更可能
```

## トラブルシューティング

### Plaudからのデータが受信できない

1. サーバーが起動しているか確認
2. ngrokを使っている場合、URLが正しいか確認
3. Plaudの Webhook 設定が正しいか確認
4. ファイアウォールでポートがブロックされていないか確認

### カテゴリ分類がうまくいかない

1. OpenAI API Keyが正しいか確認
2. APIの利用制限に達していないか確認
3. カテゴリリストを見直してより明確な分類にする

### Zapierにデータが送信されない

1. Zapier Webhook URLが正しいか確認
2. Zapier Zapがオンになっているか確認
3. サーバーのログでエラーメッセージを確認

## ライセンス

MIT License

## サポート

問題が発生した場合は、Issueを作成してください。
