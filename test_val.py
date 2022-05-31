import requests
from datetime import datetime
import time

response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc", params={"periods": 60})

# Get the i price data (OHLC) for any time chart from Cryptowatch
def get_price(minutes, i):
    data = response.json()
    # print(len(data['result'][str(minutes)])) # -> 1000 (1000 data in one request)

    return {"close_time" : data["result"][str(minutes)][i][0],
            "open_price" : data["result"][str(minutes)][i][1],
            "high_price" : data["result"][str(minutes)][i][2],
            "low_price" : data["result"][str(minutes)][i][3],
            "close_price" : data["result"][str(minutes)][i][4]}

# Print a close time, an open price and a close price
def print_price(price_data):
    close_time_str = datetime.fromtimestamp(price_data["close_time"]).strftime('%Y/%m/%d %H:%M')
    print("Time: " + close_time_str + " | Open price: " + str(price_data["open_price"]) + " | Close price: " + str(price_data["close_price"]))

# Fuction to check if each candlestick meets the condition for entry (white and black candlestick)
def check_candle(price_data, side):
    try:
        realbody_rate = abs(price_data["close_price"] - price_data["open_price"]) / (price_data["high_price"] - price_data["low_price"])
    except ZeroDivisionError:
        realbody_rate = 0

    increase_rate = price_data["close_price"] / price_data["open_price"] - 1

    if side == "buy":
        if price_data["close_price"] < price_data["open_price"]:
            return False
        elif increase_rate < 0.0003:
            return False
        elif realbody_rate < 0.5:
            return False
        else:
            return True

    if side == "sell":
        if price_data["close_price"] > price_data["open_price"]:
            return False
        elif increase_rate > -0.0003:
            return False
        elif realbody_rate < 0.5:
            return False
        else:
            return True

# Function to check if the opening and closing prices are consecutively rounded up
def check_ascend(price_data, last_data):
    if price_data["open_price"] > last_data["open_price"] and price_data["close_price"] > last_data["close_price"]:
        return True
    else:
        return False

# Function to check if the opening and closing prices are consecutively fall down
def check_descend(price_data, last_data):
    if price_data["open_price"] < last_data["open_price"] and price_data["close_price"] < last_data["close_price"]:
        return True
    else:
        return False

# Function to place a buying limit order at the light of a buying signal
def buy_signal(price_data, last_data, flag):
    if flag["buy_signal"] == 0 and check_candle(price_data, "buy"):
        flag["buy_signal"] = 1
    elif flag["buy_signal"] == 1 and check_candle(price_data, "buy") and check_ascend(price_data, last_data):
        print("2 consecutive white candlestick")
        flag["buy_signal"] = 2
    elif flag["buy_signal"] == 2 and check_candle(price_data, "buy") and check_ascend(price_data, last_data):
        print("Place a buying limit order for " + str(price_data["close_price"]) + " ! (3 consecutive white candlestick)")
        flag["buy_signal"] = 3

        # write order function
        flag["order"]["exist"] = True
        flag["order"]["side"] = "BUY"

    else:
        flag["buy_signal"] = 0

    return flag

# Function to place a selling limit order at the light of a selling signal
def sell_signal(price_data, last_data, flag):
    if flag["sell_signal"] == 0 and check_candle(price_data, "sell"):
        flag["sell_signal"] = 1
    elif flag["sell_signal"] == 1 and check_candle(price_data, "sell") and check_descend(price_data, last_data):
        flag["sell_signal"] = 2
    elif flag["sell_signal"] == 2 and check_candle(price_data, "sell") and check_descend(price_data, last_data):
        print("Place a selling limit order for " + str(price_data["close_price"]) + " ! (3 consecutive black candlestick)")
        flag["sell_signal"] = 3

        ### write order function ###
        flag["order"]["exist"] = True
        flag["order"]["side"] = "SELL"
    else:
        flag["sell_signal"] = 0
    
    return flag

# Fuction to place a market order to close when there is a signal to close
def close_position(price_data, last_data, flag):
    if flag["position"]["side"] == "BUY":
        if price_data["close_price"] < last_data["close_price"]:
            print("Because of under the previous close price, place a market order to close it at around " + str(price_data["close_price"]) + " yen.")

            ### write order function ###
            flag["position"]["exist"] = False
    
    if flag["position"]["side"] == "SELL":
        if price_data["close_price"] > last_data["close_price"]:
            print("Because of exceeding the previous close price, place a market order to close it at around " + str(price_data["close_price"]) + " yen.")

            ### write order function ###
            flag["position"]["exist"] = False

    return flag

# Function to check if an order submitted to the server has been executed
def check_order(flag):
    
    ### write check function ###
    flag["order"]["exist"] = False
    flag["order"]["count"] = 0
    flag["position"]["exist"] = True
    flag["position"]["side"] = flag["order"]["side"]
    return flag

# # Function to cancel orders
# def cancel_order(orders, flag):
#     return True

# main
def main():
    last_data = get_price(60, 0)
    print_price(last_data)

    flag = {
        "buy_signal": 0,
        "sell_signal": 0,
        "order": {
            "exist": False,
            "side": "",
            "count": 0
        },
        "position": {
            "exist": False,
            "side": ""
        }
    }

    i = 1

    while i < 1000:
        if flag["order"]["exist"]:
            flag = check_order(flag)

        price_data = get_price(60, i)
        print_price(price_data)

        if flag["position"]["exist"]:
                flag = close_position(price_data, last_data, flag)
        else:
            flag = buy_signal(price_data, last_data, flag)
            flag = sell_signal(price_data, last_data, flag)

        last_data["close_time"] = price_data["close_time"]
        last_data["open_price"] = price_data["open_price"]
        last_data["clese_price"] = price_data["close_price"]
        i += 1


if __name__ == '__main__':
    main()
    # get_price(60, -2)