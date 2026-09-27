# MDX · 分子模拟命令行助手

纯命令行的分子模拟辅助工具（类似 Claude Code 的使用方式）：结构准备、计算检查、
数据集构建。**零界面、零后台服务**，非常适合在 SSH 远程服务器上使用。
全部本地运行，不联网；每个任务输出独立目录并附带 manifest，结果可复现、可追溯。

## 快速开始

```bash
# 方式一：不安装直接用（仓库目录内）
python -m mdx                # 进入交互助手
python -m mdx tools          # 查看全部工具

# 方式二：一键安装到 bin 目录（推荐，装完后任何目录可用 `mdx` 命令）
python -m mdx install        # 自动扫描推荐 bin 位置（~/.local/bin 等）
python -m mdx install --dir ~/bin   # 或手动指定
python -m mdx install --dry-run     # 只看会装到哪，不写文件
```

安装只写入**一个启动脚本**，指向程序目录与本解释器——不创建虚拟环境、不装包、
不碰系统目录；删除启动器即完成卸载（`python -m mdx uninstall`）。

## 更新

```bash
mdx update          # 一键 git pull（--ff-only，安全快进）
mdx update --reinstall   # 更新后顺带重新 pip install -e（如依赖有变）
```

要求程序目录本身是 git 仓库（`git init && git remote add origin ...` 之后即可用）。

## 使用

```
$ mdx
MDX 分子模拟助手 v0.2.0（纯本地，不联网）
mdx> /audit              ← 检查 OUTCAR 完整性
mdx> /perturb 0.02 0.05  ← 结构微扰，按位置填参数
mdx> 帮我抽帧             ← 自然语言也认（本地关键词规则）
```

无交互执行（适合脚本 / 作业调度）：

```bash
mdx run audit   --project ~/calc/nacl --params '{"nelm": 100}'
mdx run extract --project ~/calc/nacl --params '{"start": 1, "stride": 10, "limit": 50}'
mdx run perturb --project ~/structs   --params '{"count": 5, "cell": 0.02, "displacement": 0.05, "seed": 7}'
```

## 工具一览

| 命令 | 工具 | 输入 |
|---|---|---|
| `/audit` | 计算完整性检查（结束标记 / NELM / CONTCAR） | OUTCAR |
| `/convert` | OUTCAR → extXYZ 数据集（保留能量、力、应力） | OUTCAR |
| `/extract` | 轨迹抽帧 → 独立 POSCAR | XDATCAR / XYZ |
| `/perturb` | 对称应变 + 高斯位移结构微扰 | POSCAR |
| `/vacancy` | 随机空位结构生成 | POSCAR |
| `/split` | 训练 / 测试集划分（按文件为单位） | OUTCAR |
| `/sample` | 结构无放回随机采样 | POSCAR |
| `/collect` | 递归收集 XDATCAR，保留相对路径 | XDATCAR |

依赖：Python ≥ 3.11，`ase`、`numpy`（仅执行结构类工具时需要）。

## 目录结构

```
mdx/            核心包（cli / catalog 工具契约 / operations 执行层）
legacy/         历史脚本归档（已迁移 / 待迁移说明见 legacy/README.md）
tests/          pytest 测试
.mdx/           安装记录（uninstall 时清理）
```
