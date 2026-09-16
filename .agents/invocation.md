# Skill 调用规则

编写 description、选择显式或隐式调用、跨 skill 调用或修改律师触发语时读本篇。新增、改名、删除的登记步骤见 [registration.md](./registration.md)。

## description 两套

- User-invoked（编排 skill 与路由）：一句人话，功能加后面跟什么，去掉触发词。
- Model-invoked（参考 skill）：四要素齐全（功能、触发、负向、邻居互指），第三人称、中文、触发词放最前、不超过 1,024 字。
- 跨 skill 只用「调用 skill "xxx"」一种句式，散文里可用中文叫法（如「图引擎」，只是行文，不是元数据）；改名于是成为纯机械替换。
- 路由 `ask-loo0ng` 的正文是这条的例外，两处：它写的入口名是**律师要打的那一串**（`/名 …` / `$名 …`，ADR-0005），只能裸着写；它自持的那两张表（打名字的三个入口一张、说一句话就到的四件一张）第一列是**登记用的名字**，也裸着写，那一列就是这张表的键。除这两处之外，它谈别的 skill 的行为时仍用「调用 skill "xxx"」句式指出处。裸名仍是同一个字符串，改名照样是机械替换。

## 双旗

| 类型 | `SKILL.md` frontmatter | `agents/openai.yaml` |
| --- | --- | --- |
| 编排 skill、路由 | `disable-model-invocation: true` | `policy.allow_implicit_invocation: false` |
| 参考 skill | 不写 | 不写 `policy` |

两平台各读各的旗，互不认对方的（#18 项 3）：两处都手写，`bash scripts/check-skill.sh .` 守两端一致：`disable-model-invocation: true` 与 `policy.allow_implicit_invocation: false` 要么都有要么都没有。

## 路由同步

增删或改名任一件 skill，或改了律师触发它的那句话，必改 `ask-loo0ng` 自持的两张表：打名字的三个入口一张，说一句话就到的四件一张。
