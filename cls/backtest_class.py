"""
get_price() : afterを指定しないとデフォルトで1000件までしか価格データ取れない。afterを指定すると最大6000件取れる。
"""

import requests
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class Backtest:

    log_file = "trade-log/backtest_"
    min_size = 0.001

    def __init__(self, chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, slippage, trade_risk, levarage, entry_times, entry_range, start_funds, trail_ratio, trail_until_breakeven, stop_AF, stop_AF_add, stop_AF_max):

        self.chart_sec = chart_sec
        self.buy_term = buy_term
        self.sell_term = sell_term

        self.judge_price = judge_price

        self.volatility_term = volatility_term
        self.stop_range = stop_range
        self.trade_risk = trade_risk
        self.levarage = levarage

        self.start_funds = start_funds

        self.entry_times = entry_times
        self.entry_range = entry_range

        self.stop_AF = stop_AF
        self.stop_AF_add = stop_AF_add
        self.stop_AF_max = stop_AF_max

        self.wait = wait
        self.slippage = slippage

        if trail_ratio > 1:
            self.trail_ratio = 1
        elif trail_ratio < 0:
            self.trail_ratio = 0
        else:
            self.trail_ratio = trail_ratio
        
        self.trail_until_breakeven = trail_until_breakeven

        self.flag = {
            "position": {
                "exist": False,
                "side": "",
                "price": 0,
                "stop": 0,
                "stop-AF": self.stop_AF,
                "stop-EP": 0,
                "ATR": 0,
                "lot": 0,
                "count": 0
            },
            "add-position": {
                "count": 0,
                "first-entry-price": 0,
                "last-entry-price": 0,
                "unit-range": 0,
                "unit-size": 0,
                "stop": 0
            },
            "records": {
                "date": [],
                "profit": [],
                "return": [],
                "side": [],
                "stop-count": [],
                "funds": self.start_funds,
                "holding-periods": [],
                "slippage": [],
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


    def calculate_lot(self, last_data, data, flag): # TODO: lotの小数点以下切り捨ての位を可変に（現状小数点第４位以下(1000)切り捨て）

        balance = flag["records"]["funds"]

        if flag["add-position"]["count"] == 0:
            volatility = self.calculate_volatility(last_data, flag)
            stop = self.stop_range * volatility
            calc_lot = np.floor(balance * self.trade_risk / stop * 1000) / 1000

            flag["add-position"]["unit-size"] = np.floor(calc_lot / self.entry_times * 1000) / 1000
            flag["add-position"]["unit-range"] = round(volatility * self.entry_range)
            flag["add-position"]["stop"] = stop
            flag["position"]["ATR"] = round(volatility)

            flag["records"]["log"].append(f"\n現在のアカウント残高は{balance}円です。\n")
            flag["records"]["log"].append(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。\n")
            flag["records"]["log"].append(f"{self.entry_times}回に分けて{flag['add-position']['unit-size']}BTCずつ注文します\n")

        else:
            balance = round(balance - flag["position"]["price"] * flag["position"]["lot"] / self.levarage)

        stop = flag["add-position"]["stop"]

        able_lot = np.floor(balance * self.levarage / data["close_price"] * 1000) / 1000
        lot = min(flag["add-position"]["unit-size"], able_lot)

        flag["records"]["log"].append(f"証拠金から購入できる枚数は最大{able_lot}BTCまでです。")

        return lot, stop, flag


    def add_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        if flag["add-position"]["count"] == 0:
            flag["add-position"]["first-entry-price"] = flag["position"]["price"]
            flag["add-position"]["last-entry-price"] = flag["position"]["price"]
            flag["add-position"]["count"] += 1

        while True:

            if flag["add-position"]["count"] >= self.entry_times:
                return flag

            first_entry_price = flag["add-position"]["first-entry-price"]
            last_entry_price = flag["add-position"]["last-entry-price"]
            unit_range = flag["add-position"]["unit-range"]
            current_price = data["close_price"]

            should_add_position = False
            if flag["position"]["side"] == "BUY" and (current_price - last_entry_price) > unit_range:
                should_add_position = True
            elif flag["position"]["side"] == "SELL" and (last_entry_price - current_price) > unit_range:
                should_add_position = True
            else:
                break

            if should_add_position:
                flag["records"]["log"].append(f"\n前回のエントリー価格{last_entry_price}円からブレイクアウトの方向に{self.entry_range}ATR（{round(unit_range)}）円以上動きました。\n")
                flag["records"]["log"].append(f"{flag['add-position']['count'] + 1}/{self.entry_times}回目の追加注文を出します。\n")

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot < Backtest.min_size:
                    flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")
                    return flag

                if flag["position"]["side"] == "BUY":
                    entry_price = first_entry_price + (flag["add-position"]["count"] * unit_range) # バックテスト用
                    # entry_price = round((1 + self.slippage) * entry_price)

                    flag["records"]["log"].append(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの買い注文を出します。\n")

                    # TODO: ここに買い注文のコードを入れる

                if flag["position"]["side"] == "SELL":
                    entry_price = first_entry_price - (flag["add-position"]["count"] * unit_range) # バックテスト用
                    # entry_price = round((1 - self.slippage) * entry_price)

                    flag["records"]["log"].append(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの売り注文を出します。\n")

                    # TODO: ここに売り注文のコードを入れる

                flag["position"]["stop"] = stop
                flag["position"]["price"] = int(round((flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (flag["position"]["lot"] + lot)))
                flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

                if flag["position"]["side"] == "BUY":
                    flag["records"]["log"].append(f"{flag['position']['price'] - stop}円の位置にストップを更新します。\n")
                elif flag["position"]["side"] == "SELL":
                    flag["records"]["log"].append(f"{flag['position']['price'] + stop}円の位置にストップを更新します。\n")

                flag["records"]["log"].append(f"現在のポジションの取得単価は{flag['position']['price']}円です。\n")
                flag["records"]["log"].append(f"現在のポジションサイズは{flag['position']['lot']}BTCです。\n\n")

                flag["add-position"]["count"] += 1
                flag["add-position"]["last-entry-price"] = entry_price

        return flag

    
    def trail_stop(self, data, flag):

        if flag["add-position"]["count"] < self.entry_times:
            return flag

        if flag["position"]["side"] == "BUY":
            moved_range = round(data["high_price"] - flag["position"]["price"])
        if flag["position"]["side"] == "SELL":
            moved_range = round(flag["position"]["price"] - data["low_price"])

        if moved_range < 0 or flag["position"]["stop-EP"] >= moved_range:
            return flag
        else:
            flag["position"]["stop-EP"] = moved_range

        flag["position"]["stop"] = round(flag["position"]["stop"] - (moved_range + flag["position"]["stop"]) * flag["position"]["stop-AF"])

        flag["position"]["stop-AF"] = round(flag["position"]["stop-AF"] + self.stop_AF_add, 2)
        if flag["position"]["stop-AF"] >= self.stop_AF_max:
            flag["position"]["stop-AF"] = self.stop_AF_max

        if flag["position"]["side"] == "BUY":
            flag["records"]["log"].append(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] - flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。\n")
        else:
            flag["records"]["log"].append(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] + flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。\n")

        return flag


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

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot > Backtest.min_size:
                flag["records"]["log"].append(f"{data['close_price']}円で{lot}BTCの買い指値注文を出します。\n")

                # TODO: ここに買い注文のコードを入れる
                flag["records"]["log"].append(f"{data['close_price'] - stop}円にストップを入れます。\n")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = data["close_price"]
            else:
                flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        if signal["side"] == "SELL":
            flag["records"]["log"].append(f"過去{self.sell_term}足の最安値{signal['price']}円を、直近の価格が{data[self.judge_price['SELL']]}円でブレイクしました。")

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot > Backtest.min_size:
                flag["records"]["log"].append(f"{data['close_price']}円で{lot}BTCの売り指値注文を出します。\n")

                # TODO: ここに売り注文のコードを入れる
                flag["records"]["log"].append(f"{data['close_price'] + stop}円にストップを入れます。\n")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = data["close_price"]
            else:
                flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

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

                # TODO: ここに決済の成行注文コードを入れる
                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot > Backtest.min_size:
                    flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で{lot}BTCの売り指値注文を入れてドテンします。\n")

                    # TODO: ここに売り注文のコードを入れる
                    flag["records"]["log"].append(f"{data['close_price'] + stop}円にストップを入れます。\n")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["price"] = data["close_price"]
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "SELL"
                else:
                    flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        if flag["position"]["side"] == "SELL":
            if signal["side"] == "BUY":
                flag["records"]["log"].append(f"過去{self.buy_term}足の最高値{signal['price']}円を、直近の価格が{data[self.judge_price['BUY']]}円でブレイクしました。")
                flag["records"]["log"].append(str(data['close_price']) + "円あたりで成行注文を出してポジションを決済します。\n")

                # TODO: ここに決済の成行注文コードを入れる
                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot > Backtest.min_size:
                    flag["records"]["log"].append(f"さらに{str(data['close_price'])}円で{lot}BTCの買い指値注文を入れてドテンします。\n")

                    # TODO: ここに買い注文のコードを入れる
                    flag["records"]["log"].append(f"{data['close_price'] - stop}円にストップを入れます。\n")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["price"] = data["close_price"]
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "BUY"
                else:
                    flag["records"]["log"].append(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。\n")

        return flag


    def stop_position(self, data, last_data, flag):

        flag = self.trail_stop(data, flag)

        if flag["position"]["side"] == "BUY":
            stop_price = flag["position"]["price"] - flag["position"]["stop"]
            if data["low_price"] < stop_price:
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。\n")
                stop_price = round(stop_price - 2 * self.calculate_volatility(last_data, flag) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック(ATR)分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # TODO: 成行注文コードを入れる
                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        if flag["position"]["side"] == "SELL":
            stop_price = flag["position"]["price"] + flag["position"]["stop"]
            if data["high_price"] > stop_price:
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。\n")
                stop_price = round(stop_price + 2 * self.calculate_volatility(last_data, flag) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック(ATR)分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # TODO: 成行注文コードを入れる
                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        return flag

    
    def records(self, flag, data, close_price, close_type=None):

        entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
        exit_price = int(round(close_price * flag["position"]["lot"]))
        trade_cost = round(exit_price * self.slippage)

        log = "スリッページ・手数料として " + str(trade_cost) + "円を考慮します\n"
        flag["records"]["log"].append(log)
        flag["records"]["slippage"].append(trade_cost)

        flag["records"]["date"].append(data["close_time_dt"])
        flag["records"]["holding-periods"].append(flag["position"]["count"])

        if close_type == "STOP":
            flag["records"]["stop-count"].append(1)
        else:
            flag["records"]["stop-count"].append(0)

        buy_profit = exit_price - entry_price - trade_cost
        sell_profit = entry_price - exit_price - trade_cost

        if flag["position"]["side"] == "BUY":
            flag["records"]["side"].append("BUY")
            flag["records"]["profit"].append(buy_profit)
            flag["records"]["return"].append(round(buy_profit / entry_price * 100, 4))
            flag["records"]["funds"] = flag["records"]["funds"] + buy_profit

            if buy_profit > 0:
                log = str(buy_profit) + "円の利益です\n"
                flag["records"]["log"].append(log)
            else:
                log = str(buy_profit) + "円の損失です\n"
                flag["records"]["log"].append(log)

        if flag["position"]["side"] == "SELL":
            flag["records"]["side"].append("SELL")
            flag["records"]["profit"].append(sell_profit)
            flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))
            flag["records"]["funds"] = flag["records"]["funds"] + sell_profit

            if sell_profit > 0:
                log = str(sell_profit) + "円の利益です\n\n"
                flag["records"]["log"].append(log)
            else:
                log = str(sell_profit) + "円の損失です\n\n"
                flag["records"]["log"].append(log)

        return flag

    
    def plot_gross_curve(self, date, gross):

        plt.plot(date, gross)
        plt.xlabel("Date")
        plt.ylabel("Balance")
        plt.xticks(rotation = 50)

        plt.show()

    
    def output_log(self, data):

        f = open(f"{Backtest.log_file}{datetime.now().strftime('%Y-%m-%d-%H-%M')}.txt", 'wt', encoding='utf-8')
        f.writelines(data)


    def backtest(self, flag):

        records = pd.DataFrame({
            "Date": pd.to_datetime(flag["records"]["date"]),
            "Profit": flag["records"]["profit"],
            "Side": flag["records"]["side"],
            "Rate": flag["records"]["return"],
            "Stop": flag["records"]["stop-count"],
            "Periods": flag["records"]["holding-periods"],
            "Slippage": flag["records"]["slippage"]
        })

        consecutive_defeats = []
        defeats = 0
        for p in flag["records"]["profit"]:
            if p < 0:
                defeats += 1
            else:
                consecutive_defeats.append(defeats)
                defeats = 0

        records["Gross"] = records.Profit.cumsum()

        records["Funds"] = records.Gross + self.start_funds

        records["Drawdown"] = records.Funds.cummax().subtract(records.Funds)
        records["DrawdownRate"] = round(records.Drawdown / records.Funds.cummax() * 100, 1)

        buy_records = records[records.Side.isin(["BUY"])]
        sell_records = records[records.Side.isin(["SELL"])]

        records["月別集計"] = pd.to_datetime(records.Date.apply(lambda x: x.strftime('%Y/%m')))
        grouped = records.groupby("月別集計")

        month_records = pd.DataFrame({
            "Number": grouped.Profit.count(),
            "Gross": grouped.Profit.sum(),
            "Funds": grouped.Funds.last(),
            "Rate": round(grouped.Rate.mean(), 2),
            "Drawdown": grouped.Drawdown.max(),
            "Periods": grouped.Periods.mean()
        })

        print("バックテストの結果")
        print("---------------------------")
        print("買いエントリの成績")
        print("---------------------------")
        print(f"トレード回数　　　：　{len(buy_records)}回")
        print(f"勝率　　　　　　　：　{round(len(buy_records[buy_records.Profit>0]) / len(buy_records) * 100, 1)}％")
        print(f"平均リターン　　　：　{round(buy_records.Rate.mean(), 2)}％")
        print(f"総損益　　　　　　：　{buy_records.Profit.sum()}円")
        print(f"平均保有期間　　　：　{round(buy_records.Periods.mean(), 1)}足分")
        print(f"損切りの回数　　　：　{buy_records.Stop.sum()}回")

        print("---------------------------")
        print("売りエントリの成績")
        print("---------------------------")
        print(f"トレード回数　　　：　{len(sell_records)}回")
        print(f"勝率　　　　　　　：　{round(len(sell_records[sell_records.Profit>0]) / len(sell_records) * 100, 1)}％")
        print(f"平均リターン　　　：　{round(sell_records.Rate.mean(), 2)}％")
        print(f"総損益　　　　　　：　{sell_records.Profit.sum()}円")
        print(f"平均保有期間　　　：　{round(sell_records.Periods.mean(), 1)}足分")
        print(f"損切りの回数　　　：　{sell_records.Stop.sum()}回")

        print("---------------------------")
        print("総合成績")
        print("---------------------------")
        print(f"全トレード数　　　：　{len(records)}回")
        print(f"勝率　　　　　　　：　{round(len(records[records.Profit>0]) / len(records) * 100, 1)}％")
        print(f"平均リターン　　　：　{round(records.Rate.mean(), 2)}％")
        print(f"平均保有期間　　　：　{round(records.Periods.mean(), 1)}足分")
        print(f"損切りの回数　　　：　{records.Stop.sum()}回")
        print("")
        print(f"最大の勝ちトレード：　{records.Profit.max()}円")
        print(f"最大の負けトレード：　{records.Profit.min()}円")
        print(f"最大連敗回数　　　：{max(consecutive_defeats)}回")
        print(f"最大ドローダウン　：　{-1 * records.Drawdown.max()}円 / {-1 * records.DrawdownRate.loc[records.Drawdown.idxmax()]}％")
        print(f"利益合計　　　　　：　{records[records.Profit>0].Profit.sum()}円")
        print(f"損失合計　　　　　：　{records[records.Profit<0].Profit.sum()}円")
        print(f"最終損益　　　　　：　{records.Profit.sum()}円")
        print("")
        print(f"初期資金　　　　　：　{self.start_funds}円")
        print(f"最終資金　　　　　：　{records.Funds.iloc[-1]}円")
        print(f"運用成績　　　　　：　{round(records.Funds.iloc[-1] / self.start_funds * 100, 2)}％")
        print(f"手数料合計　　　　：　{-1 * records.Slippage.sum()}円")

        print("---------------------------")
        print("月別の成績")

        for index, row in month_records.iterrows():
            print("---------------------------")
            print(f"{index.year}年{index.month}月の成績")
            print("---------------------------")
            print(f"トレード数　　　：　{row.Number.astype(int)}回")
            print(f"月間損益　　　　：　{row.Gross.astype(int)}円")
            print(f"平均リターン　　：　{row.Rate}％")
            print(f"継続ドローダウン：　{-1 * row.Drawdown.astype(int)}円")
            print(f"月末資金　　　　：　{row.Funds.astype(int)}円")

        self.output_log(flag["records"]["log"])

        self.plot_gross_curve(records.Date, records.Funds)