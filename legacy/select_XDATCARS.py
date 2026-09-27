import os
import glob
import shutil
from tqdm import tqdm
import readline
from rich.console import Console

def find_files(root_folder, file_name):
    """
    递归搜索指定文件夹中所有指定名称的文件。
    """
    files = []  # 存储找到的文件的完整路径
    for file_path in glob.glob(os.path.join(root_folder, '**', file_name), recursive=True):
        files.append(file_path)
    return files

def main():
    # 使用Tab键进行自动补全
    readline.parse_and_bind("tab: complete")
    root_folder = input('Enter the path of the folder to search for XDATCAR files: ')
    target_folder = input('Enter the path where you want to save the extracted files: ')
    console = Console()

    # 查找所有XDATCAR文件
    xdatcar_files = find_files(root_folder, 'XDATCAR')
    console.print(f'[blue]Found {len(xdatcar_files)} XDATCAR files in {root_folder}[/blue]')

    # 复制文件到目标文件夹
    for index, xdatcar_file in enumerate(tqdm(xdatcar_files, desc='Copying files')):
        dest_dir = os.path.join(target_folder, str(index + 1))  # 目标文件夹路径
        os.makedirs(dest_dir, exist_ok=True)  # 确保目录存在
        shutil.copy(xdatcar_file, dest_dir)  # 复制文件
        console.print(f'[green]Copied {xdatcar_file} to {dest_dir}[/green]')

    console.print('[bold green]All files have been copied successfully.[/bold green]')

if __name__ == '__main__':
    main()
