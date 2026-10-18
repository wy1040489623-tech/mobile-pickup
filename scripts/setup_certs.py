#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检测本机局域网地址，并为当前地址生成/续签自签证书。

优先用 cryptography（纯 Python，跨平台）；没有就退回系统 openssl。
生成物：certs/ca.crt、ca.key、server.crt、server.key。
"""
from __future__ import annotations

import datetime
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

CA_CN = "Mobile Pickup Local CA"
LEAF_CN = "mobile-pickup.local"
CA_DAYS = 3650
LEAF_DAYS = 397


def is_lan_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.version == 4 and addr.is_private and not addr.is_loopback and not addr.is_link_local


def _from_route() -> list[str]:
    found: list[str] = []
    for target in ("223.5.5.5", "8.8.8.8", "1.1.1.1"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((target, 80))  # UDP connect 不发包，只让系统选默认路由
            found.append(sock.getsockname()[0])
        except OSError:
            pass
        finally:
            sock.close()
    return found


def _from_hostname() -> list[str]:
    found: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(info[4][0])
    except OSError:
        pass
    return found


def _from_os_command() -> list[str]:
    found: list[str] = []
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=8
            ).stdout
            found += re.findall(r"IPv4[^:：]*[:：]\s*([0-9.]+)", out)
        else:
            for cmd in (["ip", "-4", "-o", "addr"], ["ifconfig"]):
                if not shutil.which(cmd[0]):
                    continue
                out = subprocess.run(
                    cmd, capture_output=True, text=True, errors="ignore", timeout=8
                ).stdout
                found += re.findall(r"inet\s+(?:addr:)?([0-9.]+)", out)
                break
    except (OSError, subprocess.SubprocessError):
        pass
    return found


def lan_ips() -> list[str]:
    """返回本机私网 IPv4，默认路由那张网卡排第一。"""
    ordered: list[str] = []
    for ip in _from_route() + _from_hostname() + _from_os_command():
        if is_lan_ip(ip) and ip not in ordered:
            ordered.append(ip)
    return ordered


# ---------- cryptography 路径 ----------

def _crypto():
    try:
        import warnings
        warnings.filterwarnings("ignore", message=r"Python 3\.8 is no longer supported.*")
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError:
        return None
    return {
        "x509": x509,
        "hashes": hashes,
        "serialization": serialization,
        "rsa": rsa,
        "ExtendedKeyUsageOID": ExtendedKeyUsageOID,
        "NameOID": NameOID,
    }


def _write_private_key(path: Path, key, serialization) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    if os.name != "nt":
        os.chmod(path, 0o600)


def _new_ca(c, cert_dir: Path):
    key = c["rsa"].generate_private_key(public_exponent=65537, key_size=2048)
    name = c["x509"].Name([c["x509"].NameAttribute(c["NameOID"].COMMON_NAME, CA_CN)])
    now = datetime.datetime.utcnow()
    cert = (
        c["x509"].CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(c["x509"].random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CA_DAYS))
        .add_extension(c["x509"].BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            c["x509"].KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, c["hashes"].SHA256())
    )
    _write_private_key(cert_dir / "ca.key", key, c["serialization"])
    (cert_dir / "ca.crt").write_bytes(cert.public_bytes(c["serialization"].Encoding.PEM))
    return key, cert


def _new_leaf(c, cert_dir: Path, ca_key, ca_cert, ips: list[str]):
    key = c["rsa"].generate_private_key(public_exponent=65537, key_size=2048)
    san = [c["x509"].IPAddress(ipaddress.ip_address("127.0.0.1"))]
    san += [c["x509"].IPAddress(ipaddress.ip_address(ip)) for ip in ips]
    san += [c["x509"].DNSName("localhost")]
    hostname = socket.gethostname()
    try:
        hostname.encode("ascii")
        san.append(c["x509"].DNSName(hostname + ".local"))
    except UnicodeEncodeError:
        pass
    name = c["x509"].Name([c["x509"].NameAttribute(c["NameOID"].COMMON_NAME, LEAF_CN)])
    now = datetime.datetime.utcnow()
    cert = (
        c["x509"].CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(c["x509"].random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=LEAF_DAYS))
        .add_extension(c["x509"].SubjectAlternativeName(san), critical=False)
        .add_extension(c["x509"].BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            c["x509"].KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            c["x509"].ExtendedKeyUsage([c["ExtendedKeyUsageOID"].SERVER_AUTH]), critical=False
        )
        .sign(ca_key, c["hashes"].SHA256())
    )
    _write_private_key(cert_dir / "server.key", key, c["serialization"])
    (cert_dir / "server.crt").write_bytes(cert.public_bytes(c["serialization"].Encoding.PEM))


def _crypto_covers(c, cert_path: Path, ip: str) -> bool:
    try:
        cert = c["x509"].load_pem_x509_certificate(cert_path.read_bytes())
        try:
            san = cert.extensions.get_extension_for_class(c["x509"].SubjectAlternativeName).value
            if ipaddress.ip_address(ip) not in san.get_values_for_type(c["x509"].IPAddress):
                return False
        except c["x509"].ExtensionNotFound:
            return False
        try:
            expiry = cert.not_valid_after_utc
            now = datetime.datetime.now(expiry.tzinfo)
        except AttributeError:
            expiry = cert.not_valid_after
            now = datetime.datetime.utcnow()
        return expiry > now
    except Exception:
        return False


# ---------- openssl 路径 ----------

def _openssl_covers(cert_path: Path, ip: str) -> bool:
    try:
        out = subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout", "-text"],
            capture_output=True,
            text=True,
            errors="ignore",
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    if f"IP Address:{ip}" not in out:
        return False
    return "Not After" in out


def _openssl_make(cert_dir: Path, ips: list[str], make_ca: bool, make_leaf: bool) -> None:
    cnf = cert_dir / "_openssl.cnf"
    ext = cert_dir / "_leaf.ext"
    cnf.write_text(
        "[req]\ndistinguished_name=dn\nprompt=no\nx509_extensions=v3_ca\n"
        "[dn]\nCN=" + CA_CN + "\n"
        "[v3_ca]\nbasicConstraints=critical,CA:TRUE\n"
        "keyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n",
        encoding="utf-8",
    )
    if make_ca:
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", str(cert_dir / "ca.key"), "-out", str(cert_dir / "ca.crt"),
             "-days", str(CA_DAYS), "-config", str(cnf)],
            check=True, capture_output=True,
        )
    if make_leaf:
        san = ",".join([f"IP:{ip}" for ip in ["127.0.0.1"] + ips] + ["DNS:localhost"])
        ext.write_text(
            f"subjectAltName={san}\nbasicConstraints=CA:FALSE\n"
            "keyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["openssl", "req", "-newkey", "rsa:2048", "-nodes",
             "-keyout", str(cert_dir / "server.key"), "-out", str(cert_dir / "server.csr"),
             "-subj", f"/CN={LEAF_CN}", "-config", str(cnf)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["openssl", "x509", "-req", "-in", str(cert_dir / "server.csr"),
             "-CA", str(cert_dir / "ca.crt"), "-CAkey", str(cert_dir / "ca.key"),
             "-CAcreateserial", "-out", str(cert_dir / "server.crt"),
             "-days", str(LEAF_DAYS), "-extfile", str(ext)],
            check=True, capture_output=True,
        )
    for name in ("_openssl.cnf", "_leaf.ext", "server.csr", "ca.srl"):
        try:
            (cert_dir / name).unlink()
        except FileNotFoundError:
            pass
    if os.name != "nt":
        for name in ("ca.key", "server.key"):
            try:
                os.chmod(cert_dir / name, 0o600)
            except OSError:
                pass


# ---------- 对外入口 ----------

def ensure_certs(cert_dir: Path, ips: list[str], force: bool = False) -> dict:
    """确保证书存在且覆盖 ips[0]。返回状态字典，不抛异常。"""
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert = cert_dir / "server.crt"
    key = cert_dir / "server.key"
    ca = cert_dir / "ca.crt"
    ca_key = cert_dir / "ca.key"
    primary = ips[0] if ips else "127.0.0.1"

    c = _crypto()
    if c:
        try:
            need_ca = force or not (ca.is_file() and ca_key.is_file())
            need_leaf = force or not (cert.is_file() and key.is_file()) or not _crypto_covers(c, cert, primary)
            if need_ca:
                ca_key_obj, ca_cert_obj = _new_ca(c, cert_dir)
                need_leaf = True
            else:
                from cryptography import x509 as _x509
                from cryptography.hazmat.primitives import serialization as _ser
                ca_key_obj = _ser.load_pem_private_key(ca_key.read_bytes(), password=None)
                ca_cert_obj = _x509.load_pem_x509_certificate(ca.read_bytes())
            if need_leaf:
                _new_leaf(c, cert_dir, ca_key_obj, ca_cert_obj, ips or ["127.0.0.1"])
            return {
                "ok": True,
                "method": "cryptography",
                "regenerated": bool(need_ca or need_leaf),
                "cert": str(cert),
                "key": str(key),
                "ca": str(ca) if ca.is_file() else None,
                "primary_ip": primary,
            }
        except Exception as exc:
            last_error = f"cryptography 失败：{exc}"
    else:
        last_error = "未安装 cryptography"

    if shutil.which("openssl"):
        try:
            need_ca = force or not (ca.is_file() and ca_key.is_file())
            need_leaf = force or not (cert.is_file() and key.is_file()) or not _openssl_covers(cert, primary)
            if need_ca:
                need_leaf = True
            if need_ca or need_leaf:
                _openssl_make(cert_dir, ips or ["127.0.0.1"], make_ca=need_ca, make_leaf=need_leaf)
            return {
                "ok": True,
                "method": "openssl",
                "regenerated": bool(need_ca or need_leaf),
                "cert": str(cert),
                "key": str(key),
                "ca": str(ca) if ca.is_file() else None,
                "primary_ip": primary,
                "note": last_error,
            }
        except Exception as exc:
            last_error = f"{last_error}；openssl 也失败：{exc}"

    return {"ok": False, "method": None, "regenerated": False, "reason": last_error}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="检测局域网 IP 并生成自签证书")
    parser.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent / "certs"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--print-ips", action="store_true")
    args = parser.parse_args()

    ips = lan_ips()
    if args.print_ips:
        print("\n".join(ips) if ips else "（没有检测到局域网 IPv4）")
        return
    result = ensure_certs(Path(args.dir), ips, force=args.force)
    print(f"检测到局域网 IP：{', '.join(ips) or '无'}")
    print(result)


if __name__ == "__main__":
    main()
