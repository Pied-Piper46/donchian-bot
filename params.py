# for simple backtest
chart_sec = 3600
buy_term = 20
sell_term = 20
judge_price = {
    "BUY": "high_price",
    "SELL": "low_price"
}
volatility_term = 30
stop_range = 1
wait = 0
lot = 0.1
slippage = 0.001


# for multiple backtest
chart_sec_list = [1800, 3600, 7200, 21600, 43200, 86400]
# chart_sec_list = [1800, 3600]
buy_term_list = [10, 15, 20, 25, 30, 40, 45]
sell_term_list = [10, 15, 20, 25, 30, 40, 45]
judge_price_list = [
    {"BUY": "close_price", "SELL": "close_price"},
    {"BUY": "high_price", "SELL": "low_price"}
]
