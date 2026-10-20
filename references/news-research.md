# 新闻研究：发现、筛选与独立审计

适用任意行业与用户时间窗口，不载入某一周的新闻答案。依次完成覆盖规划、候选发现、覆盖复查、重要性筛选、证据与时间核验、产业分析。用户明确限制来源或预算时缩减并记缺口，不能伪造记录满足覆盖。

已配置IMA时，在原有主动联网发现、候选筛选与已有资料读取上增加知识库路线，操作见[ima-source.md](ima-source.md)。配置可用时每期两路都实际尝试；未配置时如实记录未执行IMA路线，不冒用开发账户。网络独立覆盖本期产业与信息类型，不局限于IMA已出现的公司或事件。目录/关键词搜索与公开查询一起留记录，按原始上游归类到industry_research、conference等既有来源路线，不增加一个假独立“IMA确认”。先取原文，再提取事实、观点与未来验证节点；只见标题不能支持正文主张。下周排期走[next-week.md](next-week.md)，不混进本周已发生事件。

## 1. 先拆价值链，再拆信息类型

确定上游投入/设备、中游生产或服务、下游客户及基础设施与资金约束。子板块、关键公司和指标由本次范围产生，不固定TMT章节或公司名单。跨行业改用该行业适用的合同、许可、产能与经营指标。

每个子板块映射以下8类查询意图；一个实际查询可合理覆盖多格，不要求每格另搜：

| 类型ID | 查询意图，使用当地语言/主体别名扩展 |
|---|---|
| financial | 财报、业绩、指引、投资者日；earnings/results/guidance/investor day |
| technology | 产品、架构、规格、基准、展示/送样；release/architecture/benchmark/sample |
| orders | 客户、采购、订单、长期合同、交付；award/order/contract/offtake/delivery |
| capex | 资本支出、预算、设备采购与现金支付；capital spending/budget/investment |
| credit | 融资、债券、借贷、再融资、利差/评级；funding/debt/loan/spread/rating |
| supply | 产能、交期、价格、利用率、库存、供应约束；capacity/lead time/pricing/utilization |
| infrastructure | 建设、许可、接入、能源/物流、投运；construction/permit/connection/commissioning |
| regulation | 规则、审批、贸易、许可、执法；regulation/approval/export/licensing |

不适用可注明产业范围理由；不能因难搜或未找到而标不适用。泛搜“本周产业新闻”或一个大会页面不能证明所有格已查。

来源路线另查：`ir_filing`（财报/IR/交易所）、`official`（公告/监管/正式技术文档）、`media`、`industry_research`、`conference`、`contract_counterparty`（客户/采购方/公用事业/招投标）。后两类按产业相关性使用。官方、IR、媒体、行业研究都应真实尝试；访问受限记尝试与结果，不强求每类都有入选新闻。

先查窗口内财报/投资者活动日历、融资/重大合同与建设信息，再查技术热点。主办方、参与者、客户与资金方交叉定位。中文与英文各用自然表达，不只翻译同一标题；行业集中其他语区时补当地语言。搜索日期过滤用于发现，发布日期与新披露增量回原文核验。

## 2. 候选池与筛选前覆盖复查

发现时先保存候选身份、线索链接、板块、类型、实现阶段、新事实与待核项，不急于填满最终条目数。候选池可以有仅标题的重大线索，正文不得将其升级为已确认事实。

**筛选前**检查：是否同一大会/机构/地区过度集中？财报、信用、合同、capex、产能与基础设施是否被挤掉？沿别名、对手方、IR清单或非会议来源补查薄弱项。最终核验中新发现重要候选时重开筛选与覆盖检查。

