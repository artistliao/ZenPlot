
# -*- coding:utf-8 -*-
#! python3

from pandas import DataFrame, Series
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from matplotlib import ticker as mticker
#from mpl_finance import candlestick_ohlc
from mplfinance.original_flavor import candlestick_ohlc
from zp_logging import movingaverage

import matplotlib.dates as mpl_dt
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MONDAY,YEARLY
from matplotlib.dates import MonthLocator,MONTHLY
import datetime as dt
import pylab
import talib

#E:\otherdata\stock_data\1min\utf8\SH000001.csv
# E:\otherdata\stock_data\day\SH999999.csv
daylinefilespath = 'E:\otherdata\stock_data\day'
stock_b_code = 'SH999999' #平安银行
MA1 = 5
MA2 = 10
startdate = dt.date(2016, 6, 29)
enddate = dt.date(2017, 1, 30)
# mpl_dt.date2num()
# np.datetime64()

def readstkData(rootpath, stockcode):

    returndata = pd.DataFrame()
    # for yearnum in range(0,int((eday - sday).days / 365.25)+1):
    #     theyear = sday + dt.timedelta(days = yearnum * 365)
    #     # build file name
    #     filename = rootpath  + theyear.strftime('%Y') + '\\' + str(stockcode).zfill(6) + '.csv'
    #
    #     try:
    #         rawdata = pd.read_csv(filename, parse_dates = True, index_col = 0, encoding = 'gbk')
    #     except IOError:
    #         raise Exception('IoError when reading dayline data file: ' + filename)
    #
    #     returndata = pd.concat([rawdata, returndata])

    filename = rootpath + '\\' + stockcode + '.csv'

    try:
        # rawdata = pd.read_csv(filename, parse_dates = True, index_col = 0, encoding = 'utf8')
        rawdata = pd.read_csv(filename)
    except IOError:
        raise Exception('IoError when reading dayline data file: ' + filename)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    returndata = returndata.sort_index()
    # returndata.index.name = 'DateTime'
    returndata.drop('Amount', axis=1, inplace = True)
    # returndata.columns = ['Open', 'High', 'Close', 'Low', 'Volume']

    returndata = returndata[returndata.index < 100]

    return returndata


