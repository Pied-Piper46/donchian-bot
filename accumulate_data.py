import requests
from datetime import datetime
import time
import json
import pprint

chart_sec = 60 # candle stick of 1 minite
file_path = "./test.json"
URL = "https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc"


def accumulate_data(min, file_path, before=0, after=0):

    # get data
    params = {"periods" : min}
    if before != 0:
        params["before"] = before
    if after != 0:
        params["after"] = after
    
    response = requests.get(URL, params)
    data = response.json()

    # write data to file
    f = open(file_path, "w", encoding="utf-8")
    json.dump(data, f)

    return data


def accumulate_diff_data(min, read_path, save_path, before=0, after=0):

    # get data from web
    params = {"periods" : min}
    if before != 0:
        params["before"] = before
    if after != 0:
        params["after"] = after
    
    response = requests.get(URL, params)
    web_data = response.json()
    web_data_set = set(map(tuple, web_data["result"][str(min)]))

    # get data from a read file
    f = open(read_path, "r", encoding="utf-8")
    f_data = json.load(f)
    del f_data["result"][str(min)][-1] # delete last data because of duplication
    f_data_set = set(map(tuple, f_data["result"][str(min)]))

    # get diff
    diff_data_set = web_data_set - f_data_set
    diff_data = list(diff_data_set)

    # add diff
    if len(diff_data) != 0:
        print(f"There are {len(diff_data)} diff data")
        diff_data.sort(key=lambda x:x[0])
        f_data["result"][str(min)].extend(diff_data)
        pprint.pprint(diff_data)

    # write data to file
    f = open(save_path, "w", encoding="utf-8")
    json.dump(f_data, f)

    return f_data



# accumulate_data(chart_sec, file_path, after=1483228800)
accumulate_diff_data(chart_sec, file_path, file_path, after=1483228800)