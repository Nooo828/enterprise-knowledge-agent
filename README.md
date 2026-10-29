# 企业知识问答 Agent · 小影科技2027校招

帮助员工查询合成制度和产品 FAQ。输出答案、文档 ID/版本日期/原文引用、资料缺口、追问和任务状态。

交付题目：**企业知识问答 Agent**（原题未提供数字题号）。公开仓库：[Nooo828/xiaoying-ai-agent-campus-2027](https://github.com/Nooo828/xiaoying-ai-agent-campus-2027)，默认分支 main。最终 SHA 通过 `git rev-parse HEAD` 获取。

当前为本地交付版本；企业知识问答实现及本轮检查修复尚未同步到远程仓库，按用户要求暂缓上传。最终提交前需补齐平台题号、人工复核，并确认远程 SHA 与本地一致。

## 评审先看这里

- [验收结果与限制](docs/03-evaluation.md)：六项必验收场景及扩展检查。
- [真实模型结果](examples/live/summary.json)：DeepSeek 的11组实际执行结果，全部通过本项目断言；不是离线决策日志。
- [正常回答](examples/live/normal/output.json)、[冲突回答](examples/live/conflict/output.json)、[资料外问题](examples/live/outside/output.json)、[工具失败](examples/live/tool_failure/output.json)。每个目录含 input.json、corpus.json、output.json、trace.json。
- [真实冲突 Trace](examples/live/conflict/trace.json)：模型检索、读取双方原文后选择 conflict 并追问；不以版本日期决定优先级。
- [改文档测试](examples/live/mutated/output.json)：D01 从30天改为45天，答案随之改变。[冲突消除](examples/live/resolved/output.json)：两份同规则原文一致后可回答。
- [测试日志](examples/tests-final.txt)：42 passed；[检索改进对比](examples/retrieval-evaluation.json)。
- [本地合规核对表](docs/07-local-audit.md)、[真实决策路径摘录](examples/audit/decision-paths.md)、[22组材料自动复核](examples/audit/evidence-audit.json)。

## 安装与运行

本机实测 Windows / Python 3.12.7。项目使用 Python 原生执行循环，不依赖 Agent 框架。依赖及精确版本见 requirements.txt，直接依赖见 requirements.in。

在项目根目录执行（PowerShell；不要求激活脚本）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？'
.\.venv\Scripts\python.exe -X utf8 -m pytest -q -p no:cacheprovider
```

本机已有 .venv，无需重复创建。macOS/Linux 将解释器路径替换为 `.venv/bin/python`，当前仅在 Windows 实测。

真实模型：复制 .env.example 为 .env，填入自己的 OPENAI_API_KEY。默认官方 DeepSeek 地址为 `https://api.deepseek.com`，模型为 `deepseek-flash`；也可修改为支持函数调用的 OpenAI 兼容服务。API 使用产生服务商费用，ChatGPT 登录不能替代该配置。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode live --question '报销期限多久？' --output examples/manual-run.json
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode live --question '那最晚什么时候交？' --history data/history.json --corpus examples/live/normal/corpus.json
```

默认知识库有30天/15天的刻意冲突。如需单一制度回答，指定 `--corpus examples/live/normal/corpus.json`。CLI 退出码：0=正常交付（包括冲突、追问和资料外结果），2=输入/配置错误，3=工具/模型错误或步数耗尽。结果中的 status 才表示业务状态。

## 复现验证材料

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent.evaluate --mode offline_mock --out examples/offline
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent.evaluate --mode live --out examples/live
.\.venv\Scripts\python.exe -X utf8 scripts/retrieval-eval.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/audit-local.py
```

可通过 `--case conflict --case normal` 仅重跑指定用例。故障注入如 `--fault search_always`；`--max-steps 1` 验证上限。live 不会自动回退 Mock；离线模式显式标记 offline_mock，只证明流程，不证明模型决策质量。

## 设计与范围

每一轮由模型选择 search/read/finish，执行工具后将真实结果交回模型，最多12轮（可设1..30）。搜索使用中文双字、同义词和同规则版本合并；读取工具返回完整原子片段。模型选择引用，执行层核对引用确为本轮读过的完整原文，并生成抽取式答案，降低自由改写引入无依据结论的风险。

每份资料带文档ID、版本日期、rule_key和片段ID。rule_key 是合成知识库人工维护的规则分组，不包含答案或优先级。任何同组原文差异都保守视作潜在冲突；这不是通用语义冲突检测器。详见 docs/02-solution.md。

目录包含 src/、tests/、examples/、data/ 和 docs/01..05。旧的环境初始化记录保留作历史，当前验收以 examples/live/、examples/offline/ 和 tests-final.txt 为准。真实密钥仅放本机 .env，该文件、虚拟环境及登录配置均被 Git 忽略。
