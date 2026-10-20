# 数字研究价值、驱动与持久证据（audit_version=2）

本规范补充既有检索/候选池，不替换来源分级、时区与证据限制。每项要求按事件实质适用，不强造比率、基准、分部归因或业务进展。原作者或前两轮公司均不是固定清单。

## 数字量级先于排序

对财务/经营披露逐项考虑同比、环比、历史基准与利润率/适用比率。需要时补查**截至窗口已披露**的可比数据，保留实际查询；没有可比期写缺口。同行、前次指引、历史高低点都要原始证据，不能用记忆或截止后分部资料填补。所谓异常须说明相对哪个基准，不能宣称未检验的历史纪录。

- 营业利润率=营业利润/同口径收入×100；分子分母单位、期间、合并范围和会计口径匹配。初步估计所得比率仍是初步估计比率，不变成已审计结果；区间中值相除不代表确定比率，区间计算说明假设。
- 同比/环比/指引相对修订=(本期−基期)/基期×100；基期为零不能计算，负基期、亏转盈等通常展示绝对变化及方向而非误导百分比。百分点差与百分比不同。
- 金额/容量同时检查量级与实现阶段。capex可含涨价、预付款、土建与设备；没有数量和组合证据不能反算设备台数。集团业绩变化不能全归存储、AI或某细分业务。

异常值先复核原始表、单位、币种、小数点、期间、合并范围和预测属性；错误未排除则保留为待核。可计算且有研究价值就保留，不因缺分部而全部放弃；不能据此虚构价格、销量、分部利润或基准。

## 业务驱动和状态区分

对明显新增经营信息（收入/利润变化、指引修订等），除公司总数外，查同次演示相关业务页、财报问答或明确归因，再找可比前次披露。保存查过哪些业务线、结果及缺口；用户给的单一公司修订不得固化为通用行业解释。

驱动链分别记录：公司明确披露/量化的业务驱动；仅方向性提及的驱动；研究员据技术/经济机制推断的影响；无法分解的剩余部分。业务分类可能重叠，终端市场、产品线与技术路线不能直接相加。没有业务增量拆分就不能把总修订分摊到光学、交换、定制芯片等任何具体业务。

五组状态不可跳跃：

| 观察到的状态 | 不能直接写成 | 要补的证据 |
|---|---|---|
| 需要/洽谈融资 | 信用或融资条件已经恶化 | 同期限币种可比利差/利率、契约、评级、发行失败或可得性变化 |
| 签约/采购 | 交付、客户验收或收入 | 履行进度、验收、确认政策 |
| capex金额增加 | 设备数量增加 | 价格、组合、付款与实物量拆分 |
| 规划供电或承购 | 园区实际可接入IT容量 | 接入许可/约束、站点/负荷、投运及冗余损耗 |
| 公司预测/目标 | 确定订单或已实现收入 | 订单约束、交付与当期确认 |

未来条件句可以作为情景，但不要把“若融资成本上升”写成“本周融资成本上升”。谨慎边界之后仍说明当前可判断的变量、相关环节与验证方法；不知道具体归因不意味着已知变化没有研究价值。

## 持久证据

每个用于主张的来源保留实际读取的HTTP(S) `url`、已知原始发布 `original_url`、官方落地 `landing_url`（未知可null并解释）；CDN PDF链接可与官方落地页并存，不随意删除签名参数或编造稳定链接。可持续访问只是尽量选择和保存，不能保证网站永不改版。

关键主张保留**原文**短摘录 `quote` 与 `locator`，转述仍放 `evidence`；翻译标为译述，不伪装原文。依引用额度保存最短必要数字/词组，多个片段合计仍须遵守来源引用限制。无法合法取得或可靠提取摘录则 `quote=null` 并写 `quote_unavailable_reason`，该缺口应显式报告，不能只靠生成的转述冒充原证据。

必要且允许的本地证据放本期 `evidence/`，存原件或最小页图/文本，`snapshot`记录相对路径、SHA-256、范围、说明。不能把Temp、绝对个人路径或目录外文件当持久快照；快照可以缺省但须写 `persistence_note`。没有必要不要强下全部资料；仅URL也存在版本风险。PDF主文同时给来源URL和页码，即使本地附件还能打开也不用它当唯一出处。

失败记录进入 `material_access_failures`：原URL、实际尝试时刻、失败原因、替代来源ID、证据限制。镜像/转载的实际地址和原发布地址分开，未读原稿继续标未读；用对应kind/access/read_scope，不因有快照提高证据等级。

