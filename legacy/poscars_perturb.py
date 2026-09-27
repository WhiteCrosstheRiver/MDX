import numpy as np
from decimal import Decimal
import os
import dataclasses
import tempfile
from typing import Union, List, Tuple, Dict, Any, Optional, Callable
import random
import math

class Atom:
    def __init__(self, element, position,speed=[0.0,0.0,0.0] ,is_fixed=False):
        self.element = element
        self.position = position
        self.speed = speed
        self.is_fixed = is_fixed

class POSCAR:
    atoms = None
    filename = None
    elements = None
    num_elements = None
    comment = None
    scaling_factor = None
    lattice_vectors = None
    filetype = None
    coordtype = None

    def __init__(self, filename, filetype='POSCAR'):
        self.atoms = []
        self.filename = filename
        self.elements = []
        self.num_elements = []
        self.comment = None
        self.scaling_factor = None
        self.lattice_vectors = None
        self.filetype= filetype
        self.coordtype=None
        self.read_file(filetype=self.filetype)
        

    def read_file(self,filetype):
        if filetype=='POSCAR':
            with open(self.filename, 'r') as file:
                lines = file.readlines()
                self.comment = lines[0].strip()
                self.scaling_factor = float(lines[1])
                self.lattice_vectors = [list(map(float, line.split())) for line in lines[2:5]]
                self.elements = lines[5].strip().split()
                self.num_elements = list(map(int, lines[6].strip().split()))                
                # 遍历每一行，查找关键词
                for line in lines:
                    if 'Cartesian' in line:  # 如果这一行包含关键词
                        self.coordtype='Cartesian'
                    if 'Direct' in line:  # 如果这一行包含关键词
                        self.coordtype='Direct'
                for i, num in enumerate(self.num_elements):
                    page_start=9  if lines[7].strip() == "Selective Dynamics"   else   8
                    for line in lines[page_start + sum(self.num_elements[:i]): page_start + sum(self.num_elements[:i+1])]:
                        position = list(map(float, line.split()[:3]))
                        if self.coordtype == "Direct":
                            position = self.direct_to_cartesian(position)
                        is_fixed = line.split()[3:] == ['F', 'F', 'F']
                        self.atoms.append(Atom(self.elements[i], position, [0,0,0],is_fixed))
                        
        elif filetype=='CONTCAR':
            with open(self.filename, 'r') as file:
                lines = file.readlines()
                self.comment = lines[0].strip()
                self.scaling_factor = float(lines[1])
                self.lattice_vectors = [list(map(float, line.split())) for line in lines[2:5]]
                self.elements = lines[5].strip().split()
                self.num_elements = list(map(int, lines[6].strip().split()))
                totalnums=np.sum(self.num_elements)
                # 遍历每一行，查找关键词
                for line in lines:
                    if 'Cartesian' in line:  # 如果这一行包含关键词
                        self.coordtype='Cartesian'
                    if 'Direct' in line:  # 如果这一行包含关键词
                        self.coordtype='Direct'
                for i, num in enumerate(self.num_elements):
                    page_start=9  if lines[7].strip() == "Selective dynamics"   else   8
                    
                    for ii in range(page_start + sum(self.num_elements[:i]), page_start + sum(self.num_elements[:i+1])):
                        atominfo_line=lines[ii]
                        speedinfo_line=lines[ii+totalnums+1]
                        position = list(map(float, atominfo_line.split()[:3]))
                        if self.coordtype == "Direct":
                            position = self.direct_to_cartesian(position)
                        is_fixed = atominfo_line.split()[3:] == ['F', 'F', 'F']
                        speed=list(map(float, speedinfo_line.split()[:3]))
                        self.atoms.append(Atom(self.elements[i], position,speed, is_fixed))

    def write_file(self, filename,speed_tag=False):
        # 创建元素和对应原子的字典
        elements_dict = {}
        elements_list = []
        for atom in self.atoms:
            if atom.element not in elements_list:
                elements_list.append(atom.element)
            if atom.element in elements_dict:
                elements_dict[atom.element].append(atom)
            else:
                elements_dict[atom.element] = [atom]

        # 按照元素的出现顺序排序
        elements_sorted = sorted(elements_dict.keys(), key=lambda x: elements_list.index(x))
        # 获取排序后的元素对应的原子数目
        num_elements_sorted = [len(elements_dict[x]) for x in elements_sorted]

        with open(filename, 'w') as f:
            f.write(self.comment + "\n")
            f.write(f"{self.scaling_factor}\n")
            for vector in self.lattice_vectors:
                f.write(" ".join(map(str, vector)) + "\n")
            f.write(" ".join(elements_sorted) + "\n")
            f.write(" ".join(map(str, num_elements_sorted)) + "\n")
            f.write("Selective Dynamics\n")
            f.write("Cartesian\n")
            speedinfototal='\n'
            for element in elements_sorted:
                for atom in elements_dict[element]:
                    f.write(" ".join(format(Decimal(coord), ".10f") for coord in atom.position) + " ")
                    if atom.is_fixed:
                        f.write("F F F\n")
                    else:
                        f.write("T T T\n")
                    speedinfo_one=" ".join(format(Decimal(coord), ".10f") for coord in atom.speed) + " \n"
                    speedinfototal+=speedinfo_one
            if speed_tag==True:
                f.write(speedinfototal)

    def add_atom(self, element, position,speed=[0,0,0] ,is_fixed=False):
        self.atoms.append(Atom(element, position, speed,is_fixed))
        if element in self.elements:
            self.num_elements[self.elements.index(element)] += 1
        else:
            self.elements.append(element)
            self.num_elements.append(1)

    def remove_atom(self, index):
        del self.atoms[index]

    def display(self):
        for i, atom in enumerate(self.atoms):
            print(f'Atom {i+1}: Element = {atom.element}, Position = {atom.position}, Fixed = {atom.is_fixed}')

    def filter_atoms(self, ranges):
        new_atoms = []
        for atom in self.atoms:
            if all(r[0] <= p <= r[1] for p, r in zip(atom.position, ranges)):
                new_atoms.append(atom)
        self.atoms = new_atoms
        
    def display_atoms(self): 
        for i, atom in enumerate(self.atoms):
            print(f"Atom {i+1}:")
            print(f"Element: {atom.element}")
            print(f"Position: {atom.position}")
            print(f"Speed: {atom.speed}")
            print(f"Is fixed: {atom.is_fixed}")
            print()
            
    def fix_atoms_in_region(self, region):
        """
        Fix atoms within a certain region. The region is defined as [[xmin,xmax],[ymin,ymax],[zmin,zmax]]

        :param region: The region to fix atoms in.
        """
        xmin, xmax = region[0]
        ymin, ymax = region[1]
        zmin, zmax = region[2]

        for atom in self.atoms:
            x, y, z = atom.position
            if xmin <= x <= xmax and ymin <= y <= ymax and zmin <= z <= zmax:
                atom.is_fixed = True
    
    def unfix_atoms_in_region(self, region):
        """
        Unfix atoms within a certain region. The region is defined as [[xmin,xmax],[ymin,ymax],[zmin,zmax]]

        :param region: The region to unfix atoms in.
        """
        xmin, xmax = region[0]
        ymin, ymax = region[1]
        zmin, zmax = region[2]

        for atom in self.atoms:
            x, y, z = atom.position
            if xmin <= x <= xmax and ymin <= y <= ymax and zmin <= z <= zmax:
                atom.is_fixed = False
                
    def direct_to_cartesian(self, direct_coords):
        lattice_matrix = np.array(self.lattice_vectors)
        direct_coords = np.array(direct_coords)
        cartesian_coords = np.dot(direct_coords, lattice_matrix)
        return cartesian_coords.tolist()

