import time
from io import StringIO

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook
from langchain_google_genai import ChatGoogleGenerativeAI

from bs_pl import get_financial_summary
from figure import create_candlestick_chart, send_figure_to_discord
from news import fetch_news, important_news_to_str
from settings import DISCORD_WEBHOOK_URL


def fetch_sp500_metadata() -> pd.DataFrame:
    """WikipediaからS&P500のメタデータを取得する.

    Returns:
        pd.DataFrame: S&P500のメタデータ

    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    html_table = str(table)
    metadata_df = pd.read_html(StringIO(html_table))[0]

    metadata_df.loc[metadata_df["Symbol"] == "BRK.B", "Symbol"] = "BRK-B"
    metadata_df.loc[metadata_df["Symbol"] == "BF.B", "Symbol"] = "BF-B"
    return metadata_df


def get_stat_summary(symbol: str, monthly_stat_df: pd.DataFrame) -> str:
    row = monthly_stat_df[monthly_stat_df["Symbol"] == symbol].iloc[0]
    security = row["Security"]
    latest_return = row["latest_return"]
    monthly_return = row["monthly_return"]
    sigma = row["monthly_sigma"]
    return f"""
        # {security} ({symbol})
        - 直近1日のリターン: {latest_return:.2%}
        - 過去1ヶ月のリターン: {monthly_return:.2%}
        - 1ヶ月リターンの1sigma範囲: ±{sigma:.2%}
        """


def get_company_summary_prompt(symbol: str) -> str:
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return f"""
    以下は{info["shortName"]}の事業内容です。事業内容を3つの簡単な箇条書きで記載してください。
    - 業種: {info["sector"]}
    - 産業: {info["industry"]}
    - 事業内容: {info["longBusinessSummary"]}
    """


def get_report_prompt(
    symbol: str, monthly_stat_df: pd.DataFrame, min_date: str, max_date: str
) -> str:
    target_security = str(monthly_stat_df[monthly_stat_df["Symbol"] == symbol]["Security"].iloc[0])

    news_df = fetch_news(target_security, min_date, max_date, "en")
    prompt = get_stat_summary(symbol, monthly_stat_df)
    prompt += "以下は関連するニュースです。\n" + important_news_to_str(news_df, n=3)
    prefix_prompt = """
    以下は、S&P500の株式に関する情報です。
    ニュースと関連付けて、今後の動向について予測してください。
    ニュースの情報を利用する際は、参照したニュースのタイトル、ソース、公開日時、URLを明記してください。
    以下のフォーマットで回答してください。
    関連ニュースは3つまで記載してください。
    今後の動向については、簡単なコメントを3つ記載してください。
    全体で1000文字は超えないようにしてください。

    ## 数値情報の分析
    例: 過去1ヶ月のリターンは、1シグマ範囲を大きく上回っており、非常に高い上昇を示している。
    ## 関連ニュース
    1. [ニュースタイトル, 発行日時](URL)
    ニュースの要約
    2. [ニュースタイトル, 発行日時](URL)
    ニュースの要約
    3. [ニュースタイトル, 発行日時](URL)
    ニュースの要約
    ## 今後の動向について
    - 短いコメント
    - 短いコメント
    - 短いコメント
    """
    return prefix_prompt + prompt


def post_to_discord(message: str) -> None:
    webhook = DiscordWebhook(
        url=DISCORD_WEBHOOK_URL,
        content=message,
        rate_limit_retry=True,
    )
    webhook.remove_embeds()
    webhook.execute()


def main() -> None:
    # get stock price data
    metadata_df = fetch_sp500_metadata()
    symbols = metadata_df["Symbol"].tolist()
    yf_data = yf.download(tickers=symbols, interval="1d", period="1mo")
    close_df = yf_data["Close"]  # type: ignore[attr-defined]
    close_df = close_df.dropna(axis=1)  # type: ignore[attr-defined]
    return_df = close_df.pct_change().dropna()

    # calculate monthly statistics
    t = len(return_df)
    latest_ret = return_df.iloc[-1].to_numpy()
    monthly_ret = ((close_df.iloc[-1] - close_df.iloc[0]) / close_df.iloc[0]).to_numpy()
    monthly_sigma = (close_df.pct_change().dropna().std(axis=0) * (t**0.5)).to_numpy()
    symbols = return_df.columns.to_numpy()
    monthly_stat_df = pd.DataFrame(
        {
            "Symbol": symbols,
            "monthly_return": monthly_ret,
            "monthly_sigma": monthly_sigma,
            "latest_return": latest_ret,
        }
    )
    monthly_stat_df = monthly_stat_df.merge(
        metadata_df[["Symbol", "GICS Sector", "Security"]],
        left_on="Symbol",
        right_on="Symbol",
    )

    monthly_stat_df["mu/sigma"] = (
        monthly_stat_df["monthly_return"] / monthly_stat_df["monthly_sigma"]
    )

    # top_3_symbols = (
    #     monthly_stat_df.sort_values("latest_return", ascending=False).iloc[:3]["Symbol"].tolist()
    # )
    # bottom_3_symbols = monthly_stat_df.sort_values("latest_return").iloc[:3]["Symbol"].tolist()

    random_symbols = monthly_stat_df.sample(3)["Symbol"].tolist()

    dates = pd.to_datetime(close_df.index).sort_values()
    min_date, max_date = dates.strftime("%Y-%m-%d")[[0, -1]]

    # for symbol in top_3_symbols + bottom_3_symbols:
    for symbol in random_symbols:
        # 数値情報の表示
        stat_summary = get_stat_summary(symbol, monthly_stat_df)
        bs_pl = get_financial_summary(symbol)
        post_to_discord(stat_summary + bs_pl)
        time.sleep(1)
        # チャートの表示
        fig = create_candlestick_chart(symbol, yf_data)  # type: ignore[assignment]
        send_figure_to_discord(fig)
        time.sleep(1)
        # 事業内容の要約
        company_summary_prompt = get_company_summary_prompt(symbol)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        ai_message = llm.invoke(company_summary_prompt)
        post_to_discord("## 事業内容\n" + str(ai_message.content))
        time.sleep(5)
        # AIによる要約の生成
        prompt = get_report_prompt(symbol, monthly_stat_df, min_date, max_date)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        ai_message = llm.invoke(prompt)
        post_to_discord(str(ai_message.content))
        time.sleep(10)


if __name__ == "__main__":
    main()