## v2审计字段增量

沿用 [news-research.md](news-research.md) 的v1基础字段；仅新研究用2，旧审计不迁移、不覆盖。以下id与query/source/claim链接须真实存在。

**顶层**：
- `scope.regions`：用户要求覆盖的地区列表，供发现复查，不是新闻配额。
- `discovery_review`：`entity_checks,region_checks,gap_actions,summary`。
  - entity_checks：`entity,subsectors,region,selection_basis,query_ids,inventory_url,outcome,note`，outcome=checked/not_checked/access_failed；有定向查询或真实公告清单入口，不能把泛搜附会为已遍历。
  - region_checks：`region,subsectors,query_ids,candidate_ids,status,note`，status=searched/leads_insufficient/not_searched/access_failed；来自用户要求的地区，缺地区说明限制，不强配新闻。
  - gap_actions：`subsector,problem,query_ids,outcome,next_step`，记录由旧闻/窗外/泛搜不足触发的转向；没有补查写原因及下一步。
- 每个 `coverage` 格加 `search_depth`=broad/directed/primary_inventory/not_searched，`in_window_candidate_ids` 仅指本期/跨窗候选，不能拿旧闻证明窗内事件已发现；无入选也可定向搜索后无结果。
- `material_access_failures`：数组，元素`url,attempted_at,error,alternative_source_ids,limitation`，没有则空数组。
- `calculations`：数组，见下述；没有则空数组。

**来源与数字**：
IMA私有来源使用[ima-source.md](ima-source.md)的持久标识与本期原件快照合同，url允许null；公开来源仍要求可持续访问的原始链接。IMA存储位置不改变原始上游、证据级别或数字口径。
- sources加`original_url,landing_url,snapshot,persistence_note`。snapshot为null或`{path,sha256,extent,note}`，路径相对审计文件目录，sha256为文件内容哈希。CLI检查只读验证存在与散列，不创建/修改快照。
- source_refs加`quote,quote_unavailable_reason`（原文摘录优先，缺时说明）；旧evidence/locator/范围仍保留。
- numbers加唯一`id`、`normalized_value`（数值十进制字符串，日期/未知为null）；不要把日期字符串或未经核验的值强转为指标。

**每个入选候选**：
- `magnitude_review`：`checks,takeaway,priority_effect,follow_up_query_ids`。checks各含`basis,status,calculation_ids,reason`；basis取yoy/qoq/historical/margin/revision/other，status=computed/unavailable/not_applicable。至少评估一项，财务披露须覆盖yoy/qoq/historical/margin四项适用性（不要求都能算）。缺比较基准可以unavailable；not_applicable要产业理由。takeaway说明量级的研究价值，priority_effect解释对排序是否有影响，不能都用通用套话。
- `driver_review`：`status,drivers,unknown,follow_up_query_ids,reason`，status=checked/unavailable/not_applicable。drivers元素`driver,attribution,claim_ids`，attribution=disclosed/inferred；披露与推断对应不同claim种类，保留无法量化的部分。明显经营更新不应未尝试查找就记unavailable；真实未查写限制，不捏造follow_up。
- analysis加`state_checks`数组，元素`distinction,observed,not_established,claim_ids`；对orders/credit/capex/infrastructure及预测类选适用的上述状态对照，纯技术等不适用可空。脚本只能验证记录，不判断文字是否偷换因果。

**计算**：`id,candidate_id,metric,operation,input_ids,formula,result,unit,decimals,scope,interpretation,limitations`。operation取ratio_pct（输入0/输入1×100）、change_pct（输入0/输入1−1）×100、difference（输入0−输入1）；其他复杂计算先保留可复核人工记录，不假装检查器已经支持。

input_ids按上述顺序指向已核查主张的numbers.id；每个输入的unit/currency及经济定义要可比。公式、来源期间、合并范围写清；result为有限十进制字符串、decimals为展示小数位0–6、scope为口径、interpretation/limitations写研究含义与边界。机器只重算数值与基本单位/来源链接，不证明分子分母经济可比。基期非正的change_pct拒绝，改绝对变化及亏盈解释；零分母拒绝。输入仍属公司初估/预测时，计算结果必须保留同等属性，不能升级独立验证。

输出分别报告structural_ok、coverage_complete、quality_recording_complete（仅新记录字段与已记录缺口），以及始终为false的research_quality_verified。不把通过结构/算术检查说成发现、排序或分析已经改善。
