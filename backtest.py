import time

from cls.backtest_class import Backtest
from params import *


def main():

    bot1 = Backtest(
                chart_sec,
                buy_term,
                sell_term,
                volatility_term,
                stop_range,
                judge_price,
                wait,
                slippage,
                trade_risk,
                levarage,
                entry_times,
                entry_range,
                start_funds,
                trail_ratio,
                trail_until_breakeven,
                stop_AF,
                stop_AF_add,
                stop_AF_max
                )

    price = bot1.get_price(after=1483228800)

    last_data = []
    i = 0

    while i < len(price):

        if len(last_data) < bot1.need_term:
            last_data.append(price[i])
            flag = bot1.log_price(price[i], bot1.flag)
            time.sleep(bot1.wait)
            i += 1
            continue

        data = price[i]
        flag = bot1.log_price(data, flag)

        if flag["position"]["exist"]:
            flag = bot1.stop_position(data, last_data, flag)
            flag = bot1.close_position(data, last_data, flag)
            flag = bot1.add_position(data, last_data, flag)
        else:
            flag = bot1.entry_signal(data, last_data, flag)

        last_data.append(data)
        i += 1
        time.sleep(bot1.wait)

    print("-----------------------")
    print("テスト期間")
    print("開始時点：" + str(price[0]["close_time_dt"]))
    print("終了時点：" + str(price[-1]["close_time_dt"]))
    print(str(len(price)) + "件のローソク足データで検証")
    print("-----------------------")

    bot1.backtest(flag)


if __name__ == '__main__':
    main()