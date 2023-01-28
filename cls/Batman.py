import os
import json
import ccxt
import time
import inspect
import requests
import numpy as np
from datetime import datetime
from logging import getLogger, Formatter, StreamHandler, FileHandler, INFO

class Batman1G:

    MIN_LOT = 0.01
    LOG_DIR = "bot-log"
    SECRET_FILE = "secrets.json"
    CHART_API = "cryptowatch"

    def __init__(self, chart_sec, entry_term, exit_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config):

        self.chart_sec = chart_sec

        self.entry_term = entry_term
        self.exit_term = exit_term
        self.judge_price = judge_price # high_price / close_price # low_price / close_price

        self.volatility_term = volatility_term
        self.stop_range = stop_range
        self.trade_risk = trade_risk
        self.levarage = levarage

        self.entry_times = entry_times
        self.entry_range = entry_range

        self.trailing_config = trailing_config # "OFF" / "TRAILING"
        self.stop_AF = stop_AF
        self.stop_AF_add = stop_AF_add
        self.stop_AF_max = stop_AF_max

        self.filter_VER = filter_VER # "OFF" / "A" / "B"
        self.MA_term = MA_term

        self.wait = wait # ループ待機時間（高頻度で価格取得APIのリクエストを飛ばすと制限にかかる）

        self.log_config = log_config
        self.line_config = line_config
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
        self.log_file = f"{self.LOG_DIR}/{timestamp}.log"
        
        if self.log_config == "ON":
            self.logger = getLogger(__name__)
            handlerSh = StreamHandler()
            handlerFile = FileHandler(self.log_file)
            handlerSh.setLevel(INFO)
            handlerFile.setLevel(INFO)
            self.logger.setLevel(INFO)
            self.logger.addHandler(handlerSh)
            self.logger.addHandler(handlerFile)

        self.flag = {
            "position": {
                "exist": False,
                "side": "",
                "price": 0,
                "stop": 0,
                "stop-AF": self.stop_AF,
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

        if self.filter_VER == "OFF":
            self.need_term = max(self.entry_term, self.exit_term, self.volatility_term)
        else:
            self.need_term = max(self.entry_term, self.exit_term, self.volatility_term, self.MA_term)

        self.secrets = self.get_secrets(self.SECRET_FILE)
        self.bitflyer = ccxt.bitflyer()
        self.bitflyer.apiKey = self.secrets["BITFLYER"]["API_KEY"]
        self.bitflyer.secret = self.secrets["BITFLYER"]["API_SECRET"]
        self.bitflyer.timeout = 30000


    # ----- Main Functions ----- #
    @classmethod
    def get_price(cls, min, before=0, after=0):

        if cls.CHART_API == "cryptowatch":
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
                return None

        if cls.CHART_API == "cryptocompare":
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
                return None

    
    def get_realtime_price(self, min):

        if self.CHART_API == "cryptowatch":
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
                    self.print_log("Cryptowatchの価格取得でエラー発生：" + str(e))
                    self.print_log(f"{self.wait}秒待機してやり直します。")
                    time.sleep(self.wait)

        if self.CHART_API == "cryptocompare": # 1時間足のみ対応
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
                    self.print_log("Cryptocompareの価格取得でエラー発生：" + str(e))
                    self.print_log(f"{self.wait}秒待機してやり直します。")
                    time.sleep(self.wait)
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


    def donchian(self, data, last_data):

        if inspect.stack()[1].function == "entry_signal":
            term = self.entry_term
        elif inspect.stack()[1].function == "close_position":
            term = self.exit_term
        else:
            pass

        highest = max(i["high_price"] for i in last_data[(-1*term): ])
        if data[self.judge_price["BUY"]] > highest:
            return {"side": "BUY", "price": highest}

        lowest = min(i["low_price"] for i in last_data[(-1*term): ])
        if data[self.judge_price["SELL"]] < lowest:
            return {"side": "SELL", "price": lowest}

        return {"side": None, "price": 0}


    def entry_signal(self, data, last_data, flag):
        
        if flag["position"]["exist"] == True:
            return flag
        
        signal = self.donchian(data["settled"], last_data)

        if signal["side"] == "BUY":
            self.print_log(f"過去{self.entry_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][self.judge_price['BUY']]}円でブレイクしました。")

            if self.filter(signal, data["settled"], last_data) == False:
                self.print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                return flag

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot >= self.MIN_LOT:
                self.print_log(f"{data['settled']['close_price']}円あたりに{lot}BTCで買いの成り行き注文を出します。")

                # Order
                price = self.bitflyer_market("BUY", lot)

                self.print_log(f"{price - stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "BUY"
                flag["position"]["price"] = price
            else:
                self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        if signal["side"] == "SELL":
            self.print_log(f"過去{self.entry_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][self.judge_price['SELL']]}円でブレイクしました。")

            if self.filter(signal, data["settled"], last_data) == False:
                self.print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                return flag

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot >= self.MIN_LOT:
                self.print_log(f"{data['settled']['close_price']}円あたりに{lot}BTCで売りの成り行き注文を出します。")

                # Order
                price = self.bitflyer_market("SELL", lot)

                self.print_log(f"{price + stop}円にストップを入れます。")
                flag["position"]["lot"] = lot
                flag["position"]["stop"] = stop
                flag["position"]["exist"] = True
                flag["position"]["side"] = "SELL"
                flag["position"]["price"] = price
            else:
                self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")

        return flag


    def stop_position(self, data, flag):

        if self.trailing_config == "TRAILING":
            flag = self.trail_stop(data["settled"], flag)

        if flag["position"]["side"] == "BUY":
            stop_price = flag["position"]["price"] - flag["position"]["stop"]
            if data["forming"]["low_price"] < stop_price:
                self.print_log(f"{stop_price}円の損切りラインに引っかかりました。")
                self.print_log(f"{data['forming']['low_price']}円あたりで成り行き注文を出してポジションを決済します。")

                # Order
                self.bitflyer_market("SELL", flag["position"]["lot"]) 

                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        if flag["position"]["side"] == "SELL":
            stop_price = flag["position"]["price"] + flag["position"]["stop"]
            if data["forming"]["high_price"] > stop_price:
                self.print_log(f"{stop_price}円の損切りラインに引っかかりました。")
                self.print_log(f"{data['forming']['high_price']}円あたりで成り行き注文を出してポジションを決済します。")

                # Order
                self.bitflyer_market("BUY", flag["position"]["lot"]) 

                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

        return flag


    def close_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        flag["position"]["count"] += 1
        signal = self.donchian(data["settled"], last_data)

        if flag["position"]["side"] == "BUY":
            if signal["side"] == "SELL":
                self.print_log(f"過去{self.exit_term}足の最安値{signal['price']}円を、直近の価格が{data['settled'][self.judge_price['SELL']]}でブレイクしました。")
                self.print_log(f"{data['settled']['close_price']}円あたりで成り行き注文を出してポジションを決済します。")

                # Order
                self.bitflyer_market("SELL", flag["position"]["lot"])

                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                if self.filter(signal, data["settled"], last_data) == False:
                    self.print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                    return flag

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot >= self.MIN_LOT:
                    self.print_log(f"さらに{data['settled']['close_price']}円あたりに{lot}BTCの売りの成り行き注文を入れてドテンします。")

                    # Order
                    price = self.bitflyer_market("SELL", lot)

                    self.print_log(f"{price + stop}円にストップを入れます。")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "SELL"
                    flag["position"]["price"] = price

        if flag["position"]["side"] == "SELL":
            if signal["side"] == "BUY":
                self.print_log(f"過去{self.exit_term}足の最高値{signal['price']}円を、直近の価格が{data['settled'][self.judge_price['BUY']]}でブレイクしました。")
                self.print_log(f"{data['settled']['close_price']}円あたりで成り行き注文を出してポジションを決済します。")

                # Order
                self.bitflyer_market("BUY", flag["position"]["lot"])

                flag["position"]["exist"] = False
                flag["position"]["count"] = 0
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = 0

                if self.filter(signal, data["settled"], last_data) == False:
                    self.print_log("フィルターのエントリー条件を満たさなかったため、エントリーしません。")
                    return flag

                lot, stop, flag = self.calculate_lot(last_data, data, flag)
                if lot >= self.MIN_LOT:
                    self.print_log(f"さらに{data['settled']['close_price']}円あたりに{lot}BTCの買いの成り行き注文を入れてドテンします。")

                    # Order
                    price = self.bitflyer_market("BUY", lot)

                    self.print_log(f"{price + stop}円にストップを入れます。")
                    flag["position"]["lot"] = lot
                    flag["position"]["stop"] = stop
                    flag["position"]["exist"] = True
                    flag["position"]["side"] = "BUY"
                    flag["position"]["price"] = price

        return flag


    def filter(self, signal, data, last_data):

        if self.filter_VER == "OFF":
            return True

        if self.filter_VER == "A":
            if len(last_data) < self.MA_term:
                return True
            if data["close_price"] > self.calculate_MA(self.MA_term, last_data) and signal["side"] == "BUY":
                return True
            if data["close_price"] < self.calculate_MA(self.MA_term, last_data) and signal["side"] == "SELL":
                return True

        if self.filter_VER == "B":
            if len(last_data) < self.MA_term:
                return True
            if self.calculate_MA(self.MA_term, last_data) > self.calculate_MA(self.MA_term, last_data, -1) and signal["side"] == "BUY":
                return True
            if self.calculate_MA(self.MA_term, last_data) < self.calculate_MA(self.MA_term, last_data, -1) and signal["side"] == "SELL":
                return True
        
        return False


    def calculate_MA(self, value, last_data, before=None):

        if before is None:
            MA = sum(i["close_price"] for i in last_data[-1*value: ]) / value
        else:
            MA = sum(i["close_price"] for i in last_data[-1*value + before: before]) / value

        return round(MA)


    def calculate_lot(self, last_data, data, flag):

        balance = self.bitflyer_collateral()

        if flag["add-position"]["count"] == 0:

            volatility = self.calculate_volatility(last_data)
            stop = self.stop_range * volatility
            calc_lot = np.floor(balance * self.trade_risk / stop * 100) / 100

            flag["add-position"]["unit-size"] = np.floor(calc_lot / self.entry_times * 100) / 100
            flag["add-position"]["unit-range"] = round(volatility * self.entry_range)
            flag["add-position"]["stop"] = stop
            flag["position"]["ATR"] = round(volatility)

            self.print_log(f"現在のアカウント残高は{balance}円です。")
            self.print_log(f"許容リスクから購入できる枚数は最大{calc_lot}BTCまでです。")
            self.print_log(f"{self.entry_times}回に分けて{flag['add-position']['unit-size']}BTC(UnitSize) - 0.01BTCずつ注文します。")

        stop = flag["add-position"]["stop"]

        able_lot = np.floor(balance * self.levarage / data["forming"]["close_price"] * 100) / 100
        lot = min(able_lot, flag["add-position"]["unit-size"]) - 0.01

        self.print_log(f"証拠金から購入できる枚数は最大{able_lot}BTCまでです。")
        return lot, stop, flag


    def add_position(self, data, last_data, flag):

        if flag["position"]["exist"] == False:
            return flag

        if flag["add-position"]["count"] == 0:
            flag["add-position"]["first-entry-price"] = flag["position"]["price"]
            flag["add-position"]["last-entry-price"] = flag["position"]["price"]
            flag["add-position"]["count"] += 1

        if flag["add-position"]["count"] >= self.entry_times:
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
            self.print_log(f"前回のエントリー価格{last_entry_price}円からブレイクアウト方向に{self.entry_range}ATR（{round(unit_range)}円）以上動きました。")
            self.print_log(f"{flag['add-position']['count'] + 1}/{self.entry_times}回目の追加注文を出します。")

            lot, stop, flag = self.calculate_lot(last_data, data, flag)
            if lot < self.MIN_LOT:
                self.print_log(f"注文可能枚数{lot}が、最低注文単位に満たなかったので注文を見送ります。")
                flag["add-position"]["count"] += 1
                return flag
            
            # Order
            if flag["position"]["side"] == "BUY":
                self.print_log(f"現在のポジションに追加して{lot}BTCの買い注文を出します。")
                entry_price = self.bitflyer_market("BUY", lot)

            if flag["position"]["side"] == "SELL":
                self.print_log(f"現在のポジションに追加して{lot}BTCの売り注文を出します。")
                entry_price = self.bitflyer_market("SELL", lot)

            flag["position"]["stop"] = stop
            flag["position"]["price"] = int(round((flag["position"]["price"] * flag["position"]["lot"] + entry_price * lot) / (flag["position"]["lot"] + lot)))
            flag["position"]["lot"] = np.round((flag["position"]["lot"] + lot) * 100) / 100

            if flag["position"]["side"] == "BUY":
                self.print_log(f"{flag['position']['price'] - stop}円の位置にストップを更新します。")
            if flag["position"]["side"] == "SELL":
                self.print_log(f"{flag['position']['price'] + stop}円の位置にストップを更新します。")

            self.print_log(f"現在のポジション取得単価は{flag['position']['price']}円です。")
            self.print_log(f"現在のポジションサイズは{flag['position']['lot']}BTCです。")

            flag["add-position"]["count"] += 1
            flag["add-position"]["last-entry-price"] = entry_price

        return flag


    def trail_stop(self, data, flag):

        if flag["add-position"]["count"] < self.entry_times:
            return flag

        if flag["position"]["side"] == "BUY":
            moved_range = round(data["high_price"] - flag["position"]["price"])
        if flag["position"]["side"] == "SELL":
            moved_range = round(flag["position"]["price"] - data["low_price"])

        if moved_range < 0 or flag["position"]["stop-EP"] >= moved_range:
            return flag
        else:
            flag["position"]["stop-EP"] = moved_range

        flag["position"]["stop"] = round(flag["position"]["stop"] - (moved_range + flag["position"]["stop"]) * flag["position"]["stop-AF"])

        flag["position"]["stop-AF"] = round(flag["position"]["stop-AF"] + self.stop_AF_add, 2)
        if flag["position"]["stop-AF"] >= self.stop_AF_max:
            flag["position"]["stop-AF"] = self.stop_AF_max

        if flag["position"]["side"] == "BUY":
            self.print_log(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] - flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。")
        else:
            self.print_log(f"トレイリングストップの発動：ストップ位置を{round(flag['position']['price'] + flag['position']['stop'])}円に動かして、加速係数を{flag['position']['stop-AF']}に更新します。")

        return flag


    def calculate_volatility(self, last_data):

        high_sum = sum(i["high_price"] for i in last_data[-1 * self.volatility_term: ])
        low_sum = sum(i["low_price"] for i in last_data[-1 * self.volatility_term: ])
        volatility = round((high_sum - low_sum) / self.volatility_term)
        self.print_log(f"現在の{self.volatility_term}期間の平均ボラティリティは{volatility}円です。")
        return volatility


    def find_unexpected_pos(self, last_data, flag):

        if flag["position"]["exist"] == True:
            return flag

        count = 0
        while True:
            price, size, side = self.bitflyer_check_positions()
            if size == 0:
                return flag

            self.print_log("把握していないポジションが見つかりました。")
            self.print_log("反映の遅延でないことを確認するために様子を見ています。")
            count += 1

            if count > 5:
                self.print_log("把握していないポジションが見つかったためポジションを復活させます。")

                flag["position"]["exist"] = True
                flag["position"]["side"] = side
                flag["position"]["lot"] = size
                flag["position"]["price"] = price
                flag["position"]["stop-AF"] = self.stop_AF
                flag["position"]["stop-EP"] = 0
                flag["add-position"]["count"] = self.entry_times

                if flag["position"]["ATR"] == 0:
                    flag["position"]["ATR"] = self.calculate_volatility(last_data)
                    flag["position"]["stop"] = flag["position"]["ATR"] * self.stop_range
                
                self.print_log(f"flag確認：{flag}")
                return flag

            time.sleep(30)

    
    # ----- Logging Functions----- #
    def print_price(self, data):
        self.print_log("時間：" + datetime.fromtimestamp(data["close_time"]).strftime('%Y/%m/%d %H:%M') + "　高値：" + str(data["high_price"]) + "　安値：" + str(data["low_price"]) + "　終値：" + str(data["close_price"]))
   
   
    def print_log(self, text):

        if self.line_config == "ON":
            url = "https://notify-api.line.me/api/notify"
            data = {"message": str(text)}
            headers = {"Authorization": "Bearer " + self.secrets["LINE"]["API_TOKEN"]}
            try:
                requests.post(url, data=data, headers=headers)
            except requests.exceptions.RequestException as e:
                if self.log_config == "ON":
                    self.logger.info(str(e))
                else:
                    print(text)

        if self.log_config == "ON":
            self.logger.info(text)
        else:
            print(text)


    # ----- API Functions----- #
    def get_secrets(self, secret_file):

        if os.path.exists(secret_file):
            with open(secret_file) as f:
                secrets = json.load(f)
                return secrets

        else:
            self.print_log(f"{secret_file}が存在しません。プログラムを終了します。")
            quit()


    def bitflyer_market(self, side, lot):

        while True:
            try:
                order = self.bitflyer.create_order(
                    symbol = 'BTC/JPY',
                    type = 'market',
                    side = side,
                    amount = lot,
                    params = {"product_code": "FX_BTC_JPY"}
                )
                self.print_log("--------------------------")
                self.print_log(order)
                self.print_log("--------------------------")
                order_id = order["id"]
                time.sleep(30)

                average_price = self.bitflyer_check_market_order(order_id, lot)
                return average_price

            except ccxt.BaseError as e:
                self.print_log("Bitflyerの注文APIでエラー発生：" + str(e))
                self.print_log("注文が失敗しました")
                self.print_log("30秒待機してやり直します。")
                time.sleep(30)

   
    def bitflyer_check_market_order(self, id, lot):

        while True:
            try:
                size = []
                price = []
                executions = self.bitflyer.private_get_getexecutions(params={"product_code": "FX_BTC_JPY"})
                for exec in executions:
                    if exec["child_order_acceptance_id"] == id:
                        size.append(float(exec["size"]))
                        price.append(float(exec["price"]))

                if round(sum(size), 2) != lot:
                    time.sleep(20)
                    self.print_log("注文が全て約定するのを待っています。")
                else:
                    average_price = round(sum(price[i] * size[i] for i in range(len(price))) / sum(size))
                    self.print_log("全ての成り行き注文が執行されました。")
                    self.print_log(f"執行価格は平均{average_price}円です。")
                    return average_price

            except ccxt.BaseError as e:
                self.print_log("BitflyerのAPIで問題発生：" + str(e))
                self.print_log("20秒待機してやり直します。")
                time.sleep(20)

   
    def bitflyer_collateral(self):

        while True:
            try:
                collateral = self.bitflyer.private_get_getcollateral()
                spendable_collateral = np.floor(float(collateral["collateral"]) - float(collateral["require_collateral"]))
                self.print_log(f"現在のアカウントの口座残高は{int(float(collateral['collateral']))}円です。")
                self.print_log(f"新規注文に利用可能な証拠金の額は{int(spendable_collateral)}円です。")
                return int(spendable_collateral)

            except ccxt.BaseError as e:
                self.print_log("BitflyerのAPIで口座残高の取得に失敗しました：" + str(e))
                self.print_log("20秒待機してやり直します。")
                time.sleep(20)

    
    def bitflyer_check_positions(self):

        failed = 0
        while True:
            try:
                size = []
                price = []
                positions = self.bitflyer.private_get_getpositions(params={"product_code": "FX_BTC_JPY"})
                if not positions:
                    # self.print_log("現在ポジションは存在しません。")
                    return 0, 0, None
                for pos in positions:
                    size.append(float(pos["size"]))
                    price.append(float(pos["price"]))
                    side = pos["side"]

                average_price = round(sum(price[i] * size[i] for i in range(len(price))) / sum(size))
                sum_size = round(sum(size), 2)
                self.print_log(f"保有中の建玉：合計{len(price)}つ\n平均建値：{average_price}円\n合計サイズ：{sum_size}BTC\n方向：{side}")

                return average_price, sum_size, side

            except ccxt.BaseError as e:
                failed += 1
                if failed > 10:
                    self.print_log("Bitflyerのポジション取得APIで10回失敗しました：" + str(e))
                    self.print_log("20秒待機してやり直します。")
                time.sleep(20)
    

    # ----- External Functions ----- # # TODO
    # @staticmethod # TODO: インスタンス化せずに呼び出すメソッド
    # def sample():
    #     return None