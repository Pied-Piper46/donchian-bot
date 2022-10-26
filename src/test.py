import numpy as np
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt

"""
検証元関数：calculate_lot()

Problem1：
許容リスクを元に注文ロットを計算する際に、小数点第2位以下が切り捨てられて注文ロットが0BTCになる問題。
例えばentry_times=4だと注文ロットが0.04未満だと切り捨てられて本来注文できる枚数を満たしているのにも関わらず注文できなくなる。

解決策：
最低注文可能枚数を元にそれ以上の枚数は切り捨てられないようにする。なおコードはMIN_LOT=0.xxxx1を想定（0.002などを想定していない）
"""

def problem1():
    
    entry_times = 4
    calc_lot = 0.039
    unit_size = np.floor(calc_lot / entry_times * 100) / 100 # この100に依存している（1000だと小数点以下第3位切り捨て）

    print(unit_size) # 0.0

def answer1():

    MIN_LOT = 0.001
    entry_times = 4
    calc_lot = 0.039
    unit_size = np.floor(calc_lot / entry_times * (1 / MIN_LOT)) / (1 / MIN_LOT)

    print(unit_size) # 0.09 <- 注文できる！


"""
Problem2：
シークレットキーを平文でスクリプトに書いている。これではgitにpushできない。

解決策2：
簡易的であるが、各環境（PC）ごとにsecrets.jsonファイルを生成、管理。このファイルはgitの管理対象外とする。
あとは、スクリプトから適宜読み込む。
"""

def problem2():

    bitflyer.apiKey = 'blahblahblah'
    bitflyer.secret = 'blahblahblah'

def answer2():

    bitflyer.apiKey = get_secret('api_key')
    bitflyer.secret = get_secret('api_secret')


"""
Problem3 : 
蓄積データの欠損行確認 -> Notion Note: 2022.09.25
"""

def problem3():

    # ファイルデータをDataFrameで読み込み + 時刻をDatetimeに変換、DataFrameのindexに。
    f = open("data.json", "r", encoding="utf-8")
    file_data = json.load(f)
    data = file_data["result"][str(60)]
    df = pd.DataFrame(data, columns=["CloseTime", "OpenPrice", "HighPrice", "LowPrice", "ClosePrice", "Volume", "QuoteVolume"])
    df.index = df["CloseTime"].apply(datetime.fromtimestamp)
    # print(df)
    # print(len(df))

    # データの蓄積開始時刻から終了時刻まで連続したDataFrameを作成
    df_fill = pd.DataFrame(index=pd.date_range(start=df.index[0], end=df.index[-1], freq="T"))
    # print(len(df_fill))

    # 元のDataFrameとマージして、欠けている時刻のデータはNULLに。
    df_fill = df_fill.merge(df, how="outer", left_index=True, right_index=True)
    # print(len(df_fill))

    # データがNULLの時刻を抽出
    drop_time = df_fill.index[df_fill.isnull().all(axis=1)]
    # print(len(drop_time))

    # 重複した時刻を抽出
    duplicated_time = df_fill[df_fill.index.duplicated(keep='first')].index # keep=last: 重複した最後の行を抽出 / keep=false: 重複した行全て抽出
    # print(len(duplicated_time))

    return drop_time, duplicated_time
    
# drop, dupli = problem3()
# print(drop)
# print(dupli)


"""
Problem4 :
バックテストのログ出力方法変更。関数を使い回しできるようにするため。
元：flag["records"]["log"].append(text) -> logger.info(text)　に変更したい
"""

def answer4():
    from sample_bot import get_price, calculate_volatility

    price = get_price(3600)
    vol = calculate_volatility(price)
    print(vol)



"""
Problem5:
bot_logから別ファイルに変数を取得する
"""

def problem5():
    from bot_log import print_log, log_file_path
    import time

    print(log_file_path)

# problem5()

"""
Problem6:
変数のスコープ検証
"""
# value = "a"
def problem6():
    print(value)


"""
Function1:
欠損価格データの確認
"""

def func1():

    import os, sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from cls import Backtest

    chart_sec = 60
    data_file = "data.json"

    start_period = "2022/06/06 00:00"
    end_period = "2022/06/09 00:00"

    price = Backtest.Backtest1G.get_price_from_file(data_file, chart_sec, start_period, end_period)

    print("-------------------------------")
    print("Periods")
    print("Start time : " + str(price[0]["close_time_dt"]))
    print("End time : " + str(price[-1]["close_time_dt"]))
    print("validate with " + str(len(price)) + "candle sticks")
    print("-------------------------------")

    # pprint(price[:500])

    num = int(datetime.strptime(start_period, "%Y/%m/%d %H:%M").timestamp())
    for i in range(len(price)):
        match = False
        for p in price:
            if num == p["close_time"]:
                match = True
        if match == False:
            print(f"{datetime.fromtimestamp(num)}: not exsit.")

        num += chart_sec

# func1()