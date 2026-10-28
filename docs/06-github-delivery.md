# GitHub 交付环境

## 本机配置

2026-10-28 已建立独立 Git 仓库，默认分支为 main。Git 2.47.0.windows.2；GitHub CLI 2.103.3 来自 cli/cli 官方发布，已对照官方校验文件验证 SHA-256。

CLI 安装于项目 `.local-tools/gh/bin/gh.exe`；`scripts/gh.ps1` 负责调用，无需修改系统 PATH。登录配置在 `.local-tools/gh-config`，凭据由 CLI 使用系统凭据库保管；`.local-tools/` 整体被 Git 忽略。脚本不会要求将 token 写入仓库。

用户已在浏览器中完成授权，账号为 Nooo828（ID 75480697）。提交署名使用该账号及 GitHub noreply 邮箱，仅设置本仓库；如原先已有署名，配置脚本会保留。

本机为解决目录所有者检查，在 Git 全局 safe.directory 中仅信任此项目的确切路径；未设置通配信任。GitHub 凭据助手仅配置于本仓库。

实际检查记录见 `examples/github-environment.json`。尚未创建远程仓库、设置 origin 或向 GitHub 推送代码。

## 常用命令（项目根目录，PowerShell）

```powershell
.\scripts\gh.ps1 --version
.\scripts\gh.ps1 auth status
.\scripts\gh.ps1 api user --jq .login
git status
git log -1 --oneline
```

若需重新登录或在新电脑上配置：

```powershell
# 新电脑先安装 Git 与 GitHub CLI，并重新创建 Python venv。
winget install --id Git.Git --exact
winget install --id GitHub.cli --exact
# 安装后重新打开 PowerShell，再进入项目目录。
git init -b main
.\scripts\gh.ps1 auth login --hostname github.com --git-protocol https --web
.\scripts\configure-github.ps1
```

浏览器登录时如询问是否全局配置 Git，可选 No；下一条脚本仅配置本仓库。复制到其他位置后也应重新运行 configure-github.ps1，以更新凭据助手中的绝对路径。GitHub 令牌过期或撤销后需重新登录；不要提交登录配置。

## 选题完成后的上传与交付

当前项目已有基础环境代码。后续每次提交前运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git status --short
git diff
git add .
git diff --cached --stat
git commit -m 'Complete selected AI Agent project'
```

选定仓库名和公开范围后，下面示例可创建私有仓库并首次推送（将 YOUR_REPOSITORY 替换为实际仓库名）：

```powershell
.\scripts\gh.ps1 repo create Nooo828/YOUR_REPOSITORY --private --source . --remote origin --push
```

如果仓库已经存在，使用其实际 URL：

```powershell
git remote add origin https://github.com/Nooo828/YOUR_REPOSITORY.git
git push -u origin main
```

后续更新运行 `git push`。最终提交题号、GitHub URL 和 `git rev-parse HEAD` 的完整 SHA。私有仓库必须向题目指定的评审账号开放读取权限；该账号尚未提供。

`.venv`、`.env`、本地工具与登录配置、Python 缓存均被排除；`.env.example` 可提交。压缩包不包含本地 Git 历史、虚拟环境或登录凭据，不能替代最终 GitHub 交付。
