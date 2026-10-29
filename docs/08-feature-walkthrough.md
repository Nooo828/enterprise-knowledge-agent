# 逐项需求拆解与本地运行

本教程保留CLI阶段的逐项核对和历史结果。后续新增可视化网页界面，当前完整测试为66项；启动与网页操作见09-web-interface.md。

本轮按项目需求重新核对代码、已有真实模型记录，并实际执行了8条离线CLI演示。42项自动化测试通过；22组既有材料复核通过。本轮不调用模型API，不修改远程仓库。CLI演示结果见../examples/walkthrough/summary.json，真实模型历史结果见../examples/live/summary.json。

## 1. 项目的核心目标

系统应先找企业资料、核对原文，再决定如何回答。正确结果不总是给出一个数字：证据充分可回答，冲突需列出双方并追问，没资料就说明缺口，工具坏了则报告无法完成。不能用模型常识或文档日期代替制度依据。

## 2. 功能逐项对照

| 功能 | 细化需求 | 当前实现与证据 | 结论 |
|---|---|---|---|
| 问题及历史输入 | 问题非空；历史可选且不直接当事实依据 | schemas.py的Request/Message，cli.py的--question/--history；context案例重新检索 | 已实现 |
| 合成制度/产品资料 | 有稳定文档ID、版本日期与原文 | data/knowledge.json；Document/Chunk校验；D01..D06 | 已实现 |
| 检索工具 | 接收模型检索词，返回命中ID、片段ID与摘要 | KnowledgeBase.search；中文双字、同义词、权重、同规则版本合并和分页 | 已实现；不是通用语义搜索 |
| 原文读取工具 | 按检索定位读取可引用完整片段 | KnowledgeBase.read；读到的原文和日期进入实际观察 | 已实现 |
| 动态模型决策 | 每次根据实际结果选择补检、读取、追问或停止 | LiveModel.decide；Agent.run每轮回传observations；normal/outside实际有补检 | 已实现；不是固定编排日志 |
| 追问 | 冲突或问题不明确时给出需要补充的信息 | finish的conflict/needs_clarification与clarification；冲突案例实际追问适用主体/制度 | 已实现；CLI需传历史，追加网页支持继续追问 |
| 有依据回答 | 最终事实来自已读原文，并有文档ID、版本和片段 | _finish核对quote完全等于本轮已读取片段；答案抽取生成 | 已实现；不等于自动保证语义相关性 |
| 资料缺口与状态 | 区分缺资料、冲突、工具故障和超限 | status/gaps/clarification；not_found/tool_error/incomplete等 | 已实现 |
| 冲突查证 | 读取双方，不凭日期选15天，不遗漏一方引用 | 同rule_key检查；缺读版本或强选单方会拒绝finish；conflict真实引用D01/D02 | 已实现于人工分组范围内 |
| 文档替换 | 不硬编码30天，修改资料应影响结果 | mutated为45天；resolved将D02改成同一30天后返回answered | 样例已通过 |
| 终止与Trace | 有上限、错误路径、步骤参数与后续动作 | 默认12轮，最多30；step_limit明确incomplete；trace与decision-paths.md | 已实现 |

源码位置：../src/xiaoying_agent/schemas.py、knowledge.py、providers.py、agent.py、cli.py。对应说明见02-solution.md，验收边界见03-evaluation.md。

## 3. 六项必验收

| 验收项 | 已保存真实模型案例 | 预期/已有实际结果 |
|---|---|---|
| 明确答案 | live/normal/ | 单一30天规则，answered且引用D01 |
| 文档冲突 | live/conflict/ | D01=30天、D02=15天；conflict、双方引用、缺口和追问 |
| 资料外问题 | live/outside/ | 补检无资料，not_found |
| 改写相似问题 | live/paraphrase/ | 报账/最晚等表达，仍依据30天规则 |
| 上下文追问 | live/context/ | 用历史解析报销主题并重新查证 |
| 工具失败 | live/tool_failure/ | 故障注入下模型尝试调整后停止，tool_error |

上述目录均位于examples/。每个案例含input.json、corpus.json、output.json、trace.json。故障是明确注入的，不代表真实企业服务出现过事故。更多路径摘录见../examples/audit/decision-paths.md。

