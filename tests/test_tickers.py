from swingbot.tickers import load_tickers


def test_load_tickers_reads_csv(tmp_path):
    csv_file = tmp_path / "tickers.csv"
    csv_file.write_text("ticker\nAAPL\nMSFT\n\nGOOGL\n")

    result = load_tickers(csv_file)

    assert result == ["AAPL", "MSFT", "GOOGL"]
