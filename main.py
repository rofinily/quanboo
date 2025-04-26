import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pandas as pd

import requests

res = requests.get("https://d.10jqka.com.cn/v6/line/185_AAPL/01/last1800.js")

data = res.text[res.text.find("{"):res.text.rfind("}") + 1]
data = json.loads(data)
days = data["data"].split(";")
d = []
now = datetime.now()
fiveYrsAgo = (now - relativedelta(years=5)).strftime("%Y%m%d")
oneYrsAgo = (now - relativedelta(years=1)).strftime("%Y%m%d")
for day in days:
    items = day.split(",")
    if items[0] < fiveYrsAgo or items[0] > oneYrsAgo:
        continue
    d.append({
        'date': items[0],
        'open': float(items[1]),
        'high': float(items[2]),
        'low': float(items[3]),
        'close': float(items[4])
    })
df = pd.DataFrame(d)
df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
df.set_index('date', inplace=True)
print(df)
# print(data["data"])

max_close = df['close'].max()
max_close_date = df['close'].idxmax()  # 最大值对应的日期

print(f"最大值: {max_close} (日期: {max_close_date.strftime('%Y%m%d')})")

# 截取最大值之后的数据
post_max_df = df.loc[max_close_date:]

# 计算累计最大值（从峰值开始）
post_max_df['peak'] = post_max_df['close'].cummax()

# 计算每个时间点的回撤值
post_max_df['drawdown'] = (post_max_df['peak'] - post_max_df['close']) / post_max_df['peak']

# 找到最大回撤值
max_drawdown = post_max_df['drawdown'].max()
max_drawdown_date = post_max_df['drawdown'].idxmax()

print(f"最大回撤: {max_drawdown:.2%} (日期: {max_drawdown_date.strftime('%Y%m%d')})")

import matplotlib.pyplot as plt

plt.figure(figsize=(10, 5))
plt.plot(df.index, df['close'], label='Close Price')
plt.scatter(max_close_date, max_close, color='red', label='Max Close')
plt.scatter(max_drawdown_date, df.loc[max_drawdown_date, 'close'], color='green', label='Max Drawdown')
plt.title('Close Price with Max Drawdown')
plt.legend()
plt.grid()
plt.show()