## 4. 本机开始运行

打开PowerShell，先进入现有本地项目根目录：

```powershell
Set-Location -LiteralPath 'C:\Users\17739\Documents\Codex\2026-10-28\referenced-chatgpt-conversation-this-is-an\outputs\xiaoying-agent-python'
```

本机Python3.12.7、.venv及.env已存在；本轮只检查配置存在，没有输出密钥，也没有重新验证在线密钥有效性。无需激活虚拟环境，直接使用.venv内解释器。

### 先运行单一制度的离线答案

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？' --corpus examples/live/normal/corpus.json
```

预期result.status为answered、答案含30天。指定的corpus只是保存的合成资料快照，不会重放旧模型答案；程序会读取该资料并执行本次决策循环。offline_mock使用确定性策略，只验证流程。

### 再运行默认冲突资料

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？'
```

默认data/knowledge.json故意包含D01=30天与D02=15天；预期conflict，同时列出原文，并请求确认适用制度。冲突是正确的业务交付，不是程序崩溃。

### 使用真实DeepSeek模型

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode live --question '报销期限多久？' --output examples/my-run.json
```

--mode live才会调用真实模型，需网络、有效密钥和服务额度，产生服务商调用费用。配置从项目.env读取，变量名称为OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL，DeepSeek复用兼容接口名称。已保存的真实运行采用https://api.deepseek.com和deepseek-flash；当前服务是否可用以你的实际运行结果为准。

不要把.env内容复制到截图、聊天或GitHub。如需修改，用本机文本编辑器打开.env；不要用.env.example覆盖已有密钥。换新电脑时才复制.env.example并填写自己的密钥。

### 看输出

终端和--output文件均为JSON。主要看result.status、result.answer、result.citations、result.gaps、result.clarification；trace记录过程，meta记录模式、上限及调用次数。PowerShell中$LASTEXITCODE为进程退出码：0是正常业务交付（含冲突/追问/资料外）；2是输入/配置问题；3是未完成或工具/模型失败。

这是单任务CLI：每次命令处理一次请求。带历史的追问需传入--history文件，不会自动保留上条终端命令的会话；不传--question则只运行旧的环境冒烟检查。

## 5. 逐个体验其他场景

以下命令也已离线实测通过，可将offline_mock改为live体验真实模型（会产生API调用）。

```powershell
# 资料外
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '火星上有多少只独角兽？'
# 改写问题
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报账最晚能隔多长时间提交？' --corpus examples/live/normal/corpus.json
# 上下文：history.json说明前一话题为报销
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '那最晚什么时候交？' --history data/history.json --corpus examples/live/normal/corpus.json
# 工具持续失败：预期tool_error，退出码3
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？' --fault search_always
# 执行上限：预期incomplete，退出码3
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？' --max-steps 1
# 修改过的同ID资料：预期45天
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent --mode offline_mock --question '报销期限多久？' --corpus examples/live/mutated/corpus.json
```

## 6. 一次性验证

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/audit-local.py
```

本轮实测42 passed、依赖无冲突、22组已有材料复核通过。最后一条只检查已有文件，不调用模型。需要重跑整套问答时，建议保存到新目录，保留旧运行记录：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent.evaluate --mode offline_mock --out examples/my-offline-eval
.\.venv\Scripts\python.exe -X utf8 -m src.xiaoying_agent.evaluate --mode live --out examples/my-live-eval
```

## 7. 需要准确理解的限制

人工维护rule_key，所有同组文本差异都保守算潜在冲突，不能替代通用语义判断；同义词改进目前只在四条人工查询上测得Recall@5从0.5到1.0，不能当通用基准；逐字引用证明来源真实，仍须人工检查引用与问题是否相关；没有自动跨命令会话记忆、企业权限系统或线上服务。冲突追问已有真实运行证据，但无历史的模糊指代等未做完整开放域质量评估。

这些边界不影响当前六项合成验收已通过的事实，也不应被描述为更广泛的能力保证。本教程记录本地核对过程；用户随后恢复了上传授权，最终远程交付以main实际提交及SHA核对为准。
