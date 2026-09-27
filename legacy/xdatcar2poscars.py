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
        for frame in frames:
            frame = "\n".join(frame.split("\n")[1:])
            POSCAR_str = self.file_header_str + "\n" + frame

            # Create a temporary file for this frame
            with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
                temp_file.write(POSCAR_str)
                temp_file.flush()
                temp_file_path = temp_file.name

                # Process the temporary file (assuming POSCAR is a class or function that processes it)
                POSCAR_parser = POSCAR(temp_file_path)
                self.frame_list.append(POSCAR_parser)

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
    import os
    import shutil
    import glob
    from rich.progress import track
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
### Description:<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
### This script helps you autoly extract POSCAR files by frames from XDATCARs files<<<<<<<\033[0m
''')
    
    # 使用Tab键进行自动补全
    readline.parse_and_bind("tab: complete")
    show_copyright()
    show_userguide()
    def Xdatcar_frames_toPOSCAR(inputfile='./',outputfile='./',wantedsteps=[],freq=1):
        #确定采样空间的函数
        def calculate_sample_steps(data, freq):
            sample_steps = []
            for item in data:
                start_val, end_val = item[0], item[1]
                steps = (end_val - start_val) // freq + 1
                sample_steps.extend(range(start_val, end_val + 1, freq))
            return sample_steps
        inputfileaddress=os.path.join(inputfile, 'XDATCAR')
        pipeline = XDATCARParser(filename=inputfileaddress)
        pipeline._parse()
        # Get the num#ber of frames
        num_frames = pipeline.get_max_step_from_XDATCAR()# pipeline.source.num_frames
        if len(wantedsteps)==0:
            # Compute the data of the last frame
            # data = pipeline.compute(num_frames - 1)
            outputfileaddress=os.path.join(outputfile, 'POSCAR')
            # Check if the directory exists
            if not os.path.exists(outputfileaddress):
                # If the directory does not exist, create it
                os.makedirs(outputfileaddress)
            pipeline.save_specific_frame(idx=num_frames-1, name=outputfileaddress)
            # Now we export the last frame to POSCAR format
            # export_file(StaticSource(data=data), outputfileaddress, 'vasp')
        else:
            for i in calculate_sample_steps(wantedsteps,freq):
                # data = pipeline.compute(i-1)
                outputfileaddress_idx=os.path.join(outputfile, str(i))
                outputfileaddress=os.path.join(outputfileaddress_idx, 'POSCAR')
                # Check if the directory exists
                if not os.path.exists(outputfileaddress_idx):
                    # If the directory does not exist, create it
                    os.makedirs(outputfileaddress_idx)        
                # export_file(StaticSource(data=data), outputfileaddress, 'vasp')
                pipeline.save_specific_frame(idx=i-1, name=outputfileaddress)
    def find_xdatcar_folders(root_folder):
        xdatcar_folders = []  # 用于储存含有 XDATCAR 的子文件夹相对路径
        for folder in glob.glob(os.path.join(root_folder, '**', 'XDATCAR'), recursive=True):
            relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
            xdatcar_folders.append(relative_path)
        return xdatcar_folders  
    
    xdat_dirs_path=input('the file contained with XDATCAR which you wanna extract:')
    saved_dirs_path=input('OK! tell me the extracted POSCAR files location where you wanna save:')
    
    wantsteps_flag=input('which frame do you wanna extract, is the last one?(y/n)')
    wanted_steps=[]
    if not wantsteps_flag=='y' or wantsteps_flag=='Y' or wantsteps_flag=='yes' or wantsteps_flag=='YES' :
        wanted_steps=list(map(int,input('the steps start point and end point you want extract,\nPLS input at least two nums').split()))
        wanted_steps.pop() if len(wanted_steps) % 2 != 0 else None
        wanted_steps = [wanted_steps[i:i+2] for i in range(0, len(wanted_steps), 2)]
        print(wanted_steps)
        frames=int(input('the frames you want to save(Default=1)'))
        
    
    for xdat_dir in track(find_xdatcar_folders(xdat_dirs_path),description='xdatcars-progress'):
        print(xdat_dir,'is under processing...')
        try:
            Xdatcar_frames_toPOSCAR(inputfile=os.path.join(xdat_dirs_path,xdat_dir),outputfile=os.path.join(saved_dirs_path,xdat_dir),wantedsteps=wanted_steps,freq=frames)
        except:
            print('when processing ',xdat_dir,'something must wrong,maybe your wanted steps over ,or your des-dir has no xdatcar file')