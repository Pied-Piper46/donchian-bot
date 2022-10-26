import time
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from cls import Batman

def main():

    chart_sec = 300

    buy_term = 30
    sell_term = 30
    judge_price = {
        "BUY": "close_price",
        "SELL": "close_price"
    }

    volatility_term = 5
    stop_range = 2
    trade_risk = 0.03
    levarage = 2

    entry_times = 2
    entry_range = 1

    trailing_config = "ON"
    stop_AF = 0.02
    stop_AF_add = 0.02
    stop_AF_max = 0.2

    filter_VER = "OFF"
    MA_term = 200

    wait = 180

    log_config = "ON"
    line_config = "ON"

    bot = Batman.Batman1G(chart_sec, buy_term, sell_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config)

    bot.print_log(f"{bot.need_term}期間分のデータを準備中...")
    price = bot.get_price(bot.chart_sec)
    last_data = price[-1 * bot.need_term -2: -2]
    bot.print_log(f"---{bot.wait}秒待機---")
    time.sleep(bot.wait)

    bot.print_log("---実行開始---")

    while True:

        data = bot.get_realtime_price(bot.chart_sec)
        if data["settled"]["close_time"] > last_data[-1]["close_time"]:
            bot.print_price(data["settled"])

        if bot.flag["position"]["exist"]:
            bot.flag = bot.stop_position(data, bot.flag)
            bot.flag = bot.close_position(data, last_data, bot.flag)
            bot.flag = bot.add_position(data, last_data, bot.flag)
        else:
            bot.flag = bot.find_unexpected_pos(last_data, bot.flag)
            bot.flag = bot.entry_signal(data, last_data, bot.flag)

        if data["settled"]["close_time"] > last_data[-1]["close_time"]:
            last_data.append(data["settled"])
            if len(last_data) > bot.need_term:
                del last_data[0]

        time.sleep(bot.wait)


if __name__ == "__main__":
    main()