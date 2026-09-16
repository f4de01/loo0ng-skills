# AGENTS.md / CLAUDE.md 该写什么：主动写，还是违反一次再写

> **写于** 2026-09-05，对应 issue #9「编排层与参考层的 skill 清单」Q15。
> **来源等级**：本机一手原文（Matt Pocock skills 插件缓存 `mattpocock-skills/1.2.3`、Obsidian《mattpocock-skills 拆解报告 1》、本仓库文件、`docs/research/` 既有调研）为主；两平台官方文档本轮**未重新抓取**，凡引用官方说法的，标「未核实」并注明是转述。
> **红线**：不含任何案件材料。全文不用破折号。

---

## 0. 一句话结论

这类文件不是"规则手册"，是**每一轮都会整篇塞进模型脑子里的便签**。便签只该写三种东西：不能碰的硬边界、违反了产品就坏的结构不变量、指向长文档的一行指针。至于"模型该怎么做事"的行为要求，只在真实用起来发现它做错了之后再写一条，并附上那次的日期与出处。Matt 的做法与本仓库现行元规则并不冲突，它们各管一类内容；冲突的只是"什么都等违反一次"这一句话太宽。

---

## 1. 这个文件在两个平台里是怎么被用的

**它会被自动读进上下文，每一轮都在。** 模型回答你的每一句话时，这份文件都完整躺在它面前，不是"需要时去查"。所以文件里的每一行，都在每一轮花掉一点模型的注意力，不管这一行这轮用不用得上。

| | Claude Code | Codex |
| --- | --- | --- |
| 读哪个文件 | `CLAUDE.md`（仓库根、父目录、`~/.claude/CLAUDE.md`），**不读 `AGENTS.md`**（转述自 #11 调研的来源注：code.claude.com/docs/en/memory「只读 CLAUDE.md 不读 AGENTS.md」） | `AGENTS.md`（`~/.codex/AGENTS.md` 加仓库根到当前目录一路上的每一份，拼接；**未核实**，凭记忆转述） |
| 能不能引用别的文件 | 可以：`@路径` 一行把另一个文件的内容整段导入（转述自同一来源） | 文档未见导入语法；**推测**只能靠正文里"见 x 文件"让模型自己去读 |
| 有没有大小建议 | 官方说法是"保持简短、人能读"（转述自 Anthropic《Claude Code best practices》，**未核实**） | 有字节上限的配置项（`project_doc_max_bytes`，默认约 32 KiB，**未核实**） |

**对本仓库的直接后果**：本仓库 `CLAUDE.md` 现在只写了一句"权威指令文件是 `AGENTS.md`"。Claude Code 不会自动读 `AGENTS.md`，这句话只是请模型自己去读，读不读看它心情。改成 `@AGENTS.md` 一行导入，才是真正"每轮都在"。

---

## 2. 写一行的代价：Matt 的"两种负担"与"空话检验"

Matt 在 `writing-for-agents/SKILL.md` 里把这件事说透了。

**两种负担**（原文）：

> Context load is the cost of always-loaded material on the agent's window: an `AGENTS.md` line, a skill description, anything sitting in context every turn, spending tokens and attention whether or not it fires.
> （上下文负担：一直挂在模型窗口里的东西的代价，`AGENTS.md` 的一行、skill 的描述，凡是每轮都在的，无论这轮用不用得上，都在花 token 和注意力。）

> Cognitive load is the cost on the human: which documents exist and when to reach for each. The human is the index. Not a cost to minimise: it is the price of human agency.
> （认知负担：人要记住有哪些文档、什么时候去翻。人就是索引。这不是要压到零的成本，它是人保有决定权的代价。）

大白话：往 `AGENTS.md` 里多写一行，模型每轮都多读一行，它对其他行的注意力就薄一点。写少了，人要多记一点。两边都是成本，不是"写进去就万无一失"。

**该内联还是推到指针后面**（原文）：

> inline what every branch needs, and push behind a pointer what only some branches reach.
> （每条路径都要用的写在正文，只有某些分支才碰到的放到指针后面。）

**别写环境里本来就查得到的东西**（原文）：

> Cache what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha no config confesses. Leave the one-file, one-command lookups to the environment, where they cannot go stale.
> （只缓存模型自己查不到的：不成文的约定、某个选择背后的原因、配置文件不会告诉它的坑。一个文件、一条命令就能查到的，留给环境，那里不会过期。）

**空话检验**（原文）：

