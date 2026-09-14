## What it does

`to-docx` 持两个互不引用的 CLI：转换器把模型写的 Markdown 最小集以该节点的官方模板为版式载体转成 DOCX，只依赖 python-docx、离线；门禁对任意 DOCX 做只读检查，本体零第三方依赖，静态检查加版面推算，有真实渲染时以渲染加信。

结论三档：通过、需人眼、不通过。通过与需人眼才落进工作区，不通过什么都不落；退出码零只有一个，任何非零都不许当成通过用。它不写正文内容、不填槽位、不改律师写过的文件，对结论没有写权。

## When to reach for it

出一版的第 7 步由 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 驱动，模型按它的正文调本 skill 写稿、转换、门禁、落盘。你直接说「把这份 docx 检一下」「这稿子转成 word」，模型也自行调用它，产物留在临时位置或你指的位置，不进 `文书/`、不写审查报告、不动图。

| 退出码 | 结论 | 落盘 |
| --- | --- | --- |
| 0 | 通过 | 有 `--deliver` 则已落盘 |
| 3 | 需人眼 | 有 `--deliver` 则已落盘 |
| 1 | 不通过 | 否 |
| 2 | 门禁跑不动（文书或模板打不开、用法错、落盘被拒） | 否 |

稿子写什么、整读哪些材料是 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 的事；往图里追加生成条目归 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)，本 skill 自己不追加。

## Prerequisites

- 转换器要一个能 `import docx` 的解释器，版本钉在随包的 `requirements.txt`（`python-docx==1.2.0`）。约束的是这个后端的版本，不是哪个解释器；怎么弄到解释器归 agent，装出来的东西只落在临时位置。
- 门禁不需要任何第三方包，任何解释器上都跑得动。缺 Word 或 WPS 不阻断出件：那是正常路径，不是故障。

## 门禁查什么

不通过项是客观几何与结构，任一命中即不通过：行高超阈值、页数超阈值、空白页、表宽超页面、页脚页码域写死、表格直接接节尾、元数据残留作者、模板占位残留（`XX`、`【…】`、下划线串）、模板有表而成品一张表都没有。

需人眼指向的永远是一个几何量：页数、空白页、最大行高三项的推算区间横跨了阈值，门禁测不准，不是测出事故。有渲染结果时点值取代区间，这一档当场坍缩。

阈值由律师定，模型不调：为了过门禁调高阈值与跳过门禁是同一件事。

## Common questions

**律师那台 mac 没有 Word，能出件吗？**
能。没有渲染后端时三项几何判据从点值变成区间，披露项里多一条「无渲染结果」，结论可能落在需人眼，文书照样落盘、附一份须目验清单。缺 Word、WPS 或其他软件不得阻断文书生成，这是律师自己的裁定。

**需人眼要不要重试？**
不要。重试只数不通过。需人眼直接落盘交人，审查报告第一段就是门禁生成的须目验清单，一个字不改；你在 WPS 或 Word 里打开看那几处。

**没配过 python 怎么办？**
不阻断出件。agent 自备一个解释器（系统的、uv 管的、现装的都行），只要能 `import docx` 且是钉住的那个版本；转换器回显第二行写出这次用的解释器与实测到的版本，原样抄进审查报告，版本对不上照常出件、但会明写。Codex 受限沙箱里这条路已实测走通；律师那台 mac 上仍未验证。

**不通过项指着模板自带的行高，改稿改不动怎么办？**
判生成失败，把门禁输出原文交给律师，律师可以兜底自写。不要把被点名的那张表改写成正文段落换一个通过：交出去的是一份缺了正文结构的件，门禁的「模板表缺失」现在专门拦这一条。

**能单独检一份现成的 docx 吗？**
能。门禁可以单独对任意 DOCX 跑，不带 `--deliver` 就只出结论。律师兜底自写的文书走的就是这条：只披露不阻断，不搬、不改、不重转。

**`loo0ng-to-docx` 去哪了？**
改名为 `to-docx`（2026-09-13，ADR-0009 附注）：六件都去掉了 `loo0ng-` 前缀，只有路由还叫 `ask-loo0ng`。没有别名，装了旧名的机器按 README 重装。

## It's working if

- 不通过时 `文书/` 里什么都没多，门禁输出原文在回复里。
- 需人眼时审查报告的第一段是须目验清单原文，在「生成依据」之前。
- 审查报告「生成依据」段里有转换器回显的那一行：解释器与 python-docx 版本。
- 工作区里没有任何暂存目录，稿子与临时 DOCX 都在系统临时目录里。
- 阈值从来没被谁调过。

## Where it fits

`to-docx` 是参考层，出一版链条的末端：写稿、转换、门禁、落盘之后，[doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 再经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md) 追加生成条目。它读的官方模板原件住领域目录，家在 [domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md)，起手时由 [setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 拷进工作区。整套 skill 的路由是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
