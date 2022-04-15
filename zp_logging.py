
# -*- coding:utf-8 -*-
#! python3

import time
import logging
import colorlog
import logging.handlers

log_colors_config = {
	'DEBUG': 'white',  #cyan white
	'INFO': 'green',
	'WARNING': 'yellow',
	'ERROR': 'red',
	'CRITICAL': 'bold_red',
}

#增加日志库
g_logger = logging.getLogger("logger")

handler1 = logging.StreamHandler()
# handler2 = logging.FileHandler(filename="zen_plot.log", encoding="utf-8")
handler2 = logging.handlers.RotatingFileHandler("zen_plot2.log", mode="a", maxBytes=1024*1024, backupCount=0, encoding="utf-8")

g_logger.setLevel(logging.DEBUG)
handler1.setLevel(logging.DEBUG)
handler2.setLevel(logging.DEBUG)

#%(asctime)s [%(threadName)s:%(thread)d] [%(module)s:%(funcName)s] [%(levelname)s]- %(message)s
console_formatter = colorlog.ColoredFormatter(
	fmt='%(log_color)s[%(asctime)s.%(msecs)03d] [%(funcName)s:%(lineno)d] [%(levelname)s]- [%(message)s]',
	datefmt='%Y-%m-%d %H:%M:%S',
	log_colors=log_colors_config
)
handler1.setFormatter(console_formatter)

formatter = logging.Formatter(
	fmt="[%(asctime)s.%(msecs)03d] [%(thread)d] [%(lineno)d] [%(levelname)s]- [%(message)s]",
	datefmt='%Y-%m-%d %H:%M:%S')
handler2.setFormatter(formatter)

g_logger.addHandler(handler1)
g_logger.addHandler(handler2)

