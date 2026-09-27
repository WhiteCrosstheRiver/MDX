# legacy/ — 历史脚本归档

这里保存 MDX 工作台诞生前的独立脚本。它们不再被 `mdx` 包引用，仅作历史参考；
请勿在生产流程中直接运行。已迁移的脚本，其逻辑已在 `mdx/operations.py` 中重写为
非交互、可校验、带清单（manifest）的实现。

## 已迁移（逻辑进入 mdx 工具契约）

| 脚本 | 迁移为工具 | 工具 ID |
|---|---|---|
| `check_nelm.py` / `checkout_nelm.py` | 计算完整性检查 | `audit` |
| `vasp2exyz.py` | OUTCAR → extXYZ | `convert` |
| `xdatcar2poscars.py` / `xyz2poscars.py` | 轨迹抽帧 | `extract` |
| `poscars_perturb.py` | 结构微扰 | `perturb` |
| `poscars_omit.py` | 空位结构生成 | `vacancy` |
| `splitandsave_outcars.py` | 训练 / 测试集划分 | `split` |
| `select_python.py` | 结构随机采样 | `sample` |
| `select_XDATCARS.py` | 收集 XDATCAR | `collect` |

## 待迁移（依赖外部环境，暂未接入）

| 脚本 | 迁移阻碍 |
|---|---|
| `start_poscars.py` | 需要集群环境、赝势与提交配置 |
| `start_xdatcar1.py` | 需要 AIMD 模板和集群配置 |
| `rerun_historyjobs.py` | 自动修改和重提任务需专门适配 |
| `select_pick_structure.py` | 需要 NEP 模型与 calorine |
| `compare_similar_v230721_副本.py` | 依赖私有 gpymatgen 模块 |
| `nep_plot.py` | 需要实际 NEP 输出确认列定义 |
| `sketch.py` | 实验草稿，未接入执行 |

`README-old.html` 是旧版项目说明页，仅供查阅。
