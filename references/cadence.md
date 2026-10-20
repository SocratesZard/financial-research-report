# 周期生产、研究接续与交付

## 开始：先读自己的记录

在用户工作目录的outputs/financial-research-report或明确指定位置查找**实际存在**的前期report.json及需要的report.md、research-audit.json、IMA发现记录。按主题/市场、定义口径、资讯窗口和可比性选择；同一期多个草稿优先明确的交付版，不仅按文件修改时间取最近一份。保存所用前期路径、report_id及必要散列/读取范围到本期已有研究记录，不另建全局记忆或重复知识库。

读取其事件/候选、数字与measures、theses、上期next_validation和未决项；只继承有出处且截至本次截止可用的内容。来源在本期截止后才披露的判断不能倒填。没有可比前期时，从本期建基线，stance用new/pending，不虚构“维持/上修”或历史命中率。前期缺项可指出，不能用试跑问题清单反推正式评级。

## 本期处理与跨期保存

公开与IMA独立发现，结合已有材料，再合并去重核对。候选和证据先于最终目录；参考只提供可选线索，日常不重复视觉拆解。按news-research.md定向追查重大未决，按editorial-policy.md选择主线和展开深度。

沿用report.json和research-audit.json作为本期记录，不为积累再复制一套状态数据库：

| 复用记录 | 本期保存，下期实际读取 |
|---|---|
| events／candidates | 稳定event_key、本次实质增量、披露/阶段、来源与未决；转载不新建经济事件 |
| claims.numbers／measures | 原始值、单位、币种、期间、定义、实现/预测等属性、来源位置；跨期定义变化单列，不补假历史序列 |
| theses | 当前text/stance、claim_ids、支持证据；competing_explanations、counter_evidence、change_reason、previous_ref（可比前期路径+thesis_key），以及next_validation/invalidation |
| 验证与未决 | 结果支持/削弱/推翻了什么、替代解释、实际访问障碍、下次查什么；复用calendar、coverage_review和候选analysis，不再建重复清单 |

新增字段可为空但说明未知，不要求为每个小事件造一条thesis。仅当本期确有证据改变观点时记变化原因；“维持”也要说明新证据如何影响原命题。对前期已发生节点给结果与判断含义，未取得结果标未核，不写预测命中。历史期次只读，在本期另存修订与链接，不回写旧判断。

## 日报与完整周报

日报关注上次截止之后的重要新增、价格变化、观点变化与下一交易日验证。用户说“今天”时截至当前调用；未指定日期时默认最近完整自然日。新闻摘要可精选8–12条，此数不适用于完整日报/产业周报。

周报默认上一个完整周一至周日，用真实交易日端点重算收益；日收益不能直接相加。按当期产业变化、用户问题和重要未决选择主题深度，不设事件数、页数或一事件一页配额。参考六类主题只用于覆盖复查。事实、驱动、竞争解释、市场/投资含义和验证可以分多页展开，每页研究问题不同；合理查验后确实无重大变化时可短，不以短稿为默认终点。

下周日期、原时区和确认状态按[next-week.md](next-week.md)；投资含义按[investment-framework.md](investment-framework.md)。结束前满足news-research.md的研究充分性条件。真实限制下可部分交付，但不能用DRAFT或“写了缺口”代替尚能执行的重要追查。

## 产物与可复用命令

默认输出outputs/financial-research-report/YYYY-MM-DD/{daily|weekly|news|reference-demo}/，修订另建目录。新审计用audit_version=2，旧v1只读兼容。本期新目录保存report.json/md/html、research-audit.json、qa.json、manifest.json；按实际使用保存ima/及evidence/，PDF按需。新目录不覆盖旧期或测试基线；是否增加附录由内容决定，不以侧文件数量衡量质量。

Codex桌面先用load_workspace_dependencies定位Python/Node。Python需要pdfplumber/Pillow/PyYAML，PDF渲染需pdftoppm；PowerShell用`& '<绝对可执行路径>'`。Windows中文验证用-X utf8。

```text
node scripts/ima_source.cjs discover --query <本期主题> --out <本期/ima/discovery>
node scripts/ima_source.cjs fetch --snapshot <ima-snapshot.json> --id <选中媒体> --out <本期/evidence/ima-batch>
python -X utf8 scripts/check_research_audit.py <research-audit.json>
python -X utf8 scripts/prepare_visuals.py <input.json> --out <prepared.json> --plan <visual-plan.json>
python -X utf8 scripts/build_report.py <prepared.json> --out <新成稿目录>
node scripts/qa_deck.cjs <report.html> <qa目录> --modules <node_modules> --browser <Edge或Chrome路径>
node scripts/qa_deck.cjs <report.html> <qa目录> --modules <node_modules> --pdf <输出.pdf>
```

inspect_pdf.py用于首次风格建立/更换参考/明确复刻，或确需读取的研究PDF，不是日常对已分析参考稿的固定前置。PDF导出先读可用PDF skill并执行适用要求，产物登记不硬编码为跨环境依赖。HTML支持编辑与另存，改后同步JSON；PDF为静态版。导出按钮调用浏览器打印：选全部页面、关闭页眉页脚、启用背景图形；内嵌浏览器无打印界面时用Edge/Chrome或上述--pdf命令。浏览器不可用时明确视觉验收未完成，不伪造截图。字体及全页视觉仍按目标环境核对。

用户明确请求才建自动化；Skill本身不在后台运行，也不自动更新全局记忆。正常调用：“做一份上周的TMT产业周报。”“整理今天的TMT日报。”只在改范围、来源限制或输出形式时补充差异。
