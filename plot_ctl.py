
# -*- coding:utf-8 -*-
#! python3

import datetime as dt
import pylab
import talib
import pytz
import tzlocal
import time
import sys
import os
from zp_logging import g_logger
from read_data import *
from utils import *

if __name__ == "__main__":

    # levels = ['1min', '3min', '5min', '15min', '30min']
    # levels = ['5min', '15min', '30min']
    levels = ['1min']
    # stocks = ['000001.XSHG','000002.XSHG','000003.XSHG','000004.XSHG','000005.XSHG','000006.XSHG','000007.XSHG','000008.XSHG','000009.XSHG','000010.XSHG']
    stocks = ['RB8888.XSGE']

    zen_ms_data = ZenMsData('futures', 'config.ini')
    zen_ms_data.LoadAllSecurities()

    bStart = False
    for stock_code in stocks:
        # if stock_code=="SH600438":
        #     bStart = True
        # # bStart = True
        #
        # if bStart==False:
        #     continue
        for level in levels:
            g_logger.info("stock_code=%s, level=%s start", stock_code, level)
            all_count = zen_ms_data.GetSecuritiesKlineCount(stock_code, level, 1577808000)
            g_logger.info("all_count=%d", all_count)
            offset = 0
            plot_count = 10
            while(all_count>offset*ONE_PLOT_KLINE_NUM):
                str_cmd = 'python zen_plot2.py ' + stock_code + ' ' + level + ' ' + str(offset) + ' ' + str(plot_count)
                g_logger.info(str_cmd)
                os.system(str_cmd)
                offset += plot_count
                time.sleep(3)
                # break


