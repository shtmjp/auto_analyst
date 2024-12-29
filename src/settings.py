import os
from pathlib import Path

from dotenv import load_dotenv

# renderの本番環境では.envは存在しないため、存在する場合のみ読み込む
# 本番環境では手動で環境変数を設定しておく
_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

# localではDISCORD_WEBHOOK_URLはデバッグ用URLを設定しておく
# 本番環境では別に設定
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
