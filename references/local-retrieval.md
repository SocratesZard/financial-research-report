# 目录取材、本地正文检索与备用OCR

在IMA搜索缺游标、需要跨资料补查，或PDF文字层缺失/乱码时读取。它补充IMA发现和原件阅读；完整研究仍保留公开来源的独立路线。用户只要求替代路线试跑时，交付范围就是该试跑，不扩充为完整日报/周报。

## 推荐流程

**目录分页收集条目 → 筛选并下载原件 → 原生文字提取 → 当前模型识图补读 → 本地页段检索。** 本地OCR作为备用：识图不可用、仍有读不清内容，或大量扫描页需批量转文字时启用。不默认加入MinerU、PaddleOCR-VL、云解析API或额外模型服务。

### 先按实际识图能力分流

- **当前执行模型能识图**：正常页直接读取提取文字；缺失页和关键图表渲染后用模型自身的图像输入能力阅读，将实际核对内容按页补录。无法辨认的文字再使用本地OCR协助。
- **最终写作模型只有文本能力，但已有可用识图环节**：先把实际图像阅读结果整理为带原件散列、物理页、转录范围和不确定项的文本，再交最终模型综合分析。不为此默认新建子代理、切换模型或接入付费API。
- **执行环境也只有文本能力**：例如用户实际选用的DeepSeek型号不支持图像输入，先用原生文字，缺失时显式启用本地OCR（`--ocr auto`）。渲染PNG不等于看过该页，不得写VISUAL_REVIEW_RECORDED。无法核清的图形、图例、表格行列与数字留作局部缺口，不靠猜测补齐。

按本次实际模型及工具能力分流，不以品牌名推断所有型号的能力。Skill不改变模型本身的多模态能力。OCR独有的关键数字和日期，能用原生表格、原始公告或算术关系核对的先核对；仍无法确认的内容不升级为已支持事实。不要因少量图表缺口停止其余有证据的研究，除非用户明确设了停止条件。

有原生文字和表格时优先使用可定位的解析结果；复杂表格/图表优先看渲染页的行列、图例、脚注和单位，按所需证据补录。需要时用pdfplumber等工具读取原生表格并保留单元格位置，而非假定普通文本顺序就是表格结构。助手的页面视觉阅读使用当前会话的看图能力，不能称作本机离线视觉推理；明确要求全离线时，按可用本地引擎和人工看图路径执行，不自动新增云OCR服务。

目录元数据可逐层枚举；原件只下载已筛选且授权的候选，不机械下载整库。日期不明但重要的候选先核首页/摘要，不能因文件名无日期直接排除。保留未进入、未下载和未读范围。目录缺游标仍是未知；不能用别的接口游标代替。用户设定的停止条件继续优先。

### 1. 可恢复的目录分页

```text
node scripts/ima_catalog.cjs --page-size 50 --max-pages 20 --max-folders 100 --out <本期/ima/tree-01>
node scripts/ima_catalog.cjs --resume <本期/ima/tree-01/ima-snapshot.json> --page-size 50 --max-pages 20 --max-folders 100 --out <本期/ima/tree-02>
```

可用`--folder <真实目录ID>`从相关子树开始。其余配置/helper规则与ima_source.cjs一致。只调用`get_knowledge_list`，逐文件夹沿真实next_cursor走到is_end；不调用远端搜索、不下载原件。目录循环/重复项去重。预算耗尽保留pending_folders，续跑用新输出目录；UNKNOWN路线进入blocked_folders，不重放首页。ACCESS_FAILED保存失败及待续目录，停止后续依赖。失败后只有明确的新一轮调用才重试，不自动无限重试。

`VISIBLE_SCOPE_ENUMERATED`仅表示所选可见子树的记录路线均已结束；不是库内所有内容、关键词全文结果或研究覆盖完整。批次预算控制单轮工作，不是最终材料数/页数上限。

```text
node scripts/ima_source.cjs catalog-search --snapshot <已完成目录/ima-snapshot.json> --query 算力 --query 光通信 --out <本期/ima/title-matches>
node scripts/ima_source.cjs fetch --snapshot <已完成目录/ima-snapshot.json> --id <选中媒体ID> --out <本期/originals>
```