> Hunt no-ops sentence by sentence: an instruction the model already obeys by default pays load to say nothing. The test (does it change behaviour versus the default?) is model-relative … settle it by running the document, not by debate. When a sentence fails, delete the whole sentence.
> （逐句找空话：模型默认就会做的事，写出来只是白花负担。检验标准是"比起不写，它的行为变了吗"，这要靠跑一遍看，不靠争论。一句话过不了检验，整句删。）

**少用禁止句**（原文）：

> steering by prohibition drags the forbidden behaviour into context and makes it more available, not less … Prompt the positive.
> （用"不要"来驾驭，反而把被禁的行为拖进上下文，让它更容易出现。要写"要做什么"。）

这一条就是"违反一次才写"的理论根据：你事先猜模型会犯什么错、写一堆"不要"，很可能既是空话，又把错误行为提示给了它。真发生过一次，你才知道这一行不是空话。

---

## 3. Matt 自己往里写了什么、没写什么

他自己仓库的 `CLAUDE.md` 逐段归类（原文在插件缓存根目录）：

| 段 | 内容 | 类型 |
| --- | --- | --- |
| 1 | `skills/` 分五个桶，各桶什么状态 | 结构说明（目录看不出的"为什么"） |
| 2 | promoted 桶里的 skill 必须同时出现在 `README.md` 与 `plugin.json` 的 `skills` 数组 | 结构不变量 |
| 3 | 安装命令照抄 `.agents/install-block.md`；改清单后跑 `claude plugin validate . --strict`；为什么只出 Claude 插件见 ADR-0002 | 指针 + 不变量 |
| 4 | README 里 skill 名必须链到它的 `SKILL.md` | 结构不变量 |
| 5 | 每个桶有自己的 README，分 User-invoked / Model-invoked 两组 | 结构不变量 |
| 6 | promoted skill 有文档页，写法见 `.agents/writing-docs.md` | 不变量 + 指针 |
| 7 | 每个 SKILL.md 要么 user-invoked（两个旗子都设）要么 model-invoked，细则见 `.agents/invocation.md` | 不变量 + 指针 |
| 8 | 增删改名 skill 必须重读并更新 `ask-matt`，「a router that lies」 | 结构不变量 |
| 9 | 改完重跑 `scripts/link-skills.sh` | 操作不变量 |
| 10 | 全仓禁破折号，遇到就改写句子 | 风格规则（唯一一条"行为"类，且写成了"改用逗号、冒号…"的正向句） |

计数：结构不变量与指针 9 段，行为/风格 1 段，"模型应当如何思考、如何工作"的要求 0 段。工作方法全在各 skill 的正文里，不在 `CLAUDE.md`。

他往**别人**仓库写的（`setup-matt-pocock-skills` 落盘的 `## Agent skills` 块）更极端：三个小节，每节一行摘要加一个 `See docs/agents/x.md` 指针，长内容全在 `docs/agents/` 里。`domain.md` 种子模板还规定：`CONTEXT.md`、`docs/adr/` 不存在时**静默跳过**，不要预先建空文件，由 `/domain-modeling` 在真正解决术语时惰性创建。这是同一种精神：不预写，用到才有。

他的 ADR-0001 把"要不要在 skill 里写 setup 指针"也分了硬软：

> Hard dependency … Without the mapping, output is wrong, not just fuzzy. Soft dependency … If the docs aren't there, the skill still works; output is just less sharp. … avoids cargo-culting the setup pointer into places where it isn't load-bearing.
> （硬依赖：没有配置输出就是错的，不只是模糊。软依赖：没有文档也能跑，只是没那么锐利。避免把 setup 指针照抄到不承重的地方。）

"承重"（load-bearing）就是判据：一行字要么承重，要么删。

---

## 4. 官方文档建议写什么（转述，本轮未重新抓取）

- **Claude Code**（Anthropic《Claude Code best practices》，**未核实**）：常用命令、核心文件与工具函数、代码风格、测试方法、仓库礼节（分支、合并习惯）、开发环境的怪癖与警告；"保持简短、人能读"；"像调提示词一样迭代它，看它有没有改变行为"。
- **Codex / agents.md 规范**（**未核实**）：把它当"给 agent 看的 README"：项目概览、构建与测试命令、代码风格、测试要求、PR 要求。
- 两家共同点：写的都是**事实与约定**（怎么跑、怎么放、什么不许），不是"请你认真""请你严谨"这类对模型态度的要求。这与 Matt 的"空话检验"一致。

---

## 5. "违反一次才写"从哪来、什么时候成立、什么时候不成立

