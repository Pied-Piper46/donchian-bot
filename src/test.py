import numpy as np
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt

""" Problem1 ：
許容リスクを元に注文ロットを計算する際に、小数点第2位以下が切り捨てられて注文ロットが0BTCになる問題。
例えばentry_times=4だと注文ロットが0.04未満だと切り捨てられて本来注文できる枚数を満たしているのにも関わらず注文できなくなる。

検証元関数：calculate_lot()

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


""" Problem2 ：
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

""" Problem3 : 
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

""" Problem4 : 
バックテストのログ出力方法変更。関数を使い回しできるようにするため。
元：flag["records"]["log"].append(text) -> logger.info(text)　に変更したい
"""
def answer4():
    from sample_bot import get_price, calculate_volatility

    price = get_price(3600)
    vol = calculate_volatility(price)
    print(vol)

""" Problem5:
bot_logから別ファイルに変数を取得する
"""
def problem5():
    from bot_log import print_log, log_file_path
    import time

    print(log_file_path)

# problem5()

""" Problem6:
変数のスコープ検証
"""
# value = "a"
def problem6():
    print(value)


""" Function1 : 欠損価格データの確認 """
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

""" Unit Test """
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from cls import Batman
import pprint

def unit_test():

    chart_sec = 7200

    entry_term = 50
    exit_term = 30
    judge_price = {
        "BUY": "close_price",
        "SELL": "close_price"
    }

    volatility_term = 30
    stop_range = 2
    trade_risk = 0.01
    levarage = 2

    entry_times = 3
    entry_range = 0.5

    trailing_config = "TRAILING"
    stop_AF = 0.03
    stop_AF_add = 0.03
    stop_AF_max = 0.2

    filter_VER = "B"
    MA_term = 100

    wait = 180

    log_config = "OFF"
    line_config = "OFF"

    test_flag = {
        "position": {
                "exist": True,
                "side": "BUY",
                "price": 2286615,
                "stop": 20000,
                "stop-AF": 0.03,
                "stop-EP": 0,
                "ATR": 0,
                "lot": 0.02,
                "count": 0
            },
            "add-position": {
                "count": 0,
                "first-entry-price": 0,
                "last-entry-price": 0,
                "unit-range": 10000,
                "unit-size": 0.01,
                "stop": 0
            }
    }

    bot = Batman.Batman1G(chart_sec, entry_term, exit_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config)

    # bot.print_log(f"{bot.need_term}期間分のデータを準備中...")
    # price = bot.get_price(bot.chart_sec)
    # last_data = price[-1 * bot.need_term -2: -2]

    # test last_data
    last_data = [
        {'close_time': 1670522400, 'close_time_dt': '2022/12/09 03:00', 'open_price': 2315869, 'high_price': 2322595, 'low_price': 2313765, 'close_price': 2321981}, {'close_time': 1670529600, 'close_time_dt': '2022/12/09 05:00', 'open_price': 2322265, 'high_price': 2368895, 'low_price': 2321479, 'close_price': 2364734}, {'close_time': 1670536800, 'close_time_dt': '2022/12/09 07:00', 'open_price': 2364684, 'high_price': 2371333, 'low_price': 2351085, 'close_price': 2353005}, {'close_time': 1670544000, 'close_time_dt': '2022/12/09 09:00', 'open_price': 2352952, 'high_price': 2362042, 'low_price': 2351876, 'close_price': 2356300}, {'close_time': 1670551200, 'close_time_dt': '2022/12/09 11:00', 'open_price': 2356544, 'high_price': 2363228, 'low_price': 2347565, 'close_price': 2348694}, {'close_time': 1670558400, 'close_time_dt': '2022/12/09 13:00', 'open_price': 2348999, 'high_price': 2351071, 'low_price': 2338264, 'close_price': 2339543}, {'close_time': 1670565600, 'close_time_dt': '2022/12/09 15:00', 'open_price': 2339893, 'high_price': 2345206, 'low_price': 2338520, 'close_price': 2343958}, {'close_time': 1670572800, 'close_time_dt': '2022/12/09 17:00', 'open_price': 2343957, 'high_price': 2347160, 'low_price': 2339645, 'close_price': 2345174}, {'close_time': 1670580000, 'close_time_dt': '2022/12/09 19:00', 'open_price': 2345174, 'high_price': 2349938, 'low_price': 2343676, 'close_price': 2348286}, {'close_time': 1670587200, 'close_time_dt': '2022/12/09 21:00', 'open_price': 2348283, 'high_price': 2351307, 'low_price': 2341256, 'close_price': 2343013}, {'close_time': 1670594400, 'close_time_dt': '2022/12/09 23:00', 'open_price': 2343207, 'high_price': 2357281, 'low_price': 2330837, 'close_price': 2334000}, {'close_time': 1670601600, 'close_time_dt': '2022/12/10 01:00', 'open_price': 2333850, 'high_price': 2347592, 'low_price': 2326600, 'close_price': 2345025}, {'close_time': 1670608800, 'close_time_dt': '2022/12/10 03:00', 'open_price': 2344737, 'high_price': 2345206, 'low_price': 2335430, 'close_price': 2338824}, {'close_time': 1670616000, 'close_time_dt': '2022/12/10 05:00', 'open_price': 2338494, 'high_price': 2338494, 'low_price': 2331856, 'close_price': 2335530}, {'close_time': 1670623200, 'close_time_dt': '2022/12/10 07:00', 'open_price': 2335569, 'high_price': 2336188, 'low_price': 2327000, 'close_price': 2329683}, {'close_time': 1670630400, 'close_time_dt': '2022/12/10 09:00', 'open_price': 2329894, 'high_price': 2335320, 'low_price': 2329205, 'close_price': 2333154}, {'close_time': 1670637600, 'close_time_dt': '2022/12/10 11:00', 'open_price': 2333259, 'high_price': 2336600, 'low_price': 2331765, 'close_price': 2335479}, {'close_time': 1670644800, 'close_time_dt': '2022/12/10 13:00', 'open_price': 2335379, 'high_price': 2336000, 'low_price': 2330589, 'close_price': 2334520}, {'close_time': 1670652000, 'close_time_dt': '2022/12/10 15:00', 'open_price': 2334576, 'high_price': 2335692, 'low_price': 2332490, 'close_price': 2332723}, {'close_time': 1670659200, 'close_time_dt': '2022/12/10 17:00', 'open_price': 2332854, 'high_price': 2337657, 'low_price': 2332122, 'close_price': 2335396}, {'close_time': 1670666400, 'close_time_dt': '2022/12/10 19:00', 'open_price': 2336843, 'high_price': 2337400, 'low_price': 2331117, 'close_price': 2335194}, {'close_time': 1670673600, 'close_time_dt': '2022/12/10 21:00', 'open_price': 2335211, 'high_price': 2337500, 'low_price': 2334423, 'close_price': 2335298}, {'close_time': 1670680800, 'close_time_dt': '2022/12/10 23:00', 'open_price': 2335239, 'high_price': 2337927, 'low_price': 2332893, 'close_price': 2334873}, {'close_time': 1670688000, 'close_time_dt': '2022/12/11 01:00', 'open_price': 2335019, 'high_price': 2343215, 'low_price': 2333600, 'close_price': 2341433}, {'close_time': 1670695200, 'close_time_dt': '2022/12/11 03:00', 'open_price': 2341267, 'high_price': 2343119, 'low_price': 2336000, 'close_price': 2337024}, {'close_time': 1670702400, 'close_time_dt': '2022/12/11 05:00', 'open_price': 2336917, 'high_price': 2339946, 'low_price': 2334500, 'close_price': 2336164}, {'close_time': 1670709600, 'close_time_dt': '2022/12/11 07:00', 'open_price': 2336221, 'high_price': 2338025, 'low_price': 2330673, 'close_price': 2331026}, {'close_time': 1670716800, 'close_time_dt': '2022/12/11 09:00', 'open_price': 2331026, 'high_price': 2333626, 'low_price': 2327713, 'close_price': 2331156}, {'close_time': 1670724000, 'close_time_dt': '2022/12/11 11:00', 'open_price': 2331187, 'high_price': 2335557, 'low_price': 2329975, 'close_price': 2334885}, {'close_time': 1670731200, 'close_time_dt': '2022/12/11 13:00', 'open_price': 2334985, 'high_price': 2336270, 'low_price': 2332700, 'close_price': 2334231}, {'close_time': 1670738400, 'close_time_dt': '2022/12/11 15:00', 'open_price': 2334396, 'high_price': 2338553, 'low_price': 2334130, 'close_price': 2336497}, {'close_time': 1670745600, 'close_time_dt': '2022/12/11 17:00', 'open_price': 2336543, 'high_price': 2344932, 'low_price': 2336397, 'close_price': 2342603}, {'close_time': 1670752800, 'close_time_dt': '2022/12/11 19:00', 'open_price': 2342336, 'high_price': 2343567, 'low_price': 2339086, 'close_price': 2341105}, {'close_time': 1670760000, 'close_time_dt': '2022/12/11 21:00', 'open_price': 2341264, 'high_price': 2342103, 'low_price': 2338200, 'close_price': 2341764}, {'close_time': 1670767200, 'close_time_dt': '2022/12/11 23:00', 'open_price': 2341823, 'high_price': 2342222, 'low_price': 2338305, 'close_price': 2341510}, {'close_time': 1670774400, 'close_time_dt': '2022/12/12 01:00', 'open_price': 2341507, 'high_price': 2342545, 'low_price': 2338834, 'close_price': 2341910}, {'close_time': 1670781600, 'close_time_dt': '2022/12/12 03:00', 'open_price': 2341853, 'high_price': 2345804, 'low_price': 2340448, 'close_price': 2345698}, {'close_time': 1670788800, 'close_time_dt': '2022/12/12 05:00', 'open_price': 2345798, 'high_price': 2358797, 'low_price': 2342440, 'close_price': 2347510}, {'close_time': 1670796000, 'close_time_dt': '2022/12/12 07:00', 'open_price': 2347638, 'high_price': 2348268, 'low_price': 2335198, 'close_price': 2338826}, {'close_time': 1670803200, 'close_time_dt': '2022/12/12 09:00', 'open_price': 2338821, 'high_price': 2339499, 'low_price': 2329489, 'close_price': 2333705}, {'close_time': 1670810400, 'close_time_dt': '2022/12/12 11:00', 'open_price': 2333693, 'high_price': 2333908, 'low_price': 2308599, 'close_price': 2312232}, {'close_time': 1670817600, 'close_time_dt': '2022/12/12 13:00', 'open_price': 2312090, 'high_price': 2314079, 'low_price': 2302006, 'close_price': 2307925}, {'close_time': 1670824800, 'close_time_dt': '2022/12/12 15:00', 'open_price': 2307652, 'high_price': 2317733, 'low_price': 2305894, 'close_price': 2316740}, {'close_time': 1670832000, 'close_time_dt': '2022/12/12 17:00', 'open_price': 2316840, 'high_price': 2317071, 'low_price': 2309454, 'close_price': 2310500}, {'close_time': 1670839200, 'close_time_dt': '2022/12/12 19:00', 'open_price': 2310503, 'high_price': 2319475, 'low_price': 2309636, 'close_price': 2316072}, {'close_time': 1670846400, 'close_time_dt': '2022/12/12 21:00', 'open_price': 2316073, 'high_price': 2320103, 'low_price': 2315522, 'close_price': 2319350}, {'close_time': 1670853600, 'close_time_dt': '2022/12/12 23:00', 'open_price': 2319144, 'high_price': 2326578, 'low_price': 2312022, 'close_price': 2321992}, {'close_time': 1670860800, 'close_time_dt': '2022/12/13 01:00', 'open_price': 2322116, 'high_price': 2335482, 'low_price': 2321853, 'close_price': 2334214}, {'close_time': 1670868000, 'close_time_dt': '2022/12/13 03:00', 'open_price': 2334328, 'high_price': 2338739, 'low_price': 2330636, 'close_price': 2335754}, {'close_time': 1670875200, 'close_time_dt': '2022/12/13 05:00', 'open_price': 2335748, 'high_price': 2345394, 'low_price': 2335748, 'close_price': 2345021}, {'close_time': 1670882400, 'close_time_dt': '2022/12/13 07:00', 'open_price': 2345360, 'high_price': 2369100, 'low_price': 2344142, 'close_price': 2364585}, {'close_time': 1670889600, 'close_time_dt': '2022/12/13 09:00', 'open_price': 2364503, 'high_price': 2370509, 'low_price': 2359555, 'close_price': 2366122}, {'close_time': 1670896800, 'close_time_dt': '2022/12/13 11:00', 'open_price': 2366122, 'high_price': 2370432, 'low_price': 2357022, 'close_price': 2358586}, {'close_time': 1670904000, 'close_time_dt': '2022/12/13 13:00', 'open_price': 2358566, 'high_price': 2361200, 'low_price': 2356096, 'close_price': 2361021}, {'close_time': 1670911200, 'close_time_dt': '2022/12/13 15:00', 'open_price': 2360891, 'high_price': 2365616, 'low_price': 2358775, 'close_price': 2362476}, {'close_time': 1670918400, 'close_time_dt': '2022/12/13 17:00', 'open_price': 2362417, 'high_price': 2365500, 'low_price': 2343542, 'close_price': 2351089}, {'close_time': 1670925600, 'close_time_dt': '2022/12/13 19:00', 'open_price': 2350776, 'high_price': 2416667, 'low_price': 2348758, 'close_price': 2402655}, {'close_time': 1670932800, 'close_time_dt': '2022/12/13 21:00', 'open_price': 2401037, 'high_price': 2406530, 'low_price': 2387370, 'close_price': 2400094}, {'close_time': 1670940000, 'close_time_dt': '2022/12/13 23:00', 'open_price': 2400093, 'high_price': 2459000, 'low_price': 2383787, 'close_price': 2413866}, {'close_time': 1670947200, 'close_time_dt': '2022/12/14 01:00', 'open_price': 2413900, 'high_price': 2417061, 'low_price': 2394297, 'close_price': 2395922}, {'close_time': 1670954400, 'close_time_dt': '2022/12/14 03:00', 'open_price': 2396076, 'high_price': 2405142, 'low_price': 2379169, 'close_price': 2382714}, {'close_time': 1670961600, 'close_time_dt': '2022/12/14 05:00', 'open_price': 2382772, 'high_price': 2402637, 'low_price': 2381605, 'close_price': 2398392}, {'close_time': 1670968800, 'close_time_dt': '2022/12/14 07:00', 'open_price': 2398365, 'high_price': 2404993, 'low_price': 2393716, 'close_price': 2403595}, {'close_time': 1670976000, 'close_time_dt': '2022/12/14 09:00', 'open_price': 2403906, 'high_price': 2408531, 'low_price': 2391721, 'close_price': 2403970}, {'close_time': 1670983200, 'close_time_dt': '2022/12/14 11:00', 'open_price': 2403953, 'high_price': 2411313, 'low_price': 2398156, 'close_price': 2404747}, {'close_time': 1670990400, 'close_time_dt': '2022/12/14 13:00', 'open_price': 2404740, 'high_price': 2408438, 'low_price': 2399563, 'close_price': 2401533}, {'close_time': 1670997600, 'close_time_dt': '2022/12/14 15:00', 'open_price': 2401533, 'high_price': 2402559, 'low_price': 2393242, 'close_price': 2401426}, {'close_time': 1671004800, 'close_time_dt': '2022/12/14 17:00', 'open_price': 2401404, 'high_price': 2405051, 'low_price': 2398500, 'close_price': 2403592}, {'close_time': 1671012000, 'close_time_dt': '2022/12/14 19:00', 'open_price': 2404152, 'high_price': 2410000, 'low_price': 2398094, 'close_price': 2401661}, {'close_time': 1671019200, 'close_time_dt': '2022/12/14 21:00', 'open_price': 2401561, 'high_price': 2401723, 'low_price': 2392341, 'close_price': 2399344}, {'close_time': 1671026400, 'close_time_dt': '2022/12/14 23:00', 'open_price': 2399419, 'high_price': 2417334, 'low_price': 2398668, 'close_price': 2408900}, {'close_time': 1671033600, 'close_time_dt': '2022/12/15 01:00', 'open_price': 2408711, 'high_price': 2434228, 'low_price': 2408000, 'close_price': 2430101}, {'close_time': 1671040800, 'close_time_dt': '2022/12/15 03:00', 'open_price': 2430172, 'high_price': 2444234, 'low_price': 2429671, 'close_price': 2437162}, {'close_time': 1671048000, 'close_time_dt': '2022/12/15 05:00', 'open_price': 2437246, 'high_price': 2473921, 'low_price': 2395521, 'close_price': 2399247}, {'close_time': 1671055200, 'close_time_dt': '2022/12/15 07:00', 'open_price': 2398776, 'high_price': 2409730, 'low_price': 2382601, 'close_price': 2405548}, {'close_time': 1671062400, 'close_time_dt': '2022/12/15 09:00', 'open_price': 2405548, 'high_price': 2410838, 'low_price': 2396360, 'close_price': 2400978}, {'close_time': 1671069600, 'close_time_dt': '2022/12/15 11:00', 'open_price': 2400879, 'high_price': 2407248, 'low_price': 2373362, 'close_price': 2376292}, {'close_time': 1671076800, 'close_time_dt': '2022/12/15 13:00', 'open_price': 2376363, 'high_price': 2394000, 'low_price': 2368136, 'close_price': 2389852}, {'close_time': 1671084000, 'close_time_dt': '2022/12/15 15:00', 'open_price': 2390110, 'high_price': 2392904, 'low_price': 2384054, 'close_price': 2387749}, {'close_time': 1671091200, 'close_time_dt': '2022/12/15 17:00', 'open_price': 2387749, 'high_price': 2398881, 'low_price': 2387340, 'close_price': 2390714}, {'close_time': 1671098400, 'close_time_dt': '2022/12/15 19:00', 'open_price': 2390602, 'high_price': 2403872, 'low_price': 2388973, 'close_price': 2403663}, {'close_time': 1671105600, 'close_time_dt': '2022/12/15 21:00', 'open_price': 2403534, 'high_price': 2409200, 'low_price': 2398260, 'close_price': 2404496}, {'close_time': 1671112800, 'close_time_dt': '2022/12/15 23:00', 'open_price': 2404496, 'high_price': 2406000, 'low_price': 2367486, 'close_price': 2373283}, {'close_time': 1671120000, 'close_time_dt': '2022/12/16 01:00', 'open_price': 2373286, 'high_price': 2385227, 'low_price': 2365859, 'close_price': 2381532}, {'close_time': 1671127200, 'close_time_dt': '2022/12/16 03:00', 'open_price': 2381203, 'high_price': 2387345, 'low_price': 2375000, 'close_price': 2383760}, {'close_time': 1671134400, 'close_time_dt': '2022/12/16 05:00', 'open_price': 2383467, 'high_price': 2393142, 'low_price': 2370520, 'close_price': 2388057}, {'close_time': 1671141600, 'close_time_dt': '2022/12/16 07:00', 'open_price': 2387791, 'high_price': 2390401, 'low_price': 2380157, 'close_price': 2385977}, {'close_time': 1671148800, 'close_time_dt': '2022/12/16 09:00', 'open_price': 2385962, 'high_price': 2387360, 'low_price': 2368432, 'close_price': 2374139}, {'close_time': 1671156000, 'close_time_dt': '2022/12/16 11:00', 'open_price': 2374043, 'high_price': 2392645, 'low_price': 2372274, 'close_price': 2380700}, {'close_time': 1671163200, 'close_time_dt': '2022/12/16 13:00', 'open_price': 2380684, 'high_price': 2388766, 'low_price': 2380500, 'close_price': 2388485}, {'close_time': 1671170400, 'close_time_dt': '2022/12/16 15:00', 'open_price': 2388326, 'high_price': 2388758, 'low_price': 2379099, 'close_price': 2385310}, {'close_time': 1671177600, 'close_time_dt': '2022/12/16 17:00', 'open_price': 2385312, 'high_price': 2401787, 'low_price': 2382132, 'close_price': 2398666}, {'close_time': 1671184800, 'close_time_dt': '2022/12/16 19:00', 'open_price': 2398666, 'high_price': 2400002, 'low_price': 2317734, 'close_price': 2332040}, {'close_time': 1671192000, 'close_time_dt': '2022/12/16 21:00', 'open_price': 2332001, 'high_price': 2332349, 'low_price': 2315433, 'close_price': 2328634}, {'close_time': 1671199200, 'close_time_dt': '2022/12/16 23:00', 'open_price': 2328366, 'high_price': 2328366, 'low_price': 2312698, 'close_price': 2315352}, {'close_time': 1671206400, 'close_time_dt': '2022/12/17 01:00', 'open_price': 2315252, 'high_price': 2333397, 'low_price': 2305016, 'close_price': 2313264}, {'close_time': 1671213600, 'close_time_dt': '2022/12/17 03:00', 'open_price': 2313429, 'high_price': 2314272, 'low_price': 2281624, 'close_price': 2287385}, {'close_time': 1671220800, 'close_time_dt': '2022/12/17 05:00', 'open_price': 2287384, 'high_price': 2302265, 'low_price': 2285144, 'close_price': 2300213}, {'close_time': 1671228000, 'close_time_dt': '2022/12/17 07:00', 'open_price': 2300292, 'high_price': 2313342, 'low_price': 2296485, 'close_price': 2299669}, {'close_time': 1671235200, 'close_time_dt': '2022/12/17 09:00', 'open_price': 2300005, 'high_price': 2305197, 'low_price': 2258174, 'close_price': 2270850}]

    # bot.print_log("---実行開始---")

    # data = bot.get_realtime_price(bot.chart_sec)

    # test data
    data = {'settled': {'close_time': 1671249600, 'open_price': 2275455, 'high_price': 2281561, 'low_price': 2265038, 'close_price': 2507479}, 'forming': {'close_time': 1671256800, 'open_price': 2277481, 'high_price': 2280614, 'low_price': 2234812, 'close_price': 2306152}}

    bot.find_unexpected_pos(last_data, bot.flag)
    
# unit_test()