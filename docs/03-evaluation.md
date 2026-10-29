# 测试预期、实际结果与限制

网页界面追加验证：当前完整pytest为66项通过（CLI阶段42项、网页/事件相关24项），当前日志见examples/tests-final.txt。网页功能与本机访问限制见09-web-interface.md；examples/web/保留浏览器操作的实际任务快照、真实模型导出及截图。本段为追加结果，以下42项和11组真实模型记录仍是此前CLI阶段的历史验证。

2026-10-29初版36项pytest测试通过，本地复查补充6项回归测试后共42项通过，依赖检查无冲突，当前原始输出见examples/tests-final.txt和examples/dependencies-final.txt。测试包括六项必验收场景的离线回归、资料变更、伪造引用拒绝、缺读冲突版本拒绝、已知冲突强选单方拒绝、分页保护、模型错误脱敏和并行提议适配。

本地复查还发现并修复三处实际缺陷：offline_mock在search_once恢复后误读历史失败记录；工具抛出OSError等非预期异常时未转为工具观察；重复引用同一原文可被误报为冲突。修复前的实际失败输出保存在examples/audit/regressions-before-fix.txt，修复后回归测试覆盖所有四种故障注入、异常脱敏与虚假冲突拒绝。未改变真实模型的动作选择逻辑。

通过scripts/audit-local.py重新复核已有22组保存材料：资料SHA256、成功检索/读取返回与资料快照一致、引用确在本轮读取过、版本日期与原文一致、结束动作可被当前校验器接受、调用次数受限、文档本地链接有效。报告为examples/audit/evidence-audit.json；这是离线复核历史真实运行证据，不是重新执行22组真实API调用。examples/audit/decision-paths.md由原Trace生成，显式列出下一动作，方便核查至少两条动态路径。

真实模型由用户提供的DeepSeek账号接入，模型名deepseek-flash。examples/live/summary.json的11组用例全部通过预设客观断言；examples/offline/summary.json同样11组通过，但仅验证流程。实时调用有随机性，复跑结果可能不同。测试通过不代表通用企业知识问答质量已被证明。

| 用例目录（均位于examples/live/） | 预期与实测 |
|---|---|
| normal | answered，引用30天 |
| conflict | conflict，引用D01的30天与D02的15天，含缺口与追问 |
| outside | not_found，无伪造引用 |
| paraphrase | answered，改写问题仍引用30天 |
| context | answered，根据历史查报销，引用30天 |
| tool_failure | tool_error；故障注入令真实检索工具持续失败，模型根据错误决定停止 |
| tool_recovery | answered；一次读取错误后恢复，引用30天 |
| mutated | answered，原文改45天后答案含45天、不含旧30天 |
| resolved | answered，D02改为与D01相同后不再报告冲突 |
| product | answered，引用PDF和Markdown |
| step_limit | incomplete，执行1步后停止 |

每个目录的input.json是问题、历史、故障配置与上限；corpus.json是当次资料；output.json是真实输出；trace.json含动作、参数、实际工具返回、公开依据、调用计数、耗时与token用量。断言定义在src/xiaoying_agent/evaluate.py，可执行复核状态、关键事实、引用逐字匹配和上限。断言并非独立人工语义评审，应结合原文审查相关性和冲突表述。

真实路径不是预设日志：normal与conflict使用同一问题但不同资料，模型结束状态和引用不同；mutated保持D01标识只改文本，引用与答案变化；resolved令两个版本一致，冲突状态随之消失。故障由工具适配层注入，不能解释为真实服务发生了事故。

检索对比：examples/retrieval-evaluation.json，四条人工合成查询，基础双字检索的宏平均Recall@5为0.5，加入同义词和同规则版本合并后为1.0。包括“报账时限”“居家上班”等。样本很小且规则针对这些业务词，不支持泛化质量结论；没有报告未测过的向量检索收益。

失败与修复：初版把模型一次多个动作当协议错误，导致normal等用例incomplete，见examples/experiments/initial-live-summary.json与initial-normal-trace.json。验证后改为只执行第一项并重规划；tests/test_agent.py包含回归测试。离线Mock也曾在一次失败恢复后不断重试历史失败动作，已修复为仅处理最新错误，tool_recovery测试覆盖。

已知限制：规则分组人工维护，文本差异检测可能产生保守误报；不支持开放域语义冲突或复杂条件优先级；查询召回不保证完整，未发现的规则无法由引用保护补救；引用逐字匹配只证明来源真实，不能自动证明其与问题语义相关；合成资料与固定问法覆盖有限；仅本机Windows实测。文档/历史被提示为不可信数据，但没有宣称完成系统性提示注入安全评估。模型超时、协议错误返回incomplete，不自动回退Mock。现已新增本地UI，但仍无生产权限、多租户或在线部署。

examples/根目录旧的环境冒烟输出来自10月28日基础环境阶段，保留历史，不替代本题验收。pytest关闭缓存仅避免本机缓存目录权限影响，不跳过测试。
