# GitHub 交付环境

## 仓库命名与公开范围

交付仓库为 [Nooo828/xiaoying-ai-agent-campus-2027](https://github.com/Nooo828/xiaoying-ai-agent-campus-2027)，公开可读，默认分支 `main`。

企业知识问答实现和本地复查修复已完成，用户已恢复上传授权。此前同步因GitHub凭据失效而暂缓；本文件的配置历史不代表凭据始终有效。最终是否完成同步，需核对远程 main 的完整 SHA 与本地 HEAD 一致；不要把只有本地提交当作最终GitHub交付。

题目未强制仓库名，且允许公开或向评审开放读取权限的私有仓库。这里采用公开仓库，方便评审直接访问；名称包含公司、AI Agent、校招与2027届信息。已选择企业知识问答 Agent，原题未提供数字编号，名称保留不含题号。参考示例仓库仅用于理解结构，不作为实现达标依据。

## 本机配置

2026-10-28 已建立独立 Git 仓库，默认分支为 main。Git 2.47.0.windows.2；GitHub CLI 2.103.3 来自 cli/cli 官方发布，已对照官方校验文件验证 SHA-256。

CLI 安装于项目 `.local-tools/gh/bin/gh.exe`；`scripts/gh.ps1` 负责调用，无需修改系统 PATH。登录配置在 `.local-tools/gh-config`，凭据由 CLI 使用系统凭据库保管；`.local-tools/` 整体被 Git 忽略。脚本不会要求将 token 写入仓库。

用户已在浏览器中完成授权，账号为 Nooo828（ID 75480697）。提交署名使用该账号及 GitHub noreply 邮箱，仅设置本仓库；如原先已有署名，配置脚本会保留。

本机为解决目录所有者检查，在 Git 全局 safe.directory 中仅信任此项目的确切路径；未设置通配信任。GitHub 凭据助手仅配置于本仓库。

配置阶段的真实检查记录见 `examples/github-environment.json`，该历史快照记录创建远程仓库之前的状态。当前远程地址为 `https://github.com/Nooo828/xiaoying-ai-agent-campus-2027.git`；最终线上状态以仓库页面及 `git ls-remote origin main` 为准。

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

当前项目已有企业知识问答实现和真实模型验证材料。后续每次提交前运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git status --short
git diff
git add .
git diff --cached --stat
git commit -m 'Complete selected AI Agent project'
```

本机已有 origin 配置，后续提交后上传：

```powershell
git push origin main
```

在新电脑上直接克隆该仓库：

```powershell
git clone https://github.com/Nooo828/xiaoying-ai-agent-campus-2027.git
cd xiaoying-ai-agent-campus-2027
```

最终提交题目“企业知识问答 Agent”（数字题号需从考试平台补齐）、上述 GitHub URL 和 `git rev-parse HEAD` 的完整 SHA。当前公开仓库无需额外邀请评审账号。六项必验收、三类业务案例及真实模型决策记录见 docs/03-evaluation.md。

`.venv`、`.env`、本地工具与登录配置、Python 缓存均被排除；`.env.example` 可提交。压缩包不包含本地 Git 历史、虚拟环境或登录凭据，不能替代最终 GitHub 交付。