矩阵是查漏入口，不是搜过即完成。宽泛查询反复只有跨期/旧闻时，为该薄弱板块按市场地位、瓶颈或交易对手关系选少量本期关键主体，查看其日期排序的公告/IR清单，再查对手方及合作/研发/工艺/互连/封装等**适合本行业的能力与用途**关键词。不得只等标题命中“AI/算力”。以窗口范围查询配合原文日期核验，不用只含某一天的检索代替整周。主体由本期产业映射产生，不能固化前两次测试公司。

`discovery_review`记录关键主体查验、用户要求地区的覆盖与补查动作。地区新闻少时不强配数量，明确是范围内未找到、未查、访问失败或证据不足。旧闻/窗外候选能说明碰到过线索，但不构成窗内技术/订单已充分查验；无结果格需合理的定向尝试或保留发现缺口。排除合理的事件不算自动失败，审计区分未发现、待核、取舍与入选遗漏。

覆盖格状态：
- `searched_events`：真实查询且找到候选；
- `searched_no_qualifying`：已查但未找到符合本期/重要性要求的事件，不等于未发生；
- `leads_insufficient`：有线索，证据/时间不足；
- `not_searched`：未查，写原因；
- `access_failed`：本路线访问失败且未取得有效结果；
- `not_applicable`：有产业范围理由。

查询保存原始串/访问入口、语言、对应格与来源路线、实际尝试时刻、结果/失败说明、候选ID。不能事后编写“应该搜过”的记录。来源类别覆盖与板块矩阵分别检查。记录中的未查、失败或线索不足应披露；时间/预算耗尽就停止并报告局限，不无限检索、不声称全量覆盖。

## 3. 重要性与入选决策

五维写简短理由，可选高/中/低或0–2辅助分，不机械加权截断：

1. **影响**：改变供给、需求、成本、资本可得性或技术路线的哪个变量？
2. **增量**：相对先前披露新增数字、合同、结果或约束，还是仅重述？
3. **规模/范围**：量级、持续性、涉及环节与瓶颈。口径不明的大金额不能直接判重大。
4. **实现阶段**：规划、演示、样品、量产、约束性合同、交付、已实现财务、监管行动等。不是线性成熟度评分，融资冲击或规则变化也可能立即重要。
5. **证据**：原文、独立核对、公司自报、媒体转引还是标题线索，分别支持哪些内容？

只有独立新闻摘要可默认精选8–12条。完整日报/产业周报不按这个数截断，也不先定页数再倒推候选；重要主题由证据、分歧与判断需要决定深度。容易读取不等于重要；高影响难取证的候选先定向追查，再按已核事实、归属观点或未决问题决定如何呈现。没有预期资料就比较此前披露，不捏造“超预期”；板块不强分名额。

每个候选为`selected/pending/excluded/duplicate`之一，均有理由；高重要性未入选须写实际追查、障碍或取舍依据。合并保留目标ID。先建池复查，最后决策；不能从最终稿反填全部候选，也不能只标pending就停止仍可合理执行的查证。

终选需横向说明哪些候选更改变承重变量、为何留在正文或待核，不能所有条目都标high并复用同一句入选理由。归因尚未量化不自动降低重大已披露数字的重要性，反而可能提高追查优先级；这不意味着自动入选或保证利好。

对重大财务/经营数字增加量级检查：同比、环比、可用历史基准、可解释比率/利润率及预测修订幅度；各项可不适用或无法计算，但要说明。只用有来源、已核对同口径的输入；异常先回查单位/小数点、期间、分母与口径，再查业务驱动，最后重审排序。不能把缺分部数据误写成集团数字没有可分析价值；也不能凭比率异常就断言具体业务贡献。具体计算与证据规则见 [analysis-evidence.md](analysis-evidence.md)。

## 4. 证据、数字与产业传导

细则见 [research-protocol.md](research-protocol.md)。每个重要数字关联来源链接与短摘录或精确表格/章节/段落，不只给首页。记录原始值、单位、币种、期间、分母、比较基准及分类；未知保留未知与限制，不适用明示。正文可压缩，审计保留会改变结论的口径与计算。

