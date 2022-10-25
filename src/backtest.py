import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from cls import Backtest

def main():

    chart_sec = 3600

    buy_term = 30
    sell_term = 30
    judge_price = {
        "BUY": "close_price",
        "SELL": "close_price"
    }

    TEST_MODE_LOT = "adjustable" # "fixed" / "adjustable"

    volatility_term = 5
    stop_range = 2
    trade_risk = 0.03
    levarage = 2
    start_funds = 300000

    entry_times = 2
    entry_range = 1

    trailing_config = "ON"
    stop_AF = 0.02
    stop_AF_add = 0.02
    stop_AF_max = 0.2

    slippage = 0.0005

    filter_VER = "A"
    MA_term = 200

    wait = 0 # バックテストのため固定

    log_config = "ON"
    line_config = "OFF" # バックテストのため固定

    bot = Backtest.Backtest1G(chart_sec, buy_term, sell_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config, start_funds, slippage, TEST_MODE_LOT)

    price = bot.get_price(bot.chart_sec, after=1451606400)
    last_data = []

    i = 0
    while i < len(price):

        if len(last_data) < bot.need_term:
            last_data.append(price[i])
            bot.print_price(price[i])
            i += 1
            continue

        data = price[i]
        bot.print_price(data)

        if bot.flag["position"]["exist"]:
            if bot.trailing_config != "OFF":
                bot.flag = bot.stop_position(data, last_data, bot.flag)
            bot.flag = bot.close_position(data, last_data, bot.flag)
            bot.flag = bot.add_position(data, last_data, bot.flag)
        else:
            bot.flag = bot.entry_signal(data, last_data, bot.flag)

        last_data.append(data)
        i += 1
    
    bot.backtest(bot.flag)


if __name__ == "__main__":

    main()