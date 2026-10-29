# 运行材料索引

- live/：真实DeepSeek，11组实际输入、资料快照、输出和Trace；summary.json为预期/实际及断言结果。
- offline/：确定性Mock，同样11组，仅验证流程。
- experiments/：初次真实模型兼容失败，保留改进依据。
- retrieval-evaluation.json：四条合成查询的检索前后对比。
- tests-final.txt、dependencies-final.txt：最终可执行测试和依赖检查原始输出。
- work-session.json：本轮实际会话墙钟时间和工作范围。
- audit/：本地合规复核、三项修复前失败记录、显式下一动作路径摘录，以及本轮复查耗时记录。不会触发真实模型调用或上传。

每份Trace的meta包含运行模式、模型、资料SHA256、上限、模型/工具次数、耗时、token用量和丢弃的并行提议数。steps中的每项包含动作参数、公开依据与工具观察，下一项就是模型观察后的下一步；不保存内部思维过程。

根目录其余10月28日环境记录只保留历史。任何Mock、工具故障注入或已知限制均不作为未实际发生的模型/工具效果证据。