catalog-search只匹配标题/标签；不应成为唯一候选筛选手段。日期、作者、主题、重大分歧和前期未决项共同决定取件；正文线索不一定在标题里。分批fetch时分别建立索引，或在本期合并同库、同原件合同的files清单后建立索引，不跨账户混用身份。

### 2. 本地提取、OCR与索引

```text
python -X utf8 scripts/local_corpus.py doctor
python -X utf8 scripts/local_corpus.py build --evidence <原件目录/ima-evidence.json> --out <本期/corpus-01> --render-review-pages
python -X utf8 scripts/local_corpus.py search --corpus <本期/corpus-01> --query 光通信 --query CPO --out <本期/hits-01.json>
```

也接受显式本地清单`{"files":[{"path":"原件路径","title":"资料标题","sha256":"可选的原件散列"}]}`；相对路径从清单文件所在目录解析。原件SHA256有记录时先校验，不符则不索引该来源。PDF逐物理页、DOCX逐段落（含表格内段落）、TXT/MD/CSV逐行定位。Excel、PPT、旧Office及IMA笔记走对应模块；不把不支持格式悄悄丢掉或声称已读。

生成`corpus.sqlite`、`corpus-manifest.json`、逐页/段文本及`review-queue.json`。默认`--ocr off`，`--render-review-pages`只渲染提取可疑页供视觉阅读，不启用OCR。实际启用OCR时另存PNG和OCR JSON，记录图像散列、引擎、语言、原始识别文字和词框；Windows OCR无置信度就写null，不编分数。资料日期保持待核，不从文件名、入库、打印留存或创建时间自动填成发布日期。

索引区分native原生文字、visual实际视觉补录和ocr识别三种variant，检索返回原件散列、页码/段号、命中片段及复核状态。NFKC和大小写归一、中文字符间的OCR空格归一只作用于检索表示，原始文字不改。日期搜索命中可能是排期、评级历史、价格或年份片段，不能自动确认资料发布日期，也不能把零命中当作当期没有信息。

### 3. 把实际视觉阅读写回索引

打开review-queue中所需PNG，实际阅读相关页，再写本期补录JSON。不得把原生提取或OCR结果未看图就标为视觉复核。格式如下，值均来自本次实际原件、图像和阅读记录：

```json
{"supplements":[{
  "source_sha256":"原PDF的SHA256", "page":7,
  "image_path":"相对于补录JSON的渲染PNG路径", "image_sha256":"该PNG的SHA256",
  "text":"实际读到并转录的原文或明确注明的摘要",
  "extent":"body_only", "reviewed_by":"实际复核者", "reviewed_at":"实际带时区时间",
  "review_note":"正文已核；图表完整数值序列未转录"
}]}
```

extent为full_page/body_only/selected_regions；只补标题、正文或部分区域时不能填full_page。所有数字和表格内容只按实际复核范围写入，不补想象的缺项。脚本核对原件与PNG散列、物理页及记录完整性，但不能证明复核者确实读对了。

```text
python -X utf8 scripts/local_corpus.py build --evidence <原件清单> --supplements <本期/visual-review.json> --out <本期/corpus-visual>
```

新索引保留原生与视觉文本、原图及转录范围；局部补录不会把遗漏表图自动变成完整。未绑定到实际原件/页或图像散列不符会报缺口。若原件散列不变，可继续使用已有索引；下一期重要材料仍需复取核查版本，不把旧索引当作实时同步。

### 4. 备用OCR后端的选择

需要启用备用OCR时，先用**已有、本地可用**的引擎，缺什么才补什么；不为此默认安装大型GPU环境或将私有研报上传云OCR。`--ocr auto`是显式启用备用引擎的参数，不是默认行为。

- **备用引擎在Windows优先用系统离线OCR**：`windows_ocr.ps1`调用Windows.Media.Ocr，以本机实际安装语言为准。doctor列出可用语言和最大图像尺寸。无需额外Python OCR包；实际OCR通过Windows PowerShell 5.1运行，调用方可用PowerShell 7或其他shell。
- **其他系统或已有Tesseract时**：`--ocr tesseract`使用本地CLI和已安装语言包；保留TSV词框与引擎置信度。`auto`优先可用Windows引擎，再用已有Tesseract。Tesseract分数不能当作财务数字真实性分数。
- **复杂表格、图表、双栏、水印重叠**：OCR用于定位和补读，关键行列关系、坐标轴、图例、单位、脚注仍通过渲染页视觉阅读；必要时选择另一已有引擎作定向对照。不从OCR词顺序直接拼出财务表格或假定读全图内数字。

