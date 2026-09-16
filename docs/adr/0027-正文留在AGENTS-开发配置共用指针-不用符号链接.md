---
status: proposed
date: 2026-09-15
---

# 正文留在 AGENTS.md，开发配置共用指针，不用符号链接

本仓原先把共同约束放在 `AGENTS.md`，`CLAUDE.md` 用 `@AGENTS.md` 导入，再独占 issue tracker、triage labels、domain docs 三段配置。#57 要确认 Codex 实际收到什么，并核实上游的反向符号链接在 Windows 上能否使用。本记录及相应文件改动待开发者裁定，尚未宣称接受。

## 建议裁定

保留 `AGENTS.md` 为普通文件、为共同正文的唯一来源；`CLAUDE.md` 也是普通文件，只保留 `@AGENTS.md`。三段配置描述的都是通用开发工作，不是 Claude 专属能力，应让两侧看到同一组入口：在 `AGENTS.md` 的长约定指针旁加一行，按 issue 操作、分诊、领域探索三个触发条件，指向已有的 `docs/agents/` 文档。五角色标签的完整词表仍在 `triage-labels.md`，不复制一份。

这符合 AGENTS.md 只收硬边界、结构不变量与长约定指针的边界；不把三篇长文整体塞进每轮上下文，也不建立新的配置文件。后续 #54、#59 以这份共同正文为修改入口。

## Codex 实跑记录

2026-09-15（America/Los_Angeles），Windows 开发机，基线 `70211259498e9ef58f4923ca1b532c656fee14b8`。材料只有仓库指令与合成标记，没有案件材料。

1. 在本仓根目录的真实 Codex 会话中执行 `$implement #57`。调用读文件工具之前，模型上下文已含以 `# AGENTS.md instructions for` 为标题的根文件全文，含硬边界、七条结构不变量、长约定指针与「本文件写什么」末段；没有 CLAUDE.md 的三段配置。随后用工具读取 CLAUDE.md 才得到它们。后读文件不能算启动时已注入。
2. 本机 `codex --version` 为 `codex-cli 0.154.0`。在仓库根运行 `codex debug prompt-input 'Report instruction sources.'`，解析 JSON，只检查以 `# AGENTS.md instructions for` 开头的消息，不保存其余提示词或用户配置。用 `File.ReadAllText('AGENTS.md').Trim()` 与该消息做完整子串比较，得到下表。

| 检查项 | 修改前结果 |
| --- | --- |
| 根 AGENTS.md 全文是否包含 | true |
| `### Issue tracker` | false |
| `### Triage labels` | false |
| `### Domain docs` | false |
| `@AGENTS.md` | false |

3. 在临时 Git 仓库中建根 `AGENTS.md`（内容 `ROOT_PROBE_57` 与下一行 `@extra.md`）、`extra.md`（`IMPORT_PROBE_57`）、`CLAUDE.md`（`CLAUDE_PROBE_57`）、`child/AGENTS.md`（`CHILD_PROBE_57`）。在 `child/` 运行同一诊断命令，筛选相同消息后得到：

| 检查项 | 结果 |
| --- | --- |
| 根标记 `ROOT_PROBE_57` | true |
| 子目录标记 `CHILD_PROBE_57` | true |
| 字面引用 `@extra.md` | true |
| 被引用文件正文 `IMPORT_PROBE_57` | false |
| CLAUDE.md 正文 `CLAUDE_PROBE_57` | false |

当前配置下，Codex 加载了根与当前子目录两层 AGENTS.md；CLAUDE.md 未自动加载，AGENTS.md 中的 `@` 也没有展开。不能把 Claude 的导入语法当作 Codex 的加载协议。根目录实跑与隔离诊断分别记录：后者检查模型可见输入，不是另一次模型推理，也不能证明模型每次都遵守全部规则。

4. 移入三个开发指针后，在本仓根目录重跑诊断：根 AGENTS.md 全文包含为 `true`，`docs/agents/issue-tracker.md`、`docs/agents/triage-labels.md`、`docs/agents/domain.md` 三个路径均为 `true`。这证明指针已进入模型可见输入，不代表三个目标文档自动全文加载。

[OpenAI 的 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)是加载规则的查阅入口；本次结论依据上述本机实测，不外推到所有客户端、用户配置或未来版本。

## Windows 符号链接实测

本仓 `git ls-files -s AGENTS.md CLAUDE.md` 的两项 mode 均为 `100644`；`git config --show-origin --get core.symlinks` 显示 `.git/config` 中为 `false`。

在临时 Git 仓库内，以普通用户权限做了两种实验，未修改本仓 Git 配置：

- PowerShell `New-Item -ItemType SymbolicLink` 创建指向普通 CLAUDE.md 的链接，报 `Administrator privilege required for this operation.`。
- 用 `git hash-object -w` 写入内容为 `CLAUDE.md` 的 blob，`git update-index --add --cacheinfo 120000,<blob>,AGENTS.md` 登记为链接。`git -c core.symlinks=false checkout-index --force AGENTS.md` 成功，但落地为普通文件，正文只有 `CLAUDE.md`。删除这一临时文件后，用 `core.symlinks=true` 重试，退出码 1，报 `unable to create symlink AGENTS.md: Permission denied`。

所以本机当前权限与检出配置下，不能直接照抄上游 `AGENTS.md -> CLAUDE.md`。即使 Git 保存了 mode `120000`，默认检出也会丢掉正文，只给 Codex 一个目标文件名。这里证明的是本机当前环境不可行，不是 Windows 永远不支持符号链接；本票不要求提权、更改开发者模式或改全局 Git 配置。

## 取舍与验收边界

- 完全维持现状会继续把三段通用开发配置藏在 Codex 不自动加载的文件里；本次将入口共用，解决这处可见性差异。
- 反转正文并用符号链接复用，受上述本机检出和权限问题阻挡；复制两份全文又会产生两个维护源。
- 保留现有 Claude 导入方向，不以这次 Codex 实测冒充 Claude 侧导入的新证据。
- 本票只改指令文件与决策记录，没有运行代码变更，无适用的 TDD 接口或类型检查命令，不新增镜像正文的单元测试。文本、登记、接线及插件校验按仓库约定执行；脚本全套回归按 implement 流程执行。
- ADR 先以 `proposed` 提交供审阅，按 #57 评论「结论的裁定与 ADR 落字要人过」，开发者确认后才改为 `accepted`；本次不关闭 issue。实跑记录可作为 PR 的验收证据。
