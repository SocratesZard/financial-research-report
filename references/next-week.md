# 节点复盘与下周验证

先复盘已发生节点，再前瞻。章节位置与权重按本期研究调整；[主题导航](../assets/tmt-weekly-outline.json)只用于覆盖复查，不复制参考稿具体公司、日程、阈值或判断。

## 研究过程

在建立本周候选池时同步登记未来节点。先读已配置的IMA知识库中与主题相关的原报告/纪要，提取作者关注的财报、会议、监管、交付和量产窗口；再到公司IR、交易所、统计机关、监管机关及会议官网核实排期。跨时区以用户时区定窗，同时保留当地原始日期；只有日期就只列日期，原时区不明可写unknown，不生成午夜等假精度。提前发布的预告和未来实际结果分开，截止后找到的结果不能填入“截至当时已知”。

- **节点复盘**：节点／日期／结果／对原判断的含义，绑定本期事件及上期thesis。未取得上期判断就标无可比上期，不反向创造原预测。
- **下周日历**：日期／事件／看什么，记录排期来源、确认状态、重要性和实际查验时刻。confirmed只用于已读官方原文支持的排期；研报提到但未正式确认用tentative，原样参考用reference_only。
- **日期未定的观察项**：融资落地、供电接入、客户验证等无精确日程的事项单列watchlist，写预期窗口、触发指标、推翻条件与证据。不得为了填七天编日期。
- **研究重点**：根据承重变量选重点，优先级1–3只是排序。不强制每天都有事件，不人为增加新闻数量。阈值若是研究假设须绑inference/scenario及assumptions；官方指引绑定原文，不复制参考稿阈值。

## 窗口与结构化合同

Skill版本0.3与报告schema_version 1/2独立。新周报使用可选顶层`outlook`；旧稿无此字段不回填。默认anchor=period_end：覆盖周结束后的下一个周一至周日。用户说“从今天准备下周”则anchor=cutoff_at，取截止时刻所在周的下一周。两个窗口不混同；跨期迟发报告在limitations说明已过日期，不称为尚未来临。具体日期由当期计算，不能固化。

```json
{
  "outlook": {
    "anchor": "period_end",
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD",
    "reviewed_at": "带偏移的实际核对时刻",
    "status": "checked|partial|not_checked",
    "gap_reason": "未查、失败或无合格日程时说明范围和缺口",
    "watchlist": []
  },
  "calendar": [{
    "id": "N01", "date": "用户时区的ISO时刻或日期",
    "original_date": "原始时刻或日期", "original_timezone": "IANA时区或unknown（仅日期）",
    "time_precision": "instant|date", "item": "主体及事件", "focus": "具体观测项",
    "confirmation": "confirmed|tentative|reference_only",
    "schedule_basis": "official_schedule|secondary_schedule|reference_schedule",
    "priority": 1, "importance_reason": "为何会影响承重变量",
    "threshold_basis": "not_applicable|disclosed|research_assumption",
    "threshold_claim_ids": [], "claim_ids": ["CAL01"]
  }]
}
```

watchlist每项为`item,window_text,date_status(unknown/estimated_window),focus,claim_ids`。其依据可为事实或明确标识的推断，不伪装有已确认的排期。calendar的claim仍用kind=calendar；来源须在截止时可得，unknown发布时间的材料无法确定当时可得时降为待核，不因现在可访问就补成历史排期。

## 自动呈现

日历页设置`type:"calendar",calendar_ids:["N01"],blocks:[]`，claim_ids包含选中排期及阈值依据；构建器直接读取calendar生成“日期／事件／看什么”，priority=1浅蓝强调。每页最多6项，长项按实际渲染再拆页；禁止复制一份手写表格造成日期漂移。标题用“下周关注：主体＋事件＋关键观测量”，只有已确认排期才在标题写具体日期。

观察项可设置`type:"calendar",outlook_watchlist:true,blocks:[]`，单页最多7项；少量日历与观察项可同时给calendar_ids和outlook_watchlist:true，由构建器生成两块并保留不同确认状态（各最多4项、合计最多6项，长文仍按实际渲染拆分）。不为区分状态强制每类占一页。无合格排期时用有依据的观察项或缺口说明，不能填占位假新闻。空日历需outlook.gap_reason。页底写最重要的验证变量及必要边界，来源为实际读到的原文/公告。

运行build_report.py会检查窗口、时间转换、确认依据、阈值引用、证据与页面的一致性，并自动同时渲染HTML/Markdown。结构校验不能代替实际查日历或判断重大性；新页面仍要浏览器渲染验收。0.2.1的HTML编辑、PDF按钮和脚本导出继续可用。