```text
python -X utf8 scripts/local_corpus.py build --evidence <原件清单> --out <新目录> --ocr windows --ocr-language zh-Hans-CN
python -X utf8 scripts/local_corpus.py build --evidence <原件清单> --out <新目录> --ocr windows --ocr-language en-US --ocr-pages 4,7
python -X utf8 scripts/local_corpus.py build --evidence <原件清单> --out <新目录> --ocr tesseract --ocr-language chi_sim+eng
```

`--ocr-pages`追加指定物理PDF页，应用于清单中每份PDF，适合对非空但漏图/乱码的页强制补查。默认300dpi，支持`--dpi`调整；尺寸超出引擎上限或识别失败会明确留缺口，不删除原文。Poppler/Tesseract未在PATH时可用`--poppler`/`--tesseract`指定，或用RESEARCH_PDFTOPPM指定渲染器。桌面捆绑Poppler可按运行时相对位置发现；Skill不含个人绝对路径或二进制。

可按任务资源设置`--ocr-max-pages N`；未处理页写DEFERRED_BUDGET并保持PARTIAL，不把预算当作正文只读N页的研究上限。无引擎、无语言、无渲染器或OCR为空也保留相应状态。已有输出不能覆盖，原件不改。

## 如何判断该补OCR、该回看图像

脚本会检测无字/少字、图片占比高但文字少、异常字形、碎片行等候选。**这些是启发式，不是文字完整性检测器**：有一行页眉不等于正文可读；有大量水印也不等于有效内容多；图片内图表可能藏在文字正常的页面中。关键来源在阅读时仍需看结构、关键页和表图，按实际缺口追加OCR或视觉核对。

建议把成本花在所选资料的承重证据：先扫描每页提取质量，对关键缺失页进行视觉阅读并补录；扫描页很多或视觉能力不可用时，再启用本地OCR辅助检索。按命中回读整段、邻页与表图脚注。不是每页都重OCR，也不是只读前两页就结束。无需把每页百分比、图内坐标值全部转成数据库；没有转录的部分要在覆盖中说明，不能声称可完整检索该图表。

## 证据与状态

| 状态 | 能说明什么 |
|---|---|
| VISIBLE_SCOPE_ENUMERATED | 所选可见目录范围的记录分页结束 |
| DOWNLOADED_NOT_READ | 选中原件已取得并保存散列 |
| INDEXED_REVIEW_PENDING / EXTRACTED_NOT_READ | 可提取文字已入索引，尚不代表研究阅读 |
| VISUAL_REVIEW_RECORDED | 已提供实际视觉阅读记录与原件/PNG绑定；转录完整性仍按extent，不由脚本证明语义正确 |
| OCR_UNVERIFIED | 本地识别成功，尚未视觉核验；Windows没有置信度也正常 |
| PARTIAL / PARTIAL_INDEX | 存在待分页、未提取、未OCR或实际失败等缺口 |

模型实际阅读与视觉核验后，将使用页/段、原件散列、PNG散列及OCR/视觉复核情况写回本期来源与研究审计。关键数字、日期、主体和单位在视觉核验前不因OCR命中升级为已支持事实。不要把脚本自动状态改成“全文已读”；只有实际读完对应范围才更新阅读记录。机构意见归属、公开上游核验与来源独立性规则继续适用。

开发机已实测系统离线中英文OCR、图片PDF恢复检索，以及一份混合PDF的缺失页自动识别。此经验不证明每台机器都有相同语言/引擎，也不证明表格结构和所有数字识别正确。

## 最小验证

```text
node scripts/test_ima_catalog.cjs
python -X utf8 scripts/test_local_corpus.py
python -X utf8 scripts/test_local_corpus.py --ocr-smoke
```

最后一项在当前Windows实现中使用本地中文字体、实际系统OCR做图片PDF中英文恢复验收；其他平台用可用Tesseract和真实样本另验。没有执行的后端标NOT_RUN，不把离线单元测试说成全库在线验证。

实现参考：[Microsoft OcrEngine](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine)、[Tesseract命令行](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)、[Tesseract识别质量](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)。
