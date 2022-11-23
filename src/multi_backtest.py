import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import time
from cls import BacktestMulti

def main():

    chart_sec_list = [1800, 3600, 7200]

    buy_term_list = [10, 20, 30]
    judge_price_list = [
        {"BUY": "close_price", "SELL": "close_price"},
        {"BUY": "high_price", "SELL": "low_price"}
    ]

    TEST_MODE_LOT = "adjustable"

    volatility_term_list = [5, 10, 20, 30]
    stop_range_list = [2, 3]
    trade_risk = 0.04
    levarage = 2
    start_funds = 300000

    entry_times_list = [1, 2, 3]
    entry_range_list = [0.5, 1]

    trailing_config = "TRAILING"
    stop_AF_list = [0.02, 0.03]
    stop_AF_add_list = [0.02, 0.03]
    stop_AF_max_list = [0.2, 0.3]

    slippage = 0.0005

    filter_VER_list = ["OFF", "A", "B"]
    MA_term_list = [50, 100, 200]

    wait = 0

    log_config = "OFF"
    line_config = "OFF"

    combinations = [(chart_sec, buy_term, judge_price, volatility_term, stop_range, entry_times, entry_range, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term)
        for chart_sec in chart_sec_list
        for buy_term in buy_term_list
        for judge_price in judge_price_list
        for volatility_term in volatility_term_list
        for stop_range in stop_range_list
        for entry_times in entry_times_list
        for entry_range in entry_range_list
        for stop_AF in stop_AF_list
        for stop_AF_add in stop_AF_add_list
        for stop_AF_max in stop_AF_max_list
        for filter_VER in filter_VER_list
        for MA_term in MA_term_list]

    # バックテストに必要な時間軸のチャートを全て取得
    price_list = {}
    for chart_sec in chart_sec_list:
        price_list[chart_sec] = BacktestMulti.BacktestMulti1G.get_price(chart_sec, after=1451606400)
        print(f"-----{int(chart_sec/60)}分軸の価格データをCryptowatchから取得中-----")
        time.sleep(60)

    # Main
    for chart_sec, buy_term, judge_price, volatility_term, stop_range, entry_times, entry_range, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term in combinations:

        bot = BacktestMulti.BacktestMulti1G(chart_sec, buy_term, buy_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config, start_funds, slippage, TEST_MODE_LOT)

        price = price_list[chart_sec]
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