重要事件分析五问：**新事实 → 约束/经济变量 → 传导环节与条件 → 证据边界 → 后续证实/否定指标**。例如考察合同是否具约束性、何时形成需求/收入、谁承担融资/交付义务，而非套用行业结论。分开事实、合理推断、研究假设；数量、价格、现金支付与最终投运可不同步，产业受益也不等于股东收益。

依据不足则 `analysis.status=insufficient`，指出未知环节与应查内容；约束/机制可null，不硬填五问。不用“推动行业升级/重塑格局/利好相关企业”等无机制判断。分析不确定性不自动降低事实的新闻重要性。

insufficient应限定到具体归因缺口：已核集团比率或展望修订仍可计算；业务驱动另做定向追查，将公司已披露的驱动、由机制推断的影响、无法量化的贡献分开。不能全篇只重复“未来待验证”。新审计的量级、驱动与状态区分记录见 [analysis-evidence.md](analysis-evidence.md)，不在本文件重复合同。

## 5. 时间、增量与去重

分别记录原文发布日期/时区、首次可确定的公开披露、实际发生时间、本窗口新增量。预告、演示、订单、交付是不同里程碑；替换稿、重发与媒体复述不算新事件。稳定 `event_key` 用主体/对象/报告期或版本/里程碑识别经济事件，来源日期与URL不是唯一身份。新里程碑或实质修正才单列，关联旧事件。

用户时区决定窗口，能确定时另保留北京时间。只有日期、时区未知或首次披露未知时，不补时分；保留日期或可能区间及推导依据。区间完全落窗才是in_window，跨窗为overlaps_window并说明；无法定位为unknown、待核。页面更新时间、版本生效日不自动等于首次公开日。截止后发表的材料不能证明“截止当时已知”，可作后续核验材料单列。

## 6. 完整研究的结束条件

以下是实质判断，不是条数/页数配额，也不声称穷尽全网。结束前在已有coverage_review.findings及remaining_gaps中简记“充分展开/部分完成”、依据与仍影响判断的未决：

- 用户范围内的重要变化经过公开与IMA独立发现、薄弱处定向复查；未查、已查无合格事件、线索不足、访问失败和明确取舍分别可辨，不能只靠矩阵状态声称查全。
- 对可能改变主线、排序或投资判断的重大待核线索，已经查原发布/关键主体、对手方或合理替代路线，记录实际查询与结果；确有访问、权限、资料缺失等障碍要具体说明。仅在标题看到线索后标DRAFT/pending不算完成必要研究。
- 核心主题已解释新事实、关键变量、传导、竞争解释及验证条件；能归属的机构/渠道观点可参与论证，未确立的环节局部限定。重大主题允许多页，不提前缩成事件摘要。
- 重要数字、市场窗口、可核预期和主要结论互相一致；仍可能反转判断的未知没有被隐藏，已有充分证据的结论也未被泛泛免责声明替代。
- 定向补查主要返回重复/无实质增量，或核心问题已得到足够支撑且剩余工作有合理取舍；才可收束。用户明确资源边界、外部障碍下可部分交付，须指出尚未查的关键项和下一步，不能假称完成，也不无限检索。

排版、侧文件、算术/结构通过都不独立满足这些条件。DRAFT描述交付的证据/范围状态，不免除尚可执行且影响核心判断的研究。不要为使状态变好而降低原定范围或把未查写成无事件。

## 7. 审计侧文件（v1基础与v2扩展）

`assets/research-audit.template.json`是空白结构，不是执行记录。真实研究填写 `research-audit.json`，与正文同目录；只在对话交付也创建并给路径。旧测试基线只读，不把详细台账全塞正文，不为审计额外生成未请求的HTML/PDF。

顶层：`audit_version,report_id,window,scope,queries,coverage,source_coverage,coverage_review,candidates,sources,claims,limitations`。

