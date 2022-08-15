"""
get_price() : afterを指定しないとデフォルトで1000件までしか価格データ取れない。afterを指定すると最大6000件取れる。
"""

import requests
from datetime import datetime
import time

from params import *

def get_price(min, before=0, after=0):

    price = []
    params = {"periods": min}
    if before != 0:
        params["before"] = before
    if after != 0:
        params["after"] = after

    response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc", params)
    data = response.json()

    if data["result"][str(min)] is not None:
        for i in data["result"][str(min)]:
            if i[1] != 0 and i[2] != 0 and i[3] != 0 and i[4] != 0:
                price.append({"close_time": i[0],
                    "close_time_dt": datetime.fromtimestamp(i[0]).strftime('%Y/%m/%d %H:%M'),
                    "open_price": i[1],
                    "high_price": i[2],
                    "low_price": i[3],
                    "close_price": i[4]})
        
        return price

    else:
        print("データが存在しません")
        return None


def print_price(data):
    print("時間： " + data["close_time_dt"] + " 高値： " + str(data["high_price"]) + " 安値： " + str(data["low_price"]))


def donchian(data, last_data):

    highest = max(i["high_price"] for i in last_data[(-1*buy_term): ])
    if data[judge_price["BUY"]] > highest:
        return {"side": "BUY", "price": highest}

    lowest = min(i["low_price"] for i in last_data[(-1*sell_term): ])
    if data[judge_price["SELL"]] < lowest:
        return {"side": "SELL", "price": lowest}

    return {"side": None, "price": 0}


def entry_signal(data, last_data, flag):
    
    signal = donchian(data, last_data)
    if signal["side"] == "BUY":
        print(f"過去{buy_term}足の最高値{signal['price']}円を、直近の価格が{data[judge_price['BUY']]}円でブレイクしました。")
        print(str(data["close_price"]) + "円で買いの指値注文を出します。")

        # ここに買い注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"

    if signal["side"] == "SELL":
        print(f"過去{sell_term}足の最安値{signal['price']}円を、直近の価格が{data[judge_price['SELL']]}円でブレイクしました。")
        print(str(data["close_price"]) + "円で売りの指値注文を出します。")

        # ここに売り注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"

    return flag


def check_order(flag):

    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]

    return flag


def close_position(data, last_data, flag):

    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            print(f"過去{sell_term}足の最安値{signal['price']}円を、直近の価格が{data[judge_price['SELL']]}円でブレイクしました。")
            print("成行注文を出してポジションを決済します。")

            # ここに決済の成行注文コードを入れる
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            print(f"さらに{str(data['close_price'])}円で売りの指値注文を入れてドテンします。")

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            print(f"過去{buy_term}足の最高値{signal['price']}円を、直近の価格が{data[judge_price['BUY']]}円でブレイクしました。")
            print("成行注文を出してポジションを決済します。")

            # ここに決済の成行注文コードを入れる
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            print(f"さらに{str(data['close_price'])}円で買いの指値注文を入れてドテンします。")

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"

    return flag


### Main ####

def main():
    price = get_price(chart_sec)
    last_data = []

    flag = {
        "order": {
            "exist": False,
            "side": "",
            "count": 0
        },
        "position": {
            "exist": False,
            "side": "",
            "count": 0
        }
    }

    i = 0
    while i < len(price):

        if len(last_data) < buy_term or len(last_data) < sell_term:
            last_data.append(price[i])
            print_price(price[i])
            time.sleep(wait)
            i += 1
            continue

        data = price[i]
        print_price(data)

        if flag["order"]["exist"]:
            flag = check_order(flag)
        elif flag["position"]["exist"]:
            flag = close_position(data, last_data, flag)
        else:
            flag = entry_signal(data, last_data, flag)

        last_data.append(data)
        i += 1
        time.sleep(wait)

if __name__ == '__main__':

    main()