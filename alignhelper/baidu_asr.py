# -*- coding: utf-8 -*-
# author: kuangdd
# date: 2020/10/13
"""
run
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(Path(__name__).stem)

import requests
import json
import uuid
import base64

_access_token = ''  # 访问接口需要提供的token


def set_value(api_key, secret_key):
    global _access_token
    token = get_token(api_key=api_key, secret_key=secret_key)
    _access_token = token


def get_token(api_key, secret_key):
    url = "https://openapi.baidu.com/oauth/2.0/token"
    data = {'grant_type': 'client_credentials', 'client_id': api_key, 'client_secret': secret_key}
    r = requests.post(url, data=data)
    token = json.loads(r.text).get("access_token")
    return token


def recognize(sig, sr, token):
    """
    {'corpus_no': '6883073753351389860',
    'err_msg': 'success.',
    'err_no': 0,
    'result': ['大家晚上好，我是赵丽颖。'],
    'sn': '181922733721602590492'}
    :param sig:
    :param sr:
    :param token:
    :return:
    """
    url = "http://vop.baidu.com/server_api"
    speech_length = len(sig)
    speech = base64.b64encode(sig).decode("utf-8")
    mac_address = uuid.UUID(int=uuid.getnode()).hex[-12:]
    rate = sr
    data = {
        "format": "wav",
        "lan": "zh",
        "token": token,
        "len": speech_length,
        "rate": rate,
        "speech": speech,
        "cuid": mac_address,
        "channel": 1,
        "dev_pid": 1536,  # 1537则超额
    }
    data_length = len(json.dumps(data).encode("utf-8"))
    headers = {"Content-Type": "application/json",
               "Content-Length": str(data_length)}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    return r.json()


def request_one(fpath, sr=16000, token=''):
    global _access_token
    if token:
        _access_token = token
    try:
        signal = open(fpath, "rb").read()
        out = recognize(signal, sr, _access_token)
        return out
    except Exception as e:
        print(f'Failed! {fpath}')


if __name__ == "__main__":
    import my_secret

    api_key = my_secret.baidu_api_key
    secret_key = my_secret.baidu_secret_key
    filename = r"data\王凯\wangkai\wangkai_0011.wav"
    set_value(api_key=api_key, secret_key=secret_key)
    out = request_one(filename)
    print(out)
