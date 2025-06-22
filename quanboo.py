import json
from datetime import datetime
import sys

import numpy as np
from dateutil.relativedelta import relativedelta
from scipy.signal import find_peaks
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px


def fetch_stock_data(stock_name, stock_code, ths_code):
    """获取股票数据"""
    stock_url = (
        f"https://d.10jqka.com.cn/v6/line/{ths_code}_{stock_code}/01/last1800.js"
    )

    try:
        print(f"正在获取 {stock_name.upper()} 的股票数据...")
        res = requests.get(
            stock_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
            },
            timeout=10,
        )
        res.raise_for_status()

        data = res.text[res.text.find("{") : res.text.rfind("}") + 1]
        data = json.loads(data)
        days = data["data"].split(";")
        d = []
        now = datetime.now()
        fiveYrsAgo = (now - relativedelta(years=5)).strftime("%Y%m%d")

        for day in days:
            items = day.split(",")
            if items[0] < fiveYrsAgo:
                continue
            d.append(
                {
                    "date": items[0],
                    "open": float(items[1]),
                    "high": float(items[2]),
                    "low": float(items[3]),
                    "close": float(items[4]),
                }
            )

        df = pd.DataFrame(d)
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df.set_index("date", inplace=True)

        print(f"成功获取 {len(df)} 条数据记录")
        return df

    except Exception as e:
        print(f"获取股票数据失败: {e}")


def analyze_drawdowns(df):
    """分析回撤数据"""
    close_prices = df["close"].values
    peaks, _ = find_peaks(close_prices, prominence=13)
    troughs, _ = find_peaks(-close_prices, prominence=13)

    # 计算回撤并筛选>10%的
    drawdowns = []
    for peak in peaks:
        # 后面所有的谷底
        fut_troughs = troughs[troughs > peak]
        if len(fut_troughs) == 0:
            continue
        # 只取第一个
        trough = fut_troughs[0]
        if close_prices[trough] < close_prices[peak]:
            drawdowns.append(
                {
                    "peak_idx": peak,
                    "trough_idx": trough,
                    "peak_price": close_prices[peak],
                    "trough_price": close_prices[trough],
                    "drawdown": (close_prices[peak] - close_prices[trough])
                    / close_prices[peak],
                }
            )

        # # 从当前峰后开始查找
        # for future_idx in range(peak + 1, len(close_prices)):
        #     if close_prices[future_idx] < close_prices[peak]:
        #         drawdown_pct = (close_prices[peak] - close_prices[future_idx]) / close_prices[peak]
        #         if drawdown_pct >= 0.10:
        #             drawdowns.append({
        #                 'peak_idx': peak,
        #                 'trough_idx': future_idx,
        #                 'drawdown': drawdown_pct,
        #                 'peak_price': close_prices[peak],
        #                 'trough_price': close_prices[future_idx]
        #             })
        #             break  # 找到第一个符合条件的就停止查找

    return drawdowns


