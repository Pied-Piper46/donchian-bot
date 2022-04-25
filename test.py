import requests
from datetime import datetime
import time

response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc", params={"periods": 60})

# Get the i price for any time chart
def get_price(minutes, i):
    data = response.json()

    return {"close_time" : data["result"][str(minutes)][i][0],
            "open_price" : data["result"][str(minutes)][i][1],
            "high_price" : data["result"][str(minutes)][i][2],
            "low_price" : data["result"][str(minutes)][i][3],
            "close_price" : data["result"][str(minutes)][i][4]}

# Print a close time, open price and close price
def print_price(data):
    close_time_str = datetime.fromtimestamp(data["close_time"]).strftime('%Y/%m/%d %H:%M')
    print("時間: " + close_time_str + " 始値: " + str(data["open_price"]) + " 終値: " + str(data["close_price"]))

# Fuction to check if each candlestick meets the condition for entry (white candlestick)
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

# Function to check if the opening and closing prices are consecutively rounded up
def check_ascend(data, last_data):
    if data["open_price"] > last_data["open_price"] and data["close_price"] > last_data["close_price"]:
        return True
    else:
        return False

# Function to place a buying limit order at the light of a signal
def buy_signal(data, last_data, flag):
    if flag["buy_signal"] == 0 and check_candle(data):
        flag["buy_signal"] = 1
    elif flag["buy_signal"] == 1 and check_candle(data) and check_ascend(data, last_data):
        print("2 consecutive white candlestick")
        flag["buy_signal"] = 2
    elif flag["buy_signal"] == 2 and check_candle(data) and check_ascend(data, last_data):
        print("Buy! (3 consecutive white candlestick)")

        # buy
        #
        #
        flag["buy_signal"] = 3
        flag["order"] = True
    else:
        flag["buy_signal"] = 0

    return flag

# Fuction to place a selling market order to close when there is a signal to close
def close_position(data, last_data, flag):
    if data["close_price"] < last_data["close_price"]:
        print("")
        flag["position"] = False
    return flag

# Function to check if an order submitted to the server has been executed
def check_order(flag):
    flag["order"] = False
    flag["position"] = True
    return flag

# main   
last_data = get_price(60, 0)
print_price(last_data)

flag = {
    "buy_signal": 0,
    "order": False,
    "position": False
}
i = 1

while i < 1000:
    if flag["order"]:
        flag = check_order(flag)

    data = get_price(60, i)

    if data["close_time"] != last_data["close_time"]:
        print_price(data)
        
        if flag["position"]:
            flag = close_position(data, last_data, flag)
        else:
            flag = buy_signal(data, last_data, flag)

        last_data["close_time"] = data["close_time"]
        last_data["open_price"] = data["open_price"]
        last_data["clese_price"] = data["close_price"]
        i += 1

    time.sleep(0)