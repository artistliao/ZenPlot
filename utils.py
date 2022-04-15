
# -*- coding:utf-8 -*-
#! python3

import time
import sys
import os


def IntTimeToTs(starttime):
    tm_year = starttime // 10000000000
    tm_mon  = (starttime % 10000000000) //100000000
    tm_mday = (starttime % 100000000) // 1000000
    tm_hour = (starttime % 1000000) // 10000
    tm_min  = (starttime % 10000) // 100
    tm_sec  = (starttime % 100)
    tm_isdst = 0
    t = (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, 0, 0, 0)
    ts = int(time.mktime(t))
    return ts

def TsToIntTime(ts):
    if (ts < 0):
        return -1

    tm = time.localtime(ts)
    #time.struct_time(tm_year=2016, tm_mon=4, tm_mday=7, tm_hour=10, tm_min=3, tm_sec=27, tm_wday=3, tm_yday=98, tm_isdst=0)

    iTime = tm.tm_year * 10000000000
    iTime += tm.tm_mon * 100000000
    iTime += tm.tm_mday * 1000000
    iTime += tm.tm_hour * 10000
    iTime += tm.tm_min * 100
    iTime += tm.tm_sec
    return iTime


def FloatCmp(number1, number2):
    diff = number1-number2
    if (diff > 0.000001):
        return 1

    if (diff < -0.000001):
        return -1

    return 0

if __name__ == "__main__":
    print(FloatCmp(0.001, 0.001))

