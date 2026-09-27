# good for use  already!!!
# for initial multi-frame xyz file to autoly  give the POSCAR format file.
import os
import re
import glob
import warnings
from rich.progress import track
import subprocess
import readline
import shutil
from ase.io import read, write

# 通用方式过滤CIF警告（兼容所有ASE版本）
warnings.filterwarnings("ignore", 
                       category=UserWarning,
                       module="ase.io.cif",
                       message=".*crystal system.*")

readline.parse_and_bind("tab: complete")

def find_atomic_files(root_folder):
    """查找所有支持的原子文件（CIF、XYZ、POSCAR、CONTCAR）"""
    atomic_files = []
    # 查找POSCAR和CONTCAR
    for name in ['POSCAR', 'CONTCAR']:
        for file_path in glob.glob(os.path.join(root_folder, '**', name), recursive=True):
            relative_dir = os.path.relpath(os.path.dirname(file_path), root_folder)
            atomic_files.append((file_path, relative_dir))
    # 查找CIF和XYZ文件
    for ext in ['cif', 'xyz']:
        for file_path in glob.glob(os.path.join(root_folder, '**', f'*.{ext}'), recursive=True):
            relative_dir = os.path.relpath(os.path.dirname(file_path), root_folder)
            atomic_files.append((file_path, relative_dir))
    return atomic_files

def check_and_correct_poscar(poscar_path):
    """修正POSCAR第六行格式"""
    with open(poscar_path, 'r+') as file:
        lines = file.readlines()
        if len(lines) >= 6:
            sixth_line = lines[5].strip()
            if re.search(r'[^A-Za-z\s]', sixth_line):
                print(f"\033[31m修正POSCAR格式: {poscar_path}\033[0m")
                corrected_line = ' '.join(re.findall(r'[A-Z][a-z]?', sixth_line))
                lines[5] = corrected_line + '\n'
                file.seek(0)
                file.writelines(lines)
                file.truncate()
                
def is_single_frame_xyz(filename):
    """
    检查XYZ文件是否只包含单帧
    
    参数:
        filename (str): XYZ文件路径
        
    返回:
        bool: 如果是单帧返回True，否则返回False
    """
    try:
        with open(filename, 'r') as f:
            # 读取第一行获取原子数
            first_line = f.readline()
            if not first_line.strip():
                return False  # 空文件
            
            try:
                num_atoms = int(first_line.strip())
            except ValueError:
                print(f"错误: 第一行应该包含原子数，但得到的是: '{first_line.strip()}'")
                return False
                
            if num_atoms <= 0:
                return False
                
            # 跳过注释行
            f.readline()
            
            # 读取原子坐标
            atoms_read = 0
            for line in f:
                if not line.strip():  # 跳过空行
                    continue
                atoms_read += 1
                if atoms_read >= num_atoms:
                    break
            
            # 检查文件是否还有更多内容
            remaining_content = f.read().strip()
            if remaining_content:
                # 尝试检测是否有另一个帧
                try:
                    next_num_atoms = int(remaining_content.split('\n')[0].strip())
                    return False  # 发现第二帧
                except ValueError:
                    pass  # 可能是注释或其他内容
                    
            return True
            
    except FileNotFoundError:
        print(f"错误: 文件 '{filename}' 未找到")
        return False
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")
        return False
    
