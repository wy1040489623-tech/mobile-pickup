# 手机取件 · mobile-pickup

**把电脑上的文案和图片，扫码送到手机：复制即用，批量存图。**

做大众点评、小红书、公众号时，素材往往在电脑上，发布却在手机 App 里。用微信传文件、数据线拷图，步骤多、顺序乱。这个 skill 让 AI 在电脑上起一个局域网小页面，手机扫码就能拿到文案和图片：标题/正文一键复制，多张图一次保存，直接去 App 里粘贴发布。不上传云端、不装手机 App、不需要账号，手机和电脑连同一个 Wi-Fi 即可。

它只负责“送到手机”，不替你发布。

## 下载

- **Release zip（推荐给不熟 GitHub 的人）**：打开 [Releases](https://github.com/wy1040489623-tech/mobile-pickup/releases/latest)，下载 `mobile-pickup-v1.0.0.zip`，解压出 `mobile-pickup/`。
- **克隆仓库**：`git clone https://github.com/wy1040489623-tech/mobile-pickup.git`

---

## 安装到 AI 工具（GitHub / 技能目录）

这个文件夹本身就是标准 skill 包：根目录有 `SKILL.md`，脚本在 `scripts/`，示例在 `assets/`。

- **ZCode**：把整个文件夹放到 `~/.zcode/skills/mobile-pickup/`（Windows 是 `C:/Users/<你>/.zcode/skills/mobile-pickup/`），刷新技能列表。
- **Codex 或其他支持 SKILL.md 的助手**：放到它约定的 skills 目录（常见是 `~/.codex/skills/`），或把整个文件夹交给它。
- **GitHub**：把整个文件夹作为仓库根目录上传；别人 clone 或下载 zip 后，按上面方式放进 skills 目录，或直接用启动器。
- **只自己用**：不用装进 AI 工具，直接按下面的“第一次运行”双击启动器。

不要上传 `.venv/`、`certs/`、`pickup.log`、`pickup.pid`、`config.local.json`；`.gitignore` 已经排除。

---

## 你需要准备什么

- 一台 Windows / macOS / Linux 电脑，装 **Python 3.9 或更新版本**（3.8 也能跑）。
- 手机和电脑连**同一个 Wi-Fi**。
- 第一次运行时电脑要联网，用来装两个 Python 依赖（`segno`、`cryptography`），之后就离线也能用。

不需要账号，不需要云服务，不需要装手机 App。

---

## AI 助手怎么用（推荐）

AI 读 `SKILL.md` 后，只需要问用户一句“素材在哪个文件夹”，然后运行：

```bash
python scripts/run.py --folder "<绝对路径>"
```

第一次会自动建 `.venv`、装依赖，然后起服务；之后直接复用。用户不需要双击 bat、不需要选文件夹、不需要装依赖，只需要扫码。

下面“第一次运行”是给**自己手动用**的人看的；如果你让 AI 跑，按上面这条就行。

## 第一次运行

### Windows

1. 解压到一个**可写**的目录（不要放 `C:/Program Files`）。zip 里是一个 `mobile-pickup/` 文件夹，直接用它。
2. 双击 `scripts/start_windows.bat`。
3. 第一次会自动：创建 `.venv` → 安装依赖 → 生成证书 → 弹出文件夹选择框 → 起服务 → 打开浏览器。
4. 如果 Windows 防火墙弹窗，勾选“专用网络”，点“允许访问”。没弹但手机打不开，右键管理员运行 `scripts/firewall_windows.bat`。

想后台运行、不显示黑窗口：双击 `scripts/start_windows_hidden.vbs`（第一次仍会显示窗口，方便看安装进度）。

### macOS

1. 解压后，第一次在终端里给脚本执行权限：
   ```bash
   chmod +x scripts/start_macos.command
   ```
2. 双击 `scripts/start_macos.command`。如果系统提示“无法打开，因为无法验证开发者”，右键 → 打开。
3. 首次会创建 `.venv`、装依赖、生成证书、弹文件夹选择框。

### Linux

```bash
chmod +x scripts/start_linux.sh
./scripts/start_linux.sh
```

如果提示缺 `python3-venv`，先装系统包（Ubuntu/Debian：`sudo apt install python3-venv`）。

---

## 素材怎么放

**不用先整理成固定格式。** 下面几种都行，脚本会自己认，认完告诉用户分了几篇，确认后再用：

- 一家一篇：每个子文件夹里放文案和图片；
- 全部混在一个文件夹里：整个文件夹算一篇；
- 文字单独一个文件，图片放旁边；
- 只有文字，或只有图片；
- 先不整理：启动后让脚本弹选择框选文件夹，先看扫描结果。

通用认法：

- 文案文件优先找 `note.txt`、`文案.txt`、`正文.txt`；没有就找唯一的 `.txt` / `.md`。
- 第一行是标题，剩下的都是正文。
- 图片按文件名自然排序；名字里带“封面”或 `cover` 的排第一。
- 单篇默认最多 30 张，多了会提醒；要全部给加 `--all-images`。

如果文件夹里有《商铺点评笔记.txt》，会自动按大众点评模式走：封面 + `mix_`，默认 6 张，规则和原来的流水线一致。

想先试试：直接选包里的 `assets/示例/` 文件夹，里面有一篇示例和两张小图。

---

## 手机上怎么用

1. 电脑浏览器打开后，页面顶部有二维码；手机扫码。
2. 第一次会提示“证书不安全 / 连接不是私密连接”，点 **“继续访问 / 仍然访问”**。**不需要安装证书。**
3. 点开一篇：复制标题 → 复制正文 → 点“一键保存全部” → 在系统面板里选“存储到照片/保存到相册”。
4. 去 App 里粘贴、选图、发布。
5. 发完回网页点“标记为已发布”。

第一次用某台手机，建议点页面底部的 **“这台手机复制/保存测试”**：

- 一键复制能用 → 以后直接点按钮；
- 一键复制不能用 → 长按文字 → 全选 → 复制；
- 系统分享能用 → 保存走系统面板；
- 系统分享不能用 → 点按钮直接下载，图片进“下载/文件”。

测试结果会存在这台手机的浏览器里，取件页会自动按结果调整提示。

---

## 手机打不开 / 复制失败

按顺序试：

1. 确认手机和电脑连的是**同一个 Wi-Fi**，不是访客网络。
2. 看取件页上的“其他可用地址”，换一个地址试。
3. Windows：右键管理员运行 `scripts/firewall_windows.bat`，放行本局域网。
4. macOS：系统设置 → 网络 → 防火墙 → 允许 Python 接受传入连接。
5. 证书提示：点“继续访问”；连这个都不给的浏览器，换 Chrome 或系统浏览器。
6. 复制失败：先跑“复制/保存测试”；再不行长按文字 → 全选 → 复制。
7. 存图失败：系统面板里找“保存到相册/图库/Photos”；没有再点“下载全部”。

> 不要在微信内置浏览器里用，批量分享/下载支持不稳定。推荐 Chrome、Edge、系统浏览器、Safari。

### 最后手段：安装本地 CA（一般不必要）

只有某个浏览器连“继续访问”都不给、或复制始终失败时才考虑：

1. 浏览器打开 `https://电脑IP:8443/<口令>/ca.crt` 下载证书；
2. Android：设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书；
3. iPhone：设置 → 通用 → VPN与设备管理 → 安装描述文件，然后到“关于本机 → 证书信任设置”里打开完全信任；
4. 重新打开取件页。

装完仍然会有“自签证书”的提醒，但复制/分享一般不受影响。**日常流程不要装。**

---

## 停止、端口、口令

- 停止：在运行窗口按 `Ctrl+C`；或在包目录运行 `.venv\Scripts\python.exe scripts/pickup_server.py --stop`（macOS/Linux 用 `.venv/bin/python`）。
- 端口：HTTP 从 8000、HTTPS 从 8443 开始找，被占自动往后顺延 10 个；以页面和日志为准。
- 口令：首次运行随机生成，写在 `config.local.json` 里；二维码自带，不用手输。它只是防止裸地址被随手打开，**不是密码**。
- 换 Wi-Fi 或 IP 变了：重启服务会自动重新生成覆盖新 IP 的证书，二维码也会变；旧书签需要更新。

---

## 隐私与安全

- 服务**只读**：不改、不移动、不删除源文件。
- 只在你启动期间、同一个局域网内可访问；用完请停止。
- 日志只记地址和错误，不记正文。
- `certs/`（私钥）、`config.local.json`（本机路径和口令）、`pickup.log` 都只属于当前电脑，**分享给别人时不要带**。

---

## 包里的文件

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 给 AI 助手看的说明书：先问什么、怎么判断、出问题怎么退 |
| `README.md` | 本文 |
| `快速开始.txt` | 一页纸步骤 |
| `scripts/run.py` | AI 优先入口：自动准备环境并启动 |
| `scripts/pickup_server.py` | 起 HTTP/HTTPS、二维码、页面路由 |
| `scripts/pickup_content.py` | 扫描文件夹，通用模式和大众点评模式 |
| `scripts/pickup_pages.py` | 列表页、详情页、能力检测页 |
| `scripts/setup_certs.py` | 检测本机 IP，生成/续签自签证书 |
| `scripts/selftest.py` | 不依赖真机的自检 |
| `scripts/make_release.py` | 打包分享 zip，并审计有没有夹带私钥/日志/个人数据 |
| `scripts/start_windows.bat` / `scripts/start_windows_hidden.vbs` | Windows 启动器 |
| `scripts/firewall_windows.bat` | Windows 放行本局域网端口 |
| `scripts/start_macos.command` / `scripts/start_linux.sh` | macOS / Linux 启动器 |
| `config.example.json` | 配置样例 |
| `assets/示例/` | 示例素材，第一次可以先拿它试 |

---

## 给 AI 助手

把这个文件夹放进助手的技能目录，或直接把 `SKILL.md` 交给它。里面写好了：

- 先问用户什么；
- 怎么用 `--describe` 扫描并回报；
- 怎么启动、怎么让用户扫码；
- 复制/保存在不同手机上的退路；
- 哪些事不要做（不发布、不默认装 CA、不碰公网隧道、不改用户文件）。

## 卸载

删掉整个文件夹即可。Windows 如果加过防火墙规则，可在“高级安全 Windows Defender 防火墙 → 入站规则”里删除 `MobilePickup`。
