import os
import glob
import argparse
import re
from ase import io
from tqdm import tqdm
import multiprocessing
from functools import partial
import numpy as np
from ase import Atoms
from ase.units import GPa

def read_outcar_with_full_info(outcar_path):
    """
    从OUTCAR中读取完整信息：原子位置、力、应力、能量和晶胞
    
    参数:
        outcar_path: OUTCAR文件路径
        
    返回:
        ase.Atoms对象（包含力、应力、能量信息）
    """
    # 初始化变量
    positions = []
    forces = []
    stress = None
    energy = None
    lattice = None
    symbols = []
    atom_count = 0
    volume = None
    
    # 标志变量
    in_force_section = False
    skip_next_line = False
    found_atom_count = False
    in_stress_section = False
    
    with open(outcar_path, 'r') as outcar:
        lines = outcar.readlines()
        for i, line in enumerate(lines):
            # 读取晶胞信息
            if "direct lattice vectors" in line:
                lattice = []
                # 读取接下来的三行晶胞向量
                for j in range(1, 4):
                    vec_line = lines[i+j]
                    parts = vec_line.split()
                    lattice.append([float(parts[0]), float(parts[1]), float(parts[2])])
            
            # 读取原子类型和数量
            if "ions per type" in line:
                parts = line.split("=")
                if len(parts) > 1:
                    atom_counts = list(map(int, parts[1].split()))
                    atom_count = sum(atom_counts)
            
            # 读取原子符号
            if "POTCAR:" in line and "PAW" in line:
                # 示例行: "POTCAR:    PAW_PBE O 08Apr2002"
                symbol = line.split()[2]
                symbols.append(symbol)
            
            # 读取能量
            if "energy  without entropy" in line:
                parts = line.split()
                try:
                    energy = float(parts[6])  # 能量值在第七个位置
                except (IndexError, ValueError):
                    pass
            
            # 读取晶胞体积
            if "volume of cell" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        volume = float(parts[1].strip())
                    except ValueError:
                        pass
            
            # 定位应力信息区域
            if "FORCE on cell" in line:
                in_stress_section = True
                continue
            
            # 在应力区域收集相关行
            if in_stress_section:
                if "Total" in line:
                    # 下一行就是应力分量行
                    # print(f"i:{i}","line:",line)
                    
                    sxx, syy, szz, sxy, syz, szx = map(float, line.split()[1:7])

                                
                    # 转换为ASE需要的顺序: XX, XY, XZ, YY, YZ, ZZ
                    # ASE格式: "XX XY XZ XY YY YZ ZX YZ ZZ"
                    # 实际上ASE使用Voigt顺序: [xx, yy, zz, yz, xz, xy]
                    # 但extxyz格式存储为6分量: [xx, yy, zz, xy, xz, yz]?
                    # 根据ASE文档，应力存储为6分量: [xx, yy, zz, yz, xz, xy]
                    
                    # 因此我们需要转换:
                    # VASP顺序: [xx, yy, zz, xy, yz, zx]
                    # ASE顺序: [xx, yy, zz, yz, xz, xy]
                    # 所以:
                    #   xx -> xx (0->0)
                    #   yy -> yy (1->1)
                    #   zz -> zz (2->2)
                    #   xy -> xy (3->5) 但ASE要求xy在最后?
                    #   yz -> yz (4->3)
                    #   zx -> xz (5->4)
                    
                    # ASE实际顺序: [xx, yy, zz, yz, xz, xy]
                    stress = np.array([sxx, syy, szz, syz, szx, sxy])
                    
                    # 应用转换: 除以体积并乘以-1
                    if volume is not None:
                        stress = -stress / volume
                    else:
                        # 如果找不到体积，尝试计算
                        if lattice is not None:
                            cell = np.array(lattice)
                            volume = np.abs(np.linalg.det(cell))
                            stress = -stress / volume
                        else:
                            print(f"警告: 无法获取晶胞体积，跳过应力信息")
                            stress = None

                        
                    in_stress_section = False
            
            # 定位力信息区域
            if "TOTAL-FORCE (eV/Angst)" in line:
                in_force_section = True
                skip_next_line = True
                positions = []  # 重置位置列表
                forces = []     # 重置力列表
                continue
                
            if in_force_section and skip_next_line:
                skip_next_line = False
                continue
                
            # 读取位置和力数据行
            if in_force_section and len(positions) < atom_count:
                if line.strip() == '':  # 遇到空行提前结束
                    in_force_section = False
                    continue
                    
                # 解析位置和力数据
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        x, y, z = map(float, parts[:3])
                        fx, fy, fz = map(float, parts[3:6])
                        positions.append([x, y, z])
                        forces.append([fx, fy, fz])
                    except ValueError:
                        continue
    
    # 验证数据
    if len(positions) != atom_count:
        raise RuntimeError(f"读取的位置数据数量({len(positions)})与原子数量({atom_count})不匹配")
    
    if len(forces) != atom_count:
        raise RuntimeError(f"读取的力数据数量({len(forces)})与原子数量({atom_count})不匹配")
    
    if lattice is None:
        raise RuntimeError("未找到晶胞信息")
    
    if not symbols:
        raise RuntimeError("未找到原子类型信息")
    
    # 创建原子符号列表
    atom_symbols = []
    for i, count in enumerate(atom_counts):
        atom_symbols.extend([symbols[i]] * count)
    
    # 创建ASE Atoms对象
    atoms = Atoms(
        symbols=atom_symbols,
        positions=positions,
        cell=lattice,
        pbc=True
    )
    
    # 添加力信息
    atoms.arrays['forces'] = np.array(forces)
    
    # 添加应力信息
    if stress is not None:
        # 转换为GPa单位 (VASP输出的是kB, 1 kB = 0.1 GPa)
        stress_gpa = stress * 0.1
        atoms.info['stress'] = stress_gpa
    
    # 添加能量信息
    if energy is not None:
        atoms.info['energy'] = energy
    
    return atoms

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

