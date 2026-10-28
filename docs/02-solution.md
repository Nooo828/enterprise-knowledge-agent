# 基础设计

调用链：CLI 参数 → 读取项目 .env（可选）→ Pydantic 校验 → Rich 输出 JSON。

当前入口完全离线，不创建模型客户端、不调用业务工具。openai SDK 只安装并验证导入，为后续接入预留；不提前绑定框架。

requirements.in 列出直接依赖；requirements.txt 在安装成功后记录当前环境全部依赖的精确版本。pytest.ini 为测试配置 src 路径。推荐始终直接使用 .venv 中的 Python，无需激活脚本或更改 PowerShell 执行策略。

待题目确定后再实现动作选择、工具执行、结果观察、模型后续决策与结束状态，并设置执行步数/调用次数上限。当前参数校验不是 Agent 决策。
