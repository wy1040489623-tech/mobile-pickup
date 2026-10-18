#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""不依赖真机的自检：起临时服务，验证页面、图片、口令、证书和点评模式回归。"""
from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "pickup_server.py"
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + ((" — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def fetch(url: str, context=None):
    with urllib.request.urlopen(url, context=context, timeout=8) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def wait_ready(url: str, proc: subprocess.Popen, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            status, _, _ = fetch(url)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def describe(folder: Path) -> dict:
    out = subprocess.run(
        [
            sys.executable,
            str(SERVER),
            "--folder",
            str(folder),
            "--describe",
            "--no-pick",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stdout + out.stderr)
    return json.loads(out.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", help="默认用包内 示例/")
    args = parser.parse_args()

    folder = Path(args.folder) if args.folder else ROOT / "assets" / "示例"
    if not folder.is_dir():
        print(f"找不到示例文件夹：{folder}")
        return 1

    http_port = free_port()
    https_port = free_port()
    while https_port == http_port:
        https_port = free_port()
    token = "selftest"
    cmd = [
        sys.executable,
        str(SERVER),
        "--folder",
        str(folder),
        "--port",
        str(http_port),
        "--https-port",
        str(https_port),
        "--token",
        token,
        "--no-open",
        "--no-pick",
        "--host",
        "127.0.0.1",
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace"
    )
    base = f"http://127.0.0.1:{http_port}/{token}"
    try:
        if not wait_ready(base + "/_health", proc):
            output = ""
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
            print("服务没有起来。输出：\n" + output)
            return 1

        status, ctype, body = fetch(base + "/")
        text = body.decode("utf-8", "replace")
        check("首页 200", status == 200)
        check("首页是 HTML", "text/html" in ctype)
        check("首页无未替换占位符", "@@" not in text)
        check("首页有二维码或提示", "/qr.png" in text or "segno" in text)

        status, _, body = fetch(base + "/_test")
        test_text = body.decode("utf-8", "replace")
        check("能力检测页 200", status == 200)
        check("检测页含剪贴板探测", "navigator.clipboard" in test_text)
        check("检测页含分享探测", "navigator.share" in test_text)

        status, _, body = fetch(base + "/_health")
        health = json.loads(body.decode("utf-8"))
        check("健康接口字段完整", health.get("notes", 0) >= 1 and health.get("ok") is True)

        match = re.search(r"/" + token + r"/note/([A-Za-z0-9_-]+)", text)
        check("首页有笔记链接", bool(match))
        if match:
            note_url = f"{base}/note/{match.group(1)}"
            status, _, body = fetch(note_url)
            note_text = body.decode("utf-8", "replace")
            check("详情页 200", status == 200)
            check("详情页无未替换占位符", "@@" not in note_text)
            image = re.search(r"/" + token + r"/img/[^\"']+", note_text)
            check("详情页有图片链接", bool(image))
            if image:
                status, ctype, body = fetch(f"http://127.0.0.1:{http_port}{image.group(0)}")
                check("图片 200", status == 200 and ctype.startswith("image/"))

        try:
            fetch(base.replace(token, "wrong-token") + "/")
            check("错误口令返回 404", False)
        except urllib.error.HTTPError as exc:
            check("错误口令返回 404", exc.code == 404)

        context = ssl._create_unverified_context()
        status, _, body = fetch(f"https://127.0.0.1:{https_port}/{token}/_health", context=context)
        check("HTTPS 健康接口 200", status == 200 and json.loads(body.decode("utf-8")).get("https") is True)

        try:
            pem = ssl.get_server_certificate(("127.0.0.1", https_port))
            from setup_certs import _crypto

            crypto = _crypto()
            if crypto:
                import tempfile

                with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="ascii") as handle:
                    handle.write(pem)
                    temp_path = Path(handle.name)
                try:
                    cert = crypto["x509"].load_pem_x509_certificate(temp_path.read_bytes())
                    san = cert.extensions.get_extension_for_class(crypto["x509"].SubjectAlternativeName).value
                    ips = [str(ip) for ip in san.get_values_for_type(crypto["x509"].IPAddress)]
                    check("证书覆盖 127.0.0.1", "127.0.0.1" in ips, str(ips))
                finally:
                    temp_path.unlink(missing_ok=True)
            else:
                check("证书 SAN（无 cryptography，跳过）", True)
        except Exception as exc:
            check("证书 SAN 检查", False, repr(exc))

        check("CA 证书可下载", fetch(f"{base}/ca.crt")[0] == 200)

        info = describe(folder)
        check("describe 能读出示例", info.get("count", 0) == 1 and info["items"][0]["images"] == 2)

        date_dirs = sorted(
            p
            for p in ROOT.parent.iterdir()
            if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
        )
        dianping = date_dirs[-1] if date_dirs else None
        if dianping and dianping.is_dir():
            dp = describe(dianping)
            check(
                "点评批次回归（7 篇 42 图）",
                dp.get("mode") == "dianping"
                and dp.get("count") == 7
                and sum(item["images"] for item in dp["items"]) == 42,
                f"mode={dp.get('mode')} count={dp.get('count')}",
            )
        else:
            print("SKIP 点评批次回归（同级没有 YYYY-MM-DD 批次目录）")

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    print()
    if FAILED:
        print(f"失败 {len(FAILED)} 项：" + "、".join(FAILED))
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
