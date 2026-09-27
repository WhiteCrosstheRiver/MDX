# good for use  already!!!
# for initial cif to autoly execute AIMD process
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

# 用户输入根目录
root_dir = input('请输入包含原子文件的根目录: \n')

# 遍历处理所有原子文件
for file_path, rel_dir in track(find_atomic_files(root_dir), description='处理进度:'):
    try:
        # 解析文件名和扩展名
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        ext = ext.lower().lstrip('.')
        
        # 创建处理目录（以文件名命名）
        process_dir = os.path.join(os.path.dirname(file_path), f"{base_name}_AIMD")
        # 在创建目录前添加清理逻辑
        if os.path.isfile(process_dir):  # 如果存在同名文件
            os.remove(process_dir)       # 先删除文件再创建目录
        os.makedirs(process_dir, exist_ok=True)
        
        # 转换文件到POSCAR格式
        dest_poscar = os.path.join(process_dir, 'POSCAR')
        if file_name in ['POSCAR', 'CONTCAR']:
            shutil.copy(file_path, dest_poscar)
        elif ext in ['cif', 'xyz']:
            # 读取并转换结构文件
            atoms = read(file_path)
            write(dest_poscar, atoms, format='vasp')
            
            # 验证转换后的结构
            verified_atoms = read(dest_poscar, format='vasp')
            if len(verified_atoms) == 0:
                raise ValueError("转换后的POSCAR为空，请检查输入文件")
        else:
            continue  # 不支持的格式
            
        # 检查并修正POSCAR
        check_and_correct_poscar(dest_poscar)
        
        # 读取元素行
        with open(dest_poscar, 'r') as f:
            lines = f.readlines()
            sixth_line = lines[5].strip() if len(lines) >=6 else ''

        # 生成INCAR文件
        with open(os.path.join(process_dir, 'INCAR'), 'w') as f:
            f.write('''Global Parameters 
# basic parameters 
SYSTEM       = AIMD_NVT    # title
NCORE        = 8           # 8*?=?
KGAMMA       = .TRUE.      # GAMMA point
KSPACING     = 2.0         # to ensure that the k-mesh = 1 * 1 * 1
ENCUT        = 400.0       # cutoff energy for the PWB set 
PREC         = Low      # precision-mode
GGA          = PE          # GGA = PE
ISTART       = 0           # read the WAVECAR file or not (ICHARG=2) 
LWAVE        = .FALSE.     # write WAVECAR or not 
LCHARG       = .FALSE.     # write CHGCAR or not 
# Electronic Relaxation    
ISMEAR       = 0           # 0=Gaussian smearing, (1,2)=Methfessel-Paxton order N 
SIGMA        = 0.05        # width of the smearing in eV
EDIFF        = 1e-4        # global break for electronic SC-loop, eV 
EDIFFG       = -1e-2       # break for force
LREAL        = A           # projection operators
LMAXMIX      = 4           # l-quantum numbers, LMAXMIX=4 for d-electrons (or 6 for f-elements)
NELM         = 100         # maximum number of electronic SC
NELMIN       = 5           # avoid breaking after 2 steps  
# Molecular Dynamics 
IBRION       = 0           # Activate MD 
MDALGO       = 2           # 2=Nose-Hoover, 3=Langevin 
ISIF         = 2           # 1=NVE, 2=NVT, 3=NpT 
ALGO         = Normal      # Normal=IALGO=38 (Davidson), Fast=IALGO=48 (RMM-DIIS)
ISYM         = 0           # no symmetry for MD, completely
TEBEG        = 50        # Begin temperature K 
TEEND        = 1500        # Final temperature K 
NSW          = 5000        # Max ionic steps 
POTIM        = 2.5           # Timestep in fs 
SMASS        = 1.0         # fictitious mass (in amu) to lattice degrees-of-freedom 
NWRITE       = 1           # long MD-runs use NWRITE=0 or 1 
NBLOCK       = 1           # write PCF and DOS, scale kinetic energy, also the output interval of XDATCAR
''')

        # 生成运行脚本
        with open(os.path.join(process_dir, 'runvasp.sh'), 'w') as f:
            f.write(f'''#!/bin/bash
#SBATCH -J {base_name}
#SBATCH -N 1
#SBATCH -n 28
#SBATCH -t 240:00:00
#SBATCH --cpus-per-task=1

cd $SLURM_SUBMIT_DIR
srun hostname | sort > slurm.nodefile

echo "# ----------------- Job log ----------------- #" >> slurm.log
echo "Job dir    : `pwd`" >> slurm.log
echo "Start time : `date`" >> slurm.log

ulimit -s unlimited

source /vol02/hdd1/public1/install/oneapi/2024.2.1/setvars.sh
(time mpirun -hostfile slurm.nodefile -np $SLURM_NTASKS vasp_std.6.4.1-icc.2024 > slurm.out) 2>>slurm.log

echo "End time : `date`" >> slurm.log
''')

        #提交任务（按需取消注释）
        command = f"cd '{process_dir}' && qvasp -pbe {sixth_line} && sbatch runvasp.sh"
        subprocess.run(command, shell=True, executable='/bin/bash')

    except Exception as e:
        print(f"\033[31m处理失败: {file_path}\n错误信息: {str(e)}\033[0m")