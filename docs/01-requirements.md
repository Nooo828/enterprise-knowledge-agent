# 用户、目标与验收

用户为查找企业制度及产品说明的员工。目标是返回可核查依据，在资料不足或冲突时明确边界并请求补充信息。

输入为非空问题（最多2000字符）及可选对话历史（最多10条 user/assistant 消息）。资料均为合成文本，带文档ID、ISO版本日期、片段ID和人工维护的规则分组。输出包含 status、answer、citations（doc_id/chunk_id/version_date/quote）、gaps 和 clarification；运行包附加 trace 与 meta。

| 必验收点 | 成功标准 | 实际材料 |
|---|---|---|
| 明确答案 | 单一制度返回30天及原文引用 | examples/live/normal/ |
| 文档冲突 | D01/D02均引用，说明30/15天冲突并追问；不选更新版 | examples/live/conflict/ |
| 资料外问题 | 不凭常识猜测，not_found并说明缺口 | examples/live/outside/ |
| 相似问题改写 | 报账/最晚/多长时间问法仍找到报销规则 | examples/live/paraphrase/ |
| 上下文追问 | 根据历史解析“那最晚什么时候交”，重新查证 | examples/live/context/ |
| 工具失败 | 检索持续失败时tool_error，不冒充资料外问题 | examples/live/tool_failure/ |

扩展验收为一次读取失败后恢复、30天改45天、冲突消除、产品FAQ、步数上限。答案与引用必须一致；每项都有输入、当次完整资料快照、实际输出和模型动作记录。

范围是CLI与本地合成知识库。不建设UI、在线部署、多Agent、数据库或通用企业权限系统。数字题号未提供，提交时使用题目名称并由候选人补齐平台要求的编号。

模型必须从真实工具结果继续决策。固定流程只可用于执行和校验；offline_mock 是单独标识的确定性测试替身。真实执行不自动降级为Mock。
