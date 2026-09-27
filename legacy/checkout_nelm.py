import os
import re
import argparse

import os
import re

def check_outcar_and_contcar(base_dir, nelm_value=60):
    # 遍历给定的文件夹及其所有子文件夹
    for root, dirs, files in os.walk(base_dir):
        # 判断子文件夹中是否有OUTCAR文件
        if 'OUTCAR' in files:
            outcar_path = os.path.join(root, 'OUTCAR')
            contcar_path = os.path.join(root, 'CONTCAR')
            # 判断是否有CONTCAR文件
            if os.path.exists(contcar_path):
                # 打开OUTCAR文件，检查最后一次电子步数是否达到了NELM值
                last_iteration_steps = 0
                with open(outcar_path, 'r') as f:
                    # 标记是否找到关键行
                    found_timing_info = False
                    for line in f:
                        # 查找OUTCAR文件是否完整
                        if re.search(r"General timing and accounting informations for this job", line):
                            found_timing_info = True
                        # 查找电子步数信息，格式如 "Iteration 1(39)"
                        match = re.search(r"Iteration\s+\d+\(\s*(\d+)\)", line)
                        if match:
                            # 提取当前行中的电子步数
                            current_step = int(match.group(1))
                            last_iteration_steps = current_step  # 更新为最后一次的电子步数
                    if not found_timing_info:
                        print(f"OUTCAR文件不完整：Directory: {root}")
                
                # 如果最后一次电子步数达到了NELM值，输出文件目录
                if last_iteration_steps >= nelm_value:
                    print(f"达到NELM值的目录：{root}")
            else:
                print(f"不存在CONTCAR文件：Directory: {root}")
        else:
            print(f"不存在OUTCAR文件：Directory: {root}")

        
if __name__ == "__main__":
    # 使用argparse库解析命令行参数
    parser = argparse.ArgumentParser(description="Check OUTCAR files for convergence.")
    parser.add_argument('-i', '--input', default='.', help="Input directory to search for OUTCAR and CONTCAR files")   # 查找的文件夹，默认为当前文件夹
    parser.add_argument('-n', '--nelm', type=int, default=60, help="NELM value to check against (default is 60)")

    args = parser.parse_args()

    check_outcar_and_contcar(args.input, args.nelm)