@dataclasses.dataclass
class XDATCARParser:
    """
    A parser for XDATCAR files.

    Attributes:
        file_raw_str (str): Raw content of the XDATCAR file.
        file_header_str (str): Header content of the XDATCAR file.
        frame_list (List): List of frames parsed from the XDATCAR file.
        total_frame (int): Total number of frames in the XDATCAR file.
    """

    file_raw_str: str = None
    file_header_str: str = None
    frame_list: List = dataclasses.field(default_factory=list)
    total_frame: int = 0

    def __init__(self, filename: str):
        """
        Initializes the XDATCARParser with the given filename.

        :param filename: Path to the XDATCAR file.
        """
        self.filename = filename
        self.frame_list = []

    def _parse(self):
        """
        Parses the XDATCAR file and stores the frames in frame_list.
        """
        # Read the file and store its contents in file_raw_str
        with open(self.filename, 'r') as f:
            self.file_raw_str = f.read()

        # Read the first 7 lines for the header
        self.file_header_str = '\n'.join(self.file_raw_str.split('\n')[:7]) + "\n" + "Selective Dynamics\n" + "Direct"
        self.total_frame = self.get_max_step_from_XDATCAR()

        # Split the file into frames based on "Direct configuration=" lines
        frames = self.file_raw_str.split("Direct configuration=")[1:]

        # Check if the number of frames matches the total number of steps
        assert len(frames) == self.total_frame, "The number of frames is not equal to the number of steps!"

        # Process each frame
        temp_files = []  # 跟踪所有临时文件以便清理
        try:
            for frame in frames:
                frame = "\n".join(frame.split("\n")[1:])
                POSCAR_str = self.file_header_str + "\n" + frame

                # Create a temporary file for this frame
                with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.poscar') as temp_file:
                    temp_file.write(POSCAR_str)
                    temp_file.flush()
                    temp_file_path = temp_file.name
                    temp_files.append(temp_file_path)

                # Process the temporary file (assuming POSCAR is a class or function that processes it)
                POSCAR_parser = POSCAR(temp_file_path)
                self.frame_list.append(POSCAR_parser)
        finally:
            # 清理所有临时文件
            for temp_file_path in temp_files:
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception:
                    pass  # 忽略清理错误

    def save_specific_frame(self, idx: int, name: str = "POSCAR"):
        """
        Save a specific frame to a POSCAR file.

        :param idx: The index of the frame to save.
        :param name: The name of the output file.
        """
        self.frame_list[idx].write_file(name)

    def count_atoms_at_specific_frame(self, idx: int) -> int:
        """
        Count the number of atoms in a specific frame.

        :param idx: The index of the frame to count.
        :return: The number of atoms in the specified frame.
        """
        return len(self.frame_list[idx].atoms)

    def get_max_step_from_XDATCAR(self) -> int:
        """
        Get the maximum step number from the XDATCAR file.

        :return: The maximum step number.
        """
        max_step = 0
        with open(self.filename, 'r') as f:
            for line in f:
                if line.startswith('Direct configuration='):
                    step = int(line.split('=')[1].strip())
                    if step > max_step:
                        max_step = step
        return max_step

