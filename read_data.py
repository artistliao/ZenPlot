
# -*- coding:utf-8 -*-
#! python3

from pandas import DataFrame, Series
import pandas as pd
import numpy as np

import time
import sys
import os
import mysql.connector
import pymysql
import sqlalchemy
from sqlalchemy import create_engine

import configparser

from zp_logging import g_logger
from utils import *

#每张图最多画的K线数目
ONE_PLOT_KLINE_NUM=2000

#print("%s:remove watermark end!" % (time.ctime()))
def readKlineData(filepath):
    g_logger.info('readKlineData filepath=%s', filepath)
    file_skiprows = []
    file = open(filepath, encoding = 'utf8')
    idx = -1
    while True:
        idx += 1
        line = file.readline()
        if not line:
            break
        if line.startswith( '20' )==False:
            file_skiprows.append(idx)

    returndata = pd.DataFrame()
    try:
        # rawdata = pd.read_csv(filename, parse_dates = True, index_col = 0, encoding = 'utf8')
        rawdata = pd.read_table(filepath, sep='\t', index_col = False, skiprows=file_skiprows,
                                names=['Date','Time','Open','High','Low','Close', 'Volume'],
                                dtype={'Time': np.str})
    except IOError:
        raise Exception('IoError when reading dayline data file:' + filepath)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    kline_num = len(returndata.index)

    returndata['ModifyDateTime'] = pd.Series(range(kline_num),index = range(kline_num))
    for i in range(kline_num):
        sdate = returndata.loc[i,'Date']
        stime = returndata.loc[i,'Time']
        sdatetime = sdate.replace("/", "", -1).replace("-", "", -1) + stime + "00"
        idatetime = int(sdatetime)
        its = IntTimeToTs(idatetime)
        its -= 60
        idatetime = TsToIntTime(its)
        # sdatetime = str(idatetime)
        # sdatetime = sdatetime[:-2]
        returndata.loc[i, 'ModifyDateTime'] = idatetime
        returndata.loc[i, 'OriginalIndex'] = i

    returndata = returndata.reindex(columns=['Date','Time','Open','High','Low','Close', 'Volume', 'ModifyDateTime', 'OriginalIndex'])
    # returndata = returndata.iloc[0:5000, :]

    return returndata

def readStrokeData(filepath, start_time, end_time):
    g_logger.info('readStrokeData filepath=%s, start_time=%d, end_time=%d', filepath, start_time, end_time)

    returndata = pd.DataFrame()
    try:
        # rawdata = pd.read_csv(filename, parse_dates = True, index_col = 0, encoding = 'utf8')
        rawdata = pd.read_table(filepath, sep='\t', index_col = False,
                                names=['SeqNum','StartKlineIndex','EndKlineIndex','StartTime','EndTime','Volume','Direction','KlineCount', 'High', 'Low', 'Amount'],
                                dtype={'SeqNum': np.int, 'StartKlineIndex': np.int, 'EndKlineIndex': np.int})
    except IOError:
        raise Exception('IoError when reading stroke data file:' + filepath)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    # returndata = returndata[returndata['StartTime']<=end_time]
    # returndata = returndata[returndata['EndTime']>=start_time]
    # returndata.reset_index(drop=True, inplace=True)
    returndata = returndata.reindex(columns=['SeqNum','StartKlineIndex','EndKlineIndex','StartTime','EndTime','Volume','Direction','KlineCount', 'High', 'Low', 'Amount'])

    return returndata

def readLineSegmentData(filepath):
    g_logger.info('readLineSegmentData filepath=%s', filepath)

    returndata = pd.DataFrame()
    try:
        rawdata = pd.read_table(filepath, sep='\t', index_col = False,
                                names=['SeqNum','StartTime','EndTime','StartStrokeIndex','EndStrokeIndex','Volume','Direction','KlineCount', 'High', 'Low', 'Amount'],
                                dtype={'SeqNum': np.int, 'StartStrokeIndex': np.int, 'EndStrokeIndex': np.int})
    except IOError:
        raise Exception('IoError when reading linesegment data file:' + filepath)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    returndata = returndata.reindex(columns=['SeqNum','StartStrokeIndex','EndStrokeIndex','StartTime','EndTime','Volume','Direction','KlineCount', 'High', 'Low', 'Amount'])
    return returndata


