# Productivity

日常非代码的工作流工具。律师工作台的七件 skill 都住在这里：它们办的是案件，不是代码。

## User-invoked

只有律师打名字才触发（Claude Code：`disable-model-invocation: true`；Codex：`agents/openai.yaml` 里 `policy.allow_implicit_invocation: false`）。

- **[loo0ng-setup-case](./loo0ng-setup-case/SKILL.md)**: 起手。在一个空目录里长出案件工作区，一案一次：六格、起手图三选一、归档收件箱、起手清单等律师一句话拍板。
- **[loo0ng-doit](./loo0ng-doit/SKILL.md)**: 办节点。一个对话办一个节点：出一版、兜底登记、确认、不适用，拍板也在这个对话里说。
- **[ask-loo0ng](./ask-loo0ng/SKILL.md)**: 问路。只读的地图：答当前节点、上一完成、下一任务，把下一句该打的整串给你，不触发任何 skill、不写图。

## Model-invoked

律师或模型都能够到（description 里写足触发场景，模型按需自行调用）。

- **[loo0ng-graph](./loo0ng-graph/SKILL.md)**: 图引擎。`图.json` 的唯一写入口：律师一句话改图的构成，编排 skill 追加生成与确认条目，每次写图后重算视图。
- **[loo0ng-domain](./loo0ng-domain/SKILL.md)**: 领域目录与雏形。领域图、官方模板原件、指引手册原文三样的家；从指南长雏形，拍板后经引擎写入；活图与出厂种子的分工。
- **[loo0ng-filing](./loo0ng-filing/SKILL.md)**: 归档与陈述。收件箱归档搬运；律师在对话里说的一句话落成陈述文件，落盘后只读。
- **[loo0ng-to-docx](./loo0ng-to-docx/SKILL.md)**: 出件与门禁。Markdown 最小集以官方模板为载体转成 DOCX；版式门禁三档结论，不合格不落盘。
