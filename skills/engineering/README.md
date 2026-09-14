# Engineering

办案主线的 skill，对应上游的「daily code work」：六件都只在有 `图.json` 的案件工作区里工作。离了案子也能单独用的工具在 [productivity/](../productivity/README.md)。

## User-invoked

只有律师打名字才触发（Claude Code：`disable-model-invocation: true`；Codex：`agents/openai.yaml` 里 `policy.allow_implicit_invocation: false`）。

- **[setup-case](./setup-case/SKILL.md)**: 起手。在一个空目录里长出案件工作区，一案一次：六格、起手图三选一、归档收件箱、起手清单等律师一句话拍板。
- **[doit](./doit/SKILL.md)**: 办节点。一个对话办一个节点：出一版、兜底登记、确认、不适用，拍板也在这个对话里说。
- **[ask-loo0ng](./ask-loo0ng/SKILL.md)**: 问路。只读的地图：答当前节点、上一完成、下一任务，把下一句该打的整串给你，不触发任何 skill、不写图。

## Model-invoked

律师或模型都能够到（description 里写足触发场景，模型按需自行调用）。

- **[graph](./graph/SKILL.md)**: 图引擎。`图.json` 的唯一写入口：律师一句话改图的构成，编排 skill 追加生成与确认条目，每次写图后重算视图。
- **[domain](./domain/SKILL.md)**: 领域目录与雏形。领域图、官方模板原件、指引手册原文三样的家；从指南长雏形，拍板后经引擎写入；活图与出厂种子的分工。
- **[filing](./filing/SKILL.md)**: 归档与陈述。收件箱归档搬运；律师在对话里说的一句话落成陈述文件，落盘后只读。
