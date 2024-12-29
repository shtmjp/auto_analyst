from pathlib import Path

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from discord_webhook import DiscordWebhook
from matplotlib.figure import Figure

from settings import DISCORD_WEBHOOK_URL


def create_candlestick_chart(symbol: str, yf_data: pd.DataFrame) -> Figure:
    tmp_df = yf_data[[(s, symbol) for s in ["Open", "High", "Low", "Close", "Volume"]]]
    tmp_df.columns = ["Open", "High", "Low", "Close", "Volume"]
    fig, axs = plt.subplots(2, 1, figsize=(8, 6), height_ratios=[2, 1], sharex=True)
    mpf.plot(tmp_df, type="candle", volume=axs[1], style="yahoo", ax=axs[0])
    return fig


def send_figure_to_discord(fig: Figure) -> None:
    fig.savefig("temp.png", bbox_inches="tight")
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    with Path("temp.png").open("rb") as f:
        webhook.add_file(file=f.read(), filename="temp.png")
        webhook.execute()
    Path("temp.png").unlink()
