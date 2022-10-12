import os
import requests
from scipy import stats
from datetime import datetime
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sample_bot as bot
from bot_log import print_log, log_file_path


def donchian(data, last_data):

    highest = max(i["high_price"] for i in last_data[(-1*buy_term): ])
    if data[judge_price["BUY"]] > highest:
        return {"side": "BUY", "price": highest}

    lowest = min(i["low_price"] for i in last_data[(-1*sell_term): ])
    if data[judge_price["SELL"]] < lowest:
        return {"side": "SELL", "price": lowest}

    return {"side": None, "price": 0}


def calculate_lot(last_data, data, flag):

    if TEST_MODE_LOT == "fixed":
        print_log(f"--------------------【ロット計算】calculate_lot() --------------------")
        print_log("固定ロットでテスト中のため、1BTCを注文します")
        lot = 1
        volatility = bot.calculate_volatility(last_data)
        stop = stop_range * volatility
        flag["position"]["ATR"] = round(volatility)
        return lot, stop, flag

    balance = flag["records"]["funds"]

    if flag["add-position"]["count"] == 0:

        volatility = bot.calculate_volatility(last_data)
        stop = stop_range * volatility
        calc_lot = np.floor(balance * trade_risk / stop * 1000) / 1000

        flag["add-position"]["unit-size"] = np.floor(calc_lot / entry_times * 1000) / 1000
        flag["add-position"]["unit-range"] = round(volatility * entry_range)
        flag["add-position"]["stop"] = stop
        flag["position"]["ATR"] = round(volatility)

        print_log(f"--------------------【ロット計算】calculate_lot() --------------------")
        print_log(f"現在のアカウント残高は{balance}円です。")
        print_log(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
        print_log(f"{entry_times}回に分けて{flag['add-position']['unit-size']}BTCずつ注文します。")

    else:
        balance = round(balance - flag["position"]["price"] * flag["position"]["lot"] / levarage)

    stop = flag["add-position"]["stop"]

    able_lot = np.floor(balance * levarage / data["close_price"] * 1000) / 1000
    lot = min(able_lot, flag["add-position"]["unit-size"])

    print_log(f"ただし証拠金から購入できる枚数は最大{able_lot}BTCまでです。")
    return lot, stop, flag


def add_position(data, last_data, flag):

    if flag["position"]["exist"] == False:
        return flag

    if TEST_MODE_LOT == "fixed":
        return flag

    if flag["add-position"]["count"] == 0:
        flag["add-position"]["first-entry-price"] = flag["position"]["price"]
        flag["add-position"]["last-entry-price"] = flag["position"]["price"]
        flag["add-position"]["count"] += 1

    while True:

        if flag["add-position"]["count"] >= entry_times:
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
            print_log(f"--------------------【追加注文】add_position() --------------------")
            print_log(f"前回のエントリー価格{last_entry_price}からブレイクアウト方向に{entry_range}ATR（{unit_range}円）以上動きました。")
            print_log(f"{flag['add-position']['count'] + 1}/{entry_times}回目の追加注文を出します。")

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot < MIN_LOT:
                print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")
                flag["add-position"]["count"] += 1
                return flag

            if flag["position"]["side"] == "BUY":
                entry_price = first_entry_price + (flag["add-position"]["count"] * unit_range)
                print_log(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの買い注文を出します。")


            if flag["position"]["side"] == "SELL":
                entry_price = first_entry_price - (flag["add-position"]["count"] * unit_range)
                print_log(f"現在のポジションに追加して、{entry_price}円で{lot}BTCの売り注文を出します。")

            flag["position"]["stop"] = stop
            flag["position"]["price"] = int(round((flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (flag["position"]["lot"] + lot)))
            flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

            if flag["position"]["side"] == "BUY":
                print_log(f"{flag['position']['price'] - stop}円の位置にストップを更新します。")
            if flag["position"]["side"] == "SELL":
                print_log(f"{flag['position']['price'] + stop}円の位置にストップを更新します。")

            print_log(f"現在のポジションの取得単価は{flag['position']['price']}円です。")
            print_log(f"現在のポジションサイズは{flag['position']['lot']}BTCです。")

            flag["add-position"]["count"] += 1
            flag["add-position"]["last-entry-price"] = entry_price

    return flag


def filter(signal, flag):

    if filter_VER == "OFF":
        flag["records"]["filter-match"] = "True"
        return flag

    if filter_VER == "A":
        if data["close_price"] > bot.calculate_MA(MA_term, last_data) and signal["side"] == "BUY":
            flag["records"]["filter-match"] = "True"
            return flag
        elif data["close_price"] < bot.calculate_MA(MA_term, last_data) and signal["side"] == "SELL":
            flag["records"]["filter-match"] = "True"
            return flag
        else:
            flag["records"]["filter-match"] = "False"
            return flag

    if filter_VER == "B":
        if bot.calculate_MA(MA_term, last_data) > bot.calculate_MA(MA_term, last_data, -1) and signal["side"] == "BUY":
            flag["records"]["filter-match"] = "True"
            return flag
        elif bot.calculate_MA(MA_term, last_data) < bot.calculate_MA(MA_term, last_data, -1) and signal["side"] == "SELL":
            flag["records"]["filter-match"] = "True"
            return flag
        else:
            flag["records"]["filter-match"] = "False"
            return flag
    
    return flag


def entry_signal(data, last_data, flag):

    signal = donchian(data, last_data)

    if signal["side"] == "BUY":
        print_log(f"--------------------【エントリー判定】entry_signal() --------------------")
        print_log(f"【買】過去{buy_term}足の最高値{signal['price']}を直近の価格が{data[judge_price['BUY']]}円でブレイクしました。")

        flag = filter(signal, flag)

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > MIN_LOT:
            print_log(f"{data['close_price']}円で{lot}BTCの買いの指し値注文をします。")

            print_log(f"{data['close_price'] - stop}円にストップを入れます。")
            flag["position"]["lot"] = lot
            flag["position"]["stop"] = stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "BUY"
            flag["position"]["price"] = data["close_price"]
        else:
            print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    if signal["side"] == "SELL":
        print_log(f"--------------------【エントリー判定】entry_signal() --------------------")
        print_log(f"【売】過去{sell_term}足の最安値{signal['price']}を直近の価格が{data[judge_price['SELL']]}円でブレイクしました。")

        flag = filter(signal, flag)

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot > MIN_LOT:
            print_log(f"{data['close_price']}円で{lot}BTCの売りの指し値注文をします。")

            print_log(f"{data['close_price'] + stop}円にストップを入れます。")
            flag["position"]["lot"] = lot
            flag["position"]["stop"] = stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "SELL"
            flag["position"]["price"] = data["close_price"]
        else:
            print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    return flag


def close_position(data, last_data, flag):

    if flag["position"]["exist"] == False:
        return flag

    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            print_log(f"--------------------【クローズ判定】close_position() --------------------")
            print_log(f"過去{sell_term}足の最安値{signal['price']}を直近の価格が{data[judge_price['SELL']]}円でブレイクしました。")
            print_log("成り行き注文を出してポジションを決済します。")

            records(flag, data, data["close_price"])
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            print_log(f"--------------------【ドテンエントリー】close_position() --------------------")

            # if filter(signal) == False:
            #     print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。\n")
            #     return flag
            flag = filter(signal, flag)

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot > MIN_LOT:
                print_log(f"【売】さらに{str(data['close_price'])}円で{lot}BTCの売りの指値注文を入れてドテンします。")

                print_log(f"{data['close_price'] + stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = data["close_price"]
            else:
                print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            print_log(f"--------------------【クローズ判定】close_position() --------------------")
            print_log(f"過去{buy_term}足の最高値{signal['price']}を直近の価格が{data[judge_price['BUY']]}円でブレイクしました。")
            print_log("成り行き注文を出してポジションを決済します。")

            records(flag, data, data["close_price"])
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            print_log(f"--------------------【ドテンエントリー】close_position() --------------------")

            # if filter(signal) == False:
            #     print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。\n")
            #     return flag
            flag = filter(signal, flag)

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot > MIN_LOT:
                print_log(f"【買】さらに{str(data['close_price'])}円で{lot}BTCの買いの指値注文を入れてドテンします。")

                print_log(f"{data['close_price'] - stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = data["close_price"]
            else:
                print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    return flag


def stop_position(data, last_data, flag):

    if stop_config == "TRAILING":
        flag = bot.trail_stop(data, flag)

    if flag["position"]["side"] == "BUY":
        stop_price = flag["position"]["price"] - flag["position"]["stop"]
        if data["low_price"] < stop_price:
            print_log(f"--------------------【損切判定】stop_position() --------------------")
            print_log(f"{stop_price}円の損切りラインに引っかかりました。")
            stop_price = round(stop_price - 2 * bot.calculate_volatility(last_data) / (chart_sec / 60)) # 不利な価格で約定したとする
            print_log(f"{stop_price}円あたりで成り行き注文を出してポジションを決済します。")

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    if flag["position"]["side"] == "SELL":
        stop_price = flag["position"]["price"] + flag["position"]["stop"]
        if data["high_price"] > stop_price:
            print_log(f"--------------------【損切判定】stop_position() --------------------")
            print_log(f"{stop_price}円の損切りラインに引っかかりました。")
            stop_price = round(stop_price + 2 * bot.calculate_volatility(last_data) / (chart_sec / 60)) # 不利な価格で約定したとする
            print_log(f"{stop_price}円あたりで成り行き注文を出してポジションを決済します。")

            records(flag, data, stop_price, "STOP")
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    return flag


def records(flag, data, close_price, close_type=None):

    print_log(f"--------------------【記録】records() --------------------")

    flag["records"]["filter"].append(flag["records"]["filter-match"])

    entry_price = int(round(flag["position"]["price"] * flag["position"]["lot"]))
    exit_price = int(round(close_price * flag["position"]["lot"]))
    trade_cost = round(exit_price * slippage)

    print_log(f"スリッページ・手数料として{str(trade_cost)}円を考慮します")
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
            print_log(f"{str(buy_profit)}円の利益です")
        else:
            print_log(f"{str(buy_profit)}円の損失です")

    if flag["position"]["side"] == "SELL":
        flag["records"]["side"].append("SELL")
        flag["records"]["profit"].append(sell_profit)
        flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))
        flag["records"]["funds"] = flag["records"]["funds"] + sell_profit
        if sell_profit > 0:
            print_log(f"{str(sell_profit)}円の利益です")
        else:
            print_log(f"{str(sell_profit)}円の損失です")

    if flag["records"]["filter-match"] != "True":
        print_log("この取引はフィルターにかからなかったため、無効です。")

    return flag


def output_backtest(result):

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, index_col=0)
        df = df.append(pd.Series(result), ignore_index=True)
        df.to_csv(csv_file)
    else:
        df = pd.DataFrame([result], columns=result.keys())
        df.to_csv(csv_file)


def backtest(flag):

    # 使用パラメータ
    params = {
        "chart_sec": chart_sec,
        "buy_term": buy_term,
        "sell_term": sell_term,
        "judge_price": judge_price,
        "TEST_MODE_LOT": TEST_MODE_LOT,
        "volatility_term": volatility_term,
        "stop_range": stop_range,
        "trade_risk": trade_risk,
        "levarage": levarage,
        "start_funds": start_funds,
        "entry_times": entry_times,
        "entry_range": entry_range,
        "stop_config": stop_config,
        "stop_AF": stop_AF,
        "stop_AF_add": stop_AF_add,
        "stop_AF_max": stop_AF_max,
        "slippage": slippage,
        "filter_VER": filter_VER,
        "MA_term": MA_term
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
    filter_true_records = records[records.Filter.isin(["True"])]
    filter_false_records = records[records.Filter.isin(["False"])]

    filter_true_records["Gross"] = filter_true_records.Profit.cumsum()

    filter_true_records["Funds"] = filter_true_records.Gross + start_funds

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
        "StartFunds": start_funds,
        "FinalFunds": filter_true_records.Funds.iloc[-1],
        "Performance": round(filter_true_records.Funds.iloc[-1] / start_funds * 100, 2),
        "TotalSlippage": -1 * filter_true_records.Slippage.sum(),
        "LogFilePath": log_file_path,
        "Params": params
    }

    output_backtest(result)

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
    if filter_VER != "OFF":
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


if __name__ == "__main__":

    csv_file = "backtest-log/samplebot.csv"

    MIN_LOT = 0.01

    chart_sec = 3600
    chart_API = "cryptowatch" # cryptowatch / cryptocompare

    buy_term = 30
    sell_term = 30
    judge_price = {
        "BUY": "high_price",
        "SELL": "low_price"
    }

    TEST_MODE_LOT = "adjustable" # "fixed": 常に固定ロット / "adjustable": 可変ロット

    volatility_term = 10
    stop_range = 2
    trade_risk = 0.04
    levarage = 2
    start_funds = 300000

    entry_times = 2
    entry_range = 0.5

    stop_config = "TRAILING" # "ON" / "OFF" / "TRAILING"
    stop_AF = 0.02
    stop_AF_add = 0.02
    stop_AF_max = 0.2

    slippage = 0.0005

    filter_VER = "OFF" # "OFF" / "A" / "B"
    MA_term = 200

    flag = {
        "position": {
            "exist": False,
            "side": "",
            "price": 0,
            "stop": 0,
            "ATR": 0,
            "lot": 0,
            "count": 0,
            "stop-AF": stop_AF,
            "stop-EP": 0
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
            "funds": start_funds,
            "holding-periods": [],
            "slippage": [],
            "filter": [],
            "filter-match": "",
        }
    }


    price = bot.get_price(chart_sec, after=1451606400)
    last_data = []

    if filter_VER == "OFF":
        need_term = max(buy_term, sell_term, volatility_term)
    else:
        need_term = max(buy_term, sell_term, volatility_term, MA_term)

    i = 0
    while i < len(price):

        if len(last_data) < need_term:
            last_data.append(price[i])
            bot.print_price(price[i])
            i += 1
            continue

        data = price[i]
        bot.print_price(data)

        if flag["position"]["exist"]:
            if stop_config != "OFF":
                flag = stop_position(data, last_data, flag)
            flag = close_position(data, last_data, flag)
            flag = add_position(data, last_data, flag)
        else:
            flag = entry_signal(data, last_data, flag)

        last_data.append(data)
        i += 1
    
    backtest(flag)