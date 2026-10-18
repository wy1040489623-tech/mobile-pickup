#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI 优先入口：自动准备 .venv 和依赖，然后启动取件服务。

AI 用法：
    python scripts/run.py --folder "D:\\素材\\今天"

第一次会自动建 .venv、装依赖；之后直接复用。手动双击 bat 的路径仍然保留，
但不需要让用户先装 Python 包或选文件夹。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "pickup_server.py"
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NEEDS_DEPS = {"--folder", "-f", "--port", "-p", "--https-port", "--token", "--ip", "--max-images", "--all-images"}


def run_without_deps(args: list[str]) -> None:
    os.execv(sys.executable, [sys.executable, str(SERVER), *args])


def main() -> int:
    args = sys.argv[1:]

    # 只查询、停止、看帮助时不需要依赖。
    if any(a in args for a in ("--describe", "--help", "-h", "--stop")):
        run_without_deps(args)
        return 0

    if not any(a in NEEDS_DEPS for a in args) and not (ROOT / "config.local.json").is_file():
        print('缺少素材文件夹。请先问用户素材在哪，然后运行：', file=sys.stderr)
        print('  python scripts/run.py --folder "<绝对路径>"', file=sys.stderr)
        return 2

    if not VENV_PY.is_file():
        print("第一次运行：创建 .venv ...", file=sys.stderr)
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
            print("安装依赖 ...", file=sys.stderr)
            subprocess.check_call(
                [
                    str(VENV_PY),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "-r",
                    str(ROOT / "requirements.txt"),
                ]
            )
        except subprocess.CalledProcessError as exc:
            print(f"依赖安装失败（{exc}）。检查网络后重试，或让用户运行启动器。", file=sys.stderr)
            return 1

    check = subprocess.run(
        [str(VENV_PY), "-c", "import segno, cryptography"], capture_output=True
    )
    if check.returncode != 0:
        print("补齐依赖 ...", file=sys.stderr)
        subprocess.check_call(
            [
                str(VENV_PY),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(ROOT / "requirements.txt"),
            ]
        )

    os.execv(str(VENV_PY), [str(VENV_PY), str(SERVER), *args])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
