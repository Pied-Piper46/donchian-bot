import test

import requests
from datetime import datetime
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


chart_sec = 3600
term = 20
wait = 0
lot = 0.1
slippage = 0.001


def log_price(data, flag):
    log = "時間： " + data["close_time_dt"] + " 高値： " + str(data["high_price"]) + " 安値： " + str(data["low_price"]) + "\n"
    flag["records"]["log"].append(log)
    return flag


def entry_signal(data, last_data, flag):
    
    signal = test.donchian(data, last_data)
    if signal["side"] == "BUY":
        flag["records"]["log"].append(f"過去{term}足の最高値{signal['price']}円を、直近の高値が{data['high_price']}円でブレイクしました。")
        flag["records"]["log"].append(str(data["close_price"]) + "円で買いの指値注文を出します。")

        # ここに買い注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"
        flag["order"]["price"] = round(data["close_price"] * lot)

    if signal["side"] == "SELL":
        flag["records"]["log"].append(f"過去{term}足の最安値{signal['price']}円を、直近の安値が{data['low_price']}円でブレイクしました。")
        flag["records"]["log"].append(str(data["close_price"]) + "円で売りの指値注文を出します。")

        # ここに売り注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"
        flag["order"]["price"] = round(data["close_price"] * lot)

    return flag


def check_order(flag):

    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]
    flag["position"]["price"] = flag["order"]["price"]

    return flag
    

def close_position(data, last_data, flag):

    flag["position"]["count"] += 1
    signal = test.donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            flag["records"]["log"].append(f"過去{term}足の最安値{signal['price']}円を、直近の安値が{data['low_price']}円でブレイクしました。")
            flag["records"]["log"].append(str(data['close_price']) + "円あたりで成行注文を出してポジションを決済します。")

            # ここに決済の成行注文コードを入れる
            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で売りの指値注文を入れてドテンします。")

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"
            flag["order"]["price"] = round(data["close_price"] * lot)

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            flag["records"]["log"].append(f"過去{term}足の最高値{signal['price']}円を、直近の高値が{data['high_price']}円でブレイクしました。")
            flag["records"]["log"].append(str(data['close_price']) + "円あたりで成行注文を出してポジションを決済します。")

            # ここに決済の成行注文コードを入れる
            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で買いの指値注文を入れてドテンします。")

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"
            flag["order"]["price"] = round(data["close_price"] * lot)

    return flag


def records(flag, data):

    entry_price = flag["position"]["price"]
    exit_price = round(data["close_price"] * lot)
    trade_cost = round(exit_price * slippage)

    log = "スリッページ・手数料として " + str(trade_cost) + "円を考慮します\n"
    flag["records"]["log"].append(log)
    flag["records"]["slippage"].append(trade_cost)
    flag["records"]["date"].append(data["close_time_dt"])

    buy_profit = exit_price - entry_price - trade_cost
    sell_profit = entry_price - exit_price - trade_cost

    if flag["position"]["side"] == "BUY":
        flag["records"]["buy-count"] += 1
        flag["records"]["buy-profit"].append(buy_profit)
        flag["records"]["buy-return"].append(round(buy_profit / entry_price * 100, 4))
        flag["records"]["buy-holding-periods"].append(flag["position"]["count"])
        flag["records"]["gross-profit"].append(flag["records"]["gross-profit"][-1] + buy_profit)

        if buy_profit > 0:
            flag["records"]["buy-winning"] += 1
            log = str(buy_profit) + "円の利益です\n"
            flag["records"]["log"].append(log)
        else:
            log = str(buy_profit) + "円の損失です\n"
            flag["records"]["log"].append(log)

    if flag["position"]["side"] == "SELL":
        flag["records"]["sell-count"] += 1
        flag["records"]["sell-profit"].append(sell_profit)
        flag["records"]["sell-return"].append(round(sell_profit / entry_price * 100, 4))
        flag["records"]["sell-holding-periods"].append(flag["position"]["count"])
        flag["records"]["gross-profit"].append(flag["records"]["gross-profit"][-1] + sell_profit)

        if sell_profit > 0:
            flag["records"]["sell-winning"] += 1
            log = str(sell_profit) + "円の利益です\n"
            flag["records"]["log"].append(log)
        else:
            log = str(sell_profit) + "円の損失です\n"
            flag["records"]["log"].append(log)

    drawdown = max(flag["records"]["gross-profit"]) - flag["records"]["gross-profit"][-1]
    if drawdown > flag["records"]["drawdown"]:
        flag["records"]["drawdown"] = drawdown

    return flag


