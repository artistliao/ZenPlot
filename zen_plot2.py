
# -*- coding:utf-8 -*-
#! python3

from pandas import DataFrame, Series
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpathes
from matplotlib import dates as mdates
from matplotlib import ticker as mticker
import matplotlib.gridspec as gridspec #分割子图
#from mpl_finance import candlestick_ohlc
from mplfinance.original_flavor import candlestick_ohlc
import mplfinance as mpf

import talib
import time
import sys
import os
import mysql.connector

from zp_logging import g_logger
from read_data import *
from utils import *


def plot_stock(stock_code, level, idx, offset, df_stockload, strokes, first_kline_stroke_val, lines, first_kline_line_val, trend_centrals):
    g_logger.debug("start stock_code:%s, level:%s, idx:%d, offset:%d", stock_code, level, idx, offset)
    np.seterr(divide='ignore', invalid='ignore') # 忽略warning
    plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签
    plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

    # file_path = r"E:\otherdata\stock_data\1min\stroke\SH" + stock_code + ".txt"
    # strokes = readStrokeData(file_path)

    kline_num = len(df_stockload.index)
    count = kline_num/300

    #创建fig对象
    fig = plt.figure(figsize=(20*count, 10.8), dpi=100, facecolor="white")

    #设置四个绘图区域 包括 K线（均线），成交量，MACD
    gs = gridspec.GridSpec(3, 1, left=0.01, bottom=0.1, right=0.99, top=0.96, wspace=None, hspace=0, height_ratios=[3.5,1,1])
    graph_KAV = fig.add_subplot(gs[0,:])
    graph_VOL = fig.add_subplot(gs[1,:])
    graph_MACD = fig.add_subplot(gs[2,:])

    # 添加网格
    graph_KAV.grid(linestyle='--')
    graph_KAV.legend(loc='best')
    graph_KAV.set_title(stock_code)
    graph_KAV.set_ylabel(u"价格")
    graph_KAV.set_xlim(0, len(df_stockload.index))  # 设置一下x轴的范围

    #绘制K线图
    g_logger.debug('draw klines')
    klines = df_stockload.copy(deep=True)
    klines['DateTime'] = pd.Series(range(kline_num),index = range(kline_num))
    if 'Date' in klines.columns:
        klines.drop('Date', axis=1, inplace = True)
    if 'Time' in klines.columns:
        klines.drop('Time', axis=1, inplace = True)
    # columns=['Date','Time','Open','High','Low','Close', 'Volume', 'ModifyDateTime']
    klines = klines.reindex(columns=['DateTime','Open','High','Low','Close','Volume','ModifyDateTime'])
    candlestick_ohlc(graph_KAV, klines.values, width=0.5, colorup='r', colordown='g')  # 绘制K线走势

    # 绘制笔
    g_logger.debug('draw strokes')
    stroke_len = len(strokes.index)
    stroke_idx_arr = []
    stroke_val_arr = []
    this_stroke_idx = 0
    this_stroke_direction = 0
    last_j = 0
    for i in range(kline_num):
        kline_time = df_stockload.loc[i,'ModifyDateTime']
        kline_ori_idx = int(df_stockload.loc[i,'OriginalIndex'])
        # g_logger.debug('stroke kline i:%d' , i)

        for j in range(this_stroke_idx, stroke_len):
            # g_logger.debug('stroke j:%d' , j)

            high = strokes.loc[j,'High']
            low = strokes.loc[j,'Low']
            direction = strokes.loc[j,'Direction']
            start_time = strokes.loc[j,'StartTime']
            end_time = strokes.loc[j,'EndTime']
            start_kline_idx = strokes.loc[j,'StartKlineIndex']
            end_kline_idx = strokes.loc[j,'EndKlineIndex']

            if i==0 and first_kline_stroke_val>0.001:
                stroke_idx_arr.append(i)
                stroke_val_arr.append(first_kline_stroke_val)
                break
            elif i==(kline_num-1):
                this_stroke_start_kline_idx = strokes.loc[this_stroke_idx, 'StartKlineIndex']
                this_stroke_end_kline_idx = strokes.loc[this_stroke_idx, 'EndKlineIndex']
                if kline_time>=start_time and kline_time<end_time and this_stroke_idx<(stroke_len-1):
                    #上一笔向上则当前笔向下
                    end_kline_stroke_val = 0.0
                    if this_stroke_direction==1:
                        end_kline_stroke_val = low + (high-low)*(kline_ori_idx-this_stroke_start_kline_idx)/(this_stroke_end_kline_idx-this_stroke_start_kline_idx)
                    elif this_stroke_direction==2:
                        end_kline_stroke_val = high - (high-low)*(kline_ori_idx-this_stroke_start_kline_idx)/(this_stroke_end_kline_idx-this_stroke_start_kline_idx)
                    stroke_idx_arr.append(i)
                    stroke_val_arr.append(end_kline_stroke_val)
                break
            elif start_kline_idx==kline_ori_idx:
                stroke_idx_arr.append(i)
                this_stroke_idx = j
                this_stroke_direction = direction
                if direction==1:
                    stroke_val_arr.append(low)
                elif direction==2:
                    stroke_val_arr.append(high)
                break
            elif end_kline_idx==kline_ori_idx and this_stroke_idx==(stroke_len-1):
                stroke_idx_arr.append(i)
                this_stroke_idx = j
                this_stroke_direction = direction
                if direction==1:
                    stroke_val_arr.append(high)
                elif direction==2:
                    stroke_val_arr.append(low)
                break
            elif start_time>kline_time:
                this_stroke_idx = j-1
                if this_stroke_idx<0:
                    this_stroke_idx = 0
                break

    graph_KAV.plot(stroke_idx_arr, stroke_val_arr, 'black', label='stroke', lw=0.6)

    # 绘制线段
    g_logger.debug('draw lines')
    line_len = len(lines.index)
    line_idx_arr = []
    line_val_arr = []
    this_line_idx = 0
    this_line_direction = 0
    for i in range(kline_num):
        kline_time = df_stockload.loc[i,'ModifyDateTime']
        kline_ori_idx = int(df_stockload.loc[i,'OriginalIndex'])

        for j in range(this_line_idx, line_len):
            high = lines.loc[j,'High']
            low = lines.loc[j,'Low']
            direction = lines.loc[j,'Direction']
            start_time = lines.loc[j,'StartTime']
            end_time = lines.loc[j,'EndTime']
            start_stroke_idx = lines.loc[j,'StartStrokeIndex']
            end_stroke_idx = lines.loc[j,'EndStrokeIndex']
            start_kline_idx = strokes.loc[start_stroke_idx,'StartKlineIndex']
            end_kline_idx = strokes.loc[end_stroke_idx,'EndKlineIndex']

            if i==0 and first_kline_line_val>0.001:
                line_idx_arr.append(i)
                line_val_arr.append(first_kline_line_val)
                break
            elif i==(kline_num-1):
                start_stroke_idx = lines.loc[this_line_idx,'StartStrokeIndex']
                end_stroke_idx = lines.loc[this_line_idx,'EndStrokeIndex']
                this_line_start_kline_idx = strokes.loc[start_stroke_idx, 'StartKlineIndex']
                this_line_end_kline_idx = strokes.loc[end_stroke_idx, 'EndKlineIndex']
                if kline_time>=start_time and kline_time<end_time and this_line_idx<(line_len-1):
                    #上一笔向上则当前笔向下
                    end_kline_line_val = 0.0
                    if this_line_direction==1:
                        end_kline_line_val = low + (high-low)*(kline_ori_idx-this_line_start_kline_idx)/(this_line_end_kline_idx-this_line_start_kline_idx)
                    elif this_line_direction==2:
                        end_kline_line_val = high - (high-low)*(kline_ori_idx-this_line_start_kline_idx)/(this_line_end_kline_idx-this_line_start_kline_idx)
                    line_idx_arr.append(i)
                    line_val_arr.append(end_kline_line_val)
                break
            elif start_kline_idx==kline_ori_idx:
                line_idx_arr.append(i)
                this_line_idx = j
                this_line_direction = direction
                if direction==1:
                    line_val_arr.append(low)
                    graph_KAV.text(i, low*0.998, str(round(low,2)), ha='center', family='fantasy', fontsize=12, style='normal', color='mediumvioletred')
                elif direction==2:
                    line_val_arr.append(high)
                    graph_KAV.text(i, high*1.002, str(round(high,2)), ha='center', family='fantasy', fontsize=12, style='normal', color='mediumvioletred')
                break
            elif end_kline_idx==kline_ori_idx and this_line_idx==(line_len-1):
                line_idx_arr.append(i)
                this_line_idx = j
                this_line_direction = direction
                if direction==1:
                    line_val_arr.append(high)
                elif direction==2:
                    line_val_arr.append(low)
                break
            elif start_time>kline_time:
                this_line_idx = j-1
                if this_line_idx<0:
                    this_line_idx = 0
                break

    graph_KAV.plot(line_idx_arr, line_val_arr, 'blue', label='line', lw=1)


    #绘制走势中枢
    g_logger.debug('draw trend centrals')
    trend_central_len = len(trend_centrals.index)
    this_trend_central_idx = 0
    x = 0
    y = 0
    width = 0
    height = 0
    haveRect = False
    edge_color = 'black'
    for i in range(kline_num):
        kline_ori_idx = int(df_stockload.loc[i,'OriginalIndex'])

        for j in range(this_trend_central_idx, trend_central_len):
            trend_type = trend_centrals.loc[j,'TrendType']
            high = trend_centrals.loc[j,'High']
            low = trend_centrals.loc[j,'Low']
            # start_line_idx = trend_centrals.loc[j,'StartLineIndex']
            # end_line_idx = trend_centrals.loc[j,'EndLineIndex']
            # start_stroke_idx = lines.loc[start_line_idx,'StartStrokeIndex']
            # end_stroke_idx = lines.loc[end_line_idx,'EndStrokeIndex']
            start_stroke_idx = trend_centrals.loc[j, 'StartStrokeIndex']
            end_stroke_idx = trend_centrals.loc[j, 'EndStrokeIndex']
            start_kline_idx = strokes.loc[start_stroke_idx,'StartKlineIndex']
            end_kline_idx = strokes.loc[end_stroke_idx,'EndKlineIndex']

            if i==0:
                if kline_ori_idx>=end_kline_idx:
                    continue
                elif kline_ori_idx>=start_kline_idx and kline_ori_idx<end_kline_idx:
                    x = kline_ori_idx
                    y = low
                    this_trend_central_idx = j
                    haveRect = True
                    break
                elif kline_ori_idx<start_kline_idx:
                    break

            if kline_ori_idx<start_kline_idx:
                break
            elif kline_ori_idx==start_kline_idx:
                x = start_kline_idx
                y = low
                this_trend_central_idx = j
                haveRect = True
                break
            elif (kline_ori_idx==end_kline_idx or i==(kline_num-1)) and (haveRect==True):
                width = kline_ori_idx-x
                height = high-low
                xy  = (x-df_stockload.loc[0,'OriginalIndex'], y)
                if trend_type==1:
                    edge_color='red'
                elif trend_type==2:
                    edge_color='green'
                elif trend_type==3:
                    edge_color='black'

                # 画中枢区间大小标签
                text_x = x -df_stockload.loc[0,'OriginalIndex'] + width/2
                text_y = high*1.002
                text_str = str(round(low, 2)) + '--' + str(round(high, 2))
                graph_KAV.text(text_x, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)
                #K线数超过360的中枢两头也画一个标签
                if width>=360:
                    graph_KAV.text(text_x-width/2, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)
                    graph_KAV.text(text_x+width/2, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)

                rect = mpathes.Rectangle(xy , width, height, color=None, edgecolor=edge_color, fill=False, label='trend_central', lw=3)
                graph_KAV.add_patch(rect)
                this_trend_central_idx = j+1
                haveRect = False
                break

    # 标注顶底背驰点
    for i in range(kline_num):
        divergence = int(df_stockload.loc[i, 'Divergence'])
        high = df_stockload.loc[i, 'High']
        low = df_stockload.loc[i, 'Low']

        if divergence==1:
            text_x = i
            text_y = high*1.01
            graph_KAV.text(text_x, text_y, 'TDiv', ha='center', family='fantasy', fontsize=14, style='normal', color='Crimson')
        elif divergence==2:
            text_x = i
            text_y = low*0.99
            graph_KAV.text(text_x, text_y, 'BDiv', ha='center', family='fantasy', fontsize=14, style='normal', color='LimeGreen')

    # 标注开平仓点 0:无操作 1：open-buy 2: open-sell 3：cover-buy 4: cover-sell
    for i in range(kline_num):
        trade_type = int(df_stockload.loc[i, 'TradeType'])
        high = df_stockload.loc[i, 'High']
        low = df_stockload.loc[i, 'Low']

        if trade_type==1:
            text_x = i
            text_y = low*0.99
            graph_KAV.text(text_x, text_y, 'O-B', ha='center', family='fantasy', fontsize=14, style='normal', color='Crimson')
        elif trade_type==2:
            text_x = i
            text_y = high*1.01
            graph_KAV.text(text_x, text_y, 'O-S', ha='center', family='fantasy', fontsize=14, style='normal', color='LimeGreen')
        elif trade_type==3:
            text_x = i
            text_y = low*0.99
            graph_KAV.text(text_x, text_y, 'C-B', ha='center', family='fantasy', fontsize=14, style='normal', color='Crimson')
        elif trade_type==4:
            text_x = i
            text_y = high*1.01
            graph_KAV.text(text_x, text_y, 'C-S', ha='center', family='fantasy', fontsize=14, style='normal', color='LimeGreen')

    #绘制移动平均线图
    # print('draw mv')
    # df_stockload['Ma5']  = df_stockload.Close.rolling(window=5).mean()#pd.rolling_mean(df_stockload.close,window=20)
    # df_stockload['Ma10'] = df_stockload.Close.rolling(window=10).mean()#pd.rolling_mean(df_stockload.close,window=30)
    # df_stockload['Ma20'] = df_stockload.Close.rolling(window=20).mean()#pd.rolling_mean(df_stockload.close,window=60)
    # df_stockload['Ma30'] = df_stockload.Close.rolling(window=30).mean()#pd.rolling_mean(df_stockload.close,window=60)
    # df_stockload['Ma60'] = df_stockload.Close.rolling(window=60).mean()#pd.rolling_mean(df_stockload.close,window=60)
    #
    # graph_KAV.plot(np.arange(0, len(df_stockload.index)), df_stockload['Ma5'],'black', label='M5',lw=1.0)
    # graph_KAV.plot(np.arange(0, len(df_stockload.index)), df_stockload['Ma10'],'green',label='M10', lw=1.0)
    # graph_KAV.plot(np.arange(0, len(df_stockload.index)), df_stockload['Ma20'],'blue',label='M20', lw=1.0)
    # graph_KAV.plot(np.arange(0, len(df_stockload.index)), df_stockload['Ma30'],'pink', label='M30',lw=1.0)
    # graph_KAV.plot(np.arange(0, len(df_stockload.index)), df_stockload['Ma60'],'yellow',label='M60', lw=1.0)


    #绘制成交量图
    g_logger.debug('draw vol')
    graph_VOL.bar(np.arange(0, len(df_stockload.index)), df_stockload.Volume,color=['g' if df_stockload.Open[x] > df_stockload.Close[x] else 'r' for x in range(0,len(df_stockload.index))])
    graph_VOL.set_ylabel(u"成交量")
    graph_VOL.set_xlim(0,len(df_stockload.index)) #设置一下x轴的范围
    graph_VOL.set_xticks(range(0,len(df_stockload.index),15))#X轴刻度设定 每15天标一个日期

    #绘制MACD
    g_logger.debug('draw macd')
    macd_dif, macd_dea, macd_bar = talib.MACD(df_stockload['Close'].values, fastperiod=12, slowperiod=26, signalperiod=9)
    graph_MACD.plot(np.arange(0, len(df_stockload.index)), macd_dif, 'red', label='macd dif')  # dif
    graph_MACD.plot(np.arange(0, len(df_stockload.index)), macd_dea, 'blue', label='macd dea')  # dea

    bar_red = np.where(macd_bar > 0, 2 * macd_bar, 0)# 绘制BAR>0 柱状图
    bar_green = np.where(macd_bar < 0, 2 * macd_bar, 0)# 绘制BAR<0 柱状图
    graph_MACD.bar(np.arange(0, len(df_stockload.index)), bar_red, facecolor='red')
    graph_MACD.bar(np.arange(0, len(df_stockload.index)), bar_green, facecolor='green')

    graph_MACD.legend(loc='best',shadow=True, fontsize ='10')
    graph_MACD.set_ylabel(u"MACD")
    graph_MACD.set_xlabel("日期")
    graph_MACD.set_xlim(0,len(df_stockload.index)) #设置一下x轴的范围
    graph_MACD.set_xticks(range(0,len(df_stockload.index), 15))#X轴刻度设定 每15天标一个日期

    #绘制x轴标签
    #先生成DateTime数据
    date_times = []
    col_len = len(df_stockload.columns)
    df_stockload.insert(col_len, 'DateTime', '' )
    for index in df_stockload.index.values:
        # sdate = df_stockload.Date.values[index]
        # stime = df_stockload.Time.values[index]
        # sdate = sdate.replace("2020", "")
        # sdate = sdate.replace("2021", "")
        # sdate = sdate.replace("/", "")
        # date_time = sdate+stime
        date_time = str(df_stockload.ModifyDateTime.values[index])
        # date_time = date_time.replace("2020", "")
        # date_time = date_time.replace("2021", "")
        date_time = date_time[:-2]
        # date_times.append(date_time)
        df_stockload.loc[index, 'DateTime'] = date_time
    # df_stockload['DateTime'] = pd.Series(date_times)
    macd_xticklabels = [df_stockload.DateTime.values[index] for index in graph_MACD.get_xticks()]
    # graph_MACD.set_xticklabels(pd.to_datetime(macd_xticklabels).strftime('%Y-%m-%d'))  # 标签设置为日期
    graph_MACD.set_xticklabels(macd_xticklabels)  # 标签设置为日期

    # X-轴每个ticker标签都向右倾斜45度
    for label in graph_KAV.xaxis.get_ticklabels():
        label.set_visible(False)

    for label in graph_VOL.xaxis.get_ticklabels():
        label.set_visible(False)

    for label in graph_MACD.xaxis.get_ticklabels():
        label.set_rotation(45)
        label.set_fontsize(10)  # 设置标签字体

    # plt.show()
    dir_path = "E:\\othercode\\quant\\plot\\" + level + "\\"
    if os.path.exists(dir_path)==False:
        os.makedirs( dir_path )

    str_start_time = str(df_stockload.loc[0, 'ModifyDateTime'])
    str_end_time = str(df_stockload.loc[kline_num-1, 'ModifyDateTime'])
    plot_name = dir_path + stock_code + "_" + str(idx+offset+1) + "_" + str_start_time[2:8] + "_" + str_end_time[2:8] + ".png"
    g_logger.debug("savefig plot_name:%s", plot_name)
    plt.savefig(plot_name)
    g_logger.debug("end stock_code:" + stock_code)
    i=1
    # 直线方程的公式有以下几种：
    # 两点式:(x-x1)/(x2-x1)=(y-y1)/(y2-y1)

