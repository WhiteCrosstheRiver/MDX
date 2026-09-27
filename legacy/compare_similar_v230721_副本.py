#!/home/gjwang-ICME/software/anaconda3/envs/mpmv/bin/python -u
#   coding:utf-8
#   This file is part of Alkemiems.
#
#   Alkemiems is free software: you can redistribute it and/or modify
#   it under the terms of the MIT License.

__author__ = 'Guanjie Wang'
__email__ = "gjwang@buaa.edu.cn"
__version__ = 1.0
__init_date__ = '2023/07/14 07:59:43'
__maintainer__ = 'Guanjie Wang'
__update_date__ = '2023/07/14 07:59:43'

import argparse
import logging
import math
import os
import random
import shutil
import subprocess
from pathlib import Path

import tqdm
from pymatgen.analysis.structure_matcher import StructureMatcher

from gpymatgen.alk_pymatgen.alkstructure import AlkeStructure

logger = logging.getLogger(__file__)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


def run_core(directory='./', bs=1000, prefix='S', cir=0):
    """
    比较指定目录下所有POSCAR中的重复或者相似的结构
    相似的结构只会保留数字索引较小的一个，其他移动到指定目录下的SimilarStruc_*文件中
    
    :param directory: 指定目录位置
    :param bs: 每次比较多少个，考虑到效率，分批比较
    :param prefix: poscar前缀
    :param cir: 循环次数
    :return: None
    """
    matcher = StructureMatcher(ltol=0.5, stol=0.5, angle_tol=5,
                               primitive_cell=True, scale=False,
                               attempt_supercell=False, allow_subset=False)
    
    directory = Path(os.path.abspath(directory))
    repeat_file = Path(os.path.join(directory, 'SimilarStruc_%s' % Path(directory).name))
    all_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    
    if not os.path.exists(repeat_file):
        os.mkdir(repeat_file)
    
    def random_select_files(all_file, batch_size):
        # 获取所有文件
        random.shuffle(all_file)
        
        # 分批次随机选择文件
        for aa in range(0, len(all_file), batch_size):
            yield all_file[aa:aa + batch_size]
    
    _t = math.ceil(len(all_files) / bs)
    for batch in tqdm.tqdm(random_select_files(all_file=all_files, batch_size=bs),
                           total=_t, desc='  Match similar %s' % _t):
        all_struc = []
        for i in batch:
            if i.startswith(prefix):
                _fn = Path(os.path.join(directory, i))
                struc = AlkeStructure.from_file(_fn, fmt='POSCAR')
                struc.filename = _fn
                all_struc.append(struc)
        
        a = matcher.group_structures(all_struc)
        logger.info('input strucs: %d.  no similar strucs: %d' % (bs, len(a)))
        for i in a:
            _save_fn = i[0].filename.name[-5:]
            if len(i) > 1:
                for mm in i[1:]:
                    _now_fn = mm.filename
                    gogal_name = "Cir%sSim%s_%s" % (str(cir).zfill(2), _save_fn, _now_fn.name)
                    shutil.move(_now_fn, os.path.join(directory, repeat_file, gogal_name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-d', '--dir', type=str, default='./gpuc300', help='dir path')
    parser.add_argument('-b', '--bs', type=int, default=50, help='batch size')
    parser.add_argument('-p', '--prefix', type=str, default='POSCAR', help='pocar prefix name')
    _args = parser.parse_args()
    
    _directory = os.path.abspath(_args.dir)
    _bs = int(_args.bs)
    _prefix = _args.prefix
    
    result2 = subprocess.run('ls %s | wc -l' % _directory, shell=True, stdout=subprocess.PIPE)
    _all_files = int(result2.stdout.decode('utf-8'))
    _n = math.ceil(_all_files / _bs) * 5
    
    for nn in tqdm.trange(_n, desc='Cir %d' % _n):
        run_core(directory=_directory, bs=_bs, prefix=_prefix, cir=nn)
