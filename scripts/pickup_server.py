#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""手机取件服务：把电脑上的文字和图片通过局域网送到手机。

常用：
    python pickup_server.py --folder "D:\\素材\\今天"
    python pickup_server.py --folder "D:\\素材\\今天" --describe   # 只看扫描结果，不起服务

只读：不改、不移动、不删除源文件。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pickup_content as content
import pickup_pages as pages
from setup_certs import ensure_certs, lan_ips

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
VERSION = "1.0.0"
CONFIG_PATH = ROOT / "config.local.json"
PID_PATH = ROOT / "pickup.pid"
LOG_PATH = ROOT / "pickup.log"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BATCH: dict = {"mode": "generic", "root": ROOT, "items": [], "warnings": []}
NOTES_BY_ID: dict[str, dict] = {}
TOKEN = ""
BATCH_KEY = ""
FOLDER_NAME = ""
PRIMARY_URL = ""
HTTP_URL = ""
HTTPS_URL = ""
ALT_URLS: list[str] = []
QR_PATH: Path | None = None
CA_PATH: Path | None = None


def load_config(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def save_config(path: Path, data: dict) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def pick_folder_with_dialog() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        chosen = filedialog.askdirectory(title="选择要送到手机的文件夹")
        root.destroy()
        return Path(chosen) if chosen else None
    except Exception:
        return None


def resolve_folder(args, cfg: dict) -> Path:
    candidate = args.folder or cfg.get("folder")
    if candidate:
        # 用户从资源管理器拖进来或粘贴时，路径可能带外层引号。
        candidate = str(candidate).strip().strip('"').strip("'")
        path = Path(candidate).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if path.is_dir():
            return path.resolve()
        print(f"找不到文件夹：{path}")
    if not args.no_pick:
        chosen = pick_folder_with_dialog()
        if chosen and chosen.is_dir():
            cfg["folder"] = str(chosen)
            cfg.setdefault("token", cfg.get("token") or "")
            save_config(args.config, cfg)
            return chosen.resolve()
    sys.exit(
        "没有可用的文件夹。用 --folder 指定，例如：\n"
        '  python pickup_server.py --folder "D:\\素材\\今天"'
    )


def make_token(raw: str | None) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]", "", raw or "")
    return token or secrets.token_urlsafe(6)


def batch_key(folder: Path) -> str:
    return hashlib.sha1(str(folder).encode("utf-8")).hexdigest()[:8]


class PickupServer(ThreadingHTTPServer):
    # Windows 下复用地址会让两个进程抢同一端口；Unix 下反而有利于重启。
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = f"MobilePickup/{VERSION}"

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        parts = [p for p in path.split("/") if p]
        if not parts or parts[0] != TOKEN:
            if parts and parts[0] == "favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self.send_error(404)
            return
        rest = parts[1:]

        if not rest:
            self.send_html(
                pages.render_index(
                    TOKEN,
                    BATCH_KEY,
                    FOLDER_NAME,
                    "点评批次" if BATCH["mode"] == "dianping" else "通用文件夹",
                    BATCH["items"],
                    PRIMARY_URL,
                    ALT_URLS,
                    QR_PATH is not None and QR_PATH.is_file(),
                    f"/{TOKEN}/_test",
                )
            )
            return

        if rest[0] == "_test":
            self.send_html(
                pages.render_test(
                    TOKEN,
                    PRIMARY_URL,
                    (HTTPS_URL + "_test") if HTTPS_URL else PRIMARY_URL,
                    f"/{TOKEN}/",
                )
            )
            return

        if rest[0] == "_health":
            self.send_json(
                {
                    "ok": True,
                    "version": VERSION,
                    "mode": BATCH["mode"],
                    "notes": len(BATCH["items"]),
                    "images": sum(len(n["images"]) for n in BATCH["items"]),
                    "https": bool(HTTPS_URL),
                }
            )
            return

        if rest[0] == "note" and len(rest) == 2:
            note = NOTES_BY_ID.get(rest[1])
            if note:
                self.send_html(pages.render_note(note, TOKEN, BATCH_KEY, f"/{TOKEN}/_test"))
            else:
                self.send_error(404)
            return

        if rest[0] == "img" and len(rest) == 3:
            note = NOTES_BY_ID.get(rest[1])
            target = next((p for p in note["images"] if p.name == rest[2]), None) if note else None
            if target:
                self.send_image(target)
            else:
                self.send_error(404)
            return

        if rest[0] == "qr.png":
            if QR_PATH and QR_PATH.is_file():
                self.send_image(QR_PATH, cache="no-store")
            else:
                self.send_error(404)
            return

        if rest[0] == "ca.crt":
            if CA_PATH and CA_PATH.is_file():
                self.send_file(CA_PATH)
            else:
                self.send_error(404)
            return

        self.send_error(404)

    def send_html(self, body: str):
        self._send(body.encode("utf-8"), "text/html; charset=utf-8", "no-store")

    def send_json(self, data: dict):
        self._send(
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            "no-store",
        )

    def send_image(self, path: Path, cache: str = "private, max-age=3600"):
        ctype = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(path.suffix.lower(), "application/octet-stream")
        self._send(path.read_bytes(), ctype, cache)

    def send_file(self, path: Path):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/x-x509-ca-cert")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", 'attachment; filename="mobile-pickup-ca.crt"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send(self, data: bytes, ctype: str, cache: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)


