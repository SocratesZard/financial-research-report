# 报告叙事与证据图表（schema_version=2）

用于完整日报/周报的呈现阶段；先组织变量和证据，再写页面。图形数量不是目标，能说明研究问题才使用。旧schema 1可继续读取，新完整报告优先用2。代码不联网，也不验证来源内容真实性。

旧schema1示例/历史演示仍可直接运行build_report.py，不必强行prepare，也不把reference_only素材升级为已核图表输入。

## 研究整理阶段：每个事件留下可画什么

从已核主张的numbers及calculations提取：指标、值、单位/币种、统计期间、比较对象、数据属性、来源定位；同时记录本事件核心变量、候选图形和无法作图原因。不要先写完长文再把文字拆成两栏。

没有时序就不补点；有区间就保留区间；只有规划容量就不估投运进度。缺某业务贡献，不用整体值代替分部值。图形中的已实现、自报、初估、预测、附条件与未核实状态须可辨认。

| 研究问题/intent | 默认图形 | 不适用时 |
|---|---|---|
| comparison 数值/公司比较 | 水平条形；同单位多指标可分组 | 单一数值用事实标注，避免无意义的一根柱 |
| time 时间变化 | 至少4个实际时间观测点才考虑折线 | 2–3点用分期比较；缺期不补零，不能伪装连续趋势 |
| composition 结构占比 | 堆叠条形，分母与整体范围明确 | 未覆盖部分标灰；不自动推断具体用途 |
| revision 同期预测修订 | 哑铃图，版本和同一财年明确 | 不把版本变化当同比/已实现；区间图须真实上下界 |
| milestones 项目阶段 | 日期或有序里程碑 | 未知日期保留未知，不虚构百分比进度 |
| mechanism 合作/传导结构 | 有证据的主体/范围/阶段关系图 | 推断边用虚线及可见“推断”，记录假设 |
| ranking 多公司排名 | 同口径排序条形 | 跨期间须解释可比性；不能把不同单位排序 |
| matrix 多指标公司比较 | 指标矩阵，每列单独单位和期间 | 不跨列用单一数值尺度，不把矩阵当装饰热图 |

## 结构化数据与工具

报告保留sources/claims/events等原合同。将审计中的原子numbers（含id、normalized_value等）原样带入对应claim；已有计算原样放calculations。历史审计只读，新呈现计划另存。

1. 在report输入中写measure_specs及visuals，先运行：

    python -X utf8 scripts/prepare_visuals.py input.json --out prepared.json --plan visual-plan.json

2. 读取计划中的选择理由和数据边界，完成正文/标题后运行：

    python -X utf8 scripts/build_report.py prepared.json --out new-edition

   CLI拒绝覆盖已有产物。修订使用新目录。prepare只做明示单位换算、已有计算复核和图形选择；页面渲染器不估缺值。

measure_specs每项含id、label、binding、unit、precision（可省）、approximate（可省）。binding：

- number：kind、id（已核numbers.id）；factor默认为1。换算需conversion_note，代码检查货币、量纲及倍率。例：百万港元→亿港元为0.01。不得借换算改变币种。
- calculation：kind、id（已有calculations.id）。复核ratio_pct/change_pct/difference及输入基本口径；研究者仍须判断经济可比性。
- claim_literal：kind、claim_id、literal、value、unit、period、basis。只用于原主张已经核过、但没有单独数字ID的显示值，如公司公布的一位小数增长率；必须与原主张文字精确对应。不能把模型新写的数字当来源。

prepare输出measures，包含解析值、单位、期间、属性和原始引用；build再次解析核对，拒绝篡改prepared值。不要在页面blocks内手填另一份数值。

visuals每项：

