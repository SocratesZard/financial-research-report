# JSON 数据合同（schema_version = 1 / 2）

v1保持兼容；新完整报告优先v2。v2增加measure_specs、measures、visuals及可选calculations，先prepare_visuals.py再build_report.py，具体结构与选图规则见 [visual-storytelling.md](visual-storytelling.md)。图形绑定原子数字/已核主张/已有计算，渲染前重查值与来源；不是仅给自由绘图数据加一个来源标签。此schema版本与research-audit的版本独立，历史审计不回填。

完整可运行示例见 `../assets/example-report.json`；构建器先校验再生成。字段未取得时留明确缺项，不编造值。此合同是内容台账和常用版式的最小接口，不声称验证网页真实内容或覆盖所有估值分析。

真实新闻研究另须 `research-audit.json`，其独立合同与模板见 [news-research.md](news-research.md)。新闻仅文字交付不必套用本文件的slides结构。旧schema_version=1及历史样稿保持兼容；`build_report.py`不负责检索覆盖、候选排序或事实语义检查，新审计由 `check_research_audit.py`单独检查。完整报告中的关键主张应能映射到审计的候选、来源和数字记录，不能用两份不一致的台账分别支撑同一结论。

新研究审计版本为audit_version=2，量级计算、驱动与证据保存字段见 [analysis-evidence.md](analysis-evidence.md)；与本文件schema_version无关。旧v1审计不回填新字段，也不能因旧结构通过声称新质量要求已达成。

## 顶层

| 字段 | 含义 |
|---|---|
| report_id / title | 本期唯一标识与标题 |
| mode | daily / weekly / reference-demo |
| status | DEMO_REFERENCE_ONLY / DRAFT / REVIEW_READY |
| period_start / period_end | YYYY-MM-DD，资讯覆盖区间 |
| cutoff_at / timezone | 带时区的截止时刻；IANA 时区名称 |
| universe | 行业、市场或公司范围的字符串列表 |
| limitations | 本期限制，字符串列表 |
| sources / claims | 必填，来源与主张台账 |
| events / theses / calendar | 可以为空，但没有信息时须在 limitations 说明 |
| outlook | 0.3新周报使用；下周窗口、排期核对状态与无确定日期的观察项，见[next-week.md](next-week.md) |
| slides | 页面，按顺序渲染 |

## 来源

`id,title,kind,access,published_at,accessed_at,url或path,notes`。
kind = primary / secondary / channel / reference；access = opened / excerpt_only / inaccessible / not_accessed。日期可以用 `null` 表示未知，不能凭文件名补造发布日期。opened 必须有真实 accessed_at。published_at 超过截止时刻的来源不能支持当期事实或“截至当时已知”的未来日历；只有版式/历史演示可独立标示不属于当期研究。日历事件本身可以晚于截止，但公布该排期的来源须在截止时已可得。参考稿路径与散列建议保留。

IMA私有来源增加`provider:"ima",knowledge_base_name,knowledge_base_id,media_id,retrieved_at,snapshot:{path:"evidence/...",sha256,extent,note}`；url允许null，report来源的path指向本期原件绝对路径，audit来源保留snapshot相对路径。不会强迫伪造公开URL或保存签名链接。kind仍按原始上游分类，不因存储于IMA而升级。运行构建器时检查input所在目录中的snapshot及SHA256；复制原件后再构建，不能把“下载完成”当“全文读完”。详见[ima-source.md](ima-source.md)。

使用OCR时，在来源notes/snapshot.extent及对应定位中说明实际提取/阅读页、OCR引擎、是否视觉核验和未转录图表。可在本期审计保存原件SHA256、PNG路径/散列、OCR输出路径和复核记录；不能用OCR文本替换原PDF的snapshot散列。local_corpus.py的INDEXED_REVIEW_PENDING/OCR_UNVERIFIED不自动满足主张的研究支持要求；关键数字、日期、主体和单位需回看页面后再引用。详见[本地检索与OCR](local-retrieval.md)。

## 主张

