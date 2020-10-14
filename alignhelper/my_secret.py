# -*- coding: utf-8 -*-
# author: kuangdd
# date: 2020/10/14
"""
my_secret
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(Path(__name__).stem)

# 百度语音识别
baidu_api_key = ''
baidu_secret_key = ''

# 讯飞语音识别
xunfei_appid = ''
xunfei_apikey = ''
xunfei_apisecret = ''

if __name__ == "__main__":
    print(__file__)
