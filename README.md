# CTKF Community

[中文](#中文) | [English](#english)

## 中文

CTKF Community 把一份几百字或几千字的大白话需求文档，转换成可由
Codex、CatPaw 或 OpenCode 执行的受治理开发包。它不会直接承诺“AI 自动
生成完美软件”，而是先固定原始需求、识别高影响问题、建立唯一 19 阶段
主线，并生成 57 个带输入、输出、依赖、验收条件和验证命令的原子任务。

### 10 分钟快速开始

以下命令安装已检出的正式源码快照，不使用可编辑安装。Windows PowerShell：

```powershell
git clone --depth 1 --branch v0.2.0 https://github.com/gsqlhttyy-ops/ctkf-community.git
cd ctkf-community
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\ctkf-community.exe --version
.\.venv\Scripts\ctkf-community.exe doctor
.\.venv\Scripts\ctkf-community.exe init --requirements examples\booking-product-brief.zh-CN.txt --project generated\booking-demo --ide codex
.\.venv\Scripts\ctkf-community.exe status --project generated\booking-demo
```

macOS 或 Linux：

```bash
git clone --depth 1 --branch v0.2.0 https://github.com/gsqlhttyy-ops/ctkf-community.git
cd ctkf-community
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ctkf-community --version
.venv/bin/ctkf-community doctor
.venv/bin/ctkf-community init --requirements examples/booking-product-brief.zh-CN.txt --project generated/booking-demo --ide codex
.venv/bin/ctkf-community status --project generated/booking-demo
```

然后在 AI IDE 中打开 `generated\booking-demo`，让 AI 先阅读 `RUNBOOK.md`。
如果问题门禁为 `BLOCK`，先回答其中的高影响问题，不要直接开始编码。

### Community 能力

- 保留完整原始需求并记录 SHA-256 来源哈希。
- 支持 UTF-8、UTF-8 BOM 和 GB18030 长文本需求。
- 生成唯一的 19 阶段 APP/网站交付主线。
- 为每个阶段生成“产出、验证、封存证据”三个原子任务，共 57 个任务。
- 自动发现支付、权限、隐私、部署和 AI 使用中的高影响缺口。
- 生成 Codex、CatPaw、OpenCode 可执行的运行手册。
- 在本地验证来源哈希、阶段顺序、任务依赖和任务契约。
- 运行时不依赖第三方 Python 包。
- 通过 `doctor` 检查 Python、终端字符输出、原子文件写入和运行时版本。

Community 是真正可用的基础版本，但只证明本地规划包完整性。真实商用发布
仍需要项目级安全测试、浏览器验证、部署、监控、回滚和真实生产证据。

### Community 与 Pro

Community 永久免费并采用 Apache-2.0。高级多 Agent、长期恢复、商用门禁、
行业模板、高级 UI/UX、生产证据闭环和控制台属于 CTKF Pro。参见
[版本对比](docs/editions.md) 或访问 [CTKF Pro](https://pay.truststream.top/)。

## English

CTKF Community turns a long plain-language requirement document into a governed
execution package for Codex, CatPaw, or OpenCode. It preserves the source,
detects high-impact questions, creates the authoritative 19-stage delivery
mainline, and generates 57 traceable atomic tasks.

Install a tagged source snapshot with `python -m pip install .`, run
`ctkf-community doctor`, and then run `ctkf-community init`. Open the generated
project and follow `RUNBOOK.md`. A passing doctor or Community verification
proves local runtime or planning-package integrity only; neither is a
production-readiness claim.

## Security and license

Do not put credentials or customer data in public issues. See [SECURITY.md](SECURITY.md).
CTKF Community is licensed under [Apache-2.0](LICENSE). CTKF Pro and the private
engineering repository are separate proprietary products and are not covered by
this Community license.
