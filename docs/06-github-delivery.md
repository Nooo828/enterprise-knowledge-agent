# GitHub 交付环境

## 仓库命名与公开范围

交付仓库为 [Nooo828/enterprise-knowledge-agent](https://github.com/Nooo828/enterprise-knowledge-agent)，公开可读，默认分支 `main`。

企业知识问答实现和本地复查修复已完成，用户已恢复上传授权。此前同步因GitHub凭据失效而暂缓；本文件的配置历史不代表凭据始终有效。最终是否完成同步，需核对远程 main 的完整 SHA 与本地 HEAD 一致；不要把只有本地提交当作最终GitHub交付。

仓库使用通用名称 enterprise-knowledge-agent，公开可读，方便查看源码、运行说明和验证材料。项目介绍围绕企业知识问答能力、使用方式和已知限制。

## 本机配置

2026-10-28 已建立独立 Git 仓库，默认分支为 main。Git 2.47.0.windows.2；GitHub CLI 2.103.3 来自 cli/cli 官方发布，已对照官方校验文件验证 SHA-256。

CLI 安装于项目 `.local-tools/gh/bin/gh.exe`；`scripts/gh.ps1` 负责调用，无需修改系统 PATH。登录配置在 `.local-tools/gh-config`；CLI优先使用系统凭据库，不可用时会回退到本机明文配置，本次重新授权采用了该回退方式。`.local-tools/` 整体被 Git 忽略，也不包含在交付压缩包中；不得提交或分享该目录。脚本不会要求将token写入代码或受版本管理的文件。

用户已在浏览器中完成授权，账号为 Nooo828（ID 75480697）。提交署名使用该账号及 GitHub noreply 邮箱，仅设置本仓库；如原先已有署名，配置脚本会保留。

本机为解决目录所有者检查，在 Git 全局 safe.directory 中仅信任此项目的确切路径；未设置通配信任。GitHub 凭据助手仅配置于本仓库。

配置阶段的真实检查记录见 `examples/github-environment.json`，该历史快照记录创建远程仓库之前的状态。当前远程地址为 `https://github.com/Nooo828/enterprise-knowledge-agent.git`；最终线上状态以仓库页面及 `git ls-remote origin main` 为准。

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

## 上传与版本发布

当前项目已有企业知识问答实现和真实模型验证材料。后续每次提交前运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git status --short
git diff
git add .
git diff --cached --stat
git commit -m 'Update enterprise knowledge agent'
```

本机已有 origin 配置，后续提交后上传：

```powershell
git push origin main
```

在新电脑上直接克隆该仓库：

```powershell
git clone https://github.com/Nooo828/enterprise-knowledge-agent.git
cd enterprise-knowledge-agent
```

发布时提供项目名称、上述GitHub URL和 `git rev-parse HEAD` 的完整SHA。当前公开仓库可直接访问。六项核心验收、三类业务案例及真实模型决策记录见 docs/03-evaluation.md。

`.venv`、`.env`、本地工具与登录配置、Python 缓存均被排除；`.env.example` 可提交。压缩包不包含本地 Git 历史、虚拟环境或登录凭据，不能替代最终 GitHub 交付。
