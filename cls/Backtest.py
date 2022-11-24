import os
import json
import time
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import matplotlib.pyplot as plt

from .Batman import Batman1G

class Backtest1G(Batman1G):

    LOG_DIR = "backtest-log"
    SUMMARY_CSV = LOG_DIR + "/batman1G.csv"

    def __init__(self, chart_sec, entry_term, exit_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config, start_funds, slippage, TEST_MODE_LOT):

        super().__init__(chart_sec, entry_term, exit_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config)

        self.start_funds = start_funds
        self.slippage = slippage
        self.TEST_MODE_LOT = TEST_MODE_LOT

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
                "count": 0,
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
                "filter": [],
                "filter-match": False,
            }
        }

    
    @classmethod
    def get_price_from_file(cls, data_file, min, start_time=None, end_time=None):
        
        f = open(data_file, "r", encoding="utf-8")
        data = json.load(f)

        start_unix = 0
        end_unix = 9999999999

        if start_time:
            start_time = datetime.strptime(start_time, "%Y/%m/%d %H:%M")
            start_unix = int(start_time.timestamp())
        if end_time:
            end_time = datetime.strptime(end_time, "%Y/%m/%d %H:%M")
            end_unix = int(end_time.timestamp())

        price = []
        for i in data["result"][str(min)]:
            if i[0] >= start_unix and i[0] <= end_unix:
                if i[1] != 0 and i[2] != 0 and i[3] != 0 and i[4] != 0:
                    price.append({
                        "close_time": i[0],
                        "close_time_dt": datetime.fromtimestamp(i[0]).strftime("%Y/%m/%d %H:%M"),
                        "open_price": i[1],
                        "high_price": i[2],
                        "low_price": i[3],
                        "close_price": i[4]
                    })

        return price


    def entry_signal(self, data, last_data, flag):

        signal = self.donchian(data, last_data)

        if signal["side"] == "BUY":
            self.print_log(f"--------------------【エントリー判定】entry_signal() --------------------")
            self.print_log(f"【買】過去{self.entry_term}足の最高値{signal['price']}を直近の価格が{data[self.judge_price['BUY']]}円でブレイクしました。")

            flag = self.filter(signal, data, last_data ,flag)

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot > self.MIN_LOT:
                self.print_log(f"{data['close_price']}円で{lot}BTCの買いの指値注文をします。")

                self.print_log(f"{data['close_price'] - stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = data["close_price"]
            else:
                self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        if signal["side"] == "SELL":
            self.print_log(f"--------------------【エントリー判定】entry_signal() --------------------")
            self.print_log(f"【売】過去{self.entry_term}足の最安値{signal['price']}を直近の価格が{data[self.judge_price['SELL']]}円でブレイクしました。")

            flag = self.filter(signal, data, last_data, flag)

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot > self.MIN_LOT:
                self.print_log(f"{data['close_price']}円で{lot}BTCの売りの指値注文をします。")

                self.print_log(f"{data['close_price'] + stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = data["close_price"]
            else:
                self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        return flag


    def filter(self, signal, data, last_data, flag):

        if self.filter_VER == "OFF":
            flag["records"]["filter-match"] = True
            return flag

        if self.filter_VER == "A":
            if data["close_price"] > self.calculate_MA(self.MA_term, last_data) and signal["side"] == "BUY":
                flag["records"]["filter-match"] = True
                return flag
            elif data["close_price"] < self.calculate_MA(self.MA_term, last_data) and signal["side"] == "SELL":
                flag["records"]["filter-match"] = True
                return flag
            else:
                flag["records"]["filter-match"] = False
                return flag

        if self.filter_VER == "B":
            if self.calculate_MA(self.MA_term, last_data) > self.calculate_MA(self.MA_term, last_data, -1) and signal["side"] == "BUY":
                flag["records"]["filter-match"] = True
                return flag
            elif self.calculate_MA(self.MA_term, last_data) < self.calculate_MA(self.MA_term, last_data, -1) and signal["side"] == "SELL":
                flag["records"]["filter-match"] = True
                return flag
            else:
                flag["records"]["filter-match"] = False
                return flag

        return flag


    def calculate_lot(self, last_data, data, flag):

        if self.TEST_MODE_LOT == "fixed":
            self.print_log("--------------------【ロット計算】calculate_lot() --------------------")
            self.print_log("固定ロットでテスト中のため、1BTCを注文します")
            lot = 1
            volatility = self.calculate_volatility(last_data)
            stop = self.stop_range * volatility
            flag["position"]["ATR"] = round(volatility)
            return lot, stop, flag

        balance = flag["records"]["funds"]

        if flag["add-position"]["count"] == 0:

            volatility = self.calculate_volatility(last_data)
            stop = self.stop_range * volatility
            calc_lot = np.floor(balance * self.trade_risk / stop * 1000) / 1000

            flag["add-position"]["unit-size"] = np.floor(calc_lot / self.entry_times * 1000) / 1000
            flag["add-position"]["unit-range"] = round(volatility * self.entry_range)
            flag["add-position"]["stop"] = stop
            flag["position"]["ATR"] = round(volatility)

            self.print_log(f"--------------------【ロット計算】calculate_lot() --------------------")
            self.print_log(f"現在のアカウント残高は{balance}円です。")
            self.print_log(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
            self.print_log(f"{self.entry_times}回に分けて{flag['add-position']['unit-size']}BTCずつ注文します。")

        else:
            balance = round(balance - flag["position"]["price"] * flag["position"]["lot"] / self.levarage)

        stop = flag["add-position"]["stop"]

        able_lot = np.floor(balance * self.levarage / data["close_price"] * 1000) / 1000
        lot = min(able_lot, flag["add-position"]["unit-size"])

        self.print_log(f"ただし、証拠金から購入できる枚数は最大{able_lot}BTCまでです。")
        return lot, stop, flag


    def add_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        if self.TEST_MODE_LOT == "fixed":
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
                self.print_log(f"--------------------【追加注文】add_position() --------------------")
                self.print_log(f"前回のエントリー価格{last_entry_price}からブレイクアウト方向に{self.entry_range}ATR（{unit_range}円）以上動きました。")
                self.print_log(f"{flag['add-position']['count'] + 1}/{self.entry_times}回目の追加注文を出します。")

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot < self.MIN_LOT:
                    self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")
                    flag["add-position"]["count"] += 1
                    return flag

                if flag["position"]["side"] == "BUY":
                    entry_price = first_entry_price + (flag["add-position"]["count"] * unit_range)
                    self.print_log(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの買い注文を出します。")

                if flag["position"]["side"] == "SELL":
                    entry_price = first_entry_price - (flag["add-position"]["count"] * unit_range)
                    self.print_log(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの売り注文を出します。")

                flag["position"]["stop"] = stop
                flag["position"]["price"] = int(round((flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (flag["position"]["lot"] + lot)))
                flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

                if flag["position"]["side"] == "BUY":
                    self.print_log(f"{flag['position']['price'] - stop}円の位置にストップを更新します。")
                if flag["position"]["side"] == "SELL":
                    self.print_log(f"{flag['position']['price'] + stop}円の位置にストップを更新します。")

                self.print_log(f"現在のポジションの取得単価は{flag['position']['price']}円です。")
                self.print_log(f"現在のポジションサイズは{flag['position']['lot']}BTCです。")

                flag["add-position"]["count"] += 1
                flag["add-position"]["last-entry-price"] = entry_price

        return flag


    def stop_position(self, data, last_data, flag):

        if self.trailing_config == "TRAILING":
            flag = self.trail_stop(data, flag)

        if flag["position"]["side"] == "BUY":
            stop_price = flag["position"]["price"] - flag["position"]["stop"]
            if data["low_price"] < stop_price:
                self.print_log(f"--------------------【損切判定】stop_position() --------------------")
                self.print_log(f"{stop_price}円の損切りラインに引っかかりました。")
                stop_price = round(stop_price - 2 * self.calculate_volatility(last_data) / (self.chart_sec / 60)) # 不利な価格で約定したとする
                self.print_log(f"{stop_price}円あたりで成り行き注文を出してポジションを決済します。")

                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        if flag["position"]["side"] == "SELL":
            stop_price = flag["position"]["price"] + flag["position"]["stop"]
            if data["high_price"] > stop_price:
                self.print_log(f"--------------------【損切判定】stop_position() --------------------")
                self.print_log(f"{stop_price}円の損切りラインに引っかかりました。")
                stop_price = round(stop_price + 2 * self.calculate_volatility(last_data) / (self.chart_sec / 60)) # 不利な価格で約定したとする
                self.print_log(f"{stop_price}円あたりで成り行き注文を出してポジションを決済します。")

                self.records(flag, data, stop_price, "STOP")
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        return flag
    
    
    def close_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        flag["position"]["count"] += 1
        signal = self.donchian(data, last_data)

        if flag["position"]["side"] == "BUY":
            if signal["side"] == "SELL":
                self.print_log(f"--------------------【クローズ判定】close_position() --------------------")
                self.print_log(f"過去{self.exit_term}足の最安値{signal['price']}を直近の価格が{data[self.judge_price['SELL']]}円でブレイクしました。")
                self.print_log("成り行き注文を出してポジションを決済します。")

                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                self.print_log(f"--------------------【ドテンエントリー】close_position() --------------------")

                flag = self.filter(signal, data, last_data ,flag)

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot > self.MIN_LOT:
                    self.print_log(f"【売】さらに{str(data['close_price'])}円で{lot}BTCの売りの指値注文を入れてドテンします。")

                    self.print_log(f"{data['close_price'] + stop}円にストップを入れます。")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "SELL"
                    flag["position"]["price"] = data["close_price"]
                else:
                    self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        if flag["position"]["side"] == "SELL":
            if signal["side"] == "BUY":
                self.print_log(f"--------------------【クローズ判定】close_position() --------------------")
                self.print_log(f"過去{self.exit_term}足の最高値{signal['price']}を直近の価格が{data[self.judge_price['BUY']]}円でブレイクしました。")
                self.print_log("成り行き注文を出してポジションを決済します。")

                self.records(flag, data, data["close_price"])
                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                self.print_log(f"--------------------【ドテンエントリー】close_position() --------------------")

                flag = self.filter(signal, data, last_data, flag)

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot > self.MIN_LOT:
                    self.print_log(f"【買】さらに{str(data['close_price'])}円で{lot}BTCの買いの指値注文を入れてドテンします。")

                    self.print_log(f"{data['close_price'] - stop}円にストップを入れます。")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "BUY"
                    flag["position"]["price"] = data["close_price"]
                else:
                    self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        return flag


    def records(self, flag, data, close_price, close_type=None):

        self.print_log(f"--------------------【記録】records() --------------------")

        flag["records"]["filter"].append(flag["records"]["filter-match"])

        entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
        exit_price = int(round(close_price * flag["position"]["lot"]))
        trade_cost = round(exit_price * self.slippage)

        self.print_log(f"スリッページ・手数料として{str(trade_cost)}円を考慮します")
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
                self.print_log(f"{str(buy_profit)}円の利益です")
            else:
                self.print_log(f"{str(buy_profit)}円の損失です")

        if flag["position"]["side"] == "SELL":
            flag["records"]["side"].append("SELL")
            flag["records"]["profit"].append(sell_profit)
            flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))
            flag["records"]["funds"] = flag["records"]["funds"] + sell_profit
            if sell_profit > 0:
                self.print_log(f"{str(sell_profit)}円の利益です")
            else:
                self.print_log(f"{str(sell_profit)}円の損失です")

        if not flag["records"]["filter-match"]:
            self.print_log("この取引はフィルターにかからなかったため、無効です。")

        return flag


    def output_backtest(self, result):

        if os.path.exists(self.SUMMARY_CSV):
            df = pd.read_csv(self.SUMMARY_CSV, index_col=0)
            df = df.append(pd.Series(result), ignore_index=True)
            df.to_csv(self.SUMMARY_CSV)
        else:
            df = pd.DataFrame([result], columns=result.keys())
            df.to_csv(self.SUMMARY_CSV)


    def backtest(self, flag):

        # 使用パラメータ
        params = {
            "chart_sec": self.chart_sec,
            "entry_term": self.entry_term,
            "exit_term": self.exit_term,
            "judge_price": self.judge_price,
            "TEST_MODE_LOT": self.TEST_MODE_LOT,
            "volatility_term": self.volatility_term,
            "stop_range": self.stop_range,
            "trade_risk": self.trade_risk,
            "levarage": self.levarage,
            "start_funds": self.start_funds,
            "entry_times": self.entry_times,
            "entry_range": self.entry_range,
            "trailing_config": self.trailing_config,
            "stop_AF": self.stop_AF,
            "stop_AF_add": self.stop_AF_add,
            "stop_AF_max": self.stop_AF_max,
            "slippage": self.slippage,
            "filter_VER": self.filter_VER,
            "MA_term": self.MA_term
        }

        records = pd.DataFrame({
            "Date": pd.to_datetime(flag["records"]["date"]),
            "Profit": flag["records"]["profit"],
            "Side": flag["records"]["side"],
            "Rate": flag["records"]["return"],
            "Stop": flag["records"]["stop-count"],
            "Periods": flag["records"]["holding-periods"],
            "Slippage": flag["records"]["slippage"],
            "Filter": flag["records"]["filter"]
        })

        # 全recordsをfilterにかかったものとかからなかったものに分割。filterにかかった取引のみを結果として出力する。
        # filterを無効にすると全取引を出力。
        filter_true_records = records[records.Filter]
        filter_false_records = records[~records.Filter]

        filter_true_records["Gross"] = filter_true_records.Profit.cumsum()

        filter_true_records["Funds"] = filter_true_records.Gross + self.start_funds

        filter_true_records["Drawdown"] = filter_true_records.Gross.cummax().subtract(filter_true_records.Gross)
        filter_true_records["DrawdownRate"] = round(filter_true_records.Drawdown / filter_true_records.Funds.cummax() * 100, 1)

        result = {
            "TradeNum": len(filter_true_records),
            "WinningRate": round(len(filter_true_records[filter_true_records.Profit>0]) / len(filter_true_records) * 100, 1),
            "AverageReturn": round(filter_true_records.Rate.mean(), 2),
            "AverageProfit": round(filter_true_records[filter_true_records.Profit>0].Rate.mean(), 2),
            "AverageLoss": round(filter_true_records[filter_true_records.Profit<0].Rate.mean(), 2),
            "PayoffRatio": round(filter_true_records[filter_true_records.Profit>0].Rate.mean() / abs(filter_true_records[filter_true_records.Profit<0].Rate.mean()), 2),
            "AverageHoldingPeriods": round(filter_true_records.Periods.mean(), 1),
            "LossCutNum": filter_true_records.Stop.sum(),
            "BestProfit": filter_true_records.Profit.max(),
            "WorstLoss": filter_true_records.Profit.min(),
            "MaxDrawdown": -1 * filter_true_records.Drawdown.max(),
            "MaxDrawdownRate": -1 * filter_true_records.DrawdownRate.loc[filter_true_records.Drawdown.idxmax()],
            "TotalProfit": filter_true_records[filter_true_records.Profit>0].Profit.sum(),
            "TotalLoss": filter_true_records[filter_true_records.Profit<0].Profit.sum(),
            "Gross": filter_true_records.Profit.sum(),
            "StartFunds": self.start_funds,
            "FinalFunds": filter_true_records.Funds.iloc[-1],
            "Performance": round(filter_true_records.Funds.iloc[-1] / self.start_funds * 100, 2),
            "TotalSlippage": -1 * filter_true_records.Slippage.sum(),
            "LogFilePath": self.log_file,
            "Params": params
        }

        self.output_backtest(result)

        print("バックテストの結果")
        print("-------------------------")
        print(f"全トレード数：{result['TradeNum']}回")
        print(f"勝率：{result['WinningRate']}％")
        print(f"平均リターン：{result['AverageReturn']}％")
        print(f"平均利益率：{result['AverageProfit']}％")
        print(f"平均損失率：{result['AverageLoss']}％")
        print(f"損益レシオ：{result['PayoffRatio']}")
        print(f"平均保有期間：{result['AverageHoldingPeriods']}足分")
        print(f"損切り総数：{result['LossCutNum']}回")
        print("")
        print(f"最大勝ちトレード：{result['BestProfit']}円")
        print(f"最大負けトレード：{result['WorstLoss']}円")
        print(f"最大ドローダウン：{result['MaxDrawdown']}円 / {result['MaxDrawdownRate']}％")
        print(f"利益合計：{result['TotalProfit']}円")
        print(f"損失合計：{result['TotalLoss']}円")
        print(f"総損益：{result['Gross']}円")
        print("")
        print(f"初期資金：{result['StartFunds']}円")
        print(f"最終資金：{result['FinalFunds']}円")
        print(f"運用成績：{result['Performance']}％")
        print(f"手数料合計:{result['TotalSlippage']}円")

        plt.subplot(1, 2, 1)
        plt.plot(filter_true_records.Date, filter_true_records.Funds)
        plt.xlabel("Date")
        plt.ylabel("Balance")
        plt.xticks(rotation=50)

        plt.subplot(1, 2, 2)
        plt.hist(filter_true_records.Rate, 50, rwidth=0.9)
        plt.axvline(x=0, linestyle="dashed", label="Return = 0")
        plt.axvline(filter_true_records.Rate.mean(), color="orange", label="AverageReturn")
        plt.show()
        plt.legend()

        # filterの有効性を検証
        if self.filter_VER != "OFF":
            sample_a = filter_true_records.Rate.values
            sample_b = filter_false_records.Rate.values
            print("--------------------------------")
            print("t検定を実行")
            print("--------------------------------")
            p = stats.ttest_ind(sample_a, sample_b, equal_var=False)
            print(f"p value : {p[1]}")

            plt.subplot(2, 1, 1)
            plt.hist(filter_true_records.Rate, 50, rwidth=0.9)
            plt.xlim(-15, 45)
            plt.axvline(x=0, linestyle="dashed", label="Return = 0")
            plt.axvline(filter_true_records.Rate.mean(), color="orange", label="AverageReturn")
            plt.legend()

            plt.subplot(2, 1, 2)
            plt.hist(filter_false_records.Rate, 50, rwidth=0.9, color="coral")
            plt.xlim(-15, 45)
            plt.gca().invert_yaxis()
            plt.axvline(x=0, linestyle="dashed", label="Return = 0")
            plt.axvline(filter_false_records.Rate.mean(), color="orange", label="AverageReturn")
            plt.show()