def process_single_file(outcar_file):
    """
    处理单个OUTCAR文件
    """
    # 检查OUTCAR文件是否收敛
    if not is_converged(outcar_file):
        return None, outcar_file, "not_converged"
    
    try:
        # 从OUTCAR中读取完整信息
        atoms = read_outcar_with_full_info(outcar_file)
        return [atoms], outcar_file, "success"
    except Exception as e:
        print(f"Error reading file {outcar_file}: {e}")
        return None, outcar_file, "error"

def convert_all_outcars_to_xyz(outcar_folder, xyz_file):
    # 通过glob找到所有的OUTCAR文件，包括子目录
    outcar_files = glob.glob(f"{outcar_folder}/**/OUTCAR", recursive=True)
    print(f"Found {len(outcar_files)} OUTCAR files.")

    atoms_list = []
    unconverged_files = []
    error_files = []

    # 创建处理函数的部分应用
    process_func = partial(process_single_file)
    
    # 使用多进程池并行处理
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        # 使用tqdm显示进度条
        results = list(tqdm(pool.imap(process_func, outcar_files), 
                           total=len(outcar_files), 
                           desc="Converting OUTCARs to exyz"))
    
    # 处理结果
    for result in results:
        atoms_frames, outcar_file, status = result
        
        if status == "success" and atoms_frames:
            atoms_list.extend(atoms_frames)
        elif status == "not_converged":
            unconverged_files.append(outcar_file)
        elif status == "error":
            error_files.append(outcar_file)

    # 将所有的原子信息写入到一个xyz文件中
    if atoms_list:
        io.write(xyz_file, atoms_list, format='extxyz')
        print(f"All converged OUTCAR files have been converted into {xyz_file}.")
    else:
        print("No converged OUTCAR files found.")

    # 打印各类文件统计信息
    if unconverged_files:
        print(f"Unconverged OUTCAR files ({len(unconverged_files)}):")
        for file in unconverged_files:
            print(file)
    
    if error_files:
        print(f"Files with errors ({len(error_files)}):")
        for file in error_files:
            print(file)

# 使用argparse处理命令行参数
parser = argparse.ArgumentParser(description='Convert OUTCAR files to exyz format.')
parser.add_argument('-i', '--input', default='alloutcar',
                    help='Input directory containing OUTCAR files. Default is "alloutcar".')
parser.add_argument('-o', '--output', default='train.xyz',
                    help='Output filename for the exyz file. Default is "train.xyz".')

if __name__ == '__main__':
    args = parser.parse_args()
    convert_all_outcars_to_xyz(args.input, args.output)