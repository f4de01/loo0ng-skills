# Skill 调用规则

编写 description、选择显式或隐式调用、跨 skill 调用或修改律师触发语时读本篇。新增、改名、删除的登记步骤见 [registration.md](./registration.md)。

## description 两套

- User-invoked（编排 skill 与路由）：一句人话，功能加后面跟什么，去掉触发词。
- Model-invoked（参考 skill）：触发分支放最前，同一个分支只留一个触发词（不同的分支照列不算重复），后面跟一句它是什么；第三人称、中文，目标 150 汉字以内，硬上限 1,024 字符。
- description 每轮都在上下文里，比正文更该剪。两样东西不进它：兄弟地图（谁在流程里调它）收在路由 `ask-loo0ng` 那张「说一句话就到」的表里，「它不做什么」写进自己正文（「不做的」或「与邻居的边界」那一节），剪 description 之前先确认正文真的接得住。
- 跨 skill 只用「调用 skill "xxx"」一种句式，散文里可用中文叫法（如「图引擎」，只是行文，不是元数据）；改名于是成为纯机械替换。
- 路由 `ask-loo0ng` 的正文是这条的例外，两处：它写的入口名是**律师要打的那一串**（`/名 …` / `$名 …`，ADR-0005），只能裸着写；它自持的那两张表（打名字的三个入口一张、说一句话就到的四件一张）第一列是**登记用的名字**，也裸着写，那一列就是这张表的键。除这两处之外，它谈别的 skill 的行为时仍用「调用 skill "xxx"」句式指出处。裸名仍是同一个字符串，改名照样是机械替换。

## 双旗

| 类型 | `SKILL.md` frontmatter | `agents/openai.yaml` |
| --- | --- | --- |
| 编排 skill、路由 | `disable-model-invocation: true` | `policy.allow_implicit_invocation: false` |
| 参考 skill | 不写 | 不写 `policy` |

两平台各读各的旗，互不认对方的（#18 项 3）：两处都手写，`bash scripts/check-skill.sh .` 守两端一致：`disable-model-invocation: true` 与 `policy.allow_implicit_invocation: false` 要么都有要么都没有。

## 路由同步

增删或改名任一件 skill，改了律师触发它的那句话，或改了编排 skill 在流程里调谁，必改 `ask-loo0ng` 自持的两张表：打名字的三个入口一张，说一句话就到的四件一张。后一张多一列「流程里谁调它」，兄弟地图收在那里，四件参考 skill 的 description 里不再重抄一遍。它是地图不是权威：某件 skill 到底怎么做，仍以它自己的 `SKILL.md` 为准。
