# Engineering

办案主线的 skill，对应上游的「daily code work」：只在有 `图.json` 的案件工作区里工作的那些。离了案子也能单独用的工具在 [productivity/](../productivity/README.md)。

## User-invoked

只有律师打名字才触发（Claude Code：`disable-model-invocation: true`；Codex：`agents/openai.yaml` 里 `policy.allow_implicit_invocation: false`）。

- **[setup-case](./setup-case/SKILL.md)**: 起手。把当前目录长成案件工作区，一案一次：一问二选（空图还是哪份预设图）、落目录形状与图、目录里已有的挪进待归档，起手清单等律师一句话拍板。
- **[doit](./doit/SKILL.md)**: 办节点。一个对话办一个节点：照模板填出一版文书（填不了的地方留黄）、登记律师自写的那份、一句话确认或不适用；出件与确认可跨对话。
- **[ask-loo0ng](./ask-loo0ng/SKILL.md)**: 问路。只读的地图：第一行先说哪几份文书黄色已清、还等你确认，再答当前节点、上一完成、下一任务，把下一句该打的整串给你，不触发任何 skill、不写图。

## Model-invoked

律师或模型都能够到（description 里写足触发场景，模型按需自行调用）。

- **[graph](./graph/SKILL.md)**: 图引擎。`图.json` 的唯一写入口：律师一句话改图的构成，编排 skill 追加生成与确认条目，每次写图后重算视图。
- **[domain](./domain/SKILL.md)**: 预设图的家。出厂与个人两处两归属，按名与归属解析路径、分两组列出；律师一句话另存、开发者导入；雏形判同名后经引擎写入。
- **[filing](./filing/SKILL.md)**: 归档。按模型写的归档计划把待归档或工作区外目录里的文件搬进材料、参考/模板、参考/指南三格，不改名、不覆盖、按内容去重，并维护归档索引。
