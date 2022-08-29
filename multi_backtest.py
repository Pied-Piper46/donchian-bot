import requests
from datetime import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import csv

import test
from params import *


def entry_signal(data, last_data, flag):
    
    signal = test.donchian(data, last_data)
    if signal["side"] == "BUY":

        # ここに買い注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"
        flag["order"]["price"] = data["close_price"]

    if signal["side"] == "SELL":

        # ここに売り注文のコードを入れる
        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"
        flag["order"]["price"] = data["close_price"]

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

            # ここに決済の成行注文コードを入れる
            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "SELL"
            flag["order"]["price"] = data["close_price"]

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":

            # ここに決済の成行注文コードを入れる
            records(flag, data)
            flag["position"]["exist"] = False
            flag["position"]["count"] = 0

            # ここに売り注文のコードを入れる
            flag["order"]["exist"] = True
            flag["order"]["side"] = "BUY"
            flag["order"]["price"] = data["close_price"]

    return flag


def records(flag, data):

    entry_price = flag["position"]["price"]
    exit_price = round(data["close_price"] * lot)
    trade_cost = round(exit_price * slippage)
    flag["records"]["slippage"].append(trade_cost)

    flag["records"]["date"].append(data["close_time_dt"])
    flag["records"]["holding-periods"].append(flag["position"]["count"])

    buy_profit = exit_price - entry_price - trade_cost
    sell_profit = entry_price - exit_price - trade_cost

    if flag["position"]["side"] == "BUY":
        flag["records"]["side"].append("BUY")
        flag["records"]["profit"].append(buy_profit)
        flag["records"]["return"].append(round(buy_profit / entry_price * 100, 4))

    if flag["position"]["side"] == "SELL":
        flag["records"]["side"].append("SELL")
        flag["records"]["profit"].append(sell_profit)
        flag["records"]["return"].append(round(sell_profit / entry_price * 100, 4))

    return flag


def backtest(flag):

    records = pd.DataFrame({
        "Date": pd.to_datetime(flag["records"]["date"]),
        "Profit": flag["records"]["profit"],
        "Side": flag["records"]["side"],
        "Rate": flag["records"]["return"],
        "Periods": flag["records"]["holding-periods"],
        "Slippage": flag["records"]["slippage"]
    })

    records["Gross"] = records.Profit.cumsum()

    records["Drawdown"] = records.Gross.cummax().subtract(records.Gross)
    records["DrawdownRate"] = round(records.Drawdown / records.Gross.cummax() * 100, 1)

    print("バックテストの結果")
    print("---------------------------")
    print("総合成績")
    print("---------------------------")
    print(f"全トレード数　　　：　{len(records)}回")
    print(f"勝率　　　　　　　：　{round(len(records[records.Profit>0]) / len(records) * 100, 1)}％")
    print(f"平均リターン　　　：　{round(records.Rate.mean(), 2)}％")
    print(f"平均保有期間　　　：　{round(records.Periods.mean(), 1)}足分")
    print("")
    print(f"最大の勝ちトレード：　{records.Profit.max()}円")
    print(f"最大の負けトレード：　{records.Profit.min()}円")
    print(f"最大ドローダウン　：　{-1 * records.Drawdown.max()}円 / {-1 * records.DrawdownRate.loc[records.Drawdown.idxmax()]}％")
    print(f"利益合計　　　　　：　{records[records.Profit>0].Profit.sum()}円")
    print(f"損失合計　　　　　：　{records[records.Profit<0].Profit.sum()}円")
    print("")
    print(f"最終損益　　　　　：　{records.Profit.sum()}円")
    print(f"手数料合計　　　　：　{-1 * records.Slippage.sum()}円")

    result = {
        "トレード回数": len(records),
        "勝率": round(len(records[records.Profit>0]) / len(records) * 100, 1),
        "平均リターン": round(records.Rate.mean(), 2),
        "最大ドローダウン": -1 * records.Drawdown.max(),
        "最終損益": records.Profit.sum(),
        "プロフィットファクター": round(-1 * (records[records.Profit>0].Profit.sum() / records[records.Profit<0].Profit.sum()), 2)
    }

    return result


def main():
    price_list = {}
    for chart_sec in chart_sec_list:
        price_list[chart_sec] = test.get_price(chart_sec, after=1483228800)
        print(f"-----{int(chart_sec/60)}分軸の価格データをCryptowatchから取得中-----")
        time.sleep(10)

    param_buy_term = []
    param_sell_term = []
    param_chart_sec = []
    param_judge_price = []

    result_count = []
    result_winRate = []
    result_returnRate = []
    result_drawdown = []
    result_profitFactor = []
    result_gross = []

    combinations = [(chart_sec, buy_term, sell_term, judge_price)
                for chart_sec in chart_sec_list
                for buy_term in buy_term_list
                for sell_term in sell_term_list
                for judge_price in judge_price_list]

    for chart_sec, buy_term, sell_term, judge_price in combinations:

        price = price_list[chart_sec]
        last_data = []
        i = 0

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
                "date": [],
                "profit": [],
                "return": [],
                "side": [],
                "holding-periods": [],
                "slippage": [],
            }
        }

        while i < len(price):

            if len(last_data) < buy_term or len(last_data) < sell_term:
                last_data.append(price[i])
                time.sleep(wait)
                i += 1
                continue
            
            data = price[i]

            if flag["order"]["exist"]:
                flag = check_order(flag)
            elif flag["position"]["exist"]:
                flag = close_position(data, last_data, flag)
            else:
                flag = entry_signal(data, last_data, flag)

            last_data.append(data)
            i += 1
            time.sleep(wait)

        print("-----------------------")
        print("テスト期間")
        print("開始時点：" + str(price[0]["close_time_dt"]))
        print("終了時点：" + str(price[-1]["close_time_dt"]))
        print("時間軸：" + str(int(chart_sec/60)) + "分足で検証")
        print("パラメータ１" + str(buy_term) + "期間／買い")
        print("パラメータ２" + str(sell_term) + "期間／売り")
        print(str(len(price)) + "件のローソク足データで検証")
        print("-----------------------")

        result = backtest(flag)

        param_buy_term.append(buy_term)
        param_sell_term.append(sell_term)
        param_chart_sec.append(chart_sec)
        if judge_price["BUY"] == "high_price":
            param_judge_price.append("高値/安値")
        else:
            param_judge_price.append("終値/終値")

        result_count.append(result["トレード回数"])
        result_winRate.append(result["勝率"])
        result_returnRate.append(result["平均リターン"])
        result_drawdown.append(result["最大ドローダウン"])
        result_profitFactor.append(result["プロフィットファクター"])
        result_gross.append(result["最終損益"])

    df = pd.DataFrame({
        "時間軸": param_chart_sec,
        "買い期間": param_buy_term,
        "売り期間": param_sell_term,
        "判定基準": param_judge_price,
        "トレード回数": result_count,
        "勝率": result_winRate,
        "平均リターン": result_returnRate,
        "ドローダウン": result_drawdown,
        "PF": result_profitFactor,
        "最終損益": result_gross
    })

    df = df[["時間軸", "買い期間", "売り期間", "判定基準", "トレード回数", "勝率", "平均リターン", "ドローダウン", "PF", "最終損益"]]

    df.drop(df[df["トレード回数"] < 100].index, inplace=True)

    df.to_csv(f"result-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv", encoding='utf_8_sig')


if __name__ == '__main__':
    main()