def backtest(flag):

    buy_gross_profit = np.sum(flag["records"]["buy-profit"])
    sell_gross_profit = np.sum(flag["records"]["sell-profit"])

    print("バックテストの結果")
    print("---------------------------")
    print("買いエントリの成績")
    print("---------------------------")
    print(f"トレード回数：　{flag['records']['buy-count']}回")
    print(f"勝率　　　　：　{round(flag['records']['buy-winning'] / flag['records']['buy-count'] * 100, 1)}％")
    print(f"平均リターン：　{round(np.average(flag['records']['buy-return']), 2)}％")
    print(f"総損益　　　：　{np.sum(flag['records']['buy-profit'])}円")
    print(f"平均保有期間：　{round(np.average(flag['records']['buy-holding-periods']), 1)}足分")

    print("---------------------------")
    print("売りエントリの成績")
    print("---------------------------")
    print(f"トレード回数：　{flag['records']['sell-count']}回")
    print(f"勝率　　　　：　{round(flag['records']['sell-winning'] / flag['records']['sell-count'] * 100, 1)}％")
    print(f"平均リターン：　{round(np.average(flag['records']['sell-return']), 2)}％")
    print(f"総損益　　　：　{np.sum(flag['records']['sell-profit'])}円")
    print(f"平均保有期間：　{round(np.average(flag['records']['sell-holding-periods']), 1)}足分")

    print("---------------------------")
    print("総合成績")
    print("---------------------------")
    print(f"最大ドローダウン：　{-1 * flag['records']['drawdown']}円 / {-1 * round(flag['records']['drawdown'] / max(flag['records']['gross-profit']) * 100, 1)}％")
    print(f"総損益　　　：　{np.sum(flag['records']['sell-profit']) + np.sum(flag['records']['buy-profit'])}円")
    print(f"手数料合計　：　{np.sum(flag['records']['slippage'])}円")

    f = open(f"log/{datetime.now().strftime('%Y-%m-%d-%H-%M')}-backlog.txt", 'wt', encoding='utf-8')
    f.writelines(flag["records"]["log"])

    del flag["records"]["gross-profit"][0]
    data_list = pd.to_datetime(flag["records"]["date"])

    plt.plot(data_list, flag["records"]["gross-profit"])
    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.xticks(rotation = 50)

    plt.show()


def main():
    price = test.get_price(chart_sec, after=1483228800)

    flag = {
        "order": {
            "exist": False,
            "side": "",
            "price": 0,
            "count": 0
        },
        "position": {
            "exist": False,
            "side": "",
            "price": 0,
            "count": 0
        },
        "records": {
            "buy-count": 0,
            "buy-winning": 0,
            "buy-return": [],
            "buy-profit": [],
            "buy-holding-periods": [],

            "sell-count": 0,
            "sell-winning": 0,
            "sell-return": [],
            "sell-profit": [],
            "sell-holding-periods": [],

            "date": [],
            "gross-profit": [0],
            "drawdown": 0,
            "slippage": [],
            "log": []
        }
    }

    last_data = []
    i = 0
    while i < len(price):

        if len(last_data) < term:
            last_data.append(price[i])
            flag = log_price(price[i], flag)
            time.sleep(wait)
            i += 1
            continue
        
        data = price[i]
        flag = log_price(data, flag)

        if flag["order"]["exist"]:
            flag = check_order(flag)
        elif flag["position"]["exist"]:
            flag = close_position(data, last_data, flag)
        else:
            flag = entry_signal(data, last_data, flag)

        del last_data[0]
        last_data.append(data)
        i += 1
        time.sleep(wait)

    print("-----------------------")
    print("テスト期間")
    print("開始時点：" + str(price[0]["close_time_dt"]))
    print("終了時点：" + str(price[-1]["close_time_dt"]))
    print(str(len(price)) + "件のローソク足データで検証")
    print("-----------------------")

    backtest(flag)


if __name__ == '__main__':
    main()