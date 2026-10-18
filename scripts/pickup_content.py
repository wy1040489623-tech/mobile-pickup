#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把"一个文件夹"读成一批可送到手机的笔记。

两种认法：
- dianping：看到《商铺点评笔记.txt》就按大众点评流水线的老规则（封面 + mix_，默认 6 图）。
- generic：其余文件夹按通用规则（一家一篇、首行标题、图片自然序，可只给文字或只给图片）。

只读：不移动、不改名、不删除任何文件。
"""
from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".md"}
TEXT_NAMES = ("note.txt", "文案.txt", "正文.txt", "text.txt", "copy.txt", "content.txt")
CN_RE = re.compile(r"[\u4e00-\u9fff]")
DIANPING_NOTE = "商铺点评笔记.txt"
DIANPING_COVER = "商铺点评笔记_封面.jpg"


def natural_key(name: str):
    # 同时照顾 mix_2 / P_10 / 2.jpg / 10.jpg 这几种命名。
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(name).stem)]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def cn_count(text: str) -> int:
    return len(CN_RE.findall(text or ""))


def split_title_body(text: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    title = next((line.strip().lstrip("#").strip() for line in lines if line.strip()), "")
    body_start = next((i + 1 for i, line in enumerate(lines) if line.strip()), len(lines))
    body = "\n".join(lines[body_start:]).strip()
    return title, body


def text_candidates(folder: Path) -> list[Path]:
    return sorted(
        (
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in TEXT_EXTS and not p.name.startswith(".")
        ),
        key=lambda p: natural_key(p.name),
    )


def find_text_file(folder: Path) -> Path | None:
    for name in TEXT_NAMES:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    texts = text_candidates(folder)
    return texts[0] if len(texts) == 1 else None


def list_images(folder: Path, recursive: bool = False) -> list[Path]:
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    images = [
        p
        for p in iterator
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTS
        and not p.name.startswith(".")
        and not any(part == "__pycache__" for part in p.parts)
    ]
    return sorted(images, key=lambda p: natural_key(p.name))


def cover_first(images: list[Path]) -> list[Path]:
    covers = [
        p
        for p in images
        if "封面" in p.name or p.stem.lower().startswith(("cover", "封面"))
    ]
    rest = [p for p in images if p not in covers]
    return covers + rest


def dianping_images(note_dir: Path, all_images: bool) -> list[Path]:
    cover = note_dir / DIANPING_COVER
    images = [cover] if cover.is_file() else []
    mixes = sorted(
        (
            p
            for p in note_dir.iterdir()
            if p.is_file()
            and p.name.startswith("mix_")
            and not p.name.startswith("mix9_")
            and p.suffix.lower() in IMAGE_EXTS
        ),
        key=lambda p: natural_key(p.name),
    )
    if all_images:
        images += mixes
        images += sorted(
            (
                p
                for p in note_dir.iterdir()
                if p.is_file() and p.name.startswith("P_") and p.suffix.lower() in IMAGE_EXTS
            ),
            key=lambda p: natural_key(p.name),
        )
    else:
        images += mixes[: max(0, 6 - len(images))]
    if not images:
        p_files = sorted(
            (
                p
                for p in note_dir.iterdir()
                if p.is_file() and p.name.startswith("P_") and p.suffix.lower() in IMAGE_EXTS
            ),
            key=lambda p: natural_key(p.name),
        )
        originals = sorted(
            (
                p
                for p in note_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() in IMAGE_EXTS
                and not p.name.startswith(("mix_", "mix9_", "P_"))
                and "封面" not in p.name
            ),
            key=lambda p: natural_key(p.name),
        )
        images = (p_files or originals)[:6]
    return images


def _item(item_id: str, name: str, folder: Path, title: str, body: str, images: list[Path]) -> dict:
    return {
        "id": item_id,
        "store": name,
        "dir": folder,
        "title": title or name,
        "body": body,
        "images": images,
        "cn": cn_count(body),
        "total_cn": cn_count(body) + cn_count(title),
    }


def scan_dianping(folder: Path) -> list[dict] | None:
    """找到点评笔记就返回列表；一个都没有返回 None。"""
    notes: list[dict] = []
    seen: set[Path] = set()

    def add(note_dir: Path, name: str):
        txt = note_dir / DIANPING_NOTE
        if not txt.is_file() or txt in seen:
            return
        seen.add(txt)
        title, body = split_title_body(read_text(txt))
        images = dianping_images(note_dir, all_images=False)
        notes.append(_item(f"n{len(notes)}", name, note_dir, title, body, images))

    for child in sorted((p for p in folder.iterdir() if p.is_dir()), key=lambda p: p.name):
        add(child, child.name)
        for sub in sorted(
            (p for p in child.iterdir() if p.is_dir() and p.name.startswith("笔记")),
            key=lambda p: p.name,
        ):
            add(sub, f"{child.name} · {sub.name}")
    return notes or None


def scan_generic(folder: Path, max_images: int = 30) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    items: list[dict] = []

    def build(item_dir: Path, name: str) -> dict | None:
        txt = find_text_file(item_dir)
        title, body = (split_title_body(read_text(txt)) if txt else ("", ""))
        images = cover_first(list_images(item_dir))
        if not txt and not images:
            return None
        if txt is None and images:
            warnings.append(f"{name}：没找到文字文件，标题先用文件夹名。")
        if txt is None and len(text_candidates(item_dir)) > 1:
            warnings.append(f"{name}：有多个文字文件，没认出用哪个；标题先用文件夹名。")
        if images and max_images and len(images) > max_images:
            warnings.append(f"{name}：有 {len(images)} 张图，只送前 {max_images} 张。")
            images = images[:max_images]
        return _item(f"n{len(items)}", name, item_dir, title or name, body, images)

    top_text = find_text_file(folder)
    top_images = list_images(folder)
    subdirs = sorted((p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(".")))
    recognized = bool(top_text and top_text.name.lower() in {n.lower() for n in TEXT_NAMES})
    # 顶层只有 README 之类的说明文件时，不要把它当成整批素材。
    if top_images or recognized or (top_text and not subdirs):
        single = build(folder, folder.name)
        if single:
            items.append(single)
        return items, warnings

    for child in subdirs:
        item = build(child, child.name)
        if item:
            items.append(item)
    return items, warnings


def scan_batch(folder: Path, max_images: int = 30, all_images: bool = False) -> dict:
    folder = folder.resolve()
    notes = scan_dianping(folder)
    if notes is not None:
        # 点评模式沿用老规则：默认 6 图；--all-images 才给全部。
        if all_images:
            for note in notes:
                note["images"] = dianping_images(note["dir"], all_images=True)
        for note in notes:
            note["mode"] = "dianping"
        return {"mode": "dianping", "root": folder, "items": notes, "warnings": []}
    items, warnings = scan_generic(folder, max_images=0 if all_images else max_images)
    for note in items:
        note["mode"] = "generic"
    return {"mode": "generic", "root": folder, "items": items, "warnings": warnings}


def describe(batch: dict) -> dict:
    """给 AI 看的扫描摘要：不打印全文，只给判断所需的信息。"""
    items = []
    for note in batch["items"]:
        body = note["body"]
        items.append(
            {
                "id": note["id"],
                "name": note["store"],
                "title": note["title"],
                "body_preview": body[:80] + ("…" if len(body) > 80 else ""),
                "body_chars": note["total_cn"],
                "images": len(note["images"]),
                "image_names": [p.name for p in note["images"][:4]],
            }
        )
    return {
        "mode": batch["mode"],
        "folder": str(batch["root"]),
        "count": len(items),
        "items": items,
        "warnings": batch["warnings"],
    }
