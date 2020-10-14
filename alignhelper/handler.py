# -*- coding: utf-8 -*-
# author: kuangdd
# date: 2020/10/12
"""
handler

* 音频处理。
    + 音频格式转换。
    + 调整音频采样率。
    + 调整音频声道数。
    + 调整音频bit。
    + 音频降噪。
    + 用aukit工具。
* 音频切分。
    + 把音频切分为时长较短的多段音频。
    + 按照音频停顿时长切分。
    + 切分的音频时长在25秒以内。
    + 切分的音频时长分布较均匀。
    + 用aukit工具。
* 语音识别。
    + 把语音识别为文字。
    + 用讯飞语音识别接口识别。
    + 用阿里云语音识别接口识别。
    + 用百度语音识别接口识别。
* 拼音标注。
    + 标注多音字的拼音。
    + 用pypinyin标注。
    + 用其他拼音标注方法标注。

注意：my_secret模块是自己存放账号密码的脚本。
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(Path(__name__).stem)

import json
import os
import re
from tqdm import tqdm

import pydub
import pydub.silence

import phkit

from xunfei_asr import request_one as request_one_xunfei, set_value as set_value_xunfei, convert_result
from baidu_asr import request_one as request_one_baidu, set_value as set_value_baidu

duoyinzi = set('的了有中和大个为地会们要发说作经家行得过着可能同长那分好种都还重与当合场化看体其没将员把区济正无只间'
               '万提各并华度通应相见系教期解强任量术给拉结论什几委别少处车更南调省打据格数思广干难研革色台传价观王服'
               '育边参识单便转亲夫约查创厂切写空划觉且兴节阿语纪石乐仅供采片落红呢称曾尽率令读校著食模号占派底似卡待'
               '排斗吗吧担监属奇沙哈胜父答适朝句倒角降否般陆藏哪假差宁核')


def convert_audio(inpath, outpath):
    """音频预处理，音频标准化设置。"""
    aud = pydub.AudioSegment.from_file(inpath)
    aud = aud.set_channels(1)
    aud = aud.set_frame_rate(16000)
    aud = aud.set_sample_width(2)
    aud.export(outpath, format='mp3')


def remove_noise_audio(inpath, outpath):
    """音频降噪。"""
    import aukit
    wav = aukit.load_wav(inpath, sr=16000)
    out = aukit.remove_noise(wav, sr=16000)
    aukit.save_wav(out, outpath, sr=16000)


def split_audio(inpath, outdir, out_format='wav'):
    """音频切分。"""
    aud = pydub.AudioSegment.from_file(inpath)
    outs = pydub.silence.split_on_silence(aud, min_silence_len=1000, silence_thresh=-30, keep_silence=500)
    for num, out in enumerate(tqdm(outs), 1):
        outpath = os.path.join(outdir, f'{Path(inpath).stem}_{num:04d}.{out_format}')
        out.export(outpath, format=out_format)


def get_fpaths_to_asr(indir, inpath, audio_format='wav'):
    """获取需要语音合成的语音路径，如果已经合成过的则跳过。"""
    success_fpaths = set()
    if Path(inpath).is_file():
        fin = open(inpath, encoding='utf8')
        for line in fin:
            content = line.strip()
            if not content:
                continue
            parts = content.split('\t')
            if len(parts) == 2:
                idx, han = parts
            else:
                continue
            success_fpaths.add(idx)

    outs = []
    for fpath in tqdm(sorted(Path(indir).glob(f"*.{audio_format}"))):
        fpath = str(fpath).replace('\\', '/')
        if fpath not in success_fpaths:
            outs.append(fpath)
    return outs


def asr_audio_xunfei(fpaths, outpath):
    """给切分后的音频进行语音识别，获取每个音频对应的文本。用讯飞语音识别接口。"""
    from alignhelper import my_secret

    appid = my_secret.xunfei_appid
    apikey = my_secret.xunfei_apikey
    apisecret = my_secret.xunfei_apisecret

    open_file = open(outpath, 'at', encoding='utf8')

    set_value_xunfei(appid=appid, apikey=apikey, apisecret=apisecret, outfile=open_file)

    for fpath in tqdm(fpaths):
        request_one_xunfei(str(fpath))

    open_file.close()


def asr_audio_baidu(fpaths, outpath):
    """给切分后的音频进行语音识别，获取每个音频对应的文本。用百度语音识别接口。"""
    from alignhelper import my_secret

    api_key = my_secret.baidu_api_key
    secret_key = my_secret.baidu_secret_key

    set_value_baidu(api_key=api_key, secret_key=secret_key)
    outs = []
    for fpath in tqdm(fpaths):
        aud = pydub.AudioSegment.from_file(fpath)
        temp_path = str(Path(outpath).parent.joinpath('temp.wav'))
        aud.export(temp_path, format='wav')
        kw = {'rate': aud.frame_rate, 'format': 'wav'}
        out = request_one_baidu(fpath=temp_path, kwargs=kw)
        # {'corpus_no': '6883077129149798401', 'err_msg': 'success.', 'err_no': 0,
        # 'result': ['大家晚上好，我是赵丽颖。'], 'sn': '204604149221602591278'}
        if out and 'result' in out:
            if len(out['result']) >= 2:
                print(fpath, out['result'])
            text = ''.join(out['result'])
            line = f'{fpath}\t{text}\n'
            outs.append(line)
        else:
            print(fpath, out)
            text = ''
            line = f'{fpath}\t{text}\n'
            outs.append(line)

    with open(outpath, 'wt', encoding='utf8') as fout:
        for line in sorted(outs):
            fout.write(line)


def convert_json_to_text(inpath, outpath):
    """把语音识别的文本转为一个音频对应一条文本。"""
    fin = open(inpath, encoding='utf8')
    outs = []
    idx = ''
    out = []
    error_flag = False
    for line in tqdm(fin):
        content = line.strip()
        if not content:
            continue
        dt = json.loads(content)
        if 'audiofile' in dt:
            if not error_flag:
                text = ''.join(out)
                outs.append(f'{idx}\t{text}\n')
            else:
                text = ''
                outs.append(f'{idx}\t{text}\n')
                print(f'Error! {idx}')
            idx = dt['audiofile']
            out = []
            error_flag = False
        else:
            if dt['code'] == 0:
                out.append(convert_result(content))
            else:
                error_flag = True

    else:
        if not error_flag:
            text = ''.join(out)
            outs.append(f'{idx}\t{text}\n')
        else:
            text = ''
            outs.append(f'{idx}\t{text}\n')
            print(f'Error! {idx}')

    with open(outpath, 'wt', encoding='utf8') as fout:
        for line in sorted(outs):
            fout.write(line)


def pinyin_the_text(inpath, outpath):
    """给文本中的多音字注音。"""
    fin = open(inpath, encoding='utf8')
    outs = []
    for line in tqdm(fin):
        content = line.strip()
        if not content:
            continue
        parts = content.split('\t')
        if len(parts) == 2:
            idx, han = parts
        else:
            continue
        pin = phkit.text2pinyin(han, errors=lambda x: list(x))
        tmp = []
        assert len(han) == len(pin)
        for h, p in zip(han, pin):
            if h in duoyinzi:
                tmp.append(f'{h}【{p}】')
            else:
                tmp.append(h)
        out_text = ''.join(tmp)
        outs.append(f'{idx}\t{out_text}\n')

    with open(outpath, 'wt', encoding='utf8') as fout:
        for line in outs:
            fout.write(line)


def convert_ann_to_ssml(inpath, outpath):
    """
    ann格式：来 和【he2】 大【da4】家【jia1】 交流 。
    SSML格式：
    1.文本首尾分别是：<speak>、</speak>
    2.拼音标注格式：<phoneme alphabet="py" ph="pin1 yin1">拼音</phoneme>
    3.样例：
    <speak><phoneme alphabet="py" ph="gan4 ma2 a5 ni3">干嘛啊你</phoneme><phoneme alphabet="py" ph="you4 lai2">又来</phoneme><phoneme alphabet="py" ph="gou1 da5 shei2">勾搭谁</phoneme>。</speak>
    """
    _ann_re = re.compile(r'(.)【(.+?)】')

    def ann2ssml(text):
        out = _ann_re.sub(r'<phoneme alphabet="py" ph="\2">\1</phoneme>', text)
        out = f'<speak>{out}</speak>'
        return out

    name_pinyin = Path(inpath).stem.split('_')[0]
    outs = []
    if Path(inpath).is_file():
        fin = open(inpath, encoding='utf8')
        for line in tqdm(fin):
            content = line.strip()
            if not content:
                continue
            parts = content.split('\t')
            if len(parts) == 2:
                idx, han = parts
            else:
                continue
            if han.startswith('#'):
                continue

            out = ann2ssml(han)
            outs.append(f'{idx}\t{out}\t{name_pinyin}\n')

    with open(outpath, 'wt', encoding='utf8') as fout:
        for line in outs:
            fout.write(line)


def run_local():
    """运行示例。"""
    name = '赵丽颖'
    name_pinyin = 'zhaoliying'
    datadir = '../data'
    Path(datadir).mkdir(exist_ok=True)

    # 用各种方法给原始音频降噪、去除背景音乐等操作，得到只有人说话声音的音频文件

    # 音频文件规范化格式。
    inpath = f'{datadir}/{name}/【赵丽颖】小小英雄梦.m4a'
    outpath = f'{datadir}/{name}/{name_pinyin}.mp3'
    # convert_audio(inpath, outpath)

    # 切分音频。
    inpath = f'{datadir}/{name}/{name_pinyin}.mp3'
    outdir = f'{datadir}/{name}/{name_pinyin}'
    Path(outdir).mkdir(exist_ok=True)
    # split_audio(inpath, outdir, out_format='mp3')

    # input('继续执行请Enter...')

    # 获取需要做语音识别的语音文件路径。因为语音识别会有失败情况，故可能需要多次识别，已经识别成功的则不再重复识别。
    indir = f'{datadir}/{name}/{name_pinyin}'
    inpath = f'{datadir}/{name}/{name_pinyin}_info.csv'
    fpaths = get_fpaths_to_asr(indir, inpath, audio_format='mp3')

    # 用讯飞的语音识别接口把语音转为文本。
    # outpath = f'{datadir}/{name}/{name_pinyin}_json.txt'
    # asr_audio_xunfei(fpaths, outpath)
    #
    # inpath = f'{datadir}/{name}/{name_pinyin}_json.txt'
    # outpath = f'{datadir}/{name}/{name_pinyin}_info.csv'
    # convert_json_to_text(inpath, outpath)

    # 用百度的语音识别接口把语音转为文本。
    outpath = f'{datadir}/{name}/{name_pinyin}_info.csv'
    asr_audio_baidu(fpaths, outpath)

    # 标注多音字的默认拼音。
    inpath = f'{datadir}/{name}/{name_pinyin}_info.csv'
    outpath = f'{datadir}/{name}/{name_pinyin}_info_pinyin.csv'
    pinyin_the_text(inpath, outpath)

    # 人工核对文本和语音是否一一对应，核对文字是否正确、拼音是否正确、标点符号是否正确，人工修改文本以适配语音。

    # 把核对过的文本转为SSML的格式。
    inpath = f'{datadir}/{name}/{name_pinyin}_info_pinyin_check.csv'
    outpath = f'{datadir}/{name}/{name_pinyin}_ssml.txt'
    convert_ann_to_ssml(inpath, outpath)


if __name__ == "__main__":
    print(__file__)
    run_local()
