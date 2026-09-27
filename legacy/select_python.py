import glob
import os
import shutil
from rich.progress import track
import random
import readline
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
### Description:<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
### This script helps you autoly analyze POSCAR-contained files and extract specified nums you wanna to save as towards future running!<<<<<<<\033[0m
''')
    
show_copyright()
show_userguide()
def find_folders(root_folder,name_flag):
    folders = []  # 用于储存含有 XDATCAR 的子文件夹相对路径
    for folder in glob.glob(os.path.join(root_folder, '**', name_flag), recursive=True):
        relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
        folders.append(relative_path)
    return folders  
def find_index_above_random(random_num, values):
    return next((i for i, value in enumerate(values) if value > random_num), -1)
# 使用Tab键进行自动补全
readline.parse_and_bind("tab: complete")
poscar_dirs_path=input('the file contained with POSCAR which you wanna analyaze:')
nameflag='POSCAR'
poscar_folders=find_folders(poscar_dirs_path,nameflag)
print('there is **',len(poscar_folders),'** POSCARS files in ',poscar_dirs_path,'!!!')
split_flag=input('Do you wanna extract some POSCARS randomly at the number what you want?(y/n)')
if not split_flag=='y' or split_flag=='Y' or split_flag=='yes' or split_flag=='YES' :
    exit()
split_nums= int(input('PLS input the number that  some POSCARS randomly  what you want  extract?'))
split_ratio=split_nums/len(poscar_folders)
saved_dirs_path=input('OK! tell me the extracted POSCAR files location where you wanna save:')

split_dirs_ratio_list = [i * split_ratio for i in range(int(1 / split_ratio) + 1)]
split_dirs_ratio_list[0] = 0
split_dirs_ratio_list[-1] = 1

for poscar_dir in track(poscar_folders,description='poscars_processed:'):
    try:
        random_num = random.uniform(0, 1)
        saved_index=str(find_index_above_random(random_num, split_dirs_ratio_list))
        if not os.path.exists(os.path.join(saved_dirs_path,saved_index,poscar_dir)):
            os.makedirs(os.path.join(saved_dirs_path,saved_index,poscar_dir))
            shutil.copy(os.path.join(poscar_dirs_path,poscar_dir,'POSCAR'),os.path.join(saved_dirs_path,saved_index,poscar_dir,'POSCAR'))
    except:
        print(poscar_dir,'is underprocessing','something must wrong,maybe your poscarfile is empty ,or your dest-dir has no poscar file')