`id,text,kind,verification,source_refs`。
kind = fact / company_report / inference / scenario / calendar。
verification = supported / corroborated / reference_only / unverified。
source_refs = `[{source_id,locator,evidence}]`，均须非空；locator 如 `PDF p.34, 图表48`、IR 新闻稿第 3 段。evidence 是实际读到的支持摘要，通常用转述以避免长引文。supported/corroborated 需要已读的非 reference 来源；公司自报即使原文可核也不自动变成独立验证。corroborated 至少两条已读的独立来源，独立性仍需人工判断。

推断与情景须有assumptions；REVIEW_READY禁止未支持/仅标题的主张，但可包含原文支持且明确归属的机构预测或渠道观点，supported仅支持“其如此表达”，不支持预测实现。按research-protocol.md保留来源属性与结论边界。状态只表示可供研究复核，不代替研究充分性判断。

## 事件、观点、日历

- event：`id,event_key,occurred_at,summary,claim_ids`，同一 report 的 event_key 不重复；当期事件不得超过 cutoff_at，也不早于 period_start。只知道日期时 occurred_at 使用 YYYY-MM-DD，并注明精确时刻未知，不能补造23:59等时刻。更早的背景写 claims，不伪装当期事件。
- thesis：`id,thesis_key,stance,text,claim_ids,next_validation`；stance=new/maintained/upgraded/downgraded/withdrawn/pending。复用competing_explanations、counter_evidence、change_reason、previous_ref保存竞争解释、反证、变化及实际前期链接，详见[cadence.md](cadence.md)。投资观点页另有target/horizon/invalidation/valuation_status（not_assessed/qualitative/modeled），量化估值再加valuation_claim_ids；不强迫所有主题建立估值模型。
- calendar：`date,item,focus,confirmation,claim_ids`，date 为带时区时刻或 YYYY-MM-DD；confirmation = confirmed / tentative / reference_only。未来日历允许晚于截止；日历主张 kind 必须是 calendar。

0.3新稿有outlook时，calendar再含稳定id、原始日期/时区、precision、schedule_basis、priority、importance_reason和threshold_basis；旧稿保持兼容。结构化页使用`calendar_ids`或`outlook_watchlist:true`且blocks为空，由同一台账自动生成HTML与Markdown表格，不复制手写。完整合同与跨周窗口规则见[next-week.md](next-week.md)。

## 页面

共同字段：`type,section,title,claim_ids,takeaway,blocks`。type = cover / table / two_column / bars / calendar；v2另有visual_analysis（左图58%/右解释42%），要求证据绑定headline生成事实标题。takeaway是证据支持的观点，可以为空；每页至少一个claim ID。可选takeaway_label为“研究判断”（默认）、“投资观点”或“后续观察”，同时控制HTML与Markdown；投资观点须有非空takeaway及有效thesis_ids，所引用观点的来源主张也需包含在页面claim_ids中。标签与链路只验证记录，投资含义需实质审读。旧稿不回填。

cover 另有 `toc:[{number,label,detail}]`（最多6项）、`metrics:[{label,value,change}]`（最多11项），`subtitle`。metrics 是展示字段，必须由页面主张支持；行情原始计算资料不在示例中，缺少时不要造指标。

blocks 最多两块。每块 `heading,type`，type 为 text/table/bars。
v2另支持visual（visual_ids，1–2幅）及brief（kpis引用measure_id，sections含label/text）；分析页第一块必须是实际图形，不能只拆左右两段文字。sources可加short_title用于简洁可点击页脚，不替代原URL/定位。
- text：`items:[字符串]`，最多8项；
- table：`columns:[字符串]`、`rows:[[字符串...]]`，列数须相等，最多12行；可选 `focus_rows:[从0开始的行号]`；
- bars：`unit`、`values:[{label,value}]`，value 必须有限数，最多10项；可选 `orientation: vertical`（适合少量季度序列），默认横向。零值、全零与负值均支持，不能改变尺度掩盖零点。

表格每个单元格、段落与标题都通过 HTML 转义；不允许在 JSON 中塞脚本/HTML。长文用新页拆分；DOM 与截图判定实际容量，不能只凭最大行数判定合格。

报告页面文字与 claim_ids 的语义对应需要研究员检查；机器只能证明 ID 存在与链路连通。Markdown 末尾完整列出主张、来源与每条定位，HTML 页脚列出该页来源与定位。
