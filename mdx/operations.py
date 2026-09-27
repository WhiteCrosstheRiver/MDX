"""Non-interactive operations. Never import executable legacy scripts."""
import json
import os
import random
import re
import shutil
from pathlib import Path

SKIP = {".mdx", ".git", ".venv", "__pycache__", "node_modules", "NepTrainKit.win32"}

def discover(root):
    root = Path(root).resolve()
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            path = Path(parent) / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            kind = name.upper() if name.upper() in {"POSCAR", "CONTCAR", "OUTCAR", "XDATCAR"} else path.suffix.lower().lstrip(".")
            if kind in {"POSCAR", "CONTCAR", "OUTCAR", "XDATCAR", "xyz", "extxyz", "cif"}:
                yield path, kind

def audit_outcar(path, fallback=60):
    last = None
    nelm = fallback
    completed = False
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if "General timing and accounting" in line:
                completed = True
            match = re.search(r"\bNELM\s*=\s*(\d+)", line)
            if match:
                nelm = int(match[1])
            match = re.search(r"Iteration\s+\d+\s*\(\s*(\d+)\s*\)", line)
            if match:
                last = int(match[1])
    issues = []
    if not completed:
        issues.append("缺少结束标记")
    if last is None:
        issues.append("未识别电子迭代步数")
    elif last >= nelm:
        issues.append("最后电子步达到 NELM")
    if not path.with_name("CONTCAR").is_file():
        issues.append("缺少 CONTCAR")
    return dict(file=str(path), last_iteration=last, nelm=nelm, completed=completed, issues=issues,
                note="完整性检查不等同于逐离子步电子收敛或结构优化收敛判定")

def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def run(tool, root, output, params, log, cancelled):
    root, output = Path(root).resolve(), Path(output)
    kinds = {"audit": {"OUTCAR"}, "convert": {"OUTCAR"}, "extract": {"XDATCAR", "xyz", "extxyz"},
             "perturb": {"POSCAR"}, "vacancy": {"POSCAR"}, "split": {"OUTCAR"},
             "sample": {"POSCAR"}, "collect": {"XDATCAR"}}
    sources = [p for p, kind in discover(root) if kind in kinds[tool]]
    if not sources:
        raise ValueError("项目目录内没有该工具支持的输入文件")
    log(f"发现 {len(sources)} 个输入文件")
    rng = random.Random(params.get("seed", 42))
    def checkpoint():
        if cancelled():
            raise InterruptedError("任务已取消；已生成的部分结果保留")
    def copy(path, section):
        target = output / section / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        return str(target.relative_to(output))
    manifest = []
    if tool == "split":
        if len(sources) < 2:
            raise ValueError("划分至少需要两个 OUTCAR 文件")
        rng.shuffle(sources)
        cut = max(1, min(len(sources) - 1, round(len(sources) * params["ratio"])))
        for i, path in enumerate(sources):
            checkpoint()
            manifest.append(dict(source=str(path), output=copy(path, "train" if i < cut else "test")))
    elif tool in {"sample", "collect"}:
        if tool == "sample":
            if params["count"] > len(sources):
                raise ValueError(f"仅有 {len(sources)} 个结构，无法抽取 {params['count']} 个")
            sources = rng.sample(sources, params["count"])
        for path in sources:
            checkpoint()
            manifest.append(dict(source=str(path), output=copy(path, "selected")))
    elif tool == "audit":
        for path in sources:
            checkpoint()
            record = audit_outcar(path, params["nelm"])
            manifest.append(record)
            log(f"{path.relative_to(root)}：{'；'.join(record['issues']) or '完整性检查通过'}")
        save_json(output / "audit.json", manifest)
    else:
        import numpy as np
        from ase.io import iread, read, write
        np_rng = np.random.default_rng(params.get("seed", 42))
        for index, path in enumerate(sources):
            checkpoint()
            log(f"处理 {index + 1}/{len(sources)} · {path.relative_to(root)}")
            if tool == "convert":
                report = audit_outcar(path, params["nelm"])
                if report["issues"]:
                    raise ValueError(f"{path}: {'；'.join(report['issues'])}")
                atoms = read(path, format="vasp-out", index=-1)
                if atoms.calc is None or not {"energy", "forces"}.issubset(atoms.calc.results):
                    raise ValueError(f"{path}: 缺少能量或力")
                atoms.info["mdx_source"] = str(path.relative_to(root))
                write(output / "dataset.xyz", atoms, format="extxyz", append=index > 0)
                manifest.append(dict(source=str(path), output="dataset.xyz", frame="last"))
            elif tool == "extract":
                count = 0
                fmt = "vasp-xdatcar" if path.name.upper() == "XDATCAR" else "extxyz"
                for frame, atoms in enumerate(iread(path, index=":", format=fmt), 1):
                    checkpoint()
                    if frame < params["start"] or (frame - params["start"]) % params["stride"]:
                        continue
                    target = output / f"source-{index + 1:04d}" / f"frame-{frame:06d}" / "POSCAR"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    write(target, atoms, format="vasp", direct=True, sort=True)
                    manifest.append(dict(source=str(path), frame=frame, output=str(target.relative_to(output))))
                    count += 1
                    if count >= params["limit"]:
                        break
                if not count:
                    raise ValueError(f"{path}: 指定帧范围没有匹配的帧")
            else:
                original = read(path, format="vasp")
                for variant in range(params["count"]):
                    checkpoint()
                    atoms = original.copy()
                    if tool == "perturb":
                        strain = np_rng.uniform(-params["cell"], params["cell"], (3, 3))
                        strain = (strain + strain.T) / 2
                        atoms.set_cell(atoms.cell @ (np.eye(3) + strain), scale_atoms=True)
                        atoms.set_positions(atoms.positions + np_rng.normal(0, params["displacement"], atoms.positions.shape))
                    else:
                        if params["remove"] >= len(atoms):
                            raise ValueError("移除数量必须小于原子总数")
                        del atoms[np_rng.choice(len(atoms), params["remove"], replace=False)]
                    target = output / f"source-{index + 1:04d}" / f"variant-{variant + 1:04d}" / "POSCAR"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    write(target, atoms, format="vasp", direct=True, sort=True)
                    manifest.append(dict(source=str(path), output=str(target.relative_to(output))))
    checkpoint()
    save_json(output / "manifest.json", dict(tool=tool, parameters=params, records=manifest))
    log(f"完成：{len(manifest)} 条记录；来源和参数已写入 manifest.json")
    return dict(records=len(manifest), issues=sum(bool(r.get("issues")) for r in manifest))