#获得XDATCAR文件最大步数
def get_max_step_from_XDATCAR(filename) -> int:
        """
        Get the maximum step number from the XDATCAR file.
        :return: The maximum step number.
        """
        max_step = 0
        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('Direct configuration='):
                    step = int(line.split('=')[1].strip())
                    if step > max_step:
                        max_step = step
        return max_step



if __name__ == "__main__":
    import glob
    import dpdata
    import readline
    import logging
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from multiprocessing import cpu_count
    import traceback
    from functools import partial
    
    try:
        readline.parse_and_bind("tab: complete")
    except:
        pass  # Windows可能不支持readline
    
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.console import Console
    from rich.logging import RichHandler
    
    console = Console()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    logger = logging.getLogger(__name__)
    
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
### Description:<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
### This script helps you autoly perturb from POSCAR files<<<<<<<
### 支持多核并行处理，大幅提升处理速度！\033[0m
''')
    
    show_copyright()
    show_userguide()
        
    def poscar_perturb(origin_address, output_address, perturb_nums=2, cell_pert_ratio=0.02, 
                     atom_pert_ratio=0.5, pert_style='normal'):
        """
        对单个POSCAR文件进行微扰处理
        
        :param origin_address: 源POSCAR文件路径
        :param output_address: 输出目录路径
        :param perturb_nums: 微扰次数
        :param cell_pert_ratio: 晶胞微扰比例
        :param atom_pert_ratio: 原子微扰距离（埃）
        :param pert_style: 微扰样式 ('normal', 'uniform', 'const')
        :return: (成功标志, 消息)
        """
        try:
            if not os.path.exists(origin_address):
                return False, f"源文件不存在: {origin_address}"
            
            outpathdir = os.path.dirname(output_address)
            if not os.path.exists(outpathdir):
                os.makedirs(outpathdir, exist_ok=True)
            
            # 读取系统一次，避免重复读取
            system = dpdata.System(origin_address)
            
            for i in range(perturb_nums):
                s = system.perturb(
                    pert_num=1,  # 每次只生成一个微扰结构
                    cell_pert_fraction=cell_pert_ratio,
                    atom_pert_distance=atom_pert_ratio,
                    atom_pert_style=pert_style,
                )
                perpath = os.path.join(outpathdir, str(i+1))
                os.makedirs(perpath, exist_ok=True)
                s.to_vasp_poscar(os.path.join(perpath, "POSCAR"))
            
            return True, f"成功处理: {origin_address} -> {outpathdir} (生成了{perturb_nums}个微扰结构)"
        except Exception as e:
            return False, f"处理失败 {origin_address}: {str(e)}\n{traceback.format_exc()}"
    
    def process_single_poscar(args):
        """包装函数，用于并行处理"""
        poscar_dir, poscar_dirs_path, saved_dirs_path, perturb_nums, cell_pert_ratio, atom_pert_ratio, pert_style = args
        origin_address = os.path.join(poscar_dirs_path, poscar_dir, 'POSCAR')
        output_address = os.path.join(saved_dirs_path, poscar_dir, 'POSCAR')
        try:
            return poscar_dir, poscar_perturb(origin_address, output_address, perturb_nums, 
                                              cell_pert_ratio, atom_pert_ratio, pert_style)
        except Exception as e:
            return poscar_dir, (False, f"并行处理异常: {str(e)}\n{traceback.format_exc()}")
    
    def find_folders(root_folder, name_flag):
        """查找包含指定文件的文件夹，使用集合去重"""
        folders = set()
        for folder in glob.glob(os.path.join(root_folder, '**', name_flag), recursive=True):
            relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
            folders.add(relative_path)
        return sorted(list(folders))  # 返回排序后的列表，保证处理顺序一致  
    
    # 用户输入
    poscar_dirs_path = input('包含POSCAR文件的目录路径（你想要微扰的文件）: ').strip()
    if not poscar_dirs_path or not os.path.exists(poscar_dirs_path):
        logger.error(f"目录不存在: {poscar_dirs_path}")
        exit(1)
    
    saved_dirs_path = input('输出目录路径（保存微扰后的POSCAR文件）: ').strip()
    if not saved_dirs_path:
        logger.error("输出目录不能为空")
        exit(1)
    
    nameflag = 'POSCAR'
    
    # 获取微扰次数
    perturbnums_input = input('每个POSCAR文件生成多少个微扰结构？(默认=2): ').strip()
    try:
        perturbnums = int(perturbnums_input) if perturbnums_input else 2
        perturbnums = max(1, perturbnums)
    except ValueError:
        perturbnums = 2
        logger.warning("输入格式错误，使用默认值: 2")
    
    # 获取微扰参数
    pertb_change_flag = input('是否修改微扰参数？(y/n，默认n)\n(默认: cell_pert_fraction=0.02, atom_pert_distance=0.5)\ncell_pert_fraction越大，应力变化范围越大\natom_pert_distance越大，越接近Monte Carlo级别的混乱度: ').strip().lower()
    
    cell_pert_ratio = 0.02
    atom_pert_ratio = 0.5
    pert_style = 'normal'
    
    if pertb_change_flag in ['y', 'yes']:
        try:
            cell_input = input('cell_pert_ratio (默认=0.02): ').strip()
            if cell_input:
                cell_pert_ratio = float(cell_input)
                cell_pert_ratio = max(0.0, cell_pert_ratio)
        except ValueError:
            logger.warning("输入格式错误，使用默认值: 0.02")
        
        try:
            atom_input = input('atom_pert_ratio (默认=0.5): ').strip()
            if atom_input:
                atom_pert_ratio = float(atom_input)
                atom_pert_ratio = max(0.0, atom_pert_ratio)
        except ValueError:
            logger.warning("输入格式错误，使用默认值: 0.5")
        
        pert_style_input = input('pert_style (默认=normal)\n微扰样式: normal(正态分布), uniform(球内均匀), const(球面均匀): ').strip().lower()
        if pert_style_input in ['normal', 'uniform', 'const']:
            pert_style = pert_style_input
        else:
            logger.warning(f"未知的微扰样式 '{pert_style_input}'，使用默认值: normal")
    
    # 询问并行核心数
    max_workers_input = input(f'使用多少个CPU核心并行处理？(默认: {cpu_count()}，输入数字或回车使用默认值): ').strip()
    try:
        max_workers = int(max_workers_input) if max_workers_input else cpu_count()
        max_workers = max(1, min(max_workers, cpu_count()))
    except ValueError:
        max_workers = cpu_count()
        logger.warning("输入格式错误，使用默认值")
    
    logger.info(f"将使用 {max_workers} 个CPU核心进行并行处理")
    logger.info(f"系统总CPU核心数: {cpu_count()}")
    logger.info(f"微扰参数: cell_pert_ratio={cell_pert_ratio}, atom_pert_ratio={atom_pert_ratio}, pert_style={pert_style}")
    
    folders = find_folders(root_folder=poscar_dirs_path, name_flag=nameflag)
    
    if not folders:
        logger.warning(f"在 {poscar_dirs_path} 中未找到任何POSCAR文件")
        exit(0)
    
    logger.info(f"找到 {len(folders)} 个包含POSCAR的文件夹")
    
    # 准备任务参数
    tasks = [(folder, poscar_dirs_path, saved_dirs_path, perturbnums, 
              cell_pert_ratio, atom_pert_ratio, pert_style) for folder in folders]
    
    # 使用并行处理
    success_count = 0
    fail_count = 0
    failed_dirs = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]处理POSCAR文件...", total=len(tasks))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_dir = {executor.submit(process_single_poscar, task_args): task_args[0] 
                            for task_args in tasks}
            
            # 处理完成的任务
            for future in as_completed(future_to_dir):
                try:
                    poscar_dir, (success, message) = future.result()
                    progress.update(task, advance=1)
                    
                    if success:
                        success_count += 1
                        logger.debug(message)
                    else:
                        fail_count += 1
                        failed_dirs.append(poscar_dir)
                        logger.error(f"[{poscar_dir}] {message}")
                except Exception as e:
                    fail_count += 1
                    poscar_dir = future_to_dir.get(future, "未知")
                    failed_dirs.append(poscar_dir)
                    logger.error(f"[{poscar_dir}] 获取结果时发生异常: {str(e)}")
                    progress.update(task, advance=1)
    
    # 输出总结
    console.print(f"\n[green]✓ 成功处理: {success_count} 个文件[/green]")
    if fail_count > 0:
        console.print(f"[red]✗ 失败: {fail_count} 个文件[/red]")
        console.print(f"[yellow]失败的文件夹: {', '.join(failed_dirs[:10])}[/yellow]")
        if len(failed_dirs) > 10:
            console.print(f"[yellow]... 还有 {len(failed_dirs) - 10} 个失败的文件夹[/yellow]")