- `window`：`start/end/cutoff_at`为带偏移ISO时刻，`timezone`为用户IANA时区。端点偏移须与该时区一致。查询时刻可晚于历史截止，证据当时可得性另核。
- `scope`：`subsectors`字符串列表，`info_types`固定上述8个ID，`source_families`固定上述6路线。固定的是类别，不是公司或新闻。
- `queries[]`：`id,query,language,attempted_at,subsectors,info_types,source_families,outcome,notes`；outcome为`results/no_results/access_failed`；语言用zh/en等代码。
- `coverage[]`：每板块×类型一条，字段`subsector,info_type,status,query_ids,candidate_ids,note`。候选应实际涉及该格。`source_coverage[]`：每路线一条`family,status,query_ids,note`，status为`searched/not_searched/access_failed/not_applicable`。
- `coverage_review`：`before_selection:true,findings,follow_up_query_ids,remaining_gaps`，记录实际完成的筛选前复查，不用布尔值代替内容。
- `sources[]`：`id,url,title,kind,access,read_scope,accessed_at,independence_group,publication`。kind/access沿旧合同；read_scope为`full_text/excerpt/headline/not_read`。转载相同上游共用independence_group。URL、阅读与支持是否真实由研究核查，脚本不背书。
- IMA私有原件的url可为null，增加provider及库/媒体标识、retrieved_at和本期evidence快照散列，详见ima-source.md；保留同样的阅读、上游独立性、数字和时点要求，不用签名URL或平台首页补齐URL字段。
- 时间对象`publication`、候选`first_disclosed/increment_time`：`raw,timezone,precision,lower,upper,beijing_lower,beijing_upper,note`。precision为`instant/date/range/unknown`；lower/upper为带偏移的**可能界限**，未知可null。instant上下界相等且原文有依据，日期/范围说明界限推导。北京时间能确定则填，否则null加原因；范围界限不是事件精确时刻。
- `candidates[]`：`id,event_key,subsectors,info_types,stage,summary,new_fact,prior_baseline,increment,first_disclosed,increment_time,window_status,source_ids,importance,assessment,decision,reason,duplicate_of,claim_ids,analysis`。window_status为`in_window/overlaps_window/outside_window/unknown`；assessment含impact/novelty/scale/realization/evidence理由；importance为high/medium/low；stage按原文，不固定行业阶段。
- `analysis`：`status`为reasoned/insufficient；字段`new_fact,constraint,mechanism,evidence_limit,next_check,unknown_reason`。reasoned需有机制依据；insufficient允许constraint/mechanism为null，须解释未知和后续观测。
- `claims[]`：`id,candidate_id,text,kind,verification,assumptions,source_refs,numbers`，kind/verification沿旧合同；推断/情景写assumptions。source_refs含`source_id,locator,evidence,scope_limit`，evidence为短摘录或忠实转述，scope_limit解释片段边界。标题/未读不支持supported/corroborated；后者须独立上游。
- `numbers[]`：`literal,unit,currency,period,denominator,comparison,basis,source_id,locator,limitation`；basis为realized/company_forecast/company_spec/media_report/third_party_estimate/researcher_calculation。未知可null并写limitation，不适用明确说明；公司性能/指引不因有官方链接变成独立验证；计算在证据/limitation写公式与输入。

`scripts/check_research_audit.py`仅检查字段、覆盖/候选/证据链、部分日期及去重一致性。`structural_ok`不表示检索与推断正确；`coverage_complete`仅表示无**记录中的**未查/失败/不足，不代表真正查全。它不联网、不重搜、不判断摘录真假、独立性真假或研究判断优劣。

新研究用audit_version=2，在上述基础上增加 [analysis-evidence.md](analysis-evidence.md)的发现深度、计算/驱动及持久性字段。旧v1继续检查但提示新检查未覆盖，不改旧审计和旧结论。审计数据版本与完整报告schema_version分开。
