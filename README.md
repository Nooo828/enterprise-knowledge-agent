# 小影科技2027校招 AI Agent · Python 基础环境

本项目是等待选题的可运行基础骨架。尚未选择 Agent 框架，未实现业务工具或模型驱动 ReAct 循环，不是完整笔试提交答案。

## 已准备内容

- Python 独立虚拟环境 `.venv`（本机已实际创建）。
- openai、pydantic、python-dotenv、pytest、rich。
- src/、tests/、examples/、data/、docs/。
- 离线 CLI、输入校验、冒烟测试、真实验证日志。
- requirements.in（直接依赖）、requirements.txt（当前安装版本锁定）、.env.example、.gitignore。

## 本机直接运行（PowerShell）

先进入此 README 所在目录，然后执行以下命令，无需激活虚拟环境：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --message '环境已就绪'
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

默认输出为 JSON：

```json
{
  "status": "ready",
  "mode": "offline",
  "message": "Hello, Xiaoying Agent!",
  "stage": "environment_only"
}
```

空白 `--message` 返回错误和退出码 2。当前所有路径均不调用模型或网络；无需 `.env`。

## 新电脑安装

本机验证环境为 Windows / Python 3.12.7；建议使用 Python 3.12。`.venv` 与机器路径绑定，不要将其复制到其他位置使用或上传到 GitHub。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

macOS/Linux 可在重新创建 venv 后使用 `.venv/bin/python` 替换上面的解释器路径；当前只在 Windows 实测。

后续需要模型时，可将 `.env.example` 复制为 `.env` 并配置；当前不会读取其中的模型参数发起请求。禁止提交真实密钥或隐私数据。

## 评审入口

- GitHub 上传环境与交付命令见 `docs/06-github-delivery.md`；当前仅配置本地仓库和登录，不创建远程仓库。
- `examples/verification.json`：每条实际验证命令、退出码与记录文件。
- `examples/pytest.txt`：测试实际输出。
- `examples/dependency-versions.json`：解释器、隔离状态与直接依赖版本。
- `docs/01-requirements.md` 至 `docs/05-retrospective.md`：当前范围、设计、验证、AI 使用与后续计划。

## 选题后仍需完成

明确题号和业务验收点，实现至少一个真实模型选择动作、执行工具、观察结果并决定下一步或结束的循环，设置执行上限；保存至少两条不同动态决策路径，并补齐正常、资料不足、工具失败三类业务案例。当前入口与测试不作为上述能力的证明。
