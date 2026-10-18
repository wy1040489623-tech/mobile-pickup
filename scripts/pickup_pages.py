#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三个页面：批次列表、单篇详情、手机能力检测。

模板用 @@KEY@@ 占位，避免在 f-string 里转义整页 JS/CSS。
"""
from __future__ import annotations

import html
import json
import urllib.parse


CSS = r"""
:root{--bg:#f6f4f0;--card:#fff;--ink:#222;--muted:#777;--accent:#e85d2a;--ok:#2e8b57;--warn:#b45309}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.65;-webkit-text-size-adjust:100%;touch-action:manipulation}
.wrap{max-width:720px;margin:0 auto;padding:16px 14px 40px}
header h1{font-size:23px;margin:0 0 3px}
.sub{color:var(--muted);font-size:14px}
.qr{display:flex;gap:14px;align-items:center;background:var(--card);border-radius:14px;padding:12px;margin:16px 0}
.qr img{width:100px;height:100px;border-radius:6px;background:#fff}
.qr-title{font-weight:700;font-size:15px}
.qr-hint{color:var(--muted);font-size:12px;margin-top:3px}
.url{font-size:12px;color:var(--muted);word-break:break-all;margin-top:6px;user-select:text;-webkit-user-select:text}
.alt{font-size:12px;color:var(--muted);margin:4px 0 0;padding-left:18px}
.tip{font-size:13px;color:var(--muted);margin:10px 0}
.card{display:flex;gap:12px;align-items:center;background:var(--card);border-radius:14px;padding:14px;margin:10px 0;text-decoration:none;color:inherit;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card.done{opacity:.62}
.card-main{min-width:0;flex:1}
.store{font-size:13px;color:var(--accent);font-weight:600}
.title{font-size:16px;font-weight:700;margin:2px 0;word-break:break-word}
.meta{font-size:12px;color:var(--muted)}
.badge{font-size:12px;color:var(--muted);border:1px solid #ddd;border-radius:999px;padding:2px 9px;white-space:nowrap}
.card.done .badge{color:var(--ok);border-color:var(--ok)}
.back{display:inline-block;color:var(--muted);text-decoration:none;font-size:14px;margin-bottom:8px}
.store-line{font-size:13px;color:var(--accent);font-weight:700;margin-bottom:8px}
.section{background:var(--card);border-radius:14px;padding:14px;margin:12px 0}
.section-head{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.section-head h2{font-size:15px;margin:0}
.copy{margin-left:auto;border:0;background:var(--accent);color:#fff;font-size:14px;padding:8px 15px;border-radius:999px}
.copy.ok{background:var(--ok)}
.text{margin:0;white-space:pre-wrap;word-break:break-word;font-family:inherit;font-size:15px;user-select:text;-webkit-user-select:text}
.title-text{font-size:17px;font-weight:700}
.chars{font-size:12px;color:var(--muted);margin-top:6px}
.img-card{background:var(--card);border-radius:14px;padding:10px;margin:12px 0}
.img-head{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:8px}
.img-no{background:var(--accent);color:#fff;width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px}
.img-label{font-weight:700}
.save-box{padding:14px}
.save-head{display:flex;align-items:center;gap:12px}
.save-title{font-size:16px;font-weight:700}
.save-sub{font-size:12px;color:var(--muted);margin-top:2px}
.save-all{margin-left:auto;border:0;background:var(--accent);color:#fff;font-size:15px;font-weight:700;padding:12px 16px;border-radius:12px;white-space:nowrap}
.save-all:disabled{background:#bbb}
.save-hint{font-size:12px;color:var(--muted);margin-top:10px}
.download-link{margin-top:8px;border:0;background:none;color:var(--accent);font-size:12px;padding:0;text-decoration:underline}
textarea.text{width:100%;border:0;outline:none;resize:none;overflow:hidden;background:transparent;padding:0;color:inherit;line-height:1.65;display:block;font-family:inherit}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(10px);background:rgba(0,0,0,.84);color:#fff;font-size:14px;padding:10px 18px;border-radius:999px;opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:30}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.copy-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:20;align-items:center;justify-content:center;padding:16px}
.copy-modal.show{display:flex}
.copy-modal-box{background:#fff;border-radius:16px;padding:16px;width:100%;max-width:560px;max-height:86vh;display:flex;flex-direction:column}
.copy-modal-title{font-size:16px;font-weight:700;margin-bottom:6px}
.copy-modal-hint{font-size:13px;color:var(--muted);margin-bottom:10px;line-height:1.5}
.copy-modal textarea{width:100%;flex:1;min-height:220px;border:1px solid #ddd;border-radius:10px;padding:10px;font-size:15px;line-height:1.65;font-family:inherit;resize:none;white-space:pre-wrap;touch-action:auto;-webkit-touch-callout:default;user-select:text;-webkit-user-select:text}
.copy-modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:12px}
.copy-modal-actions button{border:0;border-radius:10px;padding:10px 18px;font-size:15px;background:#eee;color:#222}
.copy-modal-actions button:first-child{background:var(--accent);color:#fff}
.img-card img{width:100%;border-radius:10px;display:block}
.publish{width:100%;border:0;background:var(--ok);color:#fff;font-size:16px;padding:14px;border-radius:14px;margin-top:20px}
.publish.done{background:#888}
.publish-hint{font-size:13px;color:var(--muted);text-align:center;margin-top:10px;min-height:20px}
.back-bottom{display:block;text-align:center;text-decoration:none;background:var(--card);border:1px solid #ddd;border-radius:14px;padding:13px;margin-top:10px;color:var(--accent);font-size:15px;font-weight:700}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.93);z-index:10;flex-direction:column;align-items:center;justify-content:center;padding:12px}
.overlay.show{display:flex}
.overlay img{max-width:100%;max-height:78vh;object-fit:contain;-webkit-touch-callout:default}
.overlay .hint{color:#fff;font-size:13px;margin:12px 0;text-align:center}
.overlay button{border:0;background:#fff;color:#222;font-size:15px;padding:10px 22px;border-radius:999px}
.banner{background:#fff3e0;border:1px solid #f0c38a;color:#8a4b00;border-radius:12px;padding:10px 12px;font-size:13px;margin:12px 0}
.banner.bad{background:#fdecea;border-color:#f3b4ae;color:#a12618}
.test-link{display:block;text-align:center;color:var(--muted);font-size:13px;margin-top:22px}
.test-card{background:var(--card);border-radius:14px;padding:14px;margin:12px 0}
.test-card h2{font-size:16px;margin:0 0 6px}
.test-card p{font-size:13px;color:var(--muted);margin:4px 0 10px}
.test-card button{border:0;background:var(--accent);color:#fff;font-size:14px;padding:9px 15px;border-radius:999px;margin-right:8px}
.test-card button.ghost{background:#eee;color:#222}
.result{font-size:13px;margin-top:8px;min-height:20px;word-break:break-word}
.result.ok{color:var(--ok)}
.result.bad{color:#b42318}
.result.manual{color:var(--warn)}
.kv{display:flex;gap:8px;font-size:13px;margin:3px 0}
.kv b{min-width:120px;color:var(--muted);font-weight:400}
.kv span{word-break:break-all}
.summary{background:#eef7f0;border:1px solid #b9dcc4;border-radius:12px;padding:12px;font-size:14px;margin:12px 0;white-space:pre-wrap}
""".strip()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _fill(template: str, **values) -> str:
    for key, value in values.items():
        template = template.replace(f"@@{key}@@", str(value))
    return template


def render_index(
    token: str,
    batch_key: str,
    folder_name: str,
    mode_label: str,
    notes: list[dict],
    primary_url: str,
    alt_urls: list[str],
    qr_available: bool,
    test_url: str,
) -> str:
    cards = []
    for note in notes:
        if note.get("mode") == "generic":
            meta = f'{len(note["images"])} 张图 · 正文 {note["cn"]} 汉字'
        else:
            meta = f'{len(note["images"])} 张发布图 · 正文 {note["cn"]} 汉字 · 含标题 {note["total_cn"]} 汉字'
        cards.append(
            '<a class="card" href="/@@TOKEN@@/note/@@ID@@" data-note="@@ID@@">'
            '<div class="card-main">'
            '<div class="store">@@STORE@@</div>'
            '<div class="title">@@TITLE@@</div>'
            f'<div class="meta">{meta}</div>'
            "</div>"
            '<div class="badge">待发</div>'
            "</a>".replace("@@TOKEN@@", token).replace("@@ID@@", note["id"])
            .replace("@@STORE@@", html.escape(note["store"]))
            .replace("@@TITLE@@", html.escape(note["title"]))
        )
    qr_html = (
        f'<img src="/{token}/qr.png" alt="手机扫码打开">'
        if qr_available
        else '<div style="width:100px;height:100px;border-radius:6px;background:#eee;display:flex;align-items:center;justify-content:center;color:#999;font-size:12px;text-align:center;padding:6px">未安装<br>segno</div>'
    )
    alt_html = ""
    if alt_urls:
        alt_html = '<div class="alt">其他可用地址：' + " · ".join(
            f'<span style="word-break:break-all">{html.escape(u)}</span>' for u in alt_urls
        ) + "</div>"

    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f6f4f0">
<title>手机取件 · @@FOLDER@@</title>
<style>@@CSS@@</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>手机取件</h1>
    <div class="sub">@@FOLDER@@ · @@MODE@@ · <span id="stats">共 @@COUNT@@ 篇</span></div>
  </header>

  <div class="qr">
    @@QR@@
    <div>
      <div class="qr-title">手机扫码打开</div>
      <div class="qr-hint">手机和电脑连同一个 Wi-Fi。<br>提示“证书不安全”时点“继续访问”，不影响复制。</div>
      <div class="url">@@PRIMARY@@</div>
      @@ALT@@
    </div>
  </div>

  <p class="tip">点开一篇 → 复制标题、复制正文 → 保存图片 → 去 App 发布。</p>

  @@CARDS@@

  <p class="tip">“已发”状态存在手机浏览器里，换手机或清缓存会重置。</p>
  <a class="test-link" href="@@TEST@@">这台手机复制/保存测试</a>
</div>

<script>
const KEY = 'pickup_@@BATCH@@_status_';
function paint() {
  let done = 0;
  document.querySelectorAll('.card').forEach(function (card) {
    const yes = localStorage.getItem(KEY + card.dataset.note) === '1';
    card.classList.toggle('done', yes);
    card.querySelector('.badge').textContent = yes ? '已发' : '待发';
    if (yes) done++;
  });
  document.getElementById('stats').textContent = '共 @@COUNT@@ 篇 · 已发 ' + done + ' · 待发 ' + (@@COUNT@@ - done);
}
paint();
window.addEventListener('pageshow', paint);
document.addEventListener('visibilitychange', function () { if (!document.hidden) paint(); });
</script>
</body>
</html>"""
    return _fill(
        template,
        CSS=CSS,
        FOLDER=html.escape(folder_name),
        MODE=html.escape(mode_label),
        COUNT=len(notes),
        QR=qr_html,
        PRIMARY=html.escape(primary_url),
        ALT=alt_html,
        CARDS="".join(cards),
        TEST=html.escape(test_url),
        BATCH=batch_key,
    )


def render_note(note: dict, token: str, batch_key: str, test_url: str) -> str:
    img_list_json = _json([{"url": f"/{token}/img/{note['id']}/{urllib.parse.quote(p.name)}", "name": p.name} for p in note["images"]])
    title_json = _json(note["title"])
    body_json = _json(note["body"])
    image_cards = []
    for idx, path in enumerate(note["images"], 1):
        label = "封面" if idx == 1 and "封面" in path.name else f"图 {idx}"
        image_cards.append(
            f'<div class="img-card"><div class="img-head"><span class="img-no">{idx}</span>'
            f'<span class="img-label">{label}</span></div>'
            f'<img src="/{token}/img/{note["id"]}/{urllib.parse.quote(path.name)}" alt="{label}" '
            f'loading="{"eager" if idx == 1 else "lazy"}" onclick="openOverlay(this.src)"></div>'
        )

    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f6f4f0">
<title>@@TITLE@@</title>
<style>@@CSS@@</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="/@@TOKEN@@/">← 返回列表</a>
  <div class="store-line">@@STORE@@</div>

  <div id="capBanner" class="banner" style="display:none"></div>

  <section class="section">
    <div class="section-head">
      <h2>标题</h2>
      <button class="copy" onclick="copyText(window.TITLE_TEXT, this)">复制标题</button>
    </div>
    <pre id="titleText" class="text title-text">@@TITLE_TEXT@@</pre>
  </section>

  <section class="section">
    <div class="section-head">
      <h2>正文</h2>
      <button class="copy" onclick="copyText(window.BODY_TEXT, this)">复制正文</button>
    </div>
    <textarea id="bodyText" class="text body-text" readonly>@@BODY_TEXT@@</textarea>
    <div class="chars">正文 @@CN@@ 汉字 · 含标题 @@TOTAL_CN@@ 汉字</div>
  </section>

  @@SAVE_SECTION@@

  <p class="tip">下面是预览；点图可放大，长按也能单张保存。</p>
  @@IMAGES@@

  <button id="publishBtn" class="publish" onclick="togglePublished()">标记为已发布</button>
  <div id="publishHint" class="publish-hint"></div>
  <a id="backBottom" class="back-bottom" href="/@@TOKEN@@/">← 返回列表，发下一篇</a>
  <a class="test-link" href="@@TEST@@">复制/保存测试</a>
</div>

<div id="overlay" class="overlay" onclick="if (event.target === this) closeOverlay()">
  <img id="overlayImg" src="" alt="">
  <div class="hint">长按图片 → 存储到照片 / 下载图片</div>
  <button onclick="closeOverlay()">关闭</button>
</div>

<div id="toast" class="toast"></div>

<div id="copyModal" class="copy-modal" onclick="if (event.target === this) closeCopyModal()">
  <div class="copy-modal-box">
    <div class="copy-modal-title">再点一次复制</div>
    <div class="copy-modal-hint">点下面的“复制”；如果还是不行，长按上面的文字 → 全选 → 复制，换行会保留。</div>
    <textarea id="copyModalText" spellcheck="false" autocapitalize="off" autocomplete="off"></textarea>
    <div class="copy-modal-actions">
      <button onclick="selectCopyText()">复制</button>
      <button onclick="closeCopyModal()">关闭</button>
    </div>
  </div>
</div>

<script>
const NOTE_ID = @@NOTE_ID@@;
const KEY = 'pickup_@@BATCH@@_status_';
const IMG_LIST = @@IMG_LIST@@;
window.TITLE_TEXT = @@TITLE_JSON@@;
window.BODY_TEXT = @@BODY_JSON@@;

function caps() {
  try { return JSON.parse(localStorage.getItem('pickup_caps') || '{}'); } catch (e) { return {}; }
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(function () { el.classList.remove('show'); }, 1600);
}

function legacyCopy(text) {
  const y = window.scrollY;
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.top = '0';
  ta.style.left = '0';
  ta.style.width = '100%';
  ta.style.height = '120px';
  ta.style.padding = '0';
  ta.style.border = '0';
  ta.style.outline = 'none';
  ta.style.background = 'transparent';
  ta.style.opacity = '0.01';
  ta.style.zIndex = '99999';
  ta.style.fontSize = '16px';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, ta.value.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) {}
  try { ta.blur(); } catch (e) {}
  document.body.removeChild(ta);
  window.scrollTo(0, y);
  return ok;
}

function editableCopy(text) {
  const div = document.createElement('div');
  div.contentEditable = 'true';
  div.textContent = text;
  div.style.position = 'fixed';
  div.style.top = '0';
  div.style.left = '0';
  div.style.width = '100%';
  div.style.height = '120px';
  div.style.opacity = '0.01';
  div.style.zIndex = '99999';
  div.style.whiteSpace = 'pre-wrap';
  div.style.fontSize = '16px';
  document.body.appendChild(div);
  const range = document.createRange();
  range.selectNodeContents(div);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  div.focus();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) {}
  sel.removeAllRanges();
  document.body.removeChild(div);
  return ok;
}

function showCopyModal(text) {
  document.getElementById('copyModalText').value = text;
  document.getElementById('copyModal').classList.add('show');
}

function closeCopyModal() {
  document.getElementById('copyModal').classList.remove('show');
}

function tryCopyModal() {
  const ta = document.getElementById('copyModalText');
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, ta.value.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) {}
  return ok;
}

function selectCopyText() {
  if (tryCopyModal()) { closeCopyModal(); toast('已复制 ✓'); }
  else { toast('已全选，请长按文字 → 全选 → 复制'); }
}

async function copyText(text, btn) {
  const success = function () {
    const old = btn.textContent;
    btn.textContent = '已复制 ✓';
    btn.classList.add('ok');
    toast('已复制 ✓');
    setTimeout(function () { btn.textContent = old; btn.classList.remove('ok'); }, 1600);
  };
  if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
    try { await navigator.clipboard.writeText(text); success(); return; } catch (e) {}
  }
  if (legacyCopy(text)) { success(); return; }
  if (editableCopy(text)) { success(); return; }
  showCopyModal(text);
  if (tryCopyModal()) { closeCopyModal(); success(); }
}

function openOverlay(src) {
  document.getElementById('overlayImg').src = src;
  document.getElementById('overlay').classList.add('show');
}
function closeOverlay() {
  document.getElementById('overlay').classList.remove('show');
  document.getElementById('overlayImg').src = '';
}

let FILES = [];
let filesReady = false;

async function prepareFiles() {
  const btn = document.getElementById('saveAllBtn');
  const hint = document.getElementById('saveHint');
  if (!btn || !hint) return;
  try {
    FILES = await Promise.all(IMG_LIST.map(async function (item) {
      const resp = await fetch(item.url);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const blob = await resp.blob();
      return new File([blob], item.name, {type: blob.type || 'image/jpeg'});
    }));
    filesReady = true;
    btn.disabled = false;
    btn.textContent = '一键保存全部（' + FILES.length + ' 张）';
    hint.textContent = caps().save === 'download'
      ? '这台手机不支持系统分享，点按钮会直接下载；图片会进“下载/文件”。'
      : '点按钮后，在手机弹出的面板里选“存储到照片/保存到相册”。';
  } catch (e) {
    hint.textContent = '图片准备失败，请刷新页面重试。';
  }
}

async function saveAll() {
  const hint = document.getElementById('saveHint');
  if (!filesReady || !FILES.length) return;
  if (caps().save === 'download') {
    await downloadAll();
    return;
  }
  if (navigator.canShare && navigator.canShare({files: FILES})) {
    hint.textContent = '已打开系统面板，请选“存储到照片/保存到相册”。找不到就用下面的“下载全部”。';
    try {
      await navigator.share({files: FILES, title: document.title});
      hint.textContent = '已保存/已分享。';
      return;
    } catch (e) {
      if (e.name === 'AbortError') { hint.textContent = '已取消。可以重试，或用下面的“下载全部”。'; return; }
    }
  }
  await downloadAll();
}

async function downloadAll() {
  const hint = document.getElementById('saveHint');
  if (!filesReady || !FILES.length) return;
  hint.textContent = '正在下载 ' + FILES.length + ' 张；如果浏览器询问，请允许下载多个文件。';
  for (let i = 0; i < FILES.length; i++) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(FILES[i]);
    a.download = FILES[i].name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    await new Promise(function (r) { setTimeout(r, 350); });
  }
  hint.textContent = '已开始下载。安卓一般在“下载/相册”里；iPhone 会进“文件”，再从文件存到照片。';
}

function paintPublished() {
  const yes = localStorage.getItem(KEY + NOTE_ID) === '1';
  const btn = document.getElementById('publishBtn');
  btn.textContent = yes ? '已发布 ✓（点此取消）' : '标记为已发布';
  btn.classList.toggle('done', yes);
  const hint = document.getElementById('publishHint');
  if (hint) hint.textContent = yes ? '已标记为已发布。点下面返回列表，发下一篇。' : '';
}
function togglePublished() {
  const yes = localStorage.getItem(KEY + NOTE_ID) === '1';
  localStorage.setItem(KEY + NOTE_ID, yes ? '0' : '1');
  paintPublished();
  if (!yes) {
    const back = document.getElementById('backBottom');
    if (back) back.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }
}

(function boot() {
  const c = caps();
  if (c.copy === 'longpress') {
    const b = document.getElementById('capBanner');
    b.style.display = 'block';
    b.textContent = '这台手机不支持一键复制。请长按上面的标题或正文 → 全选 → 复制。';
  }
  const saveHint = document.getElementById('saveHint');
  if (c.save === 'download' && saveHint) {
    saveHint.textContent = '这台手机不支持系统分享，点按钮会直接下载；图片会进“下载/文件”。';
  }
  paintPublished();
  window.addEventListener('pageshow', paintPublished);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) paintPublished(); });
  prepareFiles();
  const bodyEl = document.getElementById('bodyText');
  if (bodyEl) { bodyEl.style.height = bodyEl.scrollHeight + 'px'; }
})();
</script>
</body>
</html>"""
    return _fill(
        template,
        CSS=CSS,
        TOKEN=token,
        TITLE=html.escape(note["title"]),
        STORE=html.escape(note["store"]),
        TITLE_TEXT=html.escape(note["title"]),
        BODY_TEXT=html.escape(note["body"]),
        CN=note["cn"],
        TOTAL_CN=note["total_cn"],
        SAVE_SECTION=(
            '<section class="section save-box">'
            '<div class="save-head"><div>'
            '<div class="save-title">全部图片</div>'
            f'<div class="save-sub">共 {len(note["images"])} 张</div>'
            '</div>'
            '<button id="saveAllBtn" class="save-all" onclick="saveAll()" disabled>正在准备…</button>'
            '</div>'
            '<div id="saveHint" class="save-hint">正在准备图片，稍等一下…</div>'
            '<button class="download-link" onclick="downloadAll()">没找到“保存到相册”？点这里下载全部</button>'
            '</section>'
        ) if note["images"] else '',
        IMAGES="".join(image_cards),
        TEST=html.escape(test_url),
        NOTE_ID=_json(note["id"]),
        BATCH=batch_key,
        IMG_LIST=img_list_json,
        TITLE_JSON=title_json,
        BODY_JSON=body_json,
    )


def render_test(token: str, primary_url: str, https_url: str, back_url: str) -> str:
    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f6f4f0">
<title>复制/保存测试</title>
<style>@@CSS@@</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="@@BACK@@">← 返回列表</a>
  <header><h1>这台手机能用哪种方式</h1><div class="sub">点一遍，结果会记住，取件页会自动按结果提示。</div></header>

  <div id="protoBanner" class="banner" style="display:none">
    当前是 HTTP，剪贴板一定不可用。请改用 HTTPS 地址：<span class="url">@@HTTPS@@</span>
  </div>

  <section class="test-card">
    <h2>环境</h2>
    <div class="kv"><b>页面地址</b><span id="envUrl"></span></div>
    <div class="kv"><b>安全上下文</b><span id="envSecure"></span></div>
    <div class="kv"><b>浏览器</b><span id="envUA"></span></div>
    <div class="kv"><b>剪贴板接口</b><span id="envClip"></span></div>
    <div class="kv"><b>系统分享</b><span id="envShare"></span></div>
  </section>

  <section class="test-card">
    <h2>1. 一键复制（Clipboard）</h2>
    <p>点一下，看看浏览器让不让网页直接写剪贴板。</p>
    <button onclick="testClipboard()">测一键复制</button>
    <div id="rClip" class="result"></div>
  </section>

  <section class="test-card">
    <h2>2. 老式复制（execCommand）</h2>
    <p>有些浏览器不支持上一种，但支持这一种。</p>
    <textarea id="execBox" style="position:fixed;left:-9999px;top:0" spellcheck="false">测试文字 pickup-exec-test</textarea>
    <button onclick="testExec()">测老式复制</button>
    <div id="rExec" class="result"></div>
  </section>

  <section class="test-card">
    <h2>3. 长按复制</h2>
    <p>长按下面这段字 → 全选 → 复制。任何手机都该有这一条。</p>
    <textarea readonly style="width:100%;height:70px;border:1px solid #ddd;border-radius:10px;padding:8px;font-size:15px;user-select:text;-webkit-user-select:text">长按复制测试 pickup-longpress-test</textarea>
    <div style="margin-top:8px">
      <button onclick="markLongpress(true)">我长按复制成功了</button>
      <button class="ghost" onclick="markLongpress(false)">不行</button>
    </div>
    <div id="rLong" class="result"></div>
  </section>

  <section class="test-card">
    <h2>4. 批量保存图片</h2>
    <p>先看系统分享能不能接两张图，再试下载。</p>
    <button onclick="testShare()">测系统分享</button>
    <button class="ghost" onclick="testDownload()">测下载</button>
    <div id="rShare" class="result"></div>
    <div id="rDown" class="result"></div>
  </section>

  <div id="summary" class="summary">还没测完。</div>

  <section class="test-card">
    <h2>把结果发回去</h2>
    <p>如果取件时出了问题，把这段结果复制给帮你看的人。</p>
    <button onclick="copyReport()">复制诊断结果</button>
    <textarea id="report" readonly style="width:100%;height:130px;margin-top:10px;border:1px solid #ddd;border-radius:10px;padding:8px;font-size:12px;font-family:monospace"></textarea>
  </section>
</div>
<script>
const CAP_KEY = 'pickup_caps';
const state = {copy: '', save: '', longpress: ''};

function setResult(id, text, kind) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'result' + (kind ? ' ' + kind : '');
}

function detectBrowser() {
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/.test(ua)) return /CriOS/.test(ua) ? 'iPhone · Chrome' : 'iPhone · Safari/WebKit';
  if (/Android/.test(ua)) {
    if (/QQBrowser/.test(ua)) return 'Android · QQ 浏览器';
    if (/Quark/.test(ua)) return 'Android · 夸克';
    if (/OPPO|HeyTap/.test(ua)) return 'Android · OPPO 浏览器';
    if (/Chrome/.test(ua)) return 'Android · Chrome';
    return 'Android · 其他浏览器';
  }
  if (/Windows/.test(ua)) return 'Windows 桌面';
  if (/Macintosh/.test(ua)) return 'macOS 桌面';
  return ua.slice(0, 60);
}

function env() {
  document.getElementById('envUrl').textContent = location.protocol + '//' + location.host + location.pathname;
  document.getElementById('envSecure').textContent = window.isSecureContext ? '是（HTTPS/localhost）' : '否（HTTP，网页不能直接写剪贴板）';
  document.getElementById('envUA').textContent = detectBrowser();
  document.getElementById('envClip').textContent = (navigator.clipboard && navigator.clipboard.writeText) ? '有' : '没有';
  document.getElementById('envShare').textContent = navigator.share ? ('有' + (navigator.canShare ? '（可判断文件）' : '')) : '没有';
  if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
    document.getElementById('protoBanner').style.display = 'block';
  }
}

async function testClipboard() {
  if (!(window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText)) {
    setResult('rClip', '✗ 不可用（不是安全上下文，或浏览器没这个接口）', 'bad');
    saveCaps();
    return;
  }
  try {
    await navigator.clipboard.writeText('pickup-clipboard-test');
    if (!state.copy) state.copy = 'clipboard';
    setResult('rClip', '✓ 写入成功，一键复制可用', 'ok');
  } catch (e) {
    setResult('rClip', '✗ 写入被拒绝：' + (e && e.name ? e.name : e), 'bad');
  }
  saveCaps();
}

function testExec() {
  const box = document.getElementById('execBox');
  box.focus();
  box.select();
  box.setSelectionRange(0, box.value.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) {}
  if (ok) {
    if (!state.copy) state.copy = 'exec';
    setResult('rExec', '✓ 可用（作为备用路径）', 'ok');
  } else {
    setResult('rExec', '✗ 不可用', 'bad');
  }
  saveCaps();
}

function markLongpress(ok) {
  state.longpress = ok ? 'yes' : 'no';
  if (!state.copy && ok) state.copy = 'longpress';
  setResult('rLong', ok ? '✓ 长按路径可用（保底）' : '✗ 长按也不行，换浏览器试试', ok ? 'ok' : 'bad');
  saveCaps();
}

function testPng(seed) {
  const canvas = document.createElement('canvas');
  canvas.width = 48;
  canvas.height = 48;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = seed % 2 ? '#e85d2a' : '#2e8b57';
  ctx.fillRect(0, 0, 48, 48);
  ctx.fillStyle = '#fff';
  ctx.font = '20px sans-serif';
  ctx.fillText(String(seed), 16, 32);
  return new Promise(function (resolve) {
    canvas.toBlob(function (blob) {
      resolve(new File([blob], 'pickup-test-' + seed + '.png', {type: 'image/png'}));
    }, 'image/png');
  });
}

let TEST_FILES = [];

function testShare() {
  if (!navigator.share || !navigator.canShare) {
    state.save = 'download';
    setResult('rShare', '✗ 不支持文件分享；保存走“下载”', 'manual');
    saveCaps();
    return;
  }
  if (TEST_FILES.length < 2) {
    setResult('rShare', '测试图还没准备好，稍等一秒再点一次。', 'manual');
    return;
  }
  const files = TEST_FILES.slice(0, 2);
  if (!navigator.canShare({files: files})) {
    state.save = 'download';
    setResult('rShare', '✗ 不能分享文件；保存走“下载”', 'manual');
    saveCaps();
    return;
  }
  // 必须在点击手势里直接调 share，不能先 await 生成图片。
  navigator.share({files: files, title: '手机取件测试'}).then(function () {
    state.save = 'share';
    setResult('rShare', '✓ 系统面板已打开并完成；保存走分享', 'ok');
    saveCaps();
  }).catch(function (e) {
    if (e && e.name === 'AbortError') {
      state.save = 'share';
      setResult('rShare', '✓ 面板能打开（你取消了）；保存走分享', 'ok');
    } else {
      state.save = 'download';
      setResult('rShare', '✗ 分享报错：' + (e && e.name ? e.name : e) + '；改走下载', 'bad');
    }
    saveCaps();
  });
}

function testDownload() {
  if (TEST_FILES.length < 3) {
    setResult('rDown', '测试图还没准备好，稍等一秒再点一次。', 'manual');
    return;
  }
  const file = TEST_FILES[2];
  const a = document.createElement('a');
  a.href = URL.createObjectURL(file);
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  if (!state.save) state.save = 'download';
  setResult('rDown', '已触发下载。请确认手机“下载/文件”里出现了 pickup-test-3.png。', 'manual');
  saveCaps();
}

function saveCaps() {
  const payload = {
    copy: state.copy || '',
    save: state.save || '',
    longpress: state.longpress || '',
    browser: detectBrowser(),
    secure: !!window.isSecureContext,
    at: new Date().toISOString()
  };
  localStorage.setItem(CAP_KEY, JSON.stringify(payload));
  renderSummary(payload);
}

function renderSummary(c) {
  const copyText = c.copy === 'clipboard' ? '一键复制（Clipboard）' :
                   c.copy === 'exec' ? '老式复制（execCommand）' :
                   c.copy === 'longpress' ? '长按全选复制' : '还没确认';
  const saveText = c.save === 'share' ? '系统分享面板' :
                   c.save === 'download' ? '下载全部' : '还没确认';
  document.getElementById('summary').textContent =
    '推荐复制：' + copyText + '\n推荐保存：' + saveText +
    '\n取件页会按这个结果调整提示。';
  document.getElementById('report').value =
    '手机取件诊断\n浏览器：' + (c.browser || detectBrowser()) +
    '\n地址：' + location.href +
    '\n安全上下文：' + (c.secure ? '是' : '否') +
    '\n复制：' + copyText + '\n保存：' + saveText +
    '\n长按：' + (c.longpress || '未测') + '\n时间：' + (c.at || '');
}

async function copyReport() {
  const text = document.getElementById('report').value;
  if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
    try { await navigator.clipboard.writeText(text); alert('已复制。'); return; } catch (e) {}
  }
  const ta = document.getElementById('report');
  ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) {}
  alert(ok ? '已复制。' : '没复制成功，请长按上面的文字手动复制。');
}

function load() {
  env();
  Promise.all([testPng(1), testPng(2), testPng(3)]).then(function (files) { TEST_FILES = files; }).catch(function () {});
  try {
    const c = JSON.parse(localStorage.getItem(CAP_KEY) || 'null');
    if (c) {
      state.copy = c.copy || '';
      state.save = c.save || '';
      state.longpress = c.longpress || '';
      renderSummary(c);
      setResult('rLong', c.longpress === 'yes' ? '✓ 上次记录：长按可用' : (c.longpress === 'no' ? '✗ 上次记录：长按不行' : ''), c.longpress === 'yes' ? 'ok' : '');
    }
  } catch (e) {}
}
load();
</script>
</body>
</html>"""
    return _fill(
        template,
        CSS=CSS,
        BACK=html.escape(back_url),
        TOKEN=token,
        PRIMARY=html.escape(primary_url),
        HTTPS=html.escape(https_url or primary_url),
    )
