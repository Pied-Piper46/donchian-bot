"""
get_price() : afterを指定しないとデフォルトで1000件までしか価格データ取れない。afterを指定すると最大6000件取れる。
"""

import requests
from datetime import datetime
import time
import numpy as np

from params import *

class Batman:

    log_file = "trade-log/test_"
    min_size = 0.01

    def __init__(self, chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, trade_risk, levarage):

        self.chart_sec = chart_sec
        self.buy_term = buy_term
        self.sell_term = sell_term

        self.judge_price = judge_price

        self.volatility_term = volatility_term
        self.stop_range = stop_range
        self.trade_risk = trade_risk
        self.levarage = levarage

        self.wait = wait

        self.flag = {
            "order": {
                "exist": False,
                "side": "",
                "price": 0,
                "ATR": 0,
                "count": 0
            },
            "position": {
                "exist": False,
                "side": "",
                "price": 0,
                "ATR": 0,
                "count": 0
            },
            "records": {
                "log": []
            }
        }

        self.need_term = max(self.buy_term, self.sell_term, self.volatility_term)


    def get_price(self, before=0, after=0):

        price = []
        params = {"periods": self.chart_sec}
        if before != 0:
            params["before"] = before
        if after != 0:
            params["after"] = after

        response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc", params)
        data = response.json()

        if data["result"][str(self.chart_sec)] is not None:
            for i in data["result"][str(self.chart_sec)]:
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


    def bitflyer_collateral(self):

        while True:
            try:
                collateral = bitflyer.private_get_getcollateral()
                print(f"現在のアカウント残高は{int(collateral['collateral'])}円です。")
                return int(collateral["collateral"])
            except ccxt.BaseError as e:
                print("BitflyerのAPIでの口座残高取得に失敗しました：", e)
                print("20秒待機してやり直します。")
                time.sleep(20)


    def log_price(self, data, flag):
        
        log = "時間： " + data["close_time_dt"] + " 高値： " + str(data["high_price"]) + " 安値： " + str(data["low_price"]) + "\n"
        flag["records"]["log"].append(log)
        return flag


    def calculate_volatility(self, last_data, flag):

        high_sum = sum(i["high_price"] for i in last_data[-1 * self.volatility_term:])
        low_sum = sum(i["low_price"] for i in last_data[-1 * self.volatility_term:])
        volatility = round((high_sum - low_sum) / self.volatility_term)
        flag["records"]["log"].append(f"現在の{self.volatility_term}期間の平均ボラティリティは{volatility}円です。\n")

        return volatility


    def calculate_lot(self, last_data, data, flag):

        balance = self.bitflyer_collateral()

        volatility = self.calculate_volatility(last_data, flag)
        stop = self.stop_range * volatility

        calc_lot = np.floor(balance * self.trade_risk / stop * 100) / 100
        able_lot = np.floor(balance * self.levarage / data["close_price"] * 100) / 100
        lot = min(calc_lot, able_lot)

        flag["records"]["log"].append(f"現在のアカウント残高は{balance}円です。\n")
        flag["records"]["log"].append(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
        flag["records"]["log"].append(f"証拠金から購入できる枚数は最大{able_lot}BTCまでです。")

        return lot, stop


    def donchian(self, data, last_data):

        highest = max(i["high_price"] for i in last_data[(-1*self.buy_term): ])
        if data[self.judge_price["BUY"]] > highest:
            return {"side": "BUY", "price": highest}

        lowest = min(i["low_price"] for i in last_data[(-1*self.sell_term): ])
        if data[self.judge_price["SELL"]] < lowest:
            return {"side": "SELL", "price": lowest}

        return {"side": None, "price": 0}


    def entry_signal(self, data, last_data, flag):
    
        signal = self.donchian(data, last_data)
        if signal["side"] == "BUY":
            flag["records"]["log"].append(f"過去{self.buy_term}足の最高値{signal['price']}円を、直近の価格が{data[self.judge_price['BUY']]}円でブレイクしました。")

            lot, stop = self.calculate_lot(last_data, data, flag)
            if lot > Batman.min_size:
                flag["records"]["log"].append(f"{data['close_price']}円で{lot}BTCの買い指値注文を出します。\n")

                # ここに買い注文のコードを入れる
                flag["records"]["log"].append(f"{data['close_price'] - stop}円にストップを入れます。\n")
                flag["order"]["lot"] = lot
                flag["order"]["stop"] = stop
                flag["order"]["exist"] = True
                flag["order"]["side"] = "BUY"
                flag["order"]["price"] = data["close_price"]
            else:
                flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        if signal["side"] == "SELL":
            flag["records"]["log"].append(f"過去{self.sell_term}足の最安値{signal['price']}円を、直近の価格が{data[self.judge_price['SELL']]}円でブレイクしました。")

            lot, stop = self.calculate_lot(last_data, data, flag)
            if lot > Batman.min_size:
                flag["records"]["log"].append(f"{data['close_price']}円で{lot}BTCの売り指値注文を出します。\n")

                # ここに売り注文のコードを入れる
                flag["records"]["log"].append(f"{data['close_price'] + stop}円にストップを入れます。\n")
                flag["order"]["lot"] = lot
                flag["order"]["stop"] = stop
                flag["order"]["exist"] = True
                flag["order"]["side"] = "SELL"
                flag["order"]["price"] = data["close_price"]
            else:
                flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        return flag


    def check_order(self, flag):

        flag["order"]["exist"] = False
        flag["order"]["count"] = 0
        flag["position"]["exist"] = True
        flag["position"]["side"] = flag["order"]["side"]
        flag["position"]["stop"] = flag["order"]["stop"]
        flag["position"]["price"] = flag["order"]["price"]
        flag["position"]["lot"] = flag["order"]["lot"]

        return flag

    
    def close_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        flag["position"]["count"] += 1
        signal = self.donchian(data, last_data)

        if flag["position"]["side"] == "BUY":
            if signal["side"] == "SELL":
                flag["records"]["log"].append(f"過去{self.sell_term}足の最安値{signal['price']}円を、直近の価格が{data[self.judge_price['SELL']]}円でブレイクしました。")
                flag["records"]["log"].append(str(data['close_price']) + "円あたりで成行注文を出してポジションを決済します。\n")

                # ここに決済の成行注文コードを入れる
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

                lot, stop = self.calculate_lot(last_data, data, flag)
                if lot > min_size:
                    flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で{lot}BTCの売り指値注文を入れてドテンします。\n")

                    # ここに売り注文のコードを入れる
                    flag["records"]["log"].append(f"{data['close_price'] + stop}円にストップを入れます。\n")
                    flag["order"]["lot"] = lot
                    flag["order"]["stop"] = stop
                    flag["order"]["price"] = data["close_price"]
                    flag["order"]["exist"] = True
                    flag["order"]["side"] = "SELL"
                else:
                    flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        if flag["position"]["side"] == "SELL":
            if signal["side"] == "BUY":
                flag["records"]["log"].append(f"過去{self.buy_term}足の最高値{signal['price']}円を、直近の価格が{data[self.judge_price['BUY']]}円でブレイクしました。")
                flag["records"]["log"].append(str(data['close_price']) + "円あたりで成行注文を出してポジションを決済します。\n")

                # ここに決済の成行注文コードを入れる
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

                lot, stop = self.calculate_lot(last_data, data, flag)
                if lot > min_size:
                    flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で{lot}BTCの買い指値注文を入れてドテンします。\n")

                    # ここに売り注文のコードを入れる
                    flag["records"]["log"].append(f"{data['close_price'] - stop}円にストップを入れます。\n")
                    flag["order"]["lot"] = lot
                    flag["order"]["stop"] = stop
                    flag["order"]["price"] = data["close_price"]
                    flag["order"]["exist"] = True
                    flag["order"]["side"] = "BUY"
                else:
                    flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        return flag


    def stop_position(self, data, last_data, flag):

        if flag["position"]["side"] == "BUY":
            stop_price = flag["position"]["price"] - flag["position"]["stop"]
            if data["low_price"] < stop_price:
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。")
                stop_price = round(stop_price - 2 * self.calculate_volatility(last_data) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # 成行注文コードを入れる
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        if flag["position"]["side"] == "SELL":
            stop_price = flag["position"]["price"] + flag["position"]["stop"]
            if data["high_price"] > stop_price:
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。")
                stop_price = round(stop_price + 2 * self.calculate_volatility(last_data) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # 成行注文コードを入れる
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        return flag

    
    def output_log(self, log_file, data):
        f = open(f"{log_file}{datetime.now().strftime('%Y-%m-%d-%H-%M')}.txt", 'wt', encoding='utf-8')
        f.writelines(data)


### Main ####
def main():
    bot1 = Batman(chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, trade_risk, levarage)
    price = bot1.get_price(after=1483228800)

    last_data = []
    need_term = bot1.need_term
    flag = bot1.flag

    i = 0
    while i < len(price):

        if len(last_data) < need_term:
            last_data.append(price[i])
            flag = bot1.log_price(price[i], flag)
            time.sleep(bot1.wait)
            i += 1
            continue

        data = price[i]
        flag = bot1.log_price(data, flag)

        if flag["order"]["exist"]:
            flag = bot1.check_order(flag)
        elif flag["position"]["exist"]:
            flag = bot1.stop_position(data, last_data, flag)
            flag = bot1.close_position(data, last_data, flag)
        else:
            flag = bot1.entry_signal(data, last_data, flag)

        last_data.append(data)
        i += 1
        time.sleep(bot1.wait)

    print("--------------------")
    print("テスト期間")
    print("開始時点：" + str(price[0]["close_time_dt"]))
    print("終了時点：" + str(price[-1]["close_time_dt"]))
    print(str(len(price)) + "件のローソク足データで検証")
    print("--------------------")

    bot1.output_log(Batman.log_file, flag["records"]["log"])
    

if __name__ == '__main__':
    main()