# USB Display HUD

桌面应用：选择风格模板 → 预览 → 推流到 USB 副屏。可打包为 exe。

## 功能

- **记忆上次选择的风格模板、喜欢列表与语言**（`%APPDATA%\UsbDisplayHud\settings.json`）
- 勾选主题可标为喜欢，喜欢的主题排在列表最前
- 选中模板后显示其分辨率（分辨率由模板自身定义）
- 预览区按模板宽高比自适应；推流时主题可显示实测 FPS（`snap.fps`）
- **开机启动 / 自动运行 / 实时预览**同一行；实时预览默认关闭（仅第一帧）
- **摆放方向**单选：0° / 90° / 180° / 270°（按屏物理摆放旋转后再发送）
- 预览 / 开始 / 停止
- 关闭窗口（×）最小化到托盘；标题栏旁提供「退出」真正退出
- 界面多语言（中文 / English），语言切换在「退出 / 关于」左侧
- 数据源优先 AIDA64 Shared Memory，失败回退本地（psutil / nvidia-smi）

## 风格模板（外部 Python 文件）

模板**不打进编译包逻辑**，以源码形式放在程序旁的 `themes/` 目录，用户可直接添加/删除：

```
themes/
  aida64_dense_portrait.py  # 720×1280 密排仪表盘
  classic_portrait.py       # 720×1280
  cyan_hud_portrait.py      # 720×1280
  README.txt
```

打包后请把整个 `themes/` 与 `photos/` 文件夹与 exe 放在同一目录（`release.ps1` 会自动复制）。界面有「重新扫描主题」按钮。

照片轮播默认读取 exe 旁的 `photos/`；也可在设置中指定其他文件夹。

编写规则见 `themes/README.txt`：继承 `Theme`，设置 `id` / `name` / `width` / `height`，实现 `render(snap, now, t)`。

## 运行

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_app.py
```

开机自启等价于：

```powershell
python run_app.py --minimized
```

可选参数：`--no-auto-run`（启动后不自动推流）。

## 打包 release

```powershell
.\.venv\Scripts\Activate.ps1
.\release.ps1
# 或强制清理后重打包
.\release.ps1 -Clean
```

打包产物全部在 `release/` 目录，并在项目根目录生成 `UsbDisplayHud-0.0.1.zip`（可用 `.\release.ps1 -Version 0.0.2` 改版本号）：

```
release/
  UsbDisplayHud.exe
  themes/                 # 从仓库 themes/ 复制
  photos/                 # 从仓库 photos/ 复制（轮播示例图）

UsbDisplayHud-0.0.1.zip   # 解压即用，内容与 release/ 相同
```

## AIDA64

Preferences → External Applications → 勾选 **Shared Memory**。

## GitLab / GitHub

| 远端 | 分支 | 用途 |
|------|------|------|
| GitLab | `master` | 完整开发历史 |
| GitHub | `githubmain` | 开源快照（短线性历史） |

将当前 `master` 内容同步到 GitHub（追加 1 个相关提交，不用 orphan）：

```powershell
.\sync-githubmain.ps1
```

不要在 GitHub 上 Merge `master` → `githubmain`（两边开发历史不共享，应走脚本）。也不要再用 `--orphan` 定期压扁。
