import requests
from datetime import datetime
import time
import json
from pprint import pprint

chart_sec = 60

def get_price(min, before=0, after=0):
    price = []
    params = {"periods" : min}
    if before != 0:
        params["before"] = before
    if after != 0:
        params["after"] = after

    response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc", params)
    data = response.json()

    if data["result"][str(min)]:
        for i in data["result"][str(min)]:
            price.append({
                "close_time" : i[0],
                "close_time_dt" : datetime.fromtimestamp(i[0]).strftime('%Y/%m/%d %H:%M'),
                "open_price" : i[1],
                "high_price" : i[2],
                "low_price" : i[3],
                "close_price" : i[4]
            })
        
        return price

    else:
        print("No data")
        return None


def get_price_from_file(min, file_path, start_period=None, end_period=None):
    
    f = open(file_path, "r", encoding="utf-8")
    data = json.load(f)

    start_unix = 0
    end_unix = 9999999999

    if start_period:
        start_period = datetime.strptime(start_period, "%Y/%m/%d %H:%M")
        start_unix = int(start_period.timestamp())
    if end_period:
        end_period = datetime.strptime(end_period, "%Y/%m/%d %H:%M")
        end_unix = int(end_period.timestamp())

    price = []
    for i in data["result"][str(min)]:
        if i[0] >= start_unix and i[0] <= end_unix:
            if i[1] != 0 and i[2] != 0 and i[3] != 0 and i[4] != 0:
                price.append({
                    "close_time" : i[0],
                    "close_time_dt" : datetime.fromtimestamp(i[0]).strftime("%Y/%m/%d %H:%M"),
                    "open_price" : i[1],
                    "high_price" : i[2],
                    "low_price" : i[3],
                    "close_price" : i[4],
                })

    return price


def main():
    ### get data from website ###
    # price = get_price(chart_sec, after=1653000000)

    # if price:
    #     print("first data: " + price[0]["close_time_dt"] + " UNIX TIME : " + str(price[0]["close_time"]))
    #     print("last data: " + price[-1]["close_time_dt"] + " UNIX TIME : " + str(price[-1]["close_time"]))
    #     print("Got a total of " + str(len(price)) + " candlestick data.")
    #     print("-------------------------------------")
    #     print("-------------------------------------")

    ### get data from a file ###
    FILE_PATH = "./test.json"

    start_period = "2022/06/06 00:00"
    end_period = "2022/06/08 00:00"

    price = get_price_from_file(chart_sec, FILE_PATH, start_period, end_period)

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
            print(f"Data of the time of {datetime.fromtimestamp(num)} does not exsit.")

        num += chart_sec


if __name__ == '__main__':
    main()