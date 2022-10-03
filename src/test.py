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



