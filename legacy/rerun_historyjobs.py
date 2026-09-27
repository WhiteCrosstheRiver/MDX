import os
import glob
import re
from rich.progress import track
import readline

# 配置 readline 自动补全功能
readline.parse_and_bind("tab: complete")

def show_copyright():
    copyright_info = '''
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
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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
### This script helps you automatically rerun jobs from failed directories<<<<<<<<<<<<<\033[0m
''')

def find_folders(root_folder, name_flag):
    folders = []  # 用于存储含有 POSCAR 的子文件夹相对路径
    for folder in glob.glob(os.path.join(root_folder, '**', name_flag), recursive=True):
        relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
        folders.append(relative_path)
    return folders  

def check_and_correct_poscar(poscar_path):
#有些极端情况，出来的POSCAR的元素带上了电荷，但是VASP识别不了这个QAQ
    with open(poscar_path, 'r+') as file:
        lines = file.readlines()
        if len(lines) >= 6:
            sixth_line = lines[5].strip()
            # 检查第六行的格式是否为有效的元素符号（例如 "Si F"）
            if re.search(r'[^A-Za-z\s]', sixth_line):
                # 使用红色高亮打印输出
                print(f"\033[31mInvalid element format in POSCAR at {poscar_path}. Correcting it...\033[0m")
                # 替换非标准格式（如 "Si4+"）为标准元素符号（如 "Si"）
                corrected_line = ' '.join(re.findall(r'[A-Z][a-z]?', sixth_line))
                lines[5] = corrected_line + '\n'
                # 重新写入文件
                file.seek(0)
                file.writelines(lines)
                file.truncate()
                

def is_converged(outcar_file):
    """
    检查OUTCAR是否收敛
    """
    try:
        with open(outcar_file, 'r') as f:
            content = f.read()
            if "reached required accuracy" in content:
                return True
            if "aborting loop because EDIFF is reached" in content:
                return True
        return False
    except:
        return False

poscar_dirs_path = input('Enter the directory containing POSCAR files to restart VASP jobs:\033[33mOnce confirmed, Jobs will start!!!\033[0m\n')
name_flag = 'POSCAR'

for poscar_dir in track(find_folders(root_folder=poscar_dirs_path, name_flag=name_flag), description='Processing POSCARs:'):
    try:
        poscar_dir_path = os.path.join(poscar_dirs_path, poscar_dir)
        poscar_path = os.path.join(poscar_dir_path, 'POSCAR')
        outcar_path = os.path.join(poscar_dir_path, "OUTCAR")
        incar_path = os.path.join(poscar_dir_path, 'INCAR')
        

        if os.path.exists(outcar_path):
            with open(outcar_path, "r") as file:
                content = file.read()
                if "General timing and accounting informations for this job" in content:
                #先看看OUTCAR有没有计算完毕
                    print(f'>>>Address: {poscar_dir_path} >>>\033[32mJob already finished, no need to rerun!\033[0m')
                    if "aborting loop EDIFF was not reached (unconverged)" in content:
                        # 修改INCAR文件增加nelm步数
                        print(f'>>>Address: {poscar_dir_path} >>>\033[33mUnconverged job detected! Modifying INCAR...\033[0m')
                        
                        # 读取并修改INCAR文件
                        with open(incar_path, 'r') as incar_file:
                            lines = incar_file.readlines()
                        
                        new_lines = []
                        nelm_found = False
                        for line in lines:
                            # 处理NELM参数行（不区分大小写）
                            if line.strip().upper().startswith('NELM'):
                                nelm_found = True
                                # 提取当前NELM值并增加400
                                try:
                                    current_nelm = int(line.split('=')[1].split(';')[0].strip())
                                    new_nelm = current_nelm + 400
                                    new_line = f"NELM = {new_nelm}  ; increased by 400\n"
                                    new_lines.append(new_line)
                                    print(f'  Updated NELM: {current_nelm} -> {new_nelm}')
                                except (IndexError, ValueError):
                                    # 格式错误时使用默认增量
                                    new_lines.append("NELM = 460  ; default increment\n")
                            else:
                                new_lines.append(line)
                        
                        # 若未找到NELM参数则新增
                        if not nelm_found:
                            new_lines.append("\nNELM = 460  ; added for convergence\n")
                            print('  Added new NELM parameter: 460')
                        
                        # 写入修改后的INCAR
                        with open(incar_path, 'w') as incar_file:
                            incar_file.writelines(new_lines)
                        
                        print(f'>>>Address: {poscar_dir_path} >>>\033[36mINCAR updated. Ready for resubmission.\033[0m')
                        sixth_line = os.popen(f"sed -n '6p' '{poscar_path}'").read().strip()
                        os.system(f"cd '{poscar_dir_path}' && qvasp -pbe {sixth_line} && sbatch runvasp.sh")
                else:
                #检查是不是POSCAR的格式问题
                    print(f'>>>Address: {poscar_dir_path} >>>\033[33mJob failed halfway, now rerunning!\033[0m')
                    # 检查并修正POSCAR的第六行
                    check_and_correct_poscar(poscar_path)
                    sixth_line = os.popen(f"sed -n '6p' '{poscar_path}'").read().strip()
                    
                    if "Inconsistent Bravais lattice types found for crystalline and" in content or "internal error in subroutine INVGRP" in content: 
                    #检查SYMPREC参数是否有误，如果是，加上SYMPREC = 1e-6
                        with open(incar_path, 'r+') as f:
                            lines = f.readlines()
                            # 检查是否已有SYMPREC设置
                            has_symprec = any('SYMPREC' in line for line in lines)
                            # 如果没有则添加
                            if not has_symprec:
                                f.seek(0, 2)  # 移动到文件末尾
                                f.write("\nSYMPREC = 1e-6\n")
                                print("   Added SYMPREC = 1e-6 to INCAR")
                            else:
                                print("   SYMPREC already exists in INCAR")
                                
                    os.system(f"cd '{poscar_dir_path}' && qvasp -pbe {sixth_line} && sbatch runvasp.sh")
        else:
            print(f'>>>Address: {poscar_dir_path} >>>\033[31mJob has not started, now starting!\033[0m')
            # 检查并修正POSCAR的第六行
            check_and_correct_poscar(poscar_path)
            sixth_line = os.popen(f"sed -n '6p' '{poscar_path}'").read().strip()
            os.system(f"cd '{poscar_dir_path}' && qvasp -pbe {sixth_line} && sbatch runvasp.sh")

    except Exception as e:
        print(f"{poscar_dir} is under processing. Something went wrong, maybe your POSCAR file is empty or your destination directory has no POSCAR file. Error: {e}")
