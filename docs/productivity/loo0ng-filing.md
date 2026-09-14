## What it does

`loo0ng-filing` 持两个互不引用的零依赖 CLI：归档搬运把收件箱里的东西按相对路径原样搬到材料、指南、模板/官方、模板/生成四格之一，判断去向归模型、搬运归脚本；陈述落档把你在对话里说的一句话落成 `材料/律师陈述/` 下的一个文件，落盘后只读。

不在盘上的事实不是材料。你在对话里给出的案号、日期、金额、选择，先落成陈述再用：审查报告的依据必须可引，下一个对话看不到这一句。一条陈述等于你说出的那一句，不是那句话里的事实件数；原话逐字，不润色、不概括。

## When to reach for it

你一句话说「把收件箱里的某文件归到材料」「记一句」「我确认这个日期」「按第二种办」，模型自行调用它。起手末尾与出一版开场，[loo0ng-setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-setup-case.md) 与 [loo0ng-doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-doit.md) 也先调它清收件箱。

| 这件东西是 | 去向 |
| --- | --- |
| 本案的事实来源原件（合同、账、函、笔录、照片、压缩包） | `材料` |
| 本案适用的官方要求文件（法院的通知、指引、清单） | `指南` |
| 官方发布的空白件 | `模板/官方` |
| 自己或所里做的空白件 | `模板/生成` |
| 三格都无正向证据 | 留在收件箱，回显时说一句为什么拿不准 |

确认与不适用不是陈述，是图里的条目，归 [loo0ng-graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-graph.md)。

## Prerequisites

会话当前目录是案件工作区（有 `图.json`），两个脚本只在这样的目录里工作。

## 陈述的三种性质

| 性质 | 含义 |
| --- | --- |
| 直接陈述 | 你本人是权威来源的事实 |
| 转述 | 你转录他人或他处，来源强度低一档，必须写明来源 |
| 裁定 | 你对本案某个问题的选择，不是事实 |

改口是整条取代：新陈述指向旧文件，旧文件一字不动。现行陈述就是未被任何文件指为取代目标的那些，读文件头部即得，不设清单。

## Common questions

**一句话里有两个日期，会落几条？**
一条。一句话里含几件事都不改变条数，多个值逐个列进整理表，不拆成几个文件。真要成两条，你自己分两次说。曾有一侧把一句话拆成两条陈述，正文因此写死了这条。

**收件箱里的压缩包会解压吗？照片会识别吗？**
不会。压缩包与照片只能原样归 `材料`，不解压、不识图；它也不登记、不算指纹、不去重。

**同名文件怎么办？**
不覆盖。同名已存在则那件不搬、留在收件箱并报出，其余照搬。

## It's working if

- 收件箱清空后，文件以原来的相对路径出现在四格之一，一个都没改名。
- `材料/律师陈述/` 多一个只读文件，原话逐字是你说的那句。
- 拿不准的留在收件箱，回复里有一句为什么。
- 归档从不产生陈述，陈述从不搬文件，两者都不动 `图.json`。

## Where it fits

`loo0ng-filing` 是参考层，三个进入点：起手末尾、出一版开场、你的一句话。它只保证陈述文件可引；审查报告引用它的格式住在 [loo0ng-to-docx](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-to-docx.md)；归档之后 `指南/` 非空，从指南长雏形是 [loo0ng-domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-domain.md) 的事。整套 skill 的路由是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/ask-loo0ng.md)。
