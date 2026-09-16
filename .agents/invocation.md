# Skill 调用规则

编写 description、选择显式或隐式调用、跨 skill 调用或修改律师触发语时读本篇。新增、改名、删除的登记步骤见 [registration.md](./registration.md)。

## description 两套

- User-invoked（编排 skill 与路由）：一句人话，功能加后面跟什么，去掉触发词。
- Model-invoked（参考 skill）：触发分支放最前，同一个分支只留一个触发词（不同的分支照列不算重复），后面跟一句它是什么；第三人称、中文，目标 150 汉字以内，硬上限 1,024 字符。
- description 每轮都在上下文里，比正文更该剪。两样东西不进它：兄弟地图（谁在流程里调它）收在路由 `ask-loo0ng` 那张「说一句话就到」的表里，「它不做什么」写进自己正文（「不做的」或「与邻居的边界」那一节），剪 description 之前先确认正文真的接得住。
- 跨 skill 指名道姓的写法见 [跨 skill 怎么写](#跨-skill-怎么写)：两种句式，名字一律放在引号里，改名于是成为纯机械替换。
- 路由 `ask-loo0ng` 的正文是这条的例外，两处：它写的入口名是**律师要打的那一串**（`/名 …` / `$名 …`，ADR-0005），只能裸着写；它自持的那两张表（打名字的三个入口一张、说一句话就到的四件一张）第一列是**登记用的名字**，也裸着写，那一列就是这张表的键。除这两处之外，它谈别的 skill 的行为时用下面那种非操作句 `skill "xxx"` 指出处；它不触发任何 skill，正文里一个操作句都不该有。裸名仍是同一个字符串，改名照样是机械替换。

## 跨 skill 怎么写

两种句式，名字都放在引号里：

- **操作句**（这一步就要去调它）写「调用 Skill 工具，传 "graph"」。点名 Skill 工具这件事本身才让它被加载：多数 harness 把 skill 调用暴露成一个工具，散文里扔一个 `/名` 让模型自己领会，命中率明显更低。
- **非操作句**（只陈述事实：这件事归谁、谁在流程里调它）写 `skill "graph"`，不带「调用 Skill 工具」。「与邻居的边界」一节两种都有：说「这件事归 X」是非操作句，说「要做这件事就调 X」仍是操作句。
- **一次只传一件**。一步要两件就写成两次（「调用 Skill 工具，传 "filing"；再调用一次，传 "graph"」），不写「用 X 和 Y 调它」，那读起来像一次调用吃两个名字。
- **不跨目录指别人家的参考文件**。要用兄弟 skill 的参考文件（`GRAPH-FORMAT.md`、`REVIEW-FORMAT.md` 这类），写成操作句调它的名字，由它自己的正文把那份参考文件指出来：参考文件住在拥有它的那件 skill 里，别的 skill 靠调 Skill 工具够到，不靠跨目录链接。管住的是**阅读指针**；点名兄弟的 CLI 与子命令（`preset.py list`、`graph.py rename-node`）不在此列，那是运行时要敲的命令，权威仍在它自己的正文与 `--help`。
- **user-invoked 的三件（`setup-case`、`doit`、`ask-loo0ng`）不许出现在操作句里**，任何 skill 都调不到它们（两个 harness 各自硬拦）。要它们上场只能写成叫律师自己打：「还没起手的打 `setup-case`」「不知道下一个办什么就打 `ask-loo0ng`」。`bash scripts/check-skill.sh .` 机械守这一条，扫 skill 根目录的 `*.md` 与 `scripts/` 里的说明与回显：CLI 的拒绝回显原样进模型上下文，写错了与正文写错了一样。
- 散文里可用中文叫法（如「图引擎」，只是行文，不是元数据）。

## 双旗

| 类型 | `SKILL.md` frontmatter | `agents/openai.yaml` |
| --- | --- | --- |
| 编排 skill、路由 | `disable-model-invocation: true` | `policy.allow_implicit_invocation: false` |
| 参考 skill | 不写 | 不写 `policy` |

两平台各读各的旗，互不认对方的（#18 项 3）：两处都手写，`bash scripts/check-skill.sh .` 守两端一致：`disable-model-invocation: true` 与 `policy.allow_implicit_invocation: false` 要么都有要么都没有。

## 路由同步

增删或改名任一件 skill，改了律师触发它的那句话，或改了编排 skill 在流程里调谁，必改 `ask-loo0ng` 自持的两张表：打名字的三个入口一张，说一句话就到的四件一张。后一张多一列「流程里谁调它」，兄弟地图收在那里，四件参考 skill 的 description 里不再重抄一遍。它是地图不是权威：某件 skill 到底怎么做，仍以它自己的 `SKILL.md` 为准。
