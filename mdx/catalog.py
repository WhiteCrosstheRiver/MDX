"""Declarative tool contracts shared by the API, UI and execution layer."""

def field(key, label, default, minimum, maximum, step=1):
    return dict(key=key, label=label, default=default, min=minimum, max=maximum, step=step)

SEED = field("seed", "随机种子", 42, 0, 2147483647)
TOOLS = [
    dict(id="audit", name="计算完整性检查", group="计算检查", icon="◎", description="检查 OUTCAR 结束标记、电子步数与 CONTCAR，输出逐文件报告。", files="OUTCAR", fields=[field("nelm", "NELM 回退值（优先读取文件）", 60, 1, 100000)], legacy=["check_nelm.py", "checkout_nelm.py"]),
    dict(id="convert", name="OUTCAR → extXYZ", group="数据处理", icon="⇄", description="用 ASE 读取每个 OUTCAR 的最后一帧，保留能量、力和应力。完整性异常时停止。", files="OUTCAR", fields=[field("nelm", "NELM 回退值", 60, 1, 100000)], legacy=["vasp2exyz.py"]),
    dict(id="extract", name="轨迹抽帧", group="结构准备", icon="▤", description="从 XDATCAR、XYZ 或 extXYZ 按间隔抽帧，保存独立 POSCAR。帧号从 1 开始。", files="XDATCAR / XYZ", fields=[field("start", "起始帧", 1, 1, 10000000), field("stride", "帧间隔", 10, 1, 10000000), field("limit", "每文件最多抽取帧数", 100, 1, 10000)], legacy=["xdatcar2poscars.py", "xyz2poscars.py"]),
    dict(id="perturb", name="结构微扰", group="结构准备", icon="✧", description="对 POSCAR 施加对称均匀晶胞应变与高斯原子位移。遵守固定原子约束。", files="POSCAR", fields=[field("count", "每个结构生成数量", 2, 1, 1000), field("cell", "晶胞应变上限", .02, 0, .2, .001), field("displacement", "每方向位移标准差 / Å", .05, 0, 2, .01), SEED], legacy=["poscars_perturb.py"]),
    dict(id="vacancy", name="空位结构生成", group="结构准备", icon="◇", description="随机移除指定数量原子，保存新结构和可复现种子。", files="POSCAR", fields=[field("remove", "移除原子数", 1, 1, 10000), field("count", "每个结构生成数量", 2, 1, 1000), SEED], legacy=["poscars_omit.py"]),
    dict(id="split", name="训练 / 测试集划分", group="数据处理", icon="◫", description="以 OUTCAR 文件为单位随机划分，保留来源映射；相关轨迹需在划分前分组。", files="OUTCAR", fields=[field("ratio", "训练集比例", .9, .01, .99, .01), SEED], legacy=["splitandsave_outcars.py"]),
    dict(id="sample", name="结构随机采样", group="数据处理", icon="⊞", description="按固定种子从 POSCAR 集合无放回抽取，复制到独立结果目录。", files="POSCAR", fields=[field("count", "抽取结构数", 10, 1, 100000), SEED], legacy=["select_python.py"]),
    dict(id="collect", name="收集 XDATCAR", group="数据处理", icon="⇣", description="递归收集轨迹文件，保留各文件相对路径，避免重名覆盖。", files="XDATCAR", fields=[], legacy=["select_XDATCARS.py"]),
]
BY_ID = {tool["id"]: tool for tool in TOOLS}
LEGACY_ONLY = {
    "start_poscars.py": "待迁移：需要集群环境、赝势与提交配置",
    "start_xdatcar1.py": "待迁移：需要 AIMD 模板和集群配置",
    "rerun_historyjobs.py": "待迁移：自动修改和重提任务需专门适配",
    "select_pick_structure.py": "待迁移：需要 NEP 模型与 calorine",
    "compare_similar_v230721_副本.py": "待迁移：依赖私有 gpymatgen 模块",
    "nep_plot.py": "待迁移：需要实际 NEP 输出确认列定义",
    "sketch.py": "实验草稿，未接入执行",
}

def validate(tool_id, values):
    if tool_id not in BY_ID:
        raise ValueError("未知工具")
    if not isinstance(values, dict):
        raise ValueError("参数必须为对象")
    specs = BY_ID[tool_id]["fields"]
    if set(values) - {f["key"] for f in specs}:
        raise ValueError("包含未知参数")
    result = {}
    for spec in specs:
        value = values.get(spec["key"], spec["default"])
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{spec['label']} 必须为数值")
        if not spec["min"] <= value <= spec["max"]:
            raise ValueError(f"{spec['label']} 超出范围")
        if spec["step"] == 1:
            if int(value) != value:
                raise ValueError(f"{spec['label']} 必须为整数")
            value = int(value)
        result[spec["key"]] = value
    return result
