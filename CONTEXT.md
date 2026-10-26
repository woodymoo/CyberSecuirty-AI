# 项目上下文 — Agent 化漏洞扫描实验(从 Claude.ai 对话迁移)

## 目标

在单台自有测试机(云上 Ubuntu 24.04 LTS,公网 IP,开放端口 22/80/443,
Node.js 站 + 本地 Redis 不对外)上,做授权范围内的智能漏洞扫描/探测/报告。
攻击机:M1 Max MacBook Pro(ARM64),工具跑在 Docker 容器里。
属于个人学习 + 自有资产安全自评估,非商用、非对第三方。

## 这个仓库是什么(重要背景)

- 本仓库是 fork 自 aliasrobotics/cai(归档版 v1.1.5,"CAI",不是商业的 CSI)。
- 真实架构:它把 OpenAI Agents SDK 整个 fork 进 src/cai/sdk(约2.3万行);
15万行里约44%是终端UI(repl+tui),真正的"编排+工具"只占约10%。
- 编排内核 = OpenAI Agents SDK 的 ReAct 循环(Runner.run,见 sdk/agents/run.py):
每轮一次LLM调用 → 三个出口 NextStepRunAgain / FinalOutput / Handoff。
- 多agent靠 handoff()(本质是生成 transfer_to_X 工具),属 swarm 模式。

## 两个必须记住的风险(来自代码审计)

1. 默认遥测回传:src/cai/internal/components/{endpoints,transfer}.py 会把

   session日志POST到 logs.aliasrobotics.com,端点用base64分段混淆,默认开启(opt-out)。
    → 必须 CAI_TELEMETRY=false,并在容器用 --add-host 把 aliasrobotics 域名导向 0.0.0.0。
2. 命令注入 CVE-2025-67511(Checkmarx披露):目标返回内容可致宿主执行命令。

   → 全程在Docker隔离容器内运行;自写工具一律用参数数组,绝不字符串拼接 shell。

## 许可证约束(关键)

LICENSE 是双重许可:src/cai/agents 是 MIT;其余 Alias 自写代码是"Research-Use
License",仅限非商业研究/学术。任何客户/生产/收费用途都违约。学习自用OK。