- id、intent、title、claim_ids、scope_note；数值图另有measure_ids及comparison_basis。
- chart_type可省，prepare选择并写selection_reason。显式改图形需override_reason；不得绕过稀疏时序、单位或预测期间检查。
- 分组条形：series为系列名、groups为组名；measure_ids按组优先排列。
- 折线：time_axis为与观测期间对应的有序时间键，不是生成出来的完整日期序列。
- 哑铃：两个measure_ids必须是同一期间。axis_domain可显式聚焦比较范围，必须包含两个点；在scope_note说明非零起点。比例条形仍从零起。
- 时间线：steps含label、when、status、claim_ids。status为confirmed/ongoing/planned/conditional/unknown/inference。未知日程用序数节点；calendar_axis=true时才按year定位，year_end表示原文日期范围，不能拿几何中点伪装精确日期。可用measure_id标明阶段目标。
- 结构图：nodes含id、label、column、row、status、claim_ids，可加measure_id；edges含from、to、kind、claim_ids。kind为scope/sequence/conditional/inference；推断须assumption并可见标注。先后、合作范围和条件关系不能混同。
- 矩阵：columns含label、unit；rows含label、measure_ids，与各列一一对应。
- 无法画图：status=unavailable并写reason。若有来源支持的分类关系，可另建结构图；不能用空图或装饰图充数。

## 页面与标题

选择visual_analysis版式时，blocks先visual再brief/数据对照，左58%、右42%；不是每页必须此布局。visual块含heading、visual_ids（1–2项），双图需共同解释同一问题。brief含heading、kpis（label、measure_id）和sections（label、text）；由当页问题选择经营驱动、预期差、市场反应、投资含义、边界及验证等，不固定“事实/解释/边界”三节，不重复图中数字塞满正文。

比较图还须经济定义可比：同为%不代表同指标，不能把利润率和业务收入占比画成高低排序。优先同指标跨期/同业；多个不同指标可用标注、分区矩阵或KPI。图应支撑当页命题，不能因有数字就画图。投资观点与市场反应见[investment-framework.md](investment-framework.md)，整体编排见[editorial-policy.md](editorial-policy.md)。

顶层事实标题以“主体+事件+最重要数值/变化”为默认。headline含subject、event、facts，facts各含measure_id、prefix、可选suffix/precision；directional=true时按增长/下降表达有符号变化，覆盖suffix时必须保留单位。prepare从已核测量生成title，build校验一致。封面metrics也优先用measure_id绑定值，可加precision，避免手抄漂移。没有可量化数值时写清主体和合作/技术事件。

标题不默认写研究方法、抽象主题或口号；不要用“增长兑现”“约束前移”“先核…再谈…”“路径有增量”等代替新闻事实。判断性标题需要可核证据。封面可直接用行业、报告类型与覆盖期。

每页回答一个清楚的研究问题；重大主题可由多页分别展开事实/驱动、分歧、定价与验证，不限定一事件一页。合并重复的小事件或相同论据，稀疏单页可以整合；不能为缩页牺牲重要分析，也不能为增图补造数据。无总页数目标，版面容不下时合理分页，不靠缩小字号塞入。

## 图形视觉与验收

统一蓝灰、细线和克制强调；重要值用文字/标记及颜色共同表达。预测用E/斜纹、计划用空心节点/虚线，不能只靠颜色区分。

每幅图有标题、单位/统计期、可见数据标签、适当刻度或节点状态、口径说明及可点击来源。混合货币、MW与金额、合同年限与投运容量不能共轴。不要裁断长标签；改行、改图形或增加合理画布空间。条形保留零点；点位/折线非零范围显式说明。轴刻度是数学标尺，不是新增观测。

执行qa_deck.cjs，实际渲染所有页及手机视口；检查正文、图注、页底、标题、SVG文字边界和标签互撞。看完整截图总览，再逐页放大核对数字与来源，不能只信DOM或“打开正常”。边界检查不证明视觉美观或事实准确。

固定舞台仍为1920×1080，手机竖屏仅缩放；不要把不溢出当作手机可读性通过。未要求移动重排时保留舞台，另提供Markdown阅读稿。