def bind_http(host: str, start: int) -> tuple[PickupServer, int]:
    for port in range(start, start + 10):
        try:
            return PickupServer((host, port), Handler), port
        except OSError:
            continue
    raise SystemExit(f"端口 {start}-{start + 9} 都被占用，请用 --port 换一个。")


def bind_https(host: str, start: int, cert: Path, key: Path) -> tuple[PickupServer, int] | None:
    for port in range(start, start + 10):
        try:
            server = PickupServer((host, port), Handler)
        except OSError:
            continue
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=str(cert), keyfile=str(key))
            server.socket = ctx.wrap_socket(server.socket, server_side=True)
            return server, port
        except Exception as exc:
            server.server_close()
            print(f"  HTTPS 启动失败：{exc}")
            return None
    return None


def make_qr(url: str) -> Path | None:
    try:
        import segno
    except ImportError:
        return None
    path = Path(tempfile.gettempdir()) / f"mobile_pickup_qr_{os.getpid()}.png"
    try:
        segno.make(url, error="m").save(path, scale=8, border=2)
        return path
    except Exception:
        return None


def stop_pid(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=8)
        else:
            os.kill(pid, 15)
    except (OSError, subprocess.SubprocessError):
        pass


def read_pid() -> int | None:
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, errors="ignore"
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


HTTPS_PORT = 0