def main():
    days = readstkData(daylinefilespath, stock_b_code)

    # drop the date index from the dateframe & make a copy
    daysreshape = days.reset_index()
    # convert the datetime64 column in the dataframe to 'float days'
    # daysreshape['DateTime']=mdates.date2num(daysreshape['DateTime'].astype(dt.date))
    daysreshape['DateTime'] = mdates.date2num(pd.to_datetime(daysreshape['DateTime']))

    # clean day data for candle view
    daysreshape.drop('Volume', axis=1, inplace = True)
    daysreshape = daysreshape.reindex(columns=['DateTime','Open','High','Low','Close'])

    Av1 = list(movingaverage(daysreshape.Close.values, MA1))
    Av2 = list(movingaverage(daysreshape.Close.values, MA2))
    SP = len(daysreshape.DateTime.values[MA2-1:])
    fig = plt.figure(facecolor='#07000d', figsize=(15,10))

    ax1 = plt.subplot2grid((6,4), (1,0), rowspan=4, colspan=4, facecolor='#07000d')
    kline_data = daysreshape.values[-SP:]
    candlestick_ohlc(ax1, kline_data, width=.6, colorup='#ff1717', colordown='#53c156')

    Label1 = str(MA1)+' SMA'
    Label2 = str(MA2)+' SMA'
    #
    ax1.plot(daysreshape.DateTime.values[-SP:],Av1[-SP:],'#e1edf9',label=Label1, linewidth=1)
    ax1.plot(daysreshape.DateTime.values[-SP:],Av2[-SP:],'#4ee6fd',label=Label2, linewidth=1.5)
    ax1.grid(True, color='w', linestyle='--')
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.label.set_color("w")
    ax1.yaxis.label.set_color("w")
    ax1.spines['bottom'].set_color("#5998ff")
    ax1.spines['top'].set_color("#5998ff")
    ax1.spines['left'].set_color("#5998ff")
    ax1.spines['right'].set_color("#5998ff")
    ax1.tick_params(axis='y', colors='w')
    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
    ax1.tick_params(axis='x', colors='w')

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 中文字体设置
    plt.rcParams['font.size'] = 9
    plt.rcParams['axes.unicode_minus'] = False
    plt.xlabel('日期')
    plt.ylabel('Stock Price and Volume')

    # 绘制成交量
    volumeMin = 0
    ax1v = ax1.twinx()
    ax1v.fill_between(daysreshape.DateTime.values[-SP:],volumeMin, days.Volume.values[-SP:], facecolor='#00ffe8', alpha=.4)
    ax1v.axes.yaxis.set_ticklabels([])
    ax1v.grid(False)
    ###Edit this to 3, so it's a bit larger
    ax1v.set_ylim(0, 3*days.Volume.values.max())
    ax1v.spines['bottom'].set_color("#5998ff")
    ax1v.spines['top'].set_color("#5998ff")
    ax1v.spines['left'].set_color("#5998ff")
    ax1v.spines['right'].set_color("#5998ff")
    ax1v.tick_params(axis='x', colors='w')
    ax1v.tick_params(axis='y', colors='w')

    # 绘制RSI
    maLeg = plt.legend(loc=9, ncol=2, prop={'size':7}, fancybox=True, borderaxespad=0.)
    maLeg.get_frame().set_alpha(0.4)
    textEd = pylab.gca().get_legend().get_texts()
    pylab.setp(textEd[0:5], color = 'w')

    ax0 = plt.subplot2grid((6,4), (0,0), sharex=ax1, rowspan=1, colspan=4, facecolor='#07000d')
    # rsi = rsiFunc(daysreshape.Close.values)
    rsi =talib.RSI(daysreshape.Close.values, timeperiod=6)
    rsiCol = '#c1f9f7'
    posCol = '#386d13'
    negCol = '#8f2020'

    ax0.plot(daysreshape.DateTime.values[-SP:], rsi[-SP:], rsiCol, linewidth=1.5)
    ax0.axhline(70, color=negCol)
    ax0.axhline(30, color=posCol)
    ax0.fill_between(daysreshape.DateTime.values[-SP:], rsi[-SP:], 70, where=(rsi[-SP:]>=70), facecolor=negCol, edgecolor=negCol, alpha=0.5)
    ax0.fill_between(daysreshape.DateTime.values[-SP:], rsi[-SP:], 30, where=(rsi[-SP:]<=30), facecolor=posCol, edgecolor=posCol, alpha=0.5)
    ax0.set_yticks([30,70])
    ax0.yaxis.label.set_color("w")
    ax0.spines['bottom'].set_color("#5998ff")
    ax0.spines['top'].set_color("#5998ff")
    ax0.spines['left'].set_color("#5998ff")
    ax0.spines['right'].set_color("#5998ff")
    ax0.tick_params(axis='y', colors='w')
    ax0.tick_params(axis='x', colors='w')
    plt.ylabel('RSI')

    # 绘制MACD
    ax2 = plt.subplot2grid((6,4), (5,0), sharex=ax1, rowspan=1, colspan=4, facecolor='#07000d')
    fillcolor = '#00ffe8'
    nslow = 26
    nfast = 12
    nema = 9
    # emaslow, emafast, macd = computeMACD(daysreshape.Close.values)
    emafast, emaslow, macd = talib.MACD(daysreshape.Close.values)
    # ema9 = ExpMovingAverage(macd, nema)
    ema9 = talib.EMA(macd,timeperiod=9)
    ax2.plot(daysreshape.DateTime.values[-SP:], macd[-SP:], color='#4ee6fd', lw=2)
    ax2.plot(daysreshape.DateTime.values[-SP:], ema9[-SP:], color='#e1edf9', lw=1)
    ax2.fill_between(daysreshape.DateTime.values[-SP:], macd[-SP:]-ema9[-SP:], 0, alpha=0.5, facecolor=fillcolor, edgecolor=fillcolor)
    plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
    ax2.spines['bottom'].set_color("#5998ff")
    ax2.spines['top'].set_color("#5998ff")
    ax2.spines['left'].set_color("#5998ff")
    ax2.spines['right'].set_color("#5998ff")
    ax2.tick_params(axis='x', colors='w')
    ax2.tick_params(axis='y', colors='w')
    plt.ylabel('MACD', color='w')
    ax2.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5, prune='upper'))
    for label in ax2.xaxis.get_ticklabels():
        label.set_rotation(45)


    plt.show()
    i=1
    # https://blog.csdn.net/weixin_34498545/article/details/112631706
    # ax.set_xticklabels(['A','B','C','D','E','F','G'])
    # ax.set_yticklabels(['鉴','图','化','视','可','注','关'],family = 'SimHei',fontsize = 14)


if __name__ == "__main__":
    main()


