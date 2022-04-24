import requests
from datetime import datetime
import time

response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc", params={"periods": 60})

# Get the latest price for any time chart
def get_price(minutes, i):
    data = response.json()
    last_data = data["result"][str(minutes)][i]

    return {"close_time" : last_data[0],
            "open_price" : last_data[1],
            "high_price" : last_data[2],
            "low_price" : last_data[3],
            "close_price" : last_data[4]}

# Print a close time, open price and close price
def print_price(data):
    close_time_str = datetime.fromtimestamp(data["close_time"]).strftime('%Y/%m/%d %H:%M')
    print("時間: " + close_time_str + " 始値: " + str(data["open_price"]) + " 終値: " + str(data["close_price"]))
    
def check_candle(data):
    try:
        realbody_rate = abs(data["close_price"] - data["open_price"]) / (data["high_price"] - data["low_price"])
    except ZeroDivisionError:
        realbody_rate = 0

    increase_rate = data["close_price"] / data["open_price"] - 1

    if data["close_price"] < data["open_price"]:
        return False
    elif increase_rate < 0.0005:
        return False
    elif realbody_rate < 0.5:
        return False
    else:
        return True

def check_ascend(data, last_data):
    if data["open_price"] > last_data["open_price"] and data["close_price"] > last_data["close_price"]:
        return True
    else:
        return False

last_data = get_price(60, 0)
print_price(last_data)
time.sleep(10)

flag = 0
i = 1

while i < 1000:
    data = get_price(60, i)

    if data["close_time"] != last_data["close_time"]:
        print_price(data)
        if flag == 0 and check_candle(data):
            flag = 1
        elif flag == 1 and check_candle(data) and check_ascend(data, last_data):
            print("2 consecutive white candlestick")
            flag = 2
        elif flag == 2 and check_candle(data) and check_ascend(data, last_data):
            print("Buy! (3 consecutive white candlestick)")
            flag = 3
        else:
            flag = 0

        last_data["close_time"] = data["close_time"]
        last_data["open_price"] = data["open_price"]
        last_data["clese_price"] = data["close_price"]

    i += 1
    time.sleep(0)