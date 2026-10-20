# 同事安装、配置与接口教程（0.5.1）

## 1. 安装与选择入口

解压分享包，把完整的financial-research-report文件夹复制到自己的Codex技能目录：默认是`~/.codex/skills/`；设置了CODEX_HOME则用`$CODEX_HOME/skills/`。不要覆盖其他同名版本，先保留旧版。重新打开会话并用`$financial-research-report`调用。Windows默认路径为`%USERPROFILE%\.codex\skills\financial-research-report`。

分享包不含个人API凭证、真实知识库/媒体标识、原始参考稿、私人聊天截图或实际研报。内置报告示例完全合成，只用于检验渲染，不能用于投资判断。安装Skill不授予任何IMA库的访问权限。

三种入口：

- **公开来源研究**：直接调用，无需IMA。明确说明本轮未使用IMA，仍按研究充分性和证据规则完成已授权工作。
- **IMA辅助研究**：完成下面的个人配置；公开来源与知识库分别发现线索，再合并核对。
- **只有本地材料**：用户明确限制不联网时，读取授权文件并标明范围，不自动调用IMA或网络。

## 2. 运行环境

| 功能 | 依赖 |
|---|---|
| JSON校验、HTML/Markdown构建、队列合并 | Python 3.10或更新版本；核心脚本使用标准库 |
| IMA只读适配与个人配置 | Node.js 18或更新版本；另安装IMA官方提供的ima-skill及其ima_api.cjs |
| PDF正文读取 | Python pdfplumber；按图像/OCR情况使用可用PDF工具 |
| 本地正文索引、视觉补录与备用OCR | local_corpus.py使用SQLite标准库；PDF需pdfplumber和Poppler。默认原生解析与视觉补读；Windows系统OCR和已有Tesseract均为备用。详见[本地检索与OCR](local-retrieval.md) |
| Word/Excel读取 | python-docx / openpyxl；Excel不擅自重算外部插件公式 |
| 完整Skill结构检查 | PyYAML及Codex附带的skill-creator验证器 |
| 页面截图/导出PDF | Playwright及可启动的Chromium、Edge或Chrome；qa_deck.cjs支持--modules与--browser指定位置 |

Codex桌面可先调用load_workspace_dependencies定位已有Python/Node与库；不能假定同事具有开发者机器的绝对路径。若本机无相应包，按所需功能安装，例如`python -m pip install pdfplumber python-docx openpyxl PyYAML`，页面检查可在个人工具目录安装`playwright`并使用本机浏览器。不要把node_modules、虚拟环境或浏览器二进制打进Skill包。

以下命令都在Skill目录中运行；PowerShell路径带空格时用`& '<可执行文件路径>'`。Windows中文输出使用`python -X utf8`。

## 3. 配置自己的IMA账户与知识库

