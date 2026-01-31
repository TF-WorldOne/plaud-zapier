import os
import json
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Zapier WebhookのURL
ZAPIER_WEBHOOK_URL = os.getenv('ZAPIER_WEBHOOK_URL')

# カテゴリリスト(必要に応じてカスタマイズしてください)
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


def categorize_text(text):
    """
    OpenAI GPTを使ってテキストをカテゴリ分類する
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""あなたは音声メモを分類するアシスタントです。
以下のカテゴリのいずれかに分類してください:
{', '.join(CATEGORIES)}

テキストの内容を分析し、最も適切なカテゴリを1つ選んでください。
カテゴリ名のみを返答してください。"""
                },
                {
                    "role": "user",
                    "content": f"以下のテキストを分類してください:\n\n{text}"
                }
            ],
            temperature=0.3,
            max_tokens=50
        )

        category = response.choices[0].message.content.strip()

        # カテゴリが有効かチェック
        if category in CATEGORIES:
            return category
        else:
            return "その他"

    except Exception as e:
        print(f"カテゴリ分類エラー: {str(e)}")
        return "その他"


def send_to_zapier(data):
    """
    Zapier Webhookにデータを送信する
    """
    try:
        response = requests.post(
            ZAPIER_WEBHOOK_URL,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        return True, "Zapierへの送信成功"
    except Exception as e:
        error_msg = f"Zapierへの送信エラー: {str(e)}"
        print(error_msg)
        return False, error_msg


@app.route('/webhook/plaud', methods=['POST'])
def plaud_webhook():
    """
    PlaudからのWebhookを受け取るエンドポイント
    """
    try:
        # リクエストデータを取得
        data = request.json
        print(f"受信データ: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # Plaudからのデータ構造に応じて調整が必要
        # 仮の構造を想定:
        # {
        #   "transcription": "文字起こしされたテキスト",
        #   "timestamp": "2024-01-01T12:00:00",
        #   "duration": 120,
        #   "audio_url": "https://...",
        #   ...
        # }

        transcription = data.get('transcription') or data.get('text') or data.get('content', '')

        if not transcription:
            return jsonify({
                'success': False,
                'error': '文字起こしテキストが見つかりません'
            }), 400

        # OpenAI APIでカテゴリを判定
        category = categorize_text(transcription)
        print(f"判定されたカテゴリ: {category}")

        # Zapierに送信するデータを整形
        zapier_data = {
            'text': transcription,
            'category': category,
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'duration': data.get('duration'),
            'audio_url': data.get('audio_url'),
            'original_data': data  # 元のデータも送信
        }

        # Zapierに送信
        success, message = send_to_zapier(zapier_data)

        if success:
            return jsonify({
                'success': True,
                'category': category,
                'message': 'Notionへの送信をZapierに依頼しました'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500

    except Exception as e:
        error_msg = f"エラー: {str(e)}"
        print(error_msg)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    ヘルスチェックエンドポイント
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/test', methods=['POST'])
def test_endpoint():
    """
    テスト用エンドポイント
    """
    test_text = request.json.get('text', 'これはテストメモです。明日の会議の準備をする必要があります。')

    category = categorize_text(test_text)

    return jsonify({
        'text': test_text,
        'category': category
    }), 200


if __name__ == '__main__':
    # 環境変数のチェック
    if not os.getenv('OPENAI_API_KEY'):
        print("警告: OPENAI_API_KEYが設定されていません")
    if not os.getenv('ZAPIER_WEBHOOK_URL'):
        print("警告: ZAPIER_WEBHOOK_URLが設定されていません")

    # サーバー起動
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