def readTrendCentralData(filepath):
    g_logger.info('readTrendCentralData filepath=%s', filepath)

    returndata = pd.DataFrame()
    try:
        rawdata = pd.read_table(filepath, sep='\t', index_col = False,
                                names=['SeqNum','StartStrokeIndex','EndStrokeIndex','TrendType','High','Low','Highest', 'Lowest'],
                                dtype={'SeqNum': np.int, 'StartStrokeIndex': np.int, 'EndStrokeIndex': np.int})
    except IOError:
        raise Exception('IoError when reading TrendCentral data file:' + filepath)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    returndata = returndata.reindex(columns=['SeqNum','StartStrokeIndex','EndStrokeIndex','TrendType','High','Low','Highest', 'Lowest'])
    return returndata

def readOrderData(filepath):
    g_logger.info('readOrderData filepath=%s', filepath)

    returndata = pd.DataFrame()
    try:
        rawdata = pd.read_table(filepath, sep='\t', index_col = False,
                                names=['OrderId','OpenTransTime','OpenTransPrice','CoverTransTime','CoverTransPrice',
                                       'StopLossPrice','Profit','Direction','OpenKlineIdx', 'CoverKlineIdx','IsOpen','IsCover'],
                                dtype={'Direction': np.int, 'OpenKlineIdx': np.int, 'CoverKlineIdx': np.int})
    except IOError:
        raise Exception('IoError when reading TrendCentral data file:' + filepath)

    # Wash data
    returndata = pd.concat([rawdata, returndata])
    returndata = returndata.reindex(columns=['Direction','OpenKlineIdx','CoverKlineIdx'])
    return returndata

#从mysql中读取数据类
class ZenMsData:
    mydb = None
    connect_info = None
    engine = None
    securities_type=''
    gp_securities = dict()
    gp_trade_days = list()
    def __init__(self, securities_type, path):
        self.securities_type = securities_type
        if path=='':
            g_logger.info("ZenMsData init, path is null!")

        try:
            g_logger.info('cfg_path=%s', path)
            cf = configparser.ConfigParser()
            cf.read(path)
            host = cf.get("conf", "host")
            username = cf.get("conf", "username")
            password = cf.get("conf", "password")
            dbname = cf.get("conf", "dbname")
            port = cf.get("conf", "port")
            self.mydb = mysql.connector.connect(
                host=host,
                port=port,
                user=username,
                passwd=password,
                database=dbname
            )
            self.connect_info = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(username, password, host, port, dbname) #1
            self.engine = create_engine(self.connect_info)
        except Exception as e:
            g_logger.warning(str(e))
            g_logger.exception(e)

    def __del__(self):
        self.mydb.close()

    #加载所有的gp代码
    def LoadAllSecurities(self):
        g_logger.info('LoadAllSecurities begin! securities_type=%s', self.securities_type)
        db_name = ''
        if self.securities_type=='stock':
            db_name = 'gp'
        elif self.securities_type=='index':
            db_name='idx'
        elif self.securities_type=='futures':
            db_name='futures'

        mycursor = self.mydb.cursor()
        try:
            sec_sql = "SELECT id, code, start_date, end_date FROM " + db_name + ".securities"
            mycursor.execute(sec_sql)
            # 获取所有记录列表
            results = mycursor.fetchall()
            for row in results:
                oneSecurities = dict()
                oneSecurities['id'] = int(row[0])
                oneSecurities['code'] = row[1]
                oneSecurities['start_date'] = row[2]
                oneSecurities['end_date'] = row[3]
                self.gp_securities[row[1]] = oneSecurities
                # g_logger.debug("code=%s, securities=%s", row[1], str(oneSecurities))
            g_logger.debug("securities length=%d", len(self.gp_securities))
        except Exception as e:
            g_logger.warning(str(e))
            g_logger.exception(e)

    #加载所有的交易日
    def LoadTradeDays(self):
        g_logger.info('LoadTradeDays begin!')
        mycursor = self.mydb.cursor()
        try:
            sec_sql = "SELECT day FROM gp.gp_trade_days ORDER BY day ASC"
            mycursor.execute(sec_sql)
            # 获取所有记录列表
            results = mycursor.fetchall()
            for row in results:
                self.gp_trade_days.append(row[0])

            g_logger.debug("gp_trade_days length=%d", len(self.gp_trade_days))
        except Exception as e:
            g_logger.warning(str(e))
            g_logger.exception(e)

    #加载所有的gp的kline数据
    def LoadSecuritiesKlineData(self, code, period, start_ts):
        g_logger.info('LoadSecuritiesKlineData begin! code=%s, period=%s, start_ts=%d', code, period, start_ts)
        db_name = ''
        if self.securities_type=='stock':
            db_name = 'gp'
        elif self.securities_type=='index':
            db_name='idx'
        elif self.securities_type=='futures':
            db_name='futures'

        #先找出gp_id
        if code not in self.gp_securities:
            g_logger.warning("code:%s not in gp_securities", code)
            return None

        gp_id = self.gp_securities[code]["id"]

        codes = code.split(".")
        if len(codes) != 2:
            g_logger.warning("error code:%s", code)
            return None

        try:
            g_logger.debug("pd.read_sql begin")
            table_name = period + "_prices_" + codes[0][-2:]
            if self.securities_type=='futures':
                table_name = period + "_prices_" + codes[0][0:2]
                table_name = table_name.lower()
            sec_sql = "SELECT CAST(FROM_UNIXTIME(ts, '%%Y%%m%%d%%H%%i%%s') AS UNSIGNED) AS ModifyDateTime, open, high, low, close, volume, money, factor, IFNULL(divergence, 0) as Divergence FROM " + db_name + "." + table_name \
                      + " WHERE gp_id='" + str(gp_id) + "' AND ts>=" + str(start_ts) + " ORDER BY ts ASC"
            df = pd.read_sql(sql=sec_sql, con=self.engine)
            df['OriginalIndex'] = df.index
            df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
            g_logger.debug("pd.read_sql end")

            df = df.reindex(columns=['Open','High','Low','Close', 'Volume', 'Divergence', 'ModifyDateTime', 'OriginalIndex'])
            g_logger.debug("kline length=%d", len(df))
            return df
        except Exception as e:
            g_logger.warning(str(e))
            g_logger.exception(e)
            return None

    #获取gp的kline count
    def GetSecuritiesKlineCount(self, code, period, start_ts):
        g_logger.info('GetSecuritiesKlineCount begin! code=%s, period=%s, start_ts=%d', code, period, start_ts)
        db_name = ''
        if self.securities_type=='stock':
            db_name = 'gp'
        elif self.securities_type=='index':
            db_name='idx'
        elif self.securities_type=='futures':
            db_name='futures'

        #先找出gp_id
        if code not in self.gp_securities:
            g_logger.warning("code:%s not in gp_securities", code)
            return -1

        gp_id = self.gp_securities[code]["id"]

        codes = code.split(".")
        if len(codes) != 2:
            g_logger.warning("error code:%s", code)
            return -1

        mycursor = self.mydb.cursor()
        try:
            table_name = period + "_prices_" + codes[0][-2:]
            if self.securities_type=='futures':
                table_name = period + "_prices_" + codes[0][0:2]
                table_name = table_name.lower()
            sec_sql = "SELECT count(1) FROM " + db_name + "." + table_name + " WHERE gp_id='" + str(gp_id) + "' AND ts>=" + str(start_ts)
            mycursor.execute(sec_sql)
            # 获取所有记录列表
            results = mycursor.fetchall()
            count =0
            for row in results:
                count = int(row[0])
            g_logger.debug("GetSecuritiesKlineCount code=%s, count=%d", code, count)
            return count
        except Exception as e:
            g_logger.warning(str(e))
            g_logger.exception(e)
            return -1


