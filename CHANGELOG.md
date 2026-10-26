# Changelog

本项目变更记录,格式参考 [Keep a Changelog](https://keepachangelog.com/)。

## [Unreleased] — 2026-10-25 · 安全加固 fork

非商业自用的安全加固分支,移除上游归档版(v1.1.5)中默认开启的回传与许可
后门,并清除仓库内所有 `aliasrobotics` 地址与品牌引用。

### Security / Removed
- **遥测回传**:`CAI_TELEMETRY` 默认改为 `false`(opt-in);在唯一上传咽喉
  加 fail-closed 开关;删除 `internal/components/` 的 `endpoints.py`(混淆的
  `logs.aliasrobotics.com/upload` 端点)、`transfer.py`(上传)、`network.py`
  (连通性探测)三个文件——即便误开 `CAI_TELEMETRY=true` 也无目的地可传。
- **LLM 网关**:默认兜底由 `api.aliasrobotics.com:666` 改为 `api.openai.com`;
  消除"非 alias 模型未配置 `OPENAI_API_BASE` 时静默回退 Alias 并把
  `OPENAI_API_KEY` 当 Bearer 发出"的凭证泄露路径;删除各处写死的 alias 网关分支。
- **License 后门**:移除 `util_ext.py` 的嵌入公钥、`:665/:666` 校验端点、系统
  指纹采集、RSA 签名验证与远程 key 回传;`_chk()` / `_license_off()` 固定为
  no-op(启动永不联系 Alias、永不 kill-switch,更新只走公共 PyPI);删除
  `tools/license_check.py`(机器绑定 + 签名 + 验证端点的完整后门)。
- **品牌/地址清除**:README、docs、`pyproject.toml`、`mkdocs.yml`、`CITATION.cff`、
  `.gitleaks.toml`、SVG、notebook 等中所有 `aliasrobotics` 地址重定向到 fork
  仓库;删除 Alias 网关压测脚本(`tools/{rpm,tpm,timeout}_test.py`)。

### Fixed
- 为 **CVE-2025-67511**(`run_ssh_command_with_credentials` 命令注入)新增回归
  测试。该漏洞在 v1.1.5 已用 `shlex.quote` + 端口整数校验修复(影响 ≤ 0.5.9),
  测试锁定该修复不被回退。

### Notes
- 默认 `CAI_MODEL` 仍为 `alias1`;请设置自己的 `CAI_MODEL` 与 `OPENAI_API_BASE`。
- `LICENSE` 保留 Alias Robotics 的版权署名:`src/cai` 的专有代码仍受
  Research-Use License(仅非商业研究)约束,本次加固未改变该法律约束。
