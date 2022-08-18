import requests
from datetime import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from test import Batman
from params import *

class Backtest(Batman):

    log_file = "trade-log/backtest_"

    slippage = 0.001

    def __init__(self, chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, trade_risk, levarage, start_funds):
        super().__init__(chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, trade_risk, levarage)

        self.start_funds = start_funds
        
        self.flag = {
            "order": {
                "exist": False,
                "side": "",
                "price": 0,
                "stop": 0,
                "lot": 0,
                "count": 0
            },
            "position": {
                "exist": False,
                "side": "",
                "price": 0,
                "stop": 0,
                "lot": 0,
                "count": 0
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


    def calculate_lot(self, last_data, data, flag):

        balance = flag["records"]["funds"]

        volatility = self.calculate_volatility(last_data, flag)
        stop = self.stop_range * volatility

        calc_lot = np.floor(balance * self.trade_risk / stop * 100) / 100
        able_lot = np.floor(balance * self.levarage / data["close_price"] * 100) / 100
        lot = min(calc_lot, able_lot)

        flag["records"]["log"].append(f"現在のアカウント残高{balance}")
        flag["records"]["log"].append(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
        flag["records"]["log"].append(f"証拠金から購入できる枚数は最大{able_lot}BTCまでです。")

        return lot, stop


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
                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

                lot, stop = self.calculate_lot(last_data, data, flag)
                if lot > Batman.min_size:
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
                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

                lot, stop = self.calculate_lot(last_data, data, flag)
                if lot > Batman.min_size:
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
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。\n")
                stop_price = round(stop_price - 2 * self.calculate_volatility(last_data, flag) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # 成行注文コードを入れる
                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        if flag["position"]["side"] == "SELL":
            stop_price = flag["position"]["price"] + flag["position"]["stop"]
            if data["high_price"] > stop_price:
                flag["records"]["log"].append(f"{stop_price}円の損切りラインに引っかかりました。\n")
                stop_price = round(stop_price + 2 * self.calculate_volatility(last_data, flag) / (self.chart_sec / 60)) # 約定価格（1分足で２ティック分程度注文が遅れたと仮定）
                flag["records"]["log"].append(str(stop_price) + "円あたりで成り行き注文を出してポジションを決済します。\n")

                # 成行注文コードを入れる
                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0

        return flag


    def records(self, flag, data, close_price, close_type=None):

        entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
        exit_price = int(round(close_price * flag["position"]["lot"]))
        trade_cost = round(exit_price * Backtest.slippage)

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
                log = str(sell_profit) + "円の利益です\n"
                flag["records"]["log"].append(log)
            else:
                log = str(sell_profit) + "円の損失です\n"
                flag["records"]["log"].append(log)

        return flag


    def plot_gross_curve(self, date, gross):

        plt.plot(date, gross)
        plt.xlabel("Date")
        plt.ylabel("Balance")
        plt.xticks(rotation = 50)

        plt.show()


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

        self.output_log(Backtest.log_file, flag["records"]["log"])

        self.plot_gross_curve(records.Date, records.Funds)


def main():

    bot1 = Backtest(chart_sec, buy_term, sell_term, volatility_term, stop_range, judge_price, wait, trade_risk, levarage, start_funds)
    price = bot1.get_price(after=1483228800)

    flag = bot1.flag

    last_data = []
    need_term = bot1.need_term
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

    print("-----------------------")
    print("テスト期間")
    print("開始時点：" + str(price[0]["close_time_dt"]))
    print("終了時点：" + str(price[-1]["close_time_dt"]))
    print(str(len(price)) + "件のローソク足データで検証")
    print("-----------------------")

    bot1.backtest(flag)


if __name__ == '__main__':
    main()