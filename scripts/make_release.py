#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打分享包：白名单收集 + 泄露审计。不会把证书、venv、日志、配置和真实数据打进去。"""
from __future__ import annotations

import getpass
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PACKAGE = "mobile-pickup"

FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "快速开始.txt",
    "VERSION",
    "requirements.txt",
    "config.example.json",
    ".gitignore",
    "agents/openai.yaml",
    "scripts/run.py",
    "scripts/pickup_server.py",
    "scripts/pickup_content.py",
    "scripts/pickup_pages.py",
    "scripts/setup_certs.py",
    "scripts/selftest.py",
    "scripts/make_release.py",
    "scripts/start_windows.bat",
    "scripts/start_windows_hidden.vbs",
    "scripts/firewall_windows.bat",
    "scripts/start_macos.command",
    "scripts/start_linux.sh",
]
DIRS = ["assets/示例"]

BAD_ENTRY = re.compile(
    r"(^|/)(\.venv|__pycache__|certs|dist)(/|$)|(^|/)(pickup\.log|pickup\.pid|config\.local\.json|\.DS_Store|Thumbs\.db)$|\.(key|csr|srl|pyc)$",
    re.I,
)
BAD_TEXT = [
    (re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"), "私钥内容"),
    (re.compile(r"E:\\我的项目", re.I), "个人绝对路径"),
    (re.compile(r"C:\\Users\\[^\\\s]+", re.I), "个人用户目录"),
]
DATE_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def collect() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for name in FILES:
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f"缺少文件：{name}")
        found.append((path, name))
    for name in DIRS:
        base = ROOT / name
        if not base.is_dir():
            raise SystemExit(f"缺少目录：{name}")
        for path in sorted(base.rglob("*")):
            if path.is_file() and not BAD_ENTRY.search(path.relative_to(ROOT).as_posix()):
                found.append((path, path.relative_to(ROOT).as_posix()))
    return found


def audit(zf: zipfile.ZipFile) -> list[str]:
    problems: list[str] = []
    user = getpass.getuser()
    date_names = [
        p.name for p in ROOT.parent.iterdir() if p.is_dir() and DATE_NAME.match(p.name)
    ]
    for info in zf.infolist():
        if BAD_ENTRY.search(info.filename):
            problems.append(f"不该出现的条目：{info.filename}")
            continue
        if info.filename.endswith("/"):
            continue
        data = zf.read(info)
        if b"\x00" in data[:1024]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in BAD_TEXT:
            if pattern.search(text):
                problems.append(f"{info.filename} 含{label}")
        if user and user in text:
            problems.append(f"{info.filename} 含当前用户名")
        for date_name in date_names:
            if date_name in text:
                problems.append(f"{info.filename} 含真实批次目录 {date_name}")
    return problems


def main() -> int:
    name = f"mobile-pickup-v{version()}.zip"
    DIST.mkdir(exist_ok=True)
    target = DIST / name
    items = collect()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in items:
            info = zipfile.ZipInfo(PACKAGE + "/" + arcname)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            if path.suffix.lower() in {".command", ".sh"}:
                info.external_attr = 0o755 << 16
            else:
                info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())

    with zipfile.ZipFile(target) as zf:
        problems = audit(zf)
        listed = zf.namelist()

    print(f"打包：{target}")
    print(f"文件：{len(listed)} 个，大小：{target.stat().st_size / 1024:.1f} KB")
    for item in listed:
        print("  " + item)
    if problems:
        print("\n审计未通过：")
        for problem in problems:
            print("  - " + problem)
        return 1
    print("\n审计通过：没有私钥、venv、日志、本地配置或真实批次数据。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