if __name__ == "__main__":

    # dataDir = r"E:\otherdata\stock_data\1min\\"
    #
    # stock_code = sys.argv[1]
    # g_logger.info('stock_code:%s', stock_code)
    #
    # #读取数据
    # file_path = dataDir + "utf8\\" + stock_code[:2] + "#" + stock_code[2:] + ".txt"
    # returndata = readKlineData(file_path)
    # left_data_len = len(returndata.index)
    # g_logger.debug("left_data_len=%d", left_data_len)
    #
    # file_path = dataDir + "stroke\\" + stock_code + ".txt"
    # strokes = readStrokeData(file_path)
    # strokes_len = len(strokes.index)
    # g_logger.debug("strokes_len=%d", strokes_len)
    #
    # file_path = dataDir + "line_segment\\" + stock_code + ".txt"
    # lines = readLineSegmentData(file_path)
    # lines_len = len(lines.index)
    # g_logger.debug("lines_len=%d", lines_len)
    #
    # file_path = dataDir + "trend_central\\" + stock_code + ".txt"
    # trend_centrals = readTrendCentralData(file_path)
    # trend_centrals_len = len(trend_centrals.index)
    # g_logger.debug("trend_centrals_len=%d", trend_centrals_len)

    zen_ms_data = ZenMsData('index', 'config.ini')
    zen_ms_data.LoadAllSecurities()
    zen_ms_data.LoadSecuritiesKlineData('000001.XSHG')


