import requests
from datetime import datetime
from pprint import pprint
import time
import numpy as np
import ccxt
from bot_log import print_log
from get_secrets import get_secrets

MIN_LOT = 0.001 # 最低注文枚数

wait = 180 # ループ待機時間（高頻度で価格取得APIのリクエストを飛ばすと制限にかかる）

chart_sec = 3600 # 使用する時間軸
chart_API = "cryptowatch" # cryptowatch / cryptocompare

buy_term = 30 # ブレイクアウト判定期間
sell_term = 30 # ブレイクアウト判定期間
judge_price = { # ブレイク判断
    "BUY": "close_price", # high_price / close_price
    "SELL": "close_price" # low_price / close_price
}

volatility_term = 5 # 平均ボラティリティ算出期間
stop_range = 2 # 何レンジ幅にストップを入れるか
trade_risk = 0.03 # １トレードあたり口座の何％まで損失を許容するか
levarage = 3 # レバレッジ

entry_times = 2
entry_range = 1

trailing_config = "ON"
stop_AF = 0.02
stop_AF_add = 0.02
stop_AF_max = 0.2

filter_VER = "OFF"
MA_term = 200

secrets = get_secrets("secrets.json")
bitflyer = ccxt.bitflyer()
bitflyer.apiKey = secrets["SECRETS"]["API_KEY"]
bitflyer.secret = secrets["SECRETS"]["API_SECRET"]
bitflyer.timeout = 30000

flag = {
    "position": {
        "exist": False,
        "side": "",
        "price": 0,
        "stop": 0,
        "stop-AF": stop_AF,
        "stop-EP": 0,
        "ATR": 0,
        "lot": 0,
        "count": 0
    },
    "add-position": {
        "count": 0,
        "first-entry-price": 0,
        "last-entry-price": 0,
        "unit-range": 0,
        "unit-size": 0,
        "stop": 0
    }
}


def donchian(data, last_data):

    highest = max(i["high_price"] for i in last_data[(-1*buy_term): ])
    if data["settled"][judge_price["BUY"]] > highest:
        return {"side": "BUY", "price": highest}

    lowest = min(i["low_price"] for i in last_data[(-1*sell_term): ])
    if data["settled"][judge_price["SELL"]] < lowest:
        return {"side": "SELL", "price": lowest}

    return {"side": None, "price": 0}


def entry_signal(data, last_data, flag):
    
    if flag["position"]["exist"] == True:
        return flag
    
    signal = donchian(data, last_data)

    if signal["side"] == "BUY":
        print_log(f"過去{buy_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][judge_price['BUY']]}円でブレイクしました。")

        if filter(signal) == False:
            print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
            return flag

        log, stop, flag = calculate_lot(last_data, data, flag)
        if lot >= MIN_LOT:
            print_log(f"{data['settled']['close_price']}円あたりに{lot}BTCで買いの成り行き注文を出します。")

            # Order
            price = bitflyer_market("BUY", lot)

            print_log(f"{price - stop}円にストップを入れます。")
            flag["position"]["lot"] = lot
            flag["position"]["stop"] = stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "BUY"
            flag["position"]["price"] = price
        else:
            print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    if signal["side"] == "SELL":
        print_log(f"過去{sell_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][judge_price['SELL']]}円でブレイクしました。")

        if filter(signal) == False:
            print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
            return flag

        log, stop, flag = calculate_lot(last_data, data, flag)
        if lot >= MIN_LOT:
            print_log(f"{data['settled']['close_price']}円あたりに{lot}BTCで売りの成り行き注文を出します。")

            # Order
            price = bitflyer_market("SELL", lot)

            print_log(f"{price + stop}円にストップを入れます。")
            flag["position"]["lot"] = lot
            flag["position"]["stop"] = stop
            flag["position"]["exist"] = True
            flag["position"]["side"] = "SELL"
            flag["position"]["price"] = price
        else:
            print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

    return flag