先读取已安装ima-skill的SKILL.md和knowledge-base模块。按照其说明在IMA官方的[Agent接口页](https://ima.qq.com/agent-interface)获取自己的凭证，并通过该模块支持的环境变量`IMA_OPENAPI_CLIENTID`、`IMA_OPENAPI_APIKEY`或个人配置文件完成配置。不要把密钥写入聊天、研究profile、命令参数或分享包；本Skill仅复用官方helper，不代收或分发凭据。

官方helper默认位置是`$CODEX_HOME/skills/ima-skill/ima_api.cjs`；未设置CODEX_HOME时使用`~/.codex/skills/ima-skill/ima_api.cjs`。非默认安装可设置`IMA_SKILL_DIR`或每次传`--ima-skill <目录>`。外部ima-skill是独立依赖，不随本包分发；其升级、认证和不同知识库原文权限需按各自说明确认。

先按名字查找自己有权限的库（只读）：

```text
node scripts/setup_ima.cjs libraries --query 我的研究库 --out ./my-run/libraries.json
```

查看生成文件中的名称与id，选择明确授权的库。命令不会替你选择第一个结果，也不使用“可添加知识库”接口冒充读取权限。若分页状态为PARTIAL，可缩小名称查询；原文权限仍需后续单份取件验证。

建立个人profile：

```text
node scripts/setup_ima.cjs init --name 我的研究库 --kb-id <实际知识库ID>
node scripts/setup_ima.cjs check
```

默认写到`$CODEX_HOME/config/financial-research-report/ima-source-profile.json`，不覆盖现有文件。想配置多个库时，init增加`--out <个人配置JSON文件>`，每次运行用`--profile <该文件>`选库；不要修改分享模板为自己的私有标识。

研究profile查找优先级：`--profile` → 环境变量`FINANCIAL_RESEARCH_IMA_PROFILE` → 上述个人配置 → 包内空白模板。空白模板没有库ID，IMA命令会在发起请求前明确报未配置。个人配置位于Skill外，更新Skill不会覆盖它。

check只检查运行时、配置、helper和凭证是否存在，不发送网络请求、不输出密钥，也不证明授权成功。libraries返回名称只证明可以发现该库；fetch成功仅证明该原件可取，不证明全文已读。

## 4. 从发现到阅读队列

每次--out使用新目录；同一目录不会被覆盖。文件夹ID从真实目录结果取得，不猜造。

```text
node scripts/ima_source.cjs inventory --page-size 50 --max-pages 20 --out ./my-run/catalog
node scripts/ima_source.cjs inventory --folder <相关文件夹ID> --page-size 50 --max-pages 20 --out ./my-run/catalog-topic
node scripts/ima_source.cjs discover --query 算力 --query 光通信 --out ./my-run/search
python -X utf8 scripts/merge_ima_snapshots.py ./my-run/catalog/ima-snapshot.json ./my-run/catalog-topic/ima-snapshot.json ./my-run/search/ima-snapshot.json --out ./my-run/merged
node scripts/ima_source.cjs fetch --snapshot ./my-run/merged/ima-snapshot.json --id <选中的media_id> --out ./my-run/originals
```

必要时继续目录分页：

```text
node scripts/ima_source.cjs inventory --resume ./my-run/catalog/ima-snapshot.json --page-size 50 --max-pages 20 --out ./my-run/catalog-next
```

非根目录续页须同时传相同的--folder。搜索响应缺游标时标UNKNOWN，不反复重放首批假装补页；用目录与不同定向查询补充。merged/ima-snapshot.json仍可作为fetch输入；reading-queue.json初始全部为NOT_TRIAGED/METADATA_ONLY，需在实际初筛与阅读后更新主题、日期、范围、定位及采用/排除理由。合并不会自动证明全库覆盖或相关性。

搜索缺游标或需跨文档补查时，推荐“目录分页→筛选取件→本地全文检索”。ima_catalog.cjs负责所选可见子树的可恢复分页；local_corpus.py负责原生提取、视觉补录绑定与页段检索，OCR默认备用。需要OCR再按doctor结果选择引擎，不需把私有原件上传第三方。命令与覆盖/复核边界集中在[本地检索与OCR](local-retrieval.md)。

执行模型具备识图能力时，直接用其图像阅读补读关键页；若最终及执行模型均只有文本能力，则用原生提取和必要本地OCR提供可定位的文本。具体DeepSeek型号按本次实际能力判断，不假设整个品牌都有或没有识图能力；没有看图的执行环境不得记录视觉复核完成。本流程不要求额外文档模型或新云服务。

这些文件含自己的库/媒体标识和本机路径，只用于自己的研究期次，不放回Skill分享包。两个不同库的快照不能混合后用同一个profile取件；分别处理、在研究层按原始上游去重。

## 5. 最小联调：一份原件、少量页、一页报告

向Codex发送：

> 使用$financial-research-report，只做IMA小范围联调。使用我的个人配置，从已发现候选中选1份有权限的PDF，读取相关的1—2页，写一页测试报告。区分原作者观点、机构预测和研究判断；将实际读取范围、来源、页码及原件SHA256写入台账，原件随测试稿保存。生成HTML、Markdown和JSON，检查页面、来源链接与散列。不要扩展成整份周报，不修改既有正式报告。

本版本开发账户已完成这一真实链路验收：重新取1份PDF、读取第1—2页、写1页报告、复制原件进成稿evidence/、校验内容归属/页码/链接/散列，并通过桌面及窄屏页面检查。6PDF、1Word、1Excel的额外取件和提取亦有抽样成功记录。私有原件与测试稿不随包分发；其他账户和资料类型需要各自验证，笔记模块及所有子目录未被此验收覆盖。

模型实际读完相关段落后，按[data-contract.md](data-contract.md)写report.json。IMA来源最小结构如下（此处仅为字段示意，不是可直接提交的真实证据）：

```json
{
  "id": "S_IMA_1", "title": "实际原件标题", "kind": "secondary",
  "access": "opened", "read_scope": "excerpt",
  "accessed_at": "带时区的实际读取时刻", "published_at": null,
  "provider": "ima", "knowledge_base_name": "我的研究库",
  "knowledge_base_id": "自己的实际库ID", "media_id": "实际媒体ID",
  "retrieved_at": "实际取件时刻", "url": null,
  "path": "输入稿evidence中原件的绝对路径",
  "snapshot": {
    "path": "evidence/原件.pdf", "sha256": "原始字节的64位SHA256",
    "extent": "仅PDF物理第1—2页已复核", "note": "保存原件，未宣称全文已读"
  }
}
```

source_refs写source_id、locator、实际读到的支持摘要，按审计规范保存最短必要原文。access=opened表示已打开来源，read_scope=excerpt限定只读片段；不要把fetch的DOWNLOADED_NOT_READ直接改成全文已读。构建器不会自动理解PDF，也不会把原文提取结果自动变成研究主张。

```text
python -X utf8 scripts/build_report.py ./my-run/input/report.json --out ./my-run/delivery
node scripts/qa_deck.cjs ./my-run/delivery/report.html ./my-run/qa --modules <含playwright的node_modules> --browser <Edge或Chrome路径>
```

先把用到的原件放到input/evidence/，report.json的snapshot.path从input/计算相对路径。构建器核查原件散列后将其复制到delivery/evidence/并更新source.path；不要手工在成稿里改数字而忘记更新JSON。完整正式报告还需研究审计与覆盖复查，小范围联调不伪称已完成这些工作。

## 6. 接口速查与故障定位

| 接口 | 用途与边界 |
|---|---|
| setup_ima.cjs libraries | 只读查库名称/ID；支持--query、--max-pages、--ima-skill、--out文件 |
| setup_ima.cjs init | --name、--kb-id、可选--out文件；仅创建本地profile，不接收密钥 |
| setup_ima.cjs check | 可选--profile、--ima-skill；仅环境检查，不访问网络 |
| ima_source.cjs inventory | 指定目录分页；--folder、--page-size、--max-pages、--resume、--previous |
| ima_source.cjs discover | 目录＋关键词；重复--query，其他分页选项同上 |
| ima_source.cjs fetch | --snapshot、重复--id、--max-mb；只取显式选择的原件 |
| ima_catalog.cjs | 可见子树递归分页；--out、--resume、--folder、--max-pages、--max-folders；不调用关键词搜索或下载原件 |
| local_corpus.py | doctor检查本地引擎；build --evidence --out建立原件/OCR索引；search --corpus --query回到页段和原件散列 |
| 所有ima_source命令 | 必须--out新目录；支持--profile和--ima-skill；stdout输出状态与计数，明细在JSON |
| merge_ima_snapshots.py | 多个同库快照＋--out新目录；只合并元数据，不发网络请求 |

ACCESS_FAILED或程序错误返回非零退出码，停止依赖步骤并查看实际msg；PARTIAL可以正常退出，仍需查看路线与覆盖缺口。QUERIES_COMPLETE仅指记录的路线已结束。搜索没有游标、媒体需要notes模块、文件类型不支持、乱码或公式无缓存分别处理，不能一概当成无权限或无材料。

离线自检：

```text
node scripts/test_ima_source.cjs
python -X utf8 scripts/test_ima_merge.py
python -X utf8 scripts/selfcheck.py
python -X utf8 scripts/build_report.py assets/example-report.json --out ./my-run/synthetic-demo
```

合成演示不需要IMA，不验证任何真实行情或投资观点。正式使用提示词：“使用$financial-research-report，做一份上周TMT产业周报，读取我的IMA配置，独立展开公开与库内研究，沿用已保存风格，并接续实际前期记录。”无需每期附参考稿或机械指定页数。
