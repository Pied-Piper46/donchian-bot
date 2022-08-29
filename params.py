'''
trail_ratio は0~1の範囲でのみ設定可能
trail_ratio を0に設定するとトレイリングストップを無効にできます。
'''

# for simple backtest
chart_sec = 3600 # 1時間足を使用
buy_term = 30 # 買いエントリーのブレイク期間の設定
sell_term = 30 # 売りエントリーのブレイク期間の設定

judge_price = {
    "BUY": "high_price", # ブレイク判断　高値か終値を使用
    "SELL": "low_price" # ブレイク判断　安値か終値を使用
}

volatility_term = 30 # 平均ボラティリティ（ATR）の計算に使う期間（何足分）
stop_range = 2 # 何レンジ幅（何ATR）にストップを入れるか
trade_risk = 0.01 # 1トレードあたり口座の何％まで損失を許容するか
levarage = 3 # レバレッジ倍率の設定
start_funds = 300000 # シミュレーション時の初期資金

entry_times = 4 # 何回に分けて追加ポジションを取るか
entry_range = 0.5 # 何レンジ（ATR）ごとに追加ポジションを取るか

trail_ratio = 0.5 # 価格が1レンジ動くたびに何レンジ損切り位置をトレイルするか
trail_until_breakeven = False # 損益ゼロの位置までしかトレイルしない

stop_AF = 0.02 # 加速係数
stop_AF_add = 0.02 # 加速係数の増やす度合い
stop_AF_max = 0.2 # 加速係数の上限

wait = 0 # ループの待機時間
slippage = 0.001 # 手数料・スリッページ


# for multiple backtest
chart_sec_list = [1800, 3600, 7200, 21600, 43200, 86400]
# chart_sec_list = [1800, 3600]
buy_term_list = [10, 15, 20, 25, 30, 40, 45]
sell_term_list = [10, 15, 20, 25, 30, 40, 45]
judge_price_list = [
    {"BUY": "close_price", "SELL": "close_price"},
    {"BUY": "high_price", "SELL": "low_price"}
]
