import pandas as pd
from .Backtest import Backtest1G

class BacktestMulti1G(Backtest1G):

    def __init__(self, chart_sec, buy_term, sell_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config, start_funds, slippage, TEST_MODE_LOT):
        super().__init__(chart_sec, buy_term, sell_term, judge_price, volatility_term, stop_range, trade_risk, levarage, entry_times, entry_range, trailing_config, stop_AF, stop_AF_add, stop_AF_max, filter_VER, MA_term, wait, log_config, line_config, start_funds, slippage, TEST_MODE_LOT)

    def backtest(self, flag):

        # 使用パラメータ
        params = {
            "chart_sec": self.chart_sec,
            "buy_term": self.buy_term,
            "sell_term": self.sell_term,
            "judge_price": self.judge_price,
            "TEST_MODE_LOT": self.TEST_MODE_LOT,
            "volatility_term": self.volatility_term,
            "stop_range": self.stop_range,
            "trade_risk": self.trade_risk,
            "levarage": self.levarage,
            "start_funds": self.start_funds,
            "entry_times": self.entry_times,
            "entry_range": self.entry_range,
            "trailing_config": self.trailing_config,
            "stop_AF": self.stop_AF,
            "stop_AF_add": self.stop_AF_add,
            "stop_AF_max": self.stop_AF_max,
            "slippage": self.slippage,
            "filter_VER": self.filter_VER,
            "MA_term": self.MA_term
        }

        records = pd.DataFrame({
            "Date": pd.to_datetime(flag["records"]["date"]),
            "Profit": flag["records"]["profit"],
            "Side": flag["records"]["side"],
            "Rate": flag["records"]["return"],
            "Stop": flag["records"]["stop-count"],
            "Periods": flag["records"]["holding-periods"],
            "Slippage": flag["records"]["slippage"],
            "Filter": flag["records"]["filter"]
        })

        # 全recordsをfilterにかかったものとかからなかったものに分割。filterにかかった取引のみを結果として出力する。
        # filterを無効にすると全取引を出力。
        filter_true_records = records[records.Filter]
        filter_false_records = records[~records.Filter]

        filter_true_records["Gross"] = filter_true_records.Profit.cumsum()

        filter_true_records["Funds"] = filter_true_records.Gross + self.start_funds

        filter_true_records["Drawdown"] = filter_true_records.Gross.cummax().subtract(filter_true_records.Gross)
        filter_true_records["DrawdownRate"] = round(filter_true_records.Drawdown / filter_true_records.Funds.cummax() * 100, 1)

        result = {
            "TradeNum": len(filter_true_records),
            "WinningRate": round(len(filter_true_records[filter_true_records.Profit>0]) / len(filter_true_records) * 100, 1),
            "AverageReturn": round(filter_true_records.Rate.mean(), 2),
            "AverageProfit": round(filter_true_records[filter_true_records.Profit>0].Rate.mean(), 2),
            "AverageLoss": round(filter_true_records[filter_true_records.Profit<0].Rate.mean(), 2),
            "PayoffRatio": round(filter_true_records[filter_true_records.Profit>0].Rate.mean() / abs(filter_true_records[filter_true_records.Profit<0].Rate.mean()), 2),
            "AverageHoldingPeriods": round(filter_true_records.Periods.mean(), 1),
            "LossCutNum": filter_true_records.Stop.sum(),
            "BestProfit": filter_true_records.Profit.max(),
            "WorstLoss": filter_true_records.Profit.min(),
            "MaxDrawdown": -1 * filter_true_records.Drawdown.max(),
            "MaxDrawdownRate": -1 * filter_true_records.DrawdownRate.loc[filter_true_records.Drawdown.idxmax()],
            "TotalProfit": filter_true_records[filter_true_records.Profit>0].Profit.sum(),
            "TotalLoss": filter_true_records[filter_true_records.Profit<0].Profit.sum(),
            "Gross": filter_true_records.Profit.sum(),
            "StartFunds": self.start_funds,
            "FinalFunds": filter_true_records.Funds.iloc[-1],
            "Performance": round(filter_true_records.Funds.iloc[-1] / self.start_funds * 100, 2),
            "TotalSlippage": -1 * filter_true_records.Slippage.sum(),
            "LogFilePath": self.log_file,
            "Params": params
        }

        self.output_backtest(result)