def plot_highlevel_trend_centrals(stock_code, idx, offset, df_stockload, strokes, lines, trend_centrals):
    g_logger.debug("plot_highlevel_trend_centrals start stock_code:%s, idx:%d, offset:%d", stock_code, idx, offset)
    np.seterr(divide='ignore', invalid='ignore') # 忽略warning
    plt.rcParams['font.sans-serif']=['SimHei'] #用来正常显示中文标签
    plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

    kline_num = len(df_stockload.index)
    count = kline_num/300

    #创建fig对象
    fig = plt.figure(figsize=(20*count, 10.8), dpi=100, facecolor="white")

    #设置四个绘图区域 包括 K线（均线），成交量，MACD
    gs = gridspec.GridSpec(3, 1, left=0.01, bottom=0.1, right=0.99, top=0.96, wspace=None, hspace=0, height_ratios=[3.5,1,1])
    graph_KAV = fig.add_subplot(gs[0,:])
    graph_VOL = fig.add_subplot(gs[1,:])
    graph_MACD = fig.add_subplot(gs[2,:])

    # 添加网格
    graph_KAV.grid(linestyle='--')
    graph_KAV.legend(loc='best')
    graph_KAV.set_title(stock_code)
    graph_KAV.set_ylabel(u"价格")
    graph_KAV.set_xlim(0, len(df_stockload.index))  # 设置一下x轴的范围

    #绘制K线图
    g_logger.debug('draw klines')
    klines = df_stockload.copy(deep=True)
    klines['DateTime'] = pd.Series(range(kline_num),index = range(kline_num))
    if 'Date' in klines.columns:
        klines.drop('Date', axis=1, inplace = True)
    if 'Time' in klines.columns:
        klines.drop('Time', axis=1, inplace = True)
    # columns=['Date','Time','Open','High','Low','Close', 'Volume', 'ModifyDateTime']
    klines = klines.reindex(columns=['DateTime','Open','High','Low','Close','Volume','ModifyDateTime'])
    candlestick_ohlc(graph_KAV, klines.values, width=0.5, colorup='r', colordown='g')  # 绘制K线走势

    #绘制走势中枢
    g_logger.debug('draw trend centrals')
    trend_central_len = len(trend_centrals.index)
    this_trend_central_idx = 0
    x = 0
    y = 0
    width = 0
    height = 0
    haveRect = False
    edge_color = 'black'
    for i in range(kline_num):
        kline_ori_idx = int(df_stockload.loc[i,'OriginalIndex'])

        for j in range(this_trend_central_idx, trend_central_len):
            level = trend_centrals.loc[j, 'Level']
            #只画5分钟级别以上的中枢
            if level<=1:
                continue

            trend_type = trend_centrals.loc[j,'TrendType']
            high = trend_centrals.loc[j,'High']
            low = trend_centrals.loc[j,'Low']
            start_line_idx = trend_centrals.loc[j,'StartLineIndex'] + 1
            end_line_idx = trend_centrals.loc[j,'EndLineIndex'] -1
            start_stroke_idx = lines.loc[start_line_idx,'StartStrokeIndex']
            end_stroke_idx = lines.loc[end_line_idx,'EndStrokeIndex']
            start_kline_idx = strokes.loc[start_stroke_idx,'StartKlineIndex']
            end_kline_idx = strokes.loc[end_stroke_idx,'EndKlineIndex']

            if i==0:
                if kline_ori_idx>=end_kline_idx:
                    continue
                elif kline_ori_idx>=start_kline_idx and kline_ori_idx<end_kline_idx:
                    x = kline_ori_idx
                    y = low
                    this_trend_central_idx = j
                    haveRect = True
                    break
                elif kline_ori_idx<start_kline_idx:
                    break

            if kline_ori_idx<start_kline_idx:
                break
            elif kline_ori_idx==start_kline_idx:
                x = start_kline_idx
                y = low
                this_trend_central_idx = j
                haveRect = True
                break
            elif (kline_ori_idx==end_kline_idx or i==(kline_num-1)) and (haveRect==True):
                width = kline_ori_idx-x
                height = high-low
                xy  = (x-df_stockload.loc[0,'OriginalIndex'], y)
                if trend_type==1:
                    edge_color='red'
                elif trend_type==2:
                    edge_color='green'
                elif trend_type==3:
                    edge_color='black'

                # 画中枢区间大小标签
                text_x = x -df_stockload.loc[0,'OriginalIndex'] + width/2
                text_y = high*1.002
                text_str = str(round(low, 2)) + '--' + str(round(high, 2))
                graph_KAV.text(text_x, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)
                #K线数超过360的中枢两头也画一个标签
                if width>=360:
                    graph_KAV.text(text_x-width/2, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)
                    graph_KAV.text(text_x+width/2, text_y, text_str, ha='center', family='fantasy', fontsize=14, style='normal', color=edge_color)

                rect = mpathes.Rectangle(xy , width, height, color=None, edgecolor=edge_color, fill=False, label='trend_central', lw=3)
                graph_KAV.add_patch(rect)
                this_trend_central_idx = j+1
                haveRect = False
                break

    #绘制成交量图
    g_logger.debug('draw vol')
    graph_VOL.bar(np.arange(0, len(df_stockload.index)), df_stockload.Volume,color=['g' if df_stockload.Open[x] > df_stockload.Close[x] else 'r' for x in range(0,len(df_stockload.index))])
    graph_VOL.set_ylabel(u"成交量")
    graph_VOL.set_xlim(0,len(df_stockload.index)) #设置一下x轴的范围
    graph_VOL.set_xticks(range(0,len(df_stockload.index),15))#X轴刻度设定 每15天标一个日期

    #绘制MACD
    g_logger.debug('draw macd')
    macd_dif, macd_dea, macd_bar = talib.MACD(df_stockload['Close'].values, fastperiod=12, slowperiod=26, signalperiod=9)
    graph_MACD.plot(np.arange(0, len(df_stockload.index)), macd_dif, 'red', label='macd dif')  # dif
    graph_MACD.plot(np.arange(0, len(df_stockload.index)), macd_dea, 'blue', label='macd dea')  # dea

    bar_red = np.where(macd_bar > 0, 2 * macd_bar, 0)# 绘制BAR>0 柱状图
    bar_green = np.where(macd_bar < 0, 2 * macd_bar, 0)# 绘制BAR<0 柱状图
    graph_MACD.bar(np.arange(0, len(df_stockload.index)), bar_red, facecolor='red')
    graph_MACD.bar(np.arange(0, len(df_stockload.index)), bar_green, facecolor='green')

    graph_MACD.legend(loc='best',shadow=True, fontsize ='10')
    graph_MACD.set_ylabel(u"MACD")
    graph_MACD.set_xlabel("日期")
    graph_MACD.set_xlim(0,len(df_stockload.index)) #设置一下x轴的范围
    graph_MACD.set_xticks(range(0,len(df_stockload.index), 15))#X轴刻度设定 每15天标一个日期

    #绘制x轴标签
    #先生成DateTime数据
    date_times = []
    col_len = len(df_stockload.columns)
    df_stockload.insert(col_len, 'DateTime', '' )
    for index in df_stockload.index.values:
        date_time = str(df_stockload.ModifyDateTime.values[index])
        date_time = date_time[:-2]
        df_stockload.loc[index, 'DateTime'] = date_time
    # df_stockload['DateTime'] = pd.Series(date_times)
    macd_xticklabels = [df_stockload.DateTime.values[index] for index in graph_MACD.get_xticks()]
    graph_MACD.set_xticklabels(macd_xticklabels)  # 标签设置为日期

    # X-轴每个ticker标签都向右倾斜45度
    for label in graph_KAV.xaxis.get_ticklabels():
        label.set_visible(False)

    for label in graph_VOL.xaxis.get_ticklabels():
        label.set_visible(False)

    for label in graph_MACD.xaxis.get_ticklabels():
        label.set_rotation(45)
        label.set_fontsize(10)  # 设置标签字体

    # plt.show()
    str_start_time = str(df_stockload.loc[0, 'ModifyDateTime'])
    str_end_time = str(df_stockload.loc[kline_num-1, 'ModifyDateTime'])
    plot_name = "E:\\othercode\\quant\\plot_5min\\" + stock_code + "_" + str(idx+offset+1) + "_" + str_start_time[2:8] + "_" + str_end_time[2:8] + ".png"
    g_logger.debug("savefig plot_name:%s", plot_name)
    plt.savefig(plot_name)
    g_logger.debug("end stock_code:" + stock_code)
    i=1


