import os,re
import glob
from rich.progress import track
import subprocess
import readline
readline.parse_and_bind("tab: complete")
def find_folders(root_folder,name_flag):
    folders = []  # 用于储存含有 XDATCAR 的子文件夹相对路径
    for folder in glob.glob(os.path.join(root_folder, '**', name_flag), recursive=True):
        relative_path = os.path.relpath(os.path.dirname(folder), root_folder)
        folders.append(relative_path)
    return folders  

def check_and_correct_poscar(poscar_path):
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

poscar_dirs_path=input('the file contained with POSCAR which you wanna start vasp jobs:Once confirmed,Jobs start!!!\n')
nameflag='POSCAR'

for poscar_dir in track(find_folders(root_folder=poscar_dirs_path,name_flag=nameflag),description='poscars_processed:'):
    try:
        poscar_dir_path=os.path.join(poscar_dirs_path,poscar_dir)
        poscar_path=os.path.join(poscar_dir_path,'POSCAR')
        # 检查并修正POSCAR的第六行
        check_and_correct_poscar(poscar_path)
        sixth_line = os.popen(f"sed -n '6p' '{poscar_path}'").read().strip()
        # 创建并写入 INACR 文件  ----采用PBE-D3修正----
        with open(os.path.join(poscar_dir_path, 'INCAR'), 'w') as incar_file:
            incar_file.write('''Global Parameters 
KSPACING = 0.2 
KGAMMA= .TRUE. 
ISTART =  0            (Read existing wavefunction, if there)

LREAL  = Auto       (Projection operators: automatic)
ENCUT  =  400        (Cut-off energy for plane wave basis set, in eV)
PREC   =  Normal   (Precision level: Normal or Accurate, set Accurate when perform structure lattice relaxation calculation)
LWAVE  = .FALSE.        (Write WAVECAR or not)
LCHARG = .FALSE.        (Write CHGCAR or not)

Electronic Relaxation
ISMEAR =  0
SIGMA  =  0.1
EDIFF  =  1E-06
NELM = 60
 
EDIFFG = -1E-02        (Ionic convergence, eV/A)

NCORE=4
# 色散校正的额外参数（根据需要,本文件不需要）
# LVDW = .TRUE. # 确保色散校正被激活
# IVDW = 11
''')



        # 创建并写入 runvasp.sh 文件
        with open(os.path.join(poscar_dir_path, 'runvasp.sh'), 'w') as runvasp_file:
            runvasp_file.write('''#!/bin/bash
#SBATCH -J rc-bt1
#SBATCH -N 1
#SBATCH -n 28
#SBATCH -t 240:00:00
#SBATCH --cpus-per-task=1

#### SBATCH --exclude=node[01]

cd $SLURM_SUBMIT_DIR
srun hostname | sort > slurm.nodefile

# --------------- Do NOT Change the code in the box --------------- #
echo "# ----------------- Job log ----------------- #" >> slurm.log #
echo ""                                                >> slurm.log #
echo "Job dir    is: `pwd`"                            >> slurm.log #
echo "Job starts at: `date`"                           >> slurm.log #
echo "Job works  at: `srun hostname | sort| uniq`"     >> slurm.log #
# ----------------------------------------------------------------- #

module load vasp/6.1.0-icc.2022  # 加载icc环境

ulimit -s unlimited

(time mpirun -hostfile slurm.nodefile -np $SLURM_NTASKS vasp_std.6.1.0-icc.2022 > slurm.out) 2>>slurm.log

# --------------- Do NOT Change the code in the box --------------- #
echo ""                                                >> slurm.log #
echo "Job finishes at: `date`"                         >> slurm.log #
echo ""                                                >> slurm.log #
# ----------------------------------------------------------------- #
                               ''')
        # 进入文件夹并运行 qvasp 命令
        # 避免文件夹有括号，用下面这个
        command = f"cd {poscar_dir_path} && qvasp -pbe {sixth_line} && sbatch runvasp.sh"
        command = f'cd "{poscar_dir_path}" && qvasp -pbe {sixth_line} && sbatch runvasp.sh'
        # 进入文件夹并运行 qvasp 命令
        # 使用 subprocess.run 替代 os.system 并对路径加引号
        command = f"cd '{poscar_dir_path}' && qvasp -pbe {sixth_line} && sbatch runvasp.sh"
        subprocess.run(command, shell=True, executable='/bin/bash')
        # # Execute the command
        # os.system(command)

    except:
        print(poscar_dir,'is underprocessing','something must wrong,maybe your poscarfile is empty ,or your dest-dir has no poscar file')
