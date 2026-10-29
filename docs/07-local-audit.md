# 本地交付合规检查

结论：本地代码、必需文档和验证材料已具备题目要求，发现的三处边界缺陷已修复。本表记录上传前的本地核对；用户随后恢复了上传授权，远程同步结果须单独核对完整 SHA。本结论是本地实现及合成测试范围内的检查，不保证招聘方评分。

| 考核要求 | 本地结论 | 核查依据 |
|---|---|---|
| 理解用户、目标、范围、成功标准 | 已具备 | 01-requirements.md |
| 可运行CLI、可复制安装/运行命令 | 已具备 | ../README.md、../src/xiaoying_agent/cli.py |
| 模型选择动作→工具→观察→再次决策 | 已实现 | ../src/xiaoying_agent/agent.py、providers.py；每轮decide接收实际observations |
| 不能仅靠固定分支或自动重试 | 真实模式符合 | LiveModel每轮调用真实模型；OfflineMock单独标记，不能当模型效果证据 |
| 至少两条根据结果调整的路径 | 已具备 | ../examples/audit/decision-paths.md；同问题normal/conflict的资料与结束状态不同 |
| 步骤、参数、返回、后续动作和公开依据 | 已具备 | live/*/trace.json保存逐步动作；路径摘录显式列出下一动作，无内部思维过程 |
| 步数/工具调用上限及明确未完成 | 已实现 | 默认12轮、最多30轮；step_limit返回incomplete；工具次数不超模型轮数 |
| 离线入口及Mock边界 | 已具备 | --mode offline_mock；meta.mode与mock_boundary；03-evaluation.md |
| 至少3组正常、资料不足、工具失败 | 已具备且超出最低数量 | live/normal、outside、tool_failure，及其余8组；各有input/corpus/output/trace |
| 所选题全部验收点 | 保存的用例通过 | 明确答案、冲突、资料外、改写、上下文、失败；22组材料离线复核通过 |
| src/tests/examples/data/docs | 全部存在 | ../examples/audit/evidence-audit.json中的required_files |
| 01需求、02方案、03评估、04AI使用、05复盘 | 全部存在且有实质内容 | 本目录对应五份文件；含技术取舍、失败与限制 |
| 依赖、变量示例、框架版本职责 | 已具备 | requirements.txt锁定；.env.example；原生循环，无Agent框架；SDK职责见02 |
| 如实记录AI及个人贡献 | 已具备披露 | 04明确AI产出与用户已知贡献，不虚构手工修改；个人复核待本人补充 |
| 实际用时与未完成项 | 已记录并补全边界 | work-session.json新增首次实现提交时间，约62.90分钟；不等于个人净编码时间 |
| 不提交密钥、隐私资料 | 当前交付文件检查通过 | .env等未被Git跟踪；合成资料；本地文件模式扫描无密钥特征；不等于审计所有旧历史对象 |
| 题号、URL、最终SHA | 最终提交前核对 | 原题未给数字题号；URL已知；最终SHA须与远程main核对 |

## 本次修复

1. 一次检索失败后恢复：离线策略将失败的历史搜索条目当成成功结果，造成incomplete。现只使用成功检索观察，四种故障模式都有回归测试。
2. 非预期工具异常：OSError等会直接退出循环。现转为脱敏的ToolError观察交回决策器，不把异常原文写进Trace。
3. 虚假冲突：同一片段重复引用两次也能满足数量检查。现要求实际观察到同规则的不同原文；相同证据不能据此报告冲突。

修复前记录为../examples/audit/regressions-before-fix.txt；该次复查42项pytest通过，阶段记录见../examples/audit/audit-session.json；当前../examples/tests-final.txt已更新为后续网页版本的66项结果。该次本地复查没有新增真实模型调用；已有11组真实模型结果经当前执行层逐项复核，另外11组历史离线材料也通过。网页阶段另有真实模型验证，见09-web-interface.md。

## 可复制的本地检查

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/audit-local.py
```

最后一条会验证现有资料和Trace并重建决策路径摘录，不发送API请求。没有用新的Mock日志覆盖原来的live记录。

## 正式提交前由候选人完成

从考试平台补齐数字题号（若平台只要求题目名称则使用“企业知识问答 Agent”）；亲自复跑并解释代码、核查引用、补充真实个人修改和学习收获；允许上传后恢复GitHub授权、同步最新本地提交，并核对远程main的完整SHA。当前无需为了凑材料而虚构贡献或重新包装成独立手写成果。

未建设UI、线上部署、多Agent和生产Runtime属于题目明确不强制的范围，不视为材料缺失。规则分组人工维护、保守文本冲突判断、召回和语义相关性局限见03-evaluation.md。
