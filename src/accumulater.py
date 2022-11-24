import os
import requests
from datetime import datetime
import time
import json
import pprint

import logging
formatter = '%(asctime)s : %(levelname)s : %(message)s'
logging.basicConfig(format=formatter, level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('system-log/console.log')
handler.setFormatter(logging.Formatter(formatter))
logger.addHandler(handler)

chart_sec = 60 # candle of 1 minite
symbols = ["btcjpy", "btcfxjpy"]

def accumulater(min, symbol, before=0, after=0):

    params = {"periods" : min}
    if before != 0:
        params["before"] = before
    if after != 0:
        params["after"] = after

    URL = "https://api.cryptowat.ch/markets/bitflyer/" + symbol + "/ohlc"
    response = requests.get(URL, params)
    data = response.json()

    if symbol == "btcjpy":
        filepath = "data.json"
    elif symbol == "btcfxjpy":
        filepath = "data_fx.json"

    if os.path.exists(filepath):

        data_set = set(map(tuple, data["result"][str(min)]))

        f = open(filepath, "r", encoding="utf-8")
        file_data = json.load(f)
        del file_data["result"][str(min)][-1] # delete last data due to duplication
        file_data_set = set(map(tuple, file_data["result"][str(min)]))

        diff_data_set = data_set - file_data_set
        diff_data = list(diff_data_set)

        if len(diff_data) != 0:
            diff_data.sort(key=lambda x: x[0])
            file_data["result"][str(min)].extend(diff_data)

        f = open(filepath, "w", encoding="utf-8")
        json.dump(file_data, f)
        logger.info(f"({symbol}) Accumulated {len(diff_data)} data.")
        
        return diff_data

    else:
        f = open(filepath, "w", encoding="utf-8")
        json.dump(data, f)
        logger.info(f"({symbol}) Accumulated {len(data['result'][str(min)])} data.")
        
        return data
    

if __name__ == "__main__":
    for symbol in symbols:
        accumulater(chart_sec, symbol, after=1483228800)