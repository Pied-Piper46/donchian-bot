import numpy as np
import pandas as pd
from datetime import datetime

winning_percentage = 0.387
payoff_ratio = 2.97
funds = 100000

drawdown_rate_list = np.arange(10, 100, 10)
risk_rate_list = np.arange(0.5, 10, 0.5)

def equation(x):

    k = payoff_ratio
    p = winning_percentage
    return p * x**(k+1) + (1-p) - x

def solve_equation():

    R = 0
    while equation(R) > 0:
        R += 1e-4
    if R >= 1:
        print("期待値が0を下回っています。")
        R = 1
    print(f"特性方程式の解は{R}です。")
    return R

def calculate_ruin_rate(R, risk_rate, drawdown_rate):

    bankrupt_line = int(round(funds * (1 - drawdown_rate / 100)))
    risk_rate = risk_rate / 100
    print(f"破産ライン：{bankrupt_line}円")
    unit = (np.log(funds) - np.log(bankrupt_line)) / abs(np.log(1 - risk_rate))
    unit = int(np.floor(unit))
    return R ** unit

result = []

for risk_rate in risk_rate_list:
    temp = []
    for drawdown_rate in drawdown_rate_list:
        print(f"{risk_rate}")
        print(f"{drawdown_rate}")
        R = solve_equation()
        ruin_rate = calculate_ruin_rate(R, risk_rate, drawdown_rate)
        ruin_rate = round(ruin_rate * 100, 2)

        print(f"{ruin_rate}")
        temp.append(ruin_rate)
        print("----------------------------------")

    result.append(temp)

df = pd.DataFrame(result)
df.index = [str(i)+"%" for i in risk_rate_list]
df.columns = [str(i)+"%" for i in drawdown_rate_list]
print(df)

df.to_csv(f"RuinTable.csv")