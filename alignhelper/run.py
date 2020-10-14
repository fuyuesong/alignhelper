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

import os
import re
import json
import shutil
import collections as clt
from functools import partial
from multiprocessing.pool import Pool

import numpy as np
from tqdm import tqdm


def resample_data(inpath, outpath):
    spk_line_dt = clt.defaultdict(list)
    for line in open(inpath, encoding='utf8'):
        spk = line.strip().split('\t')[-1]
        spk_line_dt[spk].append(line)

    n_per = 5
    outs = []
    for num, (spk, lines) in enumerate(spk_line_dt.items()):
        si = ((num + 1) * n_per) % len(lines)
        ei = si + n_per
        tmp = lines[si: ei]
        if ei > len(lines):
            tmp.extend(lines[: ei - len(lines)])
        outs.extend(tmp)

    with open(outpath, 'wt', encoding='utf8') as fout:
        for line in outs:
            fout.write(line)


if __name__ == "__main__":
    inpath = 'data/train.txt'
    outpath = 'data/validation.txt'
    resample_data(inpath, outpath)
