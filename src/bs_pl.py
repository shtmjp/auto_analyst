import yfinance as yf


def format_large_number(number: int) -> str:
    """大きな数値を「億」や「兆」といった単位でフォーマットする.

    Args:
        number (int): フォーマット対象の数値。

    Returns:
        str: フォーマット済みの文字列。

    """
    if number is None or number == "N/A":
        return "N/A"

    if number >= 10**12:  # 兆
        return f"{number / 10**12:.2f} 兆"
    if number >= 10**8:  # 億
        return f"{number / 10**8:.2f} 億"
    return f"{number:,}"


def get_financial_summary(symbol: str) -> str:
    """指定された株式シンボルの重要な財務指標を取得し、Discord用のフォーマットで返す.

    Args:
        symbol (str): 株式のシンボル. 例: "AAPL"

    Returns:
        str: Discordに投稿する形式の財務指標要約。

    """
    # yfinanceを使用して企業情報を取得
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # 必要な指標を抽出
    market_cap = format_large_number(info.get("marketCap", "N/A"))
    total_revenue = format_large_number(info.get("totalRevenue", "N/A"))
    gross_margins = info.get("grossMargins", "N/A")
    trailing_pe = info.get("trailingPE", "N/A")
    pbr = info.get("priceToBook", "N/A")

    # 負債資本比率を計算
    debt_to_equity = (
        f"{info['totalDebt'] / info['totalStockholderEquity']:.2f}"
        if info.get("totalDebt") and info.get("totalStockholderEquity")
        else "N/A"
    )

    return f"""
    ## 財務情報\n
    *時価総額 (Market Cap):* {market_cap}\n
    💰 *売上高 (Revenue):* {total_revenue}\n
    📊 *売上総利益率 (Gross Margins):* {gross_margins * 100:.2f}%\n
    🏦 *負債資本比率 (Debt-to-Equity):* {debt_to_equity}\n
    📈 *PER (Trailing P/E):* {trailing_pe}\n
    📚 *PBR (Price-to-Book Ratio):* {pbr}\n
    """