def stop_position(data, flag):

    if trailing_config == "ON":
        flag = trail_stop(data, flag)

    if flag["position"]["side"] == "BUY":
        stop_price = flag["position"]["price"] - flag["position"]["stop"]
        if data["forming"]["low_price"] < stop_price:
            print_log(f"{stop_price}円の損切りラインに引っかかりました。")
            print_log(f"{data['forming']['low_price']}円あたりで成り行き注文を出してポジションを決済します。")

            # Order
            bitflyer_market("SELL", flag["position"]["lot"]) 

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    if flag["position"]["side"] == "SELL":
        stop_price = flag["position"]["price"] + flag["position"]["stop"]
        if data["forming"]["high_price"] > stop_price:
            print_log(f"{stop_price}円の損切りラインに引っかかりました。")
            print_log(f"{data['forming']['high_price']}円あたりで成り行き注文を出してポジションを決済します。")

            # Order
            bitflyer_market("BUY", flag["position"]["lot"]) 

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

    return flag


def close_position(data, last_data, flag):

    if flag["position"]["exist"] == False:
        return flag

    flag["position"]["count"] += 1
    signal = donchian(data, last_data)

    if flag["position"]["side"] == "BUY":
        if signal["side"] == "SELL":
            print_log(f"過去{sell_term}足の最安値{signal['price']}円を、直近の価格が{data['settled'][judge_price['SELL']]}でブレイクしました。")
            print_log(f"{data['settled']['close_price']}円あたりで成り行き注文を出してポジションを決済します。")

            # Order
            bitflyer_market("SELL", flag["position"]["lot"])

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            if filter(signal) == False:
                print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot >= MIN_LOT:
                print_log(f"さらに{data['settled']['close_price']}円あたりに{lot}BTCの売りの成り行き注文を入れてドテンします。")

                # Order
                price = bitflyer_market("SELL", lot)

                print_log(f"{price + stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = price

    if flag["position"]["side"] == "SELL":
        if signal["side"] == "BUY":
            print_log(f"過去{buy_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][judge_price['BUY']]}でブレイクしました。")
            print_log(f"{data['settled']['close_price']}円あたりで成り行き注文を出してポジションを決済します。")

            # Order
            bitflyer_market("BUY", flag["position"]["lot"])

            flag["position"]["exist"] = False
            flag["position"]["count"] = 0
            flag["position"]["stop-AF"] = stop_AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = 0

            if filter(signal) == False:
                print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                return flag

            lot, stop, flag = calculate_lot(last_data, data, flag)
            if lot >= MIN_LOT:
                print_log(f"さらに{data['settled']['close_price']}円あたりに{lot}BTCの買いの成り行き注文を入れてドテンします。")

                # Order
                price = bitflyer_market("BUY", lot)

                print_log(f"{price + stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = price

    return flag


def filter(signal):

    if filter_VER == "OFF":
        return True

    if filter_VER == "A":
        if len(last_data) < MA_term:
            return True
        if data["settled"]["close_price"] > calculate_MA(MA_term) and signal["side"] == "BUY":
            return True
        if data["settled"]["close_price"] < calculate_MA(MA_term) and signal["side"] == "SELL":
            return True

    if filter_VER == "B":
        if len(last_data) < MA_term:
            return True
        if calculate_MA(MA_term) > calculate_MA(MA_term, -1) and signal["side"] == "BUY":
            return True
        if calculate_MA(MA_term) < calculate_MA(MA_term, -1) and signal["side"] == "SELL":
            return True
    
    return False


def calculate_MA(value, before=None):
    
    if before is None:
        MA = sum(i["close_price"] for i in last_data[-1*value: ]) / value
    else:
        MA = sum(i["close_price"] for i in last_data[-1*value + before: before]) / value
    return round(MA)


def calculate_lot(last_data, data, flag):

    balance = bitflyer_collateral()

    if flag["add-position"]["count"] == 0:

        volatility = calculate_volatility(last_data)
        stop = stop_range * volatility
        calc_lot = np.floor(balance * trade_risk / stop * 100) / 100

        flag["add-position"]["unit-size"] = np.floor(calc_lot / entry_times * (1 / MIN_LOT)) / (1 / MIN_LOT)
        flag["add-position"]["unit-range"] = round(volatility * entry_range)
        flag["add-position"]["stop"] = stop
        flag["position"]["ATR"] = round(volatility)

        print_log(f"現在のアカウント残高は{balance}円です。")
        print_log(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
        print_log(f"{entry_times}回に分けて{flag['add-position']['unit-size']}BTCずつ注文します。")

    stop = flag["add-position"]["stop"]

    able_lot = np.floor(balance * levarage / data["forming"]["close_price"] * 100) / 100
    lot = min(able_lot, flag["add-position"]["unit-size"])

    print_log(f"証拠金から購入できる枚数は最大{able_lot}BTCまでです。")
    return lot, stop, flag


def add_position(data, flag):

    if flag["position"]["exist"] == False:
        return flag

    if flag["add-position"]["count"] == 0:
        flag["add-position"]["first-entry-price"] = flag["position"]["price"]
        flag["add-position"]["last-entry-price"] = flag["position"]["price"]
        flag["add-position"]["count"] += 1

    if flag["add-position"]["count"] >= entry_times:
        return flag

    first_entry_price = flag["add-position"]["first-entry-price"]
    last_entry_price = flag["add-position"]["last-entry-price"]
    unit_range = flag["add-position"]["unit-range"]
    current_price = data["forming"]["close_price"]

    should_add_position = False
    if flag["position"]["side"] == "BUY" and (current_price - last_entry_price) > unit_range:
        should_add_position = True
    elif flag["position"]["side"] == "SELL" and (last_entry_price - current_price) > unit_range:
        should_add_position = True

    if should_add_position:
        print_log(f"前回のエントリー価格{last_entry_price}円からブレイクアウト方向に{entry_range}ATR（{round(unit_range)}円）以上動きました。")
        print_log(f"{flag['add-position']['count'] + 1}/{entry_times}回目の追加注文を出します。")

        lot, stop, flag = calculate_lot(last_data, data, flag)
        if lot < MIN_LOT:
            print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")
            flag["add-position"]["count"] += 1
            return flag
        
        # Order
        if flag["position"]["side"] == "BUY":

            print_log(f"現在のポジションに追加して{lot}BTCの買い注文を出します。")
            entry_price = bitflyer_market("BUY", lot)

        if flag["position"]["side"] == "SELL":

            print_log(f"現在のポジションに追加して{lot}BTCの売り注文を出します。")
            entry_price = bitflyer_market("SELL", lot)

        flag["position"]["stop"] = stop
        flag["position"]["price"] = int(round((flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (flag["position"]["lot"] + lot)))
        flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

        if flag["position"]["side"] == "BUY":
            print_log(f"{flag['position']['price'] - stop}円の位置にストップを更新します。")
        if flag["position"]["side"] == "SELL":
            print_log(f"{flag['position']['price'] + stop}円の位置にストップを更新します。")

        print_log(f"現在のポジション取得単価は{flag['position']['price']}円です。")
        print_log(f"現在のポジションサイズは{flag['position']['lot']}BTCです。")

        flag["add-position"]["count"] += 1
        flag["add-position"]["last-entry-price"] = entry_price

    return flag


def trail_stop(data, flag):

    if flag["add-position"]["count"] < entry_times:
        return flag

    if flag["position"]["side"] == "BUY":
        moved_range = round(data["settled"]["high_price"] - flag["position"]["price"])
    if flag["position"]["side"] == "SELL":
        moved_range = round(flag["position"]["price"] - data["settled"]["low_price"])

    if moved_range < 0 or flag["position"]["stop-EP"] >= moved_range:
        return flag
    else:
        flag["position"]["stop-EP"] = moved_range

    flag["position"]["stop-AF"] = round(flag["position"]["stop-AF"] + stop_AF_add, 2)
    if flag["position"]["stop-AF"] >= stop_AF_max:
        flag["position"]["stop-AF"] = stop_AF_max

    if flag["position"]["side"] == "BUY":
        print_log(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] - flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。")
    else:
        print_log(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] + flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。")

    return flag


def get_price(min, before=0, after=0):

    if chart_API == "cryptowatch":
        price = []
        params = {"periods": min}
        if before != 0:
            params["before"] = before
        if after != 0:
            params["after"] = after

        response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc", params)
        data = response.json()

        if data["result"][str(min)] is not None:
            for i in data["result"][str(min)]:
                if i[1] != 0 and i[2] != 0 and i[3] != 0 and i[4] != 0:
                    price.append({
                        "close_time": i[0],
                        "close_time_dt": datetime.fromtimestamp(i[0]).strftime('%Y/%m/%d %H:%M'),
                        "open_price": i[1],
                        "high_price": i[2],
                        "low_price": i[3],
                        "close_price": i[4]
                    })
            return price

        else:
            print_log("データが存在しません。")
            return None

    if chart_API == "cryptocompare": # １時間足のみ対応
        price = []
        params = {"fsym": "BTC", "tsym": "JPY", "e": "bitflyerfx", "limit": 2000}

        response = requests.get("https://min-api.cryptocompare.com/data/histhour", params, timeout=10)
        data = response.json()

        if data["Response"] == "Success":
            for i in data["Data"]:
                price.append({
                    "close_time": i["time"],
                    "close_time_dt": datetime.fromtimestamp(i["time"]).strftime('%Y/%m/%d %H:%M'),
                    "open_price": i["open"],
                    "high_price": i["high"],
                    "low_price": i["low"],
                    "close_price": i["close"]
                })
            return price

        else:
            print_log("データが存在しません。")
            return None


def get_realtime_price(min):

    if chart_API == "cryptowatch":
        params = {"periods": min}
        while True:
            try:
                response = requests.get("https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc", params, timeout=10)
                response.raise_for_status()
                data = response.json()
                return {
                    "settled": {
                        "close_time": data["result"][str(min)][-2][0],
                        "open_price": data["result"][str(min)][-2][1],
                        "high_price": data["result"][str(min)][-2][2],
                        "low_price": data["result"][str(min)][-2][3],
                        "close_price": data["result"][str(min)][-2][4]
                    },
                    "forming": {
                        "close_time": data["result"][str(min)][-1][0],
                        "open_price": data["result"][str(min)][-1][1],
                        "high_price": data["result"][str(min)][-1][2],
                        "low_price": data["result"][str(min)][-1][3],
                        "close_price": data["result"][str(min)][-1][4]
                    }
                }
            
            except requests.exceptions.RequestException as e:
                print_log("Cryptowatchの価格取得でエラー発生：" + str(e))
                print_log(f"{wait}秒待機してやり直します。")
                time.sleep(wait)

    if chart_API == "cryptocompare": # 1時間足のみ対応
        params = {"fsym": "BTC", "tsym": "JPY", "e": "bitflyerfx"}

        while True:
            try:
                response = requests.get("https://min-api.cryptocompare.com/data/histohour", params, timeout=10)
                response.raise_for_status()
                data = response.json()
                time.sleep(5)

                response2 = requests.get("http://min-api.cryptocompare.com/data/histominute", params, timeout=10)
                response2.raise_for_status()
                data2 = response2.json()

            except requests.exceptions.RequestException as e:
                print_log("Cryptocompareの価格取得でエラー発生：" + str(e))
                print_log(f"{wait}秒待機してやり直します。")
                time.sleep(wait)
                continue

            return {
                "settled": {
                    "close_time": data["Data"][-2]["time"],
                    "open_price": data["Data"][-2]["open"],
                    "high_price": data["Data"][-2]["high"],
                    "low_price": data["Data"][-2]["low"],
                    "close_price": data["Data"][-2]["close"]
                },
                "forming": {
                    "close_time": data2["Data"][-1]["time"],
                    "open_price": data2["Data"][-1]["open"],
                    "high_price": data2["Data"][-1]["high"],
                    "low_price": data2["Data"][-1]["low"],
                    "close_price": data2["Data"][-1]["close"]
                }
            }


def print_price(data):
    print_log("時間：" + datetime.fromtimestamp(data["close_price"]).strftime('%Y/%m/%d %H:%M') + "　高値：" + str(data["high_price"]) + "　安値：" + str(data["low_price"]) + "　終値：" + str(data["close_price"]))


def calculate_volatility(last_data):

    high_sum = sum(i["high_price"] for i in last_data[-1 * volatility_term: ])
    low_sum = sum(i["low_price"] for i in last_data[-1 * volatility_term: ])
    volatility = round((high_sum - low_sum) / volatility_term)
    print_log(f"現在の{volatility_term}期間の平均ボラティリティは{volatility}円です。")
    return volatility


def find_unexpected_pos(flag):

    if flag["position"]["exist"] == True:
        return flag

    count = 0
    while True:
        price, size, side = bitflyer_check_positions()
        if size == 0:
            return flag

        print_log("把握していないポジションが見つかりました。")
        print_log("反映の遅延でないことを確認するため様子を見ています。")
        count += 1

        if count > 5:
            print_log("把握していないポジションが見つかったためポジションを復活させます。")

            flag["position"]["exist"] = True
            flag["position"]["side"] = side
            flag["position"]["lot"] = size
            flag["position"]["price"] = price
            flag["position"]["stop-AF"] = stop-AF
            flag["position"]["stop-EP"] = 0
            flag["add-position"]["count"] = entry_times

            if flag["position"]["ATR"] == 0:
                flag["position"]["ATR"] = calculate_volatility(last_data)
                flag["position"]["stop"] = flag["position"]["ATR"] * stop_range
            pprint(flag)
            return flag

        time.sleep(30)


def bitflyer_market(side, lot):

    while True:
        try:
            order = bitflyer.create_order(
                symbol = 'BTC/JPY',
                type = 'market',
                side = side,
                amount = lot,
                params = {"product_code": "FX_BTC_JPY"}
            )
            print_log("-------------------------")
            print_log(order)
            print_log("-------------------------")
            order_id = order["id"]
            time.sleep(30)

            average_price = bitflyer_check_market_order(order_id, lot)
            return average_price

        except ccxt.BaseError as e:
            print_log("Bitflyerの注文APIでエラー発生：" + str(e))
            print_log("注文が失敗しました")
            print_log("30秒待機してやり直します。")
            time.sleep(30)


def bitflyer_check_market_order(id, lot):

    while True:
        try:
            size = []
            price = []

            executions = bitflyer.private_get_getexecutions(params={"product_code": "FX_BTC_JPY"})
            for exec in executions:
                if exec["child_order_acceptance_id"] == id:
                    size.append(exec["size"])
                    price.append(exec["price"])

            if round(sum(size), 2) != lot:
                time.sleep(20)
                print_log("注文が全て約定するのを待っています。")
            else:
                average_price = round(sum(price[i] * size[i] for i in range(len(price))) / sum(size))
                print_log("全ての成行注文が執行されました。")
                print_log(f"執行価格は平均{average_price}円です。")
                return average_price

        except ccxt.BaseError as e:
            print_log("BitflyerのAPIで問題発生：" + str(e))
            print_log("20秒待機してやり直します。")
            time.sleep(20)


def bitflyer_collateral():

    while True:
        try:
            collateral = bitflyer.private_get_getcollateral()
            spendable_collateral = np.floor(collateral["collateral"] - collateral["require_collateral"])
            print_log(f"現在のアカウントの口座残高は{int(collateral['collateral'])}円です。")
            print_log(f"新規注文に利用可能な証拠金の額は{int(spendable_collateral)}円です。")
            return int(spendable_collateral)

        except ccxt.BaseError as e:
            print_log("BitflyerのAPIでの口座残高取得に失敗しました：" + str(e))
            print_log("20秒待機してやり直します。")
            time.sleep(20)


def bitflyer_check_positions():

    failed = 0
    while True:
        try:
            size = []
            price = []
            positions = bitflyer.private_get_getpositions(params={"product_code": "FX_BTC_JPY"})
            if not position:
                # print_log("現在ポジションは存在しません。")
                return 0, 0, None
            for pos in positions:
                size.append(pos["size"])
                price.append(pos["price"])
                side = pos["side"]

            average_price = round(sum(price[i] * size[i] for i in range(len(price))) / sum(size))
            sum_size = round(sum(size), 2)
            # print_log(f"保有中の建玉：合計{len(price)}つ\n平均建値：{average_price}円\n合計サイズ：{sum_size}BTC\n方向：{side}")

            return average_price, sum_size, side

        except ccxt.BaseError as e:
            failed += 1
            if failed > 10:
                print_log("Bitflyerのポジション取得APIで10回失敗しました。：" + str(e))
                print_log("20秒待機してやり直します。")
            time.sleep(20)


### MAIN ###

# need_term = max(buy_term, sell_term, volatility_term, MA_term)
# print_log(f"{need_term}期間分のデータの準備中")

# price = get_price(chart_sec)
# last_data = price[-1*need_term - 2: -2]
# print_price(last_data[-1])
# print_log(f"---{wait}秒待機---")
# time.sleep(wait)

# print_log("---実行開始---")

# while True:

#     data = get_realtime_price(chart_sec)
#     if data["settled"]["close_time"] > last_data[-1]["close_time"]:
#         print_price(data["settled"])

#     if flag["position"]["exist"]:
#         flag = stop_position(data, flag)
#         flag = close_position(data, last_data, flag)
#         flag = add_position(data, flag)

#     else:
#         flag = find_unexpected_pos(flag)
#         flag = entry_signal(data, last_data, flag)

#     if data["settled"]["close_time"] > last_data[-1]["close_time"]: # 確定足が更新されたら
#         last_data.append(data["settled"])
#         if len(last_data) > need_term:
#             del last_data[0]

#     time.sleep(wait)