def process_xyz_to_poscars(input_file, base_output_dir='output', frame_ranges=None, frame_step=1):
    """
    将多帧XYZ文件转换为独立的POSCAR文件
    支持按帧范围选择和帧频率设置
    
    参数:
        input_file: 输入XYZ文件路径
        base_output_dir: 输出目录
        frame_ranges: 帧范围列表，如 [[20,50], [70,80]]
        frame_step: 帧频率（每隔n帧取一帧），默认为1（取所有帧）
    """
    os.makedirs(base_output_dir, exist_ok=True)
    
    # 读取所有帧
    try:
        all_frames = read(input_file, index=':')  # 读取所有帧
    except Exception as e:
        raise ValueError(f"读取XYZ文件失败: {str(e)}")
    
    if not all_frames:
        raise ValueError("XYZ文件中没有有效帧")
    
    total_frames = len(all_frames)
    print(f"检测到总帧数: {total_frames}")
    
    # 验证帧频率参数
    if not isinstance(frame_step, int) or frame_step < 1:
        raise ValueError("帧频率必须为正整数")
    
    # 处理帧范围选择（自动调整超出范围的部分）
    selected_frames = []
    if frame_ranges:
        for start, end in frame_ranges:
            # 调整到有效范围内
            adj_start = max(1, min(start, total_frames))
            adj_end = max(1, min(end, total_frames))
            
            # 确保start <= end
            if adj_start > adj_end:
                adj_start, adj_end = adj_end, adj_start
            
            # 只添加有有效帧的范围（应用帧频率）
            if adj_start <= adj_end:
                print(f"处理帧范围: {adj_start}-{adj_end} (原始输入: {start}-{end}), 帧频率: 每 {frame_step} 帧")
                selected_frames.extend(all_frames[adj_start-1:adj_end:frame_step])
            else:
                print(f"跳过无效范围: {start}-{end}")
    else:
        # 如果没有指定范围，处理全部帧（应用帧频率）
        print(f"处理全部帧 (1-{total_frames}), 帧频率: 每 {frame_step} 帧")
        selected_frames = all_frames[::frame_step]
    
    if not selected_frames:
        raise ValueError("没有有效的帧被选择")
    
    print(f"实际选择帧数: {len(selected_frames)}")
    
    # 为每帧创建独立文件夹并保存POSCAR
    output_dirs = []
    for idx, atoms in enumerate(selected_frames, 1):
        # 创建帧文件夹 (例如 output/frame_001)
        frame_dir = os.path.join(base_output_dir, f'frame_{idx:03d}')
        os.makedirs(frame_dir, exist_ok=True)
        
        # 保存POSCAR文件
        poscar_path = os.path.join(frame_dir, 'POSCAR')
        write(poscar_path, atoms, format='vasp')
        
        output_dirs.append(frame_dir)
    
    return output_dirs

def parse_frame_ranges(frame_str):
    """解析帧范围字符串，如 '20-50,70-80' 转换为 [[20,50], [70,80]]"""
    if not frame_str:
        return None
    
    ranges = []
    for part in frame_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            ranges.append([start, end])
        else:
            frame = int(part)
            ranges.append([frame, frame])
    return ranges
# 用户输入根目录
root_dir = input('请输入包含原子文件的根目录: \n')

# 储存目录saved_dir
saved_dir = input('请输入用于保存处理结果的目录: \n')
if not os.path.exists(saved_dir):
    os.makedirs(saved_dir)
    
# 是否跳过单帧文件
skip_single_flag = input('是否跳过单帧文件(y/n): \n').lower() == 'y'

# 输入frame范围
'''
    输入格式如 --frames 20-50,70-80
    自动转换为 [[20,50], [70,80]] 格式
    支持单帧（如 5）和连续帧范围（如 10-20）
'''
frame_ranges = parse_frame_ranges(input('请输入帧范围(如 20-50,70-80): \n'))
frame_freq = int(input('请输入帧频率(每隔n帧取一帧): \n'))





# 遍历处理所有原子文件
for file_path, rel_dir in track(find_atomic_files(root_dir), description='处理进度:'):
    try:
        # 解析文件名和扩展名
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        ext = ext.lower().lstrip('.')
        print(file_path, rel_dir, base_name, ext)
        if skip_single_flag and is_single_frame_xyz(os.path.join(root_dir, rel_dir, file_name)):
            print(f"\033[33m跳过单帧文件: {file_path}\033[0m")
            continue
        
        
        
        # 创建处理目录（以文件名命名）
        process_dir = os.path.join(saved_dir,rel_dir, f"{base_name}_AIMD")
        print(file_path,process_dir)
        # 在创建目录前添加清理逻辑
        if os.path.isfile(process_dir):  # 如果存在同名文件
            os.remove(process_dir)       # 先删除文件再创建目录
        os.makedirs(process_dir, exist_ok=True)
        
        # 转换文件到POSCAR格式
        dest_poscar = os.path.join(process_dir, 'POSCAR')
        if file_name in ['POSCAR', 'CONTCAR']:
            shutil.copy(file_path, dest_poscar)
        elif ext in ['cif', 'xyz']:
            # 转换多帧XYZ文件到POSCAR
            try:
                saved_dirs = process_xyz_to_poscars(
                    file_path,
                    base_output_dir=process_dir,
                    frame_ranges=frame_ranges,
                    frame_step=frame_freq
                )
                
                print(f"成功转换 {len(saved_dirs)} 帧:")
                for d in saved_dirs:
                    print(f"  - {d}/POSCAR")
            
            except Exception as e:
                print(f"错误: {str(e)}")
                exit(1)
            
        else:
            continue  # 不支持的格式


    except Exception as e:
        print(f"\033[31m处理失败: {file_path}\n错误信息: {str(e)}\033[0m")