def create_plotly_chart(df, drawdowns, stock_name):
    """创建plotly图表"""
    fig = go.Figure()

    # 添加价格线
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"],
            mode="lines",
            name="Close Price",
            line=dict(color="#e0e0e0", width=1.5),
            opacity=0.9,
            hovertemplate="<b>Price:</b> %{y:.2f}<extra></extra>",
        )
    )

    # 颜色循环
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFEEAD", "#DDA0DD", "#98FB98"]

    # 添加回撤段
    for i, dd in enumerate(drawdowns):
        c = colors[i % len(colors)]

        # 关键点坐标
        peak_date = df.index[dd["peak_idx"]]
        trough_date = df.index[dd["trough_idx"]]

        # 添加虚线连接高低点
        fig.add_trace(
            go.Scatter(
                x=[peak_date, trough_date],
                y=[dd["peak_price"], dd["trough_price"]],
                mode="lines",
                line=dict(color=c, width=1.5, dash="dot"),
                opacity=0.7,
                showlegend=False,
                hovertemplate="<b>Drawdown:</b> %{text}<extra></extra>",
                text=[f"{dd['drawdown']:.1%}", f"{dd['drawdown']:.1%}"],
            )
        )

        # 添加高点标记
        fig.add_trace(
            go.Scatter(
                x=[peak_date],
                y=[dd["peak_price"]],
                mode="markers",
                marker=dict(color=c, size=12, line=dict(color="white", width=1)),
                showlegend=False,
                hovertemplate=f'<b>Peak Price</b>: {dd["peak_price"]:.2f}<extra></extra>',
            )
        )

        # 添加低点标记
        fig.add_trace(
            go.Scatter(
                x=[trough_date],
                y=[dd["trough_price"]],
                mode="markers",
                marker=dict(
                    color=c,
                    size=12,
                    symbol="triangle-down",
                    line=dict(color="white", width=1),
                ),
                showlegend=False,
                hovertemplate=f'<b>Trough Price</b>: {dd["trough_price"]:.2f}<extra></extra>',
            )
        )

    # 添加斐波那契回撤线（基于最后一个峰值）
    if drawdowns:
        last_peak = drawdowns[-1]
        last_peak_price = last_peak["peak_price"]
        last_peak_date = df.index[last_peak["peak_idx"]]

        # 斐波那契比例
        fib_ratios = [0.9, 0.8, 0.618, 0.5, 0.382, 0.236]

        # 颜色映射：从红色（高比例）到绿色（低比例）
        color_scale = [
            "#FF0000",  # 红色 - 0.9
            "#FF8040",  # 橙色 - 0.8
            "#FFFF80",  # 黄色 - 0.618
            "#80FF80",  # 浅绿 - 0.5
            "#40FF40",  # 绿色 - 0.382
            "#00FF00",  # 深绿 - 0.236
        ]

        # 绘制斐波那契回撤线
        for i, ratio in enumerate(fib_ratios):
            fib_price = last_peak_price * ratio
            color = color_scale[i]

            # 横向贯穿整个图表的虚线
            fig.add_trace(
                go.Scatter(
                    x=[df.index[0], df.index[-1]],
                    y=[fib_price, fib_price],
                    mode="lines",
                    line=dict(color=color, width=1.5, dash="dot"),
                    opacity=0.5,
                    showlegend=True,
                    name=f"-{1-ratio:.1%} ({fib_price:.2f})",
                    hovertemplate=f"<b>-{1-ratio:.1%} Level</b><br>Price: {fib_price:.2f}<extra></extra>",
                )
            )

    # 更新布局
    fig.update_layout(
        title=f"{stock_name.upper()} Stock Price with Drawdowns (Plotly)",
        xaxis_title="Date",
        yaxis_title="Close Price",
        template="plotly_dark",
        plot_bgcolor="#2d2d2d",
        paper_bgcolor="#2d2d2d",
        font=dict(color="white"),
        hovermode="x unified",
        showlegend=True,
        height=700,
        width=1200,
    )

    # 更新x轴
    fig.update_xaxes(gridcolor="#555555", gridwidth=1, showgrid=True)

    # 更新y轴
    fig.update_yaxes(gridcolor="#555555", gridwidth=1, showgrid=True)

    return fig


def quanboo(stock_name, stock_code, ths_code):
    """主函数"""
    print("=== 股票回撤分析工具 (Plotly版本) ===")

    # 获取股票数据
    df = fetch_stock_data(stock_name, stock_code, ths_code)

    # 分析回撤
    drawdowns = analyze_drawdowns(df)

    if not drawdowns:
        print("未检测到符合条件的回撤段（>10%）")
        return

    print(f"检测到 {len(drawdowns)} 个回撤段:")
    for i, dd in enumerate(drawdowns, 1):
        peak_date = df.index[dd["peak_idx"]].strftime("%Y-%m-%d")
        trough_date = df.index[dd["trough_idx"]].strftime("%Y-%m-%d")
        print(f"  {i}. {peak_date} -> {trough_date}: {dd['drawdown']:.1%} 回撤")

    # 创建图表
    fig = create_plotly_chart(df, drawdowns, stock_name)

    # 显示图表
    print("\n正在生成交互式图表...")
    fig.show()

    print("\n图表功能说明:")
    print("- 鼠标悬停可查看详细数据")
    print("- 可以缩放、平移图表")
    print("- 双击可重置视图")
    print("- 右上角工具栏提供更多交互选项")


if __name__ == "__main__":
    quanboo('苹果','AAPL','185')
