## What it does

`graph` 持有 `图.json` 的唯一写入口：一个零依赖的 CLI。你一句话改图的构成（加节点、改标题、调顺序、跨模块移动、改空白模板、增删改模块、节点或整个模块不适用）由模型调它落盘并回显；编排 skill 追加生成与确认条目也调它；每次写图后它整体重算 `图视图.md`（你读的）与 `图视图.json`（路由与插件读的）。

## When to reach for it

模型会在需要改图时调用它，你不用记名字。在案件工作区的对话里说一句就行：

| 你说 | 它跑 |
| --- | --- |
| 在某模块下加一个节点 | `add-node` |
| 把某节点标题改成…… | `rename-node` |
| 某节点挪到某节点前面 / 挪到某模块下 | `move-node` |
| 某节点用某模板 / 不用模板 | `set-template` |
| 加一个模块 / 模块改名 / 删空模块 | `add-module` / `rename-module` / `delete-module` |
| 某节点不适用 / 整个模块不适用 | `not-applicable` |
| 我在 Word 里去了黄，视图跟上 | `views` |

起手拷入预设图、办完一案另存成预设图、出一版之后追加条目，也都是它在跑，只是由别的 skill 驱动。

## Prerequisites

会话当前目录是案件工作区（有 `图.json`）。脚本只用 Python 标准库，跑得动 python 3.9。

## 唯一写入口，写完就有视图

改标题、生成文书、确认一版，看起来是三件事，最后都由同一个引擎把变化记进图。**唯一写入口**让这些变化遵守同一套规则：模型不能为了完成眼前一步，直接改 JSON 绕过拒写；你读到的两份视图也随写入一起重算。

`图视图.md` 里每个节点有状态（未生成、已生成、已确认、不适用）、空白模板、高亮是否已清、时限，另有一整张**前方**，把还没生成的节点按图序放在各自模块里。你在 Word 里去掉高亮后，可以让模型刷新视图；看见「已清」仍要由你说一句确认，才会留下确认条目。

## 构成能调整，条目只增不改

模块和节点安排的是要办什么，条目记的是已经发生什么。你可以改标题、调顺序、跨模块移动，这些构成调整一句话即落；生成过哪一版、确认时说了什么，则靠**只追加的条目**保留下来，没有修改或删除旧条目的入口。

例如，一份已确认文书需要修改时，要重出一版，图里再追加生成条目，旧记录仍在。节点也永不删除：误加或不再需要的节点记为不适用，且不适用是终态；已经确认的节点不能再记不适用。这里保留的是办过与放弃过的痕迹，图不会因为整理流程就抹掉它们。

## Common questions

**「前方」空了，或者高亮已清，就算全案办完了吗？**
都不能单独这么判。「前方」只装未生成节点，已生成未确认的也不在里面；高亮已清只是提示，确认仍要律师一句话。只有待生成、待确认都不剩，才可以说图上的节点办完。出处：[#87，前方为空的纠正](https://github.com/f4de01/loo0ng-skills/issues/87#issuecomment-5706326093)、[CHANGELOG 0.6.0，图引擎新增高亮列](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**旧的惰性带入、来源列和领域图参数去哪了？**
图格式升到 2，起手只剩空图或整份拷入预设图；`--full`、`--from`、`--domain` 与惰性带入删除。视图不再按节点 id 去另一张图查来源，前方从案件图自己的条目算。预设图后来新增节点，也不会自动进已起手的案件图。出处：[CHANGELOG 0.6.0，图引擎收敛](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**误加的节点能删吗，已确认的能改成不适用吗？**
节点永不删除，误加的记不适用；不适用是终态。已确认的节点不能再记不适用，要改就重出；模块中有已确认节点，也不能整模块记不适用。条目只追加，旧记录保留。出处：[CHANGELOG 0.6.0，图引擎保留的规则](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

## It's working if

- 你一句话之后 `图视图.md` 立刻变，回显是 CLI 的原话。
- 引擎拒写时文件一字不动，原因在 stderr，模型把它照实转告而不是绕过去。
- 图里找不到「删除」这回事，只有不适用。
- 标题里带 `/`、`:` 这类字符时，文书目录名由引擎统一换成全角，谁都不自己转义第二遍。

## Where it fits

`graph` 是参考层，所有写图都经它：[doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 的生成与确认条目、[setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 的起手图、[domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md) 的另存与雏形写入，都是它的子进程。它不出 HTML、不做可视化，也不认任何领域语义。整套的路由是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
