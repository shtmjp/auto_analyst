import pandas as pd
import requests

from settings import NEWS_API_KEY


def fetch_news(
    query: str,
    from_date: str,  # like "2024-12-01"
    to_date: str,  # like "2024-12-23"
    language: str = "en",
) -> pd.DataFrame:
    """Fetch news from NewsAPI."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": language,
        "sortBy": "relevancy",
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(url, params=params, timeout=100)
    data = response.json()
    if data.get("status") == "ok":
        news_list = data.get("articles", [])
        return pd.DataFrame(
            [
                {
                    "source": news["source"]["name"],
                    "title": news["title"],
                    "description": news["description"],
                    "publishedAt": news["publishedAt"],
                    "URL": news["url"],
                }
                for news in news_list
            ]
        )
    return pd.DataFrame()


def important_news_to_str(news_df: pd.DataFrame, n: int) -> str:
    """Top nの関連ニュースと最新n件のニュースを抽出し, strに変換する."""
    titles = []
    # top relevant news
    prompt = f"Top {n} relevant news:\n\n"
    for _, row in news_df.iloc[:n].iterrows():
        titles.append(row["title"])
        prompt += f"{row['title']}\n"
        prompt += f"Source: {row['source']}\n"
        prompt += f"Published at: {row['publishedAt']}\n"
        prompt += f"Description: {row['description']}\n"
        prompt += f"URL: {row['URL']}\n\n"
    # latest news
    prompt += f"Top {n} latest news:\n\n"
    c = 0
    for _, row in news_df.sort_values("publishedAt", ascending=False).iterrows():
        title = row["title"]
        if title in titles:  # avoid duplication
            continue
        if c == n:
            break
        prompt += f"{row['title']}\n"
        prompt += f"Source: {row['source']}\n"
        prompt += f"Published at: {row['publishedAt']}\n"
        prompt += f"Description: {row['description']}\n"
        prompt += f"URL: {row['URL']}\n\n"
        c += 1
    return prompt