if __name__ == "__main__":

    dataDir = r"E:\otherdata\stock_data\\"
    orderDir = r"E:\otherdata\stock_data\order\\"
    # dataDir = "/data/stock_data/"
    # orderDir = "/data/stock_data/order/"
    # dataDir5Min = r"E:\otherdata\stock_data\5min\\"

    stock_code = sys.argv[1] # '000001.XSHG'
    level = sys.argv[2]      # '5min'
    offset = int(sys.argv[3]) # 0
    count = int(sys.argv[4])  # 10
    g_logger.info('stock_code:%s, level:%s, offset:%d, count:%d', stock_code, level, offset, count)
    dataDir += level
    dataDir += "/"

    #读取数据
    zen_ms_data = ZenMsData('futures', 'config.ini')
    zen_ms_data.LoadAllSecurities()
    klines = zen_ms_data.LoadSecuritiesKlineData(stock_code, level, 1577808000)
    if klines is None:
        g_logger.warning("read code:%s, level:%s, klines is None!", stock_code, level)
        sys.exit(-1)

    left_klines_len = len(klines.index)
    g_logger.debug("left_klines_len=%d", left_klines_len)

    start_time = klines.loc[0, 'ModifyDateTime']
    end_time = klines.loc[left_klines_len-1, 'ModifyDateTime']

    file_path = dataDir + "stroke/" + stock_code + ".txt"
    strokes = readStrokeData(file_path, start_time, end_time)

    file_path = dataDir + "line_segment/" + stock_code + ".txt"
    lines = readLineSegmentData(file_path)

    file_path = dataDir + "trend_central/" + stock_code + ".txt"
    trend_centrals = readTrendCentralData(file_path)

    file_path = orderDir + stock_code + ".txt"
    orders = readOrderData(file_path)

    # stroke_len = len(strokes.index)
    # for i in range(stroke_len):
    #     stroke_end_kline_idx = strokes.loc[i,'EndKlineIndex']
    #     if i==24245 or stroke_end_kline_idx==0:
    #         print(i)

    #标注o-c位置
    kline_num = len(klines.index)
    order_num = len(orders.index)
    this_kline_idx = 0
    klines['TradeType'] = pd.Series(np.zeros((kline_num,), dtype=int),index = range(kline_num))
    for i in range(order_num):
        open_kline_idx = orders.loc[i,'OpenKlineIdx']
        cover_kline_idx = orders.loc[i,'CoverKlineIdx']
        direction = orders.loc[i,'Direction']

        # g_logger.debug('stroke kline i:%d' , i)

        for j in range(this_kline_idx, kline_num):
            if j%10000==0:
                g_logger.debug('kline j:%d' , j)
            kline_ori_idx = int(klines.loc[j,'OriginalIndex'])
            if kline_ori_idx!=open_kline_idx and kline_ori_idx!=cover_kline_idx:
                continue # 0:无操作 1：open-buy 2: open-sell 3：cover-buy 4: cover-sell
            elif kline_ori_idx==open_kline_idx:
                if direction==1:
                    klines.loc[j,'TradeType'] = 1
                elif direction==2:
                    klines.loc[j,'TradeType'] = 2
                else:
                    g_logger.debug('order error direction:%d' , direction)
                    klines.loc[j,'TradeType'] = 0
            elif kline_ori_idx==cover_kline_idx:
                if direction==1:
                    klines.loc[j,'TradeType'] = 4
                elif direction==2:
                    klines.loc[j,'TradeType'] = 3
                else:
                    g_logger.debug('order error direction:%d' , direction)
                this_kline_idx = j+1
                break

    start_time = TsToIntTime(0)
    idx=0
    while(idx<len(klines.index)):
        modify_time = klines.loc[idx, 'ModifyDateTime']
        if (modify_time>=start_time) and idx>0:
            klines = klines.iloc[idx:, :]
            break
        elif (modify_time>=start_time) and idx==0:
            break
        idx+=1
    g_logger.debug('start idx:%d' , idx)

    #level级别画图
    last_kline_idx = 0
    idx = 0
    while(idx<count):
        if left_klines_len>=ONE_PLOT_KLINE_NUM:
            df_stockload = klines.iloc[(idx+offset)*ONE_PLOT_KLINE_NUM:(idx+offset+1)*ONE_PLOT_KLINE_NUM, :]
        else:
            df_stockload = klines.iloc[(idx+offset)*ONE_PLOT_KLINE_NUM:(idx+offset)*ONE_PLOT_KLINE_NUM+left_klines_len, :]

        df_stockload.reset_index(drop=True, inplace=True)

        # 第一根K线的时间
        first_kline_time = df_stockload.loc[0, 'ModifyDateTime']
        first_kline_idx = int(df_stockload.loc[0, 'OriginalIndex'])
        first_kline_stroke_val = 0.0
        first_kline_line_val = 0.0
        stroke_start_kline_idx = 0
        stroke_end_kline_idx = 0
        high = 0.0
        low = 0.0
        direction = 0

        # 查找第一个kline对应的笔值
        stroke_len = len(strokes.index)
        for i in range(stroke_len):
            high = strokes.loc[i,'High']
            low = strokes.loc[i,'Low']
            direction = strokes.loc[i,'Direction']
            stroke_start_kline_idx = strokes.loc[i,'StartKlineIndex']
            stroke_end_kline_idx = strokes.loc[i,'EndKlineIndex']
            kline_count = strokes.loc[i,'KlineCount']

            if stroke_start_kline_idx!=0 and stroke_end_kline_idx!=0 and first_kline_idx>=stroke_start_kline_idx and first_kline_idx<stroke_end_kline_idx:
                if direction==1:
                    first_kline_stroke_val = low + (high-low)*(first_kline_idx-stroke_start_kline_idx)/(stroke_end_kline_idx-stroke_start_kline_idx)
                elif direction==2:
                    first_kline_stroke_val = high - (high-low)*(first_kline_idx-stroke_start_kline_idx)/(stroke_end_kline_idx-stroke_start_kline_idx)
                else:
                    g_logger.debug("error direction=%d", direction)

            if stroke_start_kline_idx>first_kline_idx:
                    break

        g_logger.debug("first_kline_stroke_val=%.2f", first_kline_stroke_val)

        # 查找第一个kline对应的线段值
        line_len = len(lines.index)
        for i in range(line_len):
            high = lines.loc[i,'High']
            low = lines.loc[i,'Low']
            direction = lines.loc[i,'Direction']
            line_start_stroke_idx = lines.loc[i,'StartStrokeIndex']
            line_end_stroke_idx = lines.loc[i,'EndStrokeIndex']
            line_start_kline_idx = strokes.loc[line_start_stroke_idx,'StartKlineIndex']
            line_end_kline_idx = strokes.loc[line_end_stroke_idx,'EndKlineIndex']
            kline_count = lines.loc[i,'KlineCount']

            if line_start_kline_idx!=0 and line_end_kline_idx!=0 and first_kline_idx>=line_start_kline_idx and first_kline_idx<line_end_kline_idx:
                if direction==1:
                    first_kline_line_val = low + (high-low)*(first_kline_idx-line_start_kline_idx)/(line_end_kline_idx-line_start_kline_idx)
                elif direction==2:
                    first_kline_line_val = high - (high-low)*(first_kline_idx-line_start_kline_idx)/(line_end_kline_idx-line_start_kline_idx)
                else:
                    g_logger.debug("error direction=" + str(direction))

            if line_start_kline_idx>first_kline_idx:
                break

        g_logger.debug("first_kline_line_val=" + str(first_kline_line_val))

        # for test
        if idx>=0:
            plot_stock(stock_code, level, idx, offset, df_stockload, strokes, first_kline_stroke_val, lines, first_kline_line_val, trend_centrals)
        left_klines_len = len(klines.index)-(idx+offset+1)*ONE_PLOT_KLINE_NUM
        idx+=1

        if left_klines_len <= 0:
            break


    #5min级别画图
    # last_kline_idx = 0
    # idx = 0
    # while(idx<count):
    #     if left_klines_5min_len>=ONE_PLOT_KLINE_NUM:
    #         df_stockload = klines_5min.iloc[(idx+offset)*ONE_PLOT_KLINE_NUM:(idx+offset+1)*ONE_PLOT_KLINE_NUM, :]
    #     else:
    #         df_stockload = klines_5min.iloc[(idx+offset)*ONE_PLOT_KLINE_NUM:(idx+offset)*ONE_PLOT_KLINE_NUM+left_klines_5min_len, :]
    #
    #     df_stockload.reset_index(drop=True, inplace=True)
    #
    #     # for test
    #     if idx>=0:
    #         plot_highlevel_trend_centrals(stock_code, idx, offset, df_stockload, strokes_5min, lines, trend_centrals_5min)
    #     left_klines_len = len(klines_5min.index)-(idx+offset+1)*ONE_PLOT_KLINE_NUM
    #     idx+=1
    #
    #     if left_klines_len <= 0:
    #         break

