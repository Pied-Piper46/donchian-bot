import sample_bot as bot
import sample_bot_backtest as sbb
from bot_log import print_log, log_file_path


if __name__ == "__main__":

    # csv_file = "backtest-log/samplebot_multi.csv"

    # MIN_LOT = 0.01
    # wait = 60

    # chart_sec_list = [900, 1800, 3600, 7200]
    # chart_API = "cryptowatcher"

    # buy_term_list = [10, 15, 20, 25, 30, 50] # buyとsellの期間は統一することにする。バイアスがかかるため。
    # # sell_term_list = [10, 15, 20, 25, 30, 50]
    # judge_price_list = [
    #     {"BUY": "close_price", "SELL": "close_price"},
    #     {"BUY": "high_price", "SELL": "low_price"}
    # ]

    # TEST_MODE_LOT = "adjustable"

    # volatility_term_list = [5, 10, 15, 20, 30]
    # stop_range_list = [2, 3, 4]
    # trade_risk = 0.04
    # levarage = 2
    # start_funds = 300000

    # entry_times_list = [1, 2, 3, 4]
    # entry_range_list = [0.5, 1]

    # stop_config_list = ["TRAILING", "ON", "OFF"]
    # stop_AF_list = [0.02, 0.03, 0.04]
    # stop_AF_add_list = [0.02, 0.03, 0.04]
    # stop_AF_max_list = [0.2, 0.3, 0.4]

    # slippage = 0.0005

    # filter_VER_list = ["OFF", "A", "B"]
    # MA_term_list = [50, 100, 200]

    # price = bot.get_price(3600, after=1451606400)
    # print(price)

    # combinations = [(chart_sec, buy_term, judge_price, volatility_term, stop_range, entry_times, entry_range, stop_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term)
    #     for chart_sec in chart_sec_list
    #     for buy_term in buy_term_list
    #     for judge_price in judge_price_list
    #     for volatility_term in volatility_term_list
    #     for stop_range in stop_range_list
    #     for entry_times in entry_times_list
    #     for entry_range in entry_range_list
    #     for stop_config in stop_config_list
    #     for stop_AF in stop_AF_list
    #     for stop_AF_add in stop_AF_add_list
    #     for stop_AF_max in stop_AF_max_list
    #     for filter_VER in filter_VER_list
    #     for MA_term in MA_term_list]

    # for chart_sec, buy_term, judge_price, volatility_term, stop_range, entry_times, entry_range, stop_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term in combinations:

    #     price = bot.get_price(chart_sec, after=1451606400)

    #     last_data = []

