import os
import glob
import shutil
from rich.progress import track
import readline
import random
readline.parse_and_bind("tab: complete")
def show_copyright():
        copyright_info='''
\033[34m
Copyright (c) [2023_0823] [Zemeng Feng]\033[1m\033[32m

███████╗███████╗███╗   ███╗███████╗███╗   ██╗ ██████╗     ███████╗███████╗███╗   ██╗ ██████╗ 
╚══███╔╝██╔════╝████╗ ████║██╔════╝████╗  ██║██╔════╝     ██╔════╝██╔════╝████╗  ██║██╔════╝ 
  ███╔╝ █████╗  ██╔████╔██║█████╗  ██╔██╗ ██║██║  ███╗    █████╗  █████╗  ██╔██╗ ██║██║  ███╗
 ███╔╝  ██╔══╝  ██║╚██╔╝██║██╔══╝  ██║╚██╗██║██║   ██║    ██╔══╝  ██╔══╝  ██║╚██╗██║██║   ██║
███████╗███████╗██║ ╚═╝ ██║███████╗██║ ╚████║╚██████╔╝    ██║     ███████╗██║ ╚████║╚██████╔╝
╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝ ╚═════╝     ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ 
\033[0m\033[33m
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", 1WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
\033[36m
Author: Zemeng Feng 
Email: alanakakuki123@gmail.com
Source: Kui Xu Group 
Funding Support: National Youth Fund
Affiliation: College of Flexible Electronics (Future Technologies), Nanjing Tech University, Nanjing, Jiangsu, China\033[0m'''
        print(copyright_info)
    
def show_userguide():
    print('''\n\033[35m
### Description:<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
### This script helps you autoly rerun jobs form failed dirs<<<<<<<<<<<<<\033[0m
''')
def find_folders(root_folder,name_flag):
    folders = []  # 用于储存含有 XDATCAR 的子文件夹相对路径
    for folder in glob.glob(os.path.join(root_folder, '**', name_flag), recursive=True):
        relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
        folders.append(relative_path)
    return folders  

outcar_dirs_path=input('the file contained with OUTCAR which you wanna extract and split and save them to a new dir:\n')
split_partion=tuple(map(float,input('PLS tell me the partion you wanna split about outcars [TRAINING SET:TEST SET](suggested DEFAULT=9,1)').split()))
if all(isinstance(item, tuple) and len(item) == 2 or isinstance(item, float) for item in split_partion):
    print('PLS input reasonable numbers ,It has been cofigurated default values!>>> [TRAINING SET:TEST SET](suggested DEFAULT=9,1)')
    split_partion=(9.0,1.0)
saved_dirs_path=input('the splitted OUTCARs path you want to save:\033[33mOnce confirmed,Jobs start!!!\033[0m\n')
nameflag='OUTCAR'

train_sum=0
test_sum=0
for outcar_dir in track(find_folders(root_folder=outcar_dirs_path,name_flag=nameflag),description='outcars_processed:'):
    try:
        outcar_dir_path=os.path.join(outcar_dirs_path,outcar_dir)
        outcar_path=os.path.join(outcar_dir_path,'OUTCAR')
        train_outcar_path=os.path.join(saved_dirs_path,'train',outcar_dir,'OUTCAR')
        test_outcar_path=os.path.join(saved_dirs_path,'test',outcar_dir,'OUTCAR')
        train_outcar_dirpath=os.path.dirname(train_outcar_path)
        test_outcar_dirpath=os.path.dirname(test_outcar_path)
        if os.path.exists(outcar_path):
            if random.uniform(0,1)>=(split_partion[1]/(split_partion[1]+split_partion[0])):
                if not os.path.exists(train_outcar_dirpath):
                    os.makedirs(train_outcar_dirpath)
                shutil.copy(outcar_path,train_outcar_path)
                train_sum+=1
                print(f'\33[7m{train_sum}\33[0m:{train_outcar_path} has been added to \033[33mTRAINING SET!!!\033[0m')
            else:
                if not os.path.exists(test_outcar_dirpath):
                    os.makedirs(test_outcar_dirpath)
                shutil.copy(outcar_path,test_outcar_path)
                test_sum+=1
                print(f'\33[7m{test_sum}\33[0m:{test_outcar_path} has been added to \033[34mTESTING SET!!!\033[0m')
        else:
            print(f'\033[31m{outcar_path} has been not found !!!\033[0m')
    except Exception as e:
        # 捕获异常并打印错误信息
        print(f"\033[33m>>>Something abnormal has happened,error info : \033[31m{e}\033[0m")