**来源**：legal-skills 调研的 J11（`docs/research/legal-skills-与本项目交叉对比.md` L134）："规则带「被违反的那一次」的日期与出处"，出自那个仓库各 CHANGELOG 里大量"背景：实际使用中发现"的条目（独立调研 §六列了 16 条）。同一份调研的缺陷 1 是反面教材：它的 `AGENTS.md` 要求每个 skill 带 DECISIONS/TASKS，`.gitignore` 却全局忽略，规则写了没人守（§1.5 执行率 4/63）。教训是两句：**没被现实检验过的规则，多半是空话**；**规则要带出处，读的人才知道它承不承重**。

**成立的范围**：对**行为规则**成立。"模型该怎么做事"事先猜不准，猜错了就是空话或反向提示（第 2 节）。真发生一次，你拿到的是一条被验证过承重的规则，还顺手拿到了它的出处。

**不成立的范围**：对**结构不变量**不成立。"每个 skill 必须登记进 `plugin.json`""改名必改路由表"这类规则，违反的后果不是"模型表现差一点"，是产品直接坏（插件缺 skill、路由指向不存在的入口）。它们不是对模型行为的猜测，是配置的一部分，与 `plugin.json` 本身同级。等它坏一次再写，付的是一次事故的钱，换不到任何信息。Matt 的 `CLAUDE.md` 主动写的恰好全是这一类（第 3 节）。

**也不成立的范围**：**硬边界**。本仓库两条硬边界（案件材料永不入库、办案会话对仓库只读）违反一次的代价不可接受，当然主动写。这一点现行 `AGENTS.md` 已经这么做了，它自己就没等违反。

所以两者不冲突，只是现行元规则那句"一条规则只在真实使用里被违反过一次之后才写进本文件"把"规则"一词用得太宽，把结构不变量也罩了进去。

---

## 6. 对本仓库的建议（给律师拍板用）

`AGENTS.md` 分四段，每段各有一条"进入规则"：

```markdown
# 律师工作台 3.0
一句定位。（保留现状）

## 硬边界（不上桌）           ← 主动写，已有两条，不动
1. 案件材料永不入本仓库……
2. 办案会话对本仓库只读……

## 结构不变量                 ← 主动写，每条一行，不解释理由（理由在 ADR）
- 每个 skill 同时登记在根 README 与 plugin.json；改完跑 claude plugin validate . --strict
- 增删改名 skill 必更新 ask-loo0ng 的入口表
- 每个 SKILL.md 两个旗子同真同假（user-invoked / model-invoked）
- 改动 skills/ 后重跑 scripts/link-skills.ps1
- 领域目录只有三样：领域图、官方模板原件、指引手册原文

## 约定                       ← 一行指针，长文放 .agents/registration.md
命名与前缀见 `.agents/registration.md`，description 两套写法见 `.agents/invocation.md`，发布流程见 `.agents/release.md`。

## 行为规则                   ← 违反一次后才写，附日期与出处（J11）；现在为空
（空）
```

三条进入规则，替换现行那一句元规则：

1. **硬边界与结构不变量主动写**：违反的后果是产品坏或红线破，不等事故。
2. **约定推到指针后面**：`AGENTS.md` 只留一行"见 x"，正文按主题在 `.agents/`（调用规则与 Matt 的 `.agents/invocation.md` 同位）。
3. **行为规则违反一次才写**：写入时附日期与出处；写之前先过"空话检验"（不写它，模型会不会做错）。

另加一条本轮发现的修正：`CLAUDE.md` 改为 `@AGENTS.md` 导入，让 Claude Code 也真的每轮读到它。

---

## 7. 来源清单

- `C:\Users\32892\.claude\plugins\cache\claude-plugins-official\mattpocock-skills\1.2.3\CLAUDE.md`
- 同上 `skills/productivity/writing-for-agents/SKILL.md`（Context pointers、The two loads、information hierarchy、no-ops、Negation）
- 同上 `.agents/invocation.md`、`.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md`
- 同上 `skills/engineering/setup-matt-pocock-skills/SKILL.md`、`domain.md`
- `C:\Users\32892\Documents\Obsidian Vault\知识\mattpocock-skills拆解报告 1.md` 第二、三、八节
- 本仓库 `AGENTS.md`；`docs/research/legal-skills-独立调研.md` §1.5、§六；`docs/research/legal-skills-与本项目交叉对比.md` J11、B5；`docs/research/skill-platforms-claude-code-与-codex.md` §7 来源注（Claude Code memory 页转述）
