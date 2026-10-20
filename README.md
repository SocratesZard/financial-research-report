# Financial Research Report

面向支持工具调用的AI代理的投研日报、产业周报与TMT跟踪Skill。当前版本 **0.5.1**。

从公开原始来源与使用者自行配置的IMA知识库分别发现线索，读取证据后形成中文研究文稿、可编辑16:9 HTML和可追溯台账。支持本地正文检索、模型自身识图与备用本地OCR。

## 能力与边界

- 独立展开行业研究，筛选重要变化，讨论产业传导、分歧和后续验证点。
- 生成Markdown、HTML、JSON与研究审计；PDF按需导出。
- 沿用保存的风格及前期记录，日常不重复拆解参考稿。
- 可选接入自己的IMA库；搜索缺游标时使用目录分页→筛选取件→本地正文检索。
- 多模态模型直接识图补读关键页，本地OCR备用；纯文本执行模型使用原生提取和必要OCR。

目录结束、机器提取或版式检查通过，都不代表全库覆盖、全文已读或事实已核。完整要求见[模型执行入口](SKILL.md)。

## 安装

从[Releases](https://github.com/SocratesZard/financial-research-report/releases)下载ZIP，将解压出的完整`financial-research-report`目录放到自己的Skill目录：

- 默认：`~/.codex/skills/`
- Windows：`%USERPROFILE%\.codex\skills\`
- 自定义CODEX_HOME：`$CODEX_HOME/skills/`

已有同名版本先备份；个人IMA配置位于Skill之外。重新打开会话后调用`$financial-research-report`。

也可克隆仓库到默认Skill目录：

```bash
git clone https://github.com/SocratesZard/financial-research-report.git ~/.codex/skills/financial-research-report
```

其他支持SKILL.md的代理按自身规则安装。文件、浏览器、模型与工具能力由实际运行环境提供；普通聊天窗口不会因粘贴说明就自动具备IMA或OCR能力。

## 运行环境

| 用途 | 依赖 |
|---|---|
| 台账、HTML/Markdown构建与校验 | Python 3.10+ |
| IMA取材 | Node.js 18+；自行安装并配置官方ima-skill |
| PDF提取和渲染 | pdfplumber、Pillow、Poppler的pdftoppm |
| Word/Excel辅助读取 | python-docx、openpyxl；不擅自重算外部公式 |
| 本地索引 | Python标准库SQLite |
| 备用OCR | Windows系统OCR及已安装语言，或已有Tesseract |
| 页面截图/PDF导出 | Playwright及可启动的Chrome、Edge或Chromium |

在独立Python环境中安装依赖：

```bash
python -m pip install -r requirements.txt
```

Codex桌面可先调用load_workspace_dependencies使用已有运行时。Node依赖、浏览器、Poppler和OCR语言包不随仓库分发。页面检查可在个人工具目录安装Playwright，通过qa_deck.cjs的`--modules`与`--browser`指定位置。

## 快速使用

无需IMA也可执行公开来源研究：

> 使用$financial-research-report，制作上一个完整自然周的TMT产业周报。独立查找原始来源，沿用保存的风格，保存到新目录。重要缺口如实说明，不凑数。

完成个人IMA配置后：

> 使用$financial-research-report，制作指定日期范围的TMT报告。公开来源与我的IMA库分别发现候选；搜索缺游标时采用目录分页、筛选取件和本地正文检索。模型识图补读关键页，本地OCR备用。保留来源页码、散列和实际阅读范围。

仅验证接入时明确要求“只取一份原件、读相关章节、做一页测试稿”；小样本不能代替完整报告取材。

## 配置自己的IMA

先按官方[IMA Agent接口页](https://ima.qq.com/agent-interface)与官方ima-skill说明配置自己的账户凭证。此仓库不分发认证代码或凭据，不授予知识库权限。

```text
node scripts/setup_ima.cjs check
node scripts/setup_ima.cjs libraries --query 我的研究库 --out ./my-run/libraries.json
node scripts/setup_ima.cjs init --name 我的研究库 --kb-id <自己实际选择的知识库ID>
```

个人profile默认位于`$CODEX_HOME/config/financial-research-report/ima-source-profile.json`；CODEX_HOME未设置时使用`~/.codex/config/financial-research-report/`。支持`--profile`及FINANCIAL_RESEARCH_IMA_PROFILE。凭证由官方helper读取，不写入研究profile、仓库、Issue、报告或分享包。

详见[同事安装与个人配置教程](references/team-setup.md)。

## 目录替代路线与正文检索

```text
node scripts/ima_catalog.cjs --page-size 50 --max-pages 20 --max-folders 100 --out ./my-run/catalog
node scripts/ima_source.cjs fetch --snapshot ./my-run/catalog/ima-snapshot.json --id <显式选中的媒体ID> --out ./my-run/originals
python -X utf8 scripts/local_corpus.py build --evidence ./my-run/originals/ima-evidence.json --out ./my-run/corpus --render-review-pages
python -X utf8 scripts/local_corpus.py search --corpus ./my-run/corpus --query 光通信 --query CPO --out ./my-run/hits.json
```

分页预算耗尽时查看pending_folders并续跑到新目录。可见目录枚举不等于全库，标题匹配不等于正文检索。发布日期须核原文，不能把入库、文件名或打印时间当成披露时间。

完整步骤：[IMA资料入口](references/ima-source.md) · [本地检索与备用OCR](references/local-retrieval.md)。

## 识图与OCR

- 当前模型支持图像输入：原生文字优先，关键图片页用模型自身识图，实际补录后进入索引。
- 最终模型纯文本、已有识图环节：把图像阅读结果整理成带页码、原件散列和不确定项的文本。
- 执行环境也只有文本能力：先用原生文字，缺失时为build命令加入`--ocr auto`；未看图不能标成视觉核验完成。

先用`python -X utf8 scripts/local_corpus.py doctor`检查本地OCR。默认`--ocr off`；Windows或Tesseract识别结果标OCR_UNVERIFIED。关键数字、日期、单位和表格关系仍需核对。当前不依赖MinerU、额外文档模型或云解析API；具体DeepSeek等型号按实际能力分流。

## 验证与分享

已对目录分页/续页、所选原件下载、本地中英文检索、视觉补录及Windows备用OCR进行样本验证；Tesseract需在使用者环境另验。

```text
node scripts/test_ima_source.cjs
node scripts/test_ima_catalog.cjs
python -X utf8 scripts/test_local_corpus.py
python -X utf8 scripts/selfcheck.py
```

Windows实际OCR验收可另运行`python -X utf8 scripts/test_local_corpus.py --ocr-smoke`，需要本机OCR语言及中文字体。普通CI不宣称执行这一环境相关检查。

仓库和发行包不包含私人研报、原始参考稿、真实知识库标识、凭证、聊天历史或个人研究结果。示例均为合成演示。机构预测、公司自报和模型推断保持明确归属；输出由使用者复核。

第三方运行时与外部ima-skill按各自条款使用。本仓库暂未指定开源许可证。