def main() -> None:
    global BATCH, NOTES_BY_ID, TOKEN, BATCH_KEY, FOLDER_NAME
    global PRIMARY_URL, HTTP_URL, HTTPS_URL, ALT_URLS, QR_PATH, CA_PATH, HTTPS_PORT

    parser = argparse.ArgumentParser(description="把电脑上的文字和图片送到手机（局域网）")
    parser.add_argument("--folder", "-f", help="要取件的文件夹；不填则读配置或弹选择框")
    parser.add_argument("--port", "-p", type=int, default=None, help="HTTP 起始端口，默认 8000")
    parser.add_argument("--https-port", type=int, default=None, help="HTTPS 起始端口，默认 8443")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    parser.add_argument("--ip", help="指定手机访问用的本机 IP（多网卡时用）")
    parser.add_argument("--token", help="访问口令；默认读配置或随机生成")
    parser.add_argument("--max-images", type=int, default=None, help="通用模式单篇最多送几张图，默认 30")
    parser.add_argument("--all-images", action="store_true", help="不限制图片数量（点评模式给全部 mix_ 和 P_）")
    parser.add_argument("--describe", action="store_true", help="只输出扫描结果 JSON，不起服务")
    parser.add_argument("--no-https", action="store_true", help="只起 HTTP（复制会受限）")
    parser.add_argument("--regen-certs", action="store_true", help="强制重新生成证书")
    parser.add_argument("--no-open", action="store_true", help="不自动打开电脑浏览器")
    parser.add_argument("--no-pick", action="store_true", help="没有文件夹时直接报错，不弹选择框")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="本地配置文件")
    parser.add_argument("--stop", action="store_true", help="停止本包正在运行的服务")
    args = parser.parse_args()

    if args.stop:
        pid = read_pid()
        if pid and pid_alive(pid):
            stop_pid(pid)
            print(f"已停止进程 {pid}")
        else:
            print("没有正在运行的服务。")
        try:
            PID_PATH.unlink()
        except OSError:
            pass
        return

    if args.describe:
        args.no_pick = True
    cfg = load_config(Path(args.config))
    folder = resolve_folder(args, cfg)
    max_images = args.max_images if args.max_images is not None else int(cfg.get("max_images") or 30)
    BATCH = content.scan_batch(folder, max_images=max_images, all_images=args.all_images)
    if not BATCH["items"]:
        sys.exit(
            f"{folder} 里没有找到可送的文案或图片。\n"
            "通用规则：一家一篇（子文件夹），里面放一个 txt/md 当文案，图片放旁边；"
            "或者直接选一个只有文案和图片的文件夹。"
        )
    NOTES_BY_ID = {note["id"]: note for note in BATCH["items"]}
    FOLDER_NAME = folder.name
    BATCH_KEY = batch_key(folder)

    if args.describe:
        print(json.dumps(content.describe(BATCH), ensure_ascii=False, indent=2))
        return

    TOKEN = make_token(args.token or cfg.get("token"))
    cfg["token"] = TOKEN
    cfg["folder"] = str(folder)
    save_config(Path(args.config), cfg)

    ips = lan_ips()
    primary_ip = args.ip or cfg.get("preferred_ip") or (ips[0] if ips else "127.0.0.1")
    if args.ip:
        ips = [args.ip] + [ip for ip in ips if ip != args.ip]

    cert_dir = ROOT / "certs"
    cert_result = {"ok": False}
    if not args.no_https:
        cert_result = ensure_certs(cert_dir, ips or ["127.0.0.1"], force=args.regen_certs)
        if not cert_result.get("ok"):
            print(f"  证书生成失败：{cert_result.get('reason')}")
            print("  HTTPS 不启动；复制只能走备用路径。")

    http_start = args.port or int(cfg.get("port") or 8000)
    https_start = args.https_port or int(cfg.get("https_port") or 8443)
    http_server, http_port = bind_http(args.host, http_start)
    HTTPS_PORT = https_start
    https_server = None
    if cert_result.get("ok"):
        bound = bind_https(
            args.host, https_start, Path(cert_result["cert"]), Path(cert_result["key"])
        )
        if bound:
            https_server, HTTPS_PORT = bound
        else:
            HTTPS_PORT = 0
    CA_PATH = Path(cert_result["ca"]) if cert_result.get("ca") else None

    HTTP_URL = f"http://{primary_ip}:{http_port}/{TOKEN}/"
    HTTPS_URL = f"https://{primary_ip}:{HTTPS_PORT}/{TOKEN}/" if https_server else ""
    PRIMARY_URL = HTTPS_URL or HTTP_URL
    local_url = f"http://127.0.0.1:{http_port}/{TOKEN}/"
    alt = []
    for ip in ips:
        if ip == primary_ip:
            continue
        alt.append(f"https://{ip}:{HTTPS_PORT}/{TOKEN}/" if https_server else f"http://{ip}:{http_port}/{TOKEN}/")
    ALT_URLS = alt

    QR_PATH = make_qr(PRIMARY_URL)
    for server in (http_server, https_server):
        if server is not None:
            server.qr_path = QR_PATH
            server.ca_path = CA_PATH

    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    total_images = sum(len(note["images"]) for note in BATCH["items"])

    print()
    print("=" * 52)
    print("  手机取件已启动")
    print(f"  文件夹：{folder}（{len(BATCH['items'])} 篇，{total_images} 张图）")
    print(f"  模式：{'大众点评' if BATCH['mode'] == 'dianping' else '通用'}")
    print(f"  电脑打开：{local_url}")
    print(f"  手机打开：{PRIMARY_URL}")
    if https_server:
        print("  提示证书不安全时点“继续访问”，不影响复制。")
    else:
        print("  HTTPS 未启动：复制可能只能用长按。")
    if ALT_URLS:
        print("  其他地址：" + " · ".join(ALT_URLS))
    if QR_PATH:
        print("  二维码：浏览器页面顶部，扫码即可")
    else:
        print("  未安装 segno，页面没有二维码；直接输入上面的地址。")
    if BATCH["warnings"]:
        for warning in BATCH["warnings"]:
            print(f"  提醒：{warning}")
    print("  停止：Ctrl+C，或运行 python scripts/pickup_server.py --stop")
    print("=" * 52)
    print()

    if https_server:
        threading.Thread(target=https_server.serve_forever, daemon=True).start()

    if not args.no_open:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        http_server.server_close()
        if https_server is not None:
            try:
                https_server.shutdown()
            except Exception:
                pass
            https_server.server_close()
        try:
            if read_pid() == os.getpid():
                PID_PATH.unlink()
        except OSError:
            pass
        if QR_PATH:
            try:
                QR_PATH.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
