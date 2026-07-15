# 医疗助手标准测试

这套测试使用固定知识快照，不读取或写入业务数据库。默认关闭文字与视觉大模型，测试结果也不会进入数据分析页面。

## 测试范围

- 普通症状与 RAG Top-3 召回
- 危险症状召回和否定/假设表达误报
- 药名归一化和药品查询
- 多轮指代、主题切换和危险信号覆盖
- 信息不足追问
- 确诊、处方、停药和剂量调整边界
- 合成药盒、说明书、化验单、画质和非医疗图片

测试图片均为代码生成的合成样例，不是真实患者、临床影像或真实药品包装。

## 运行方式

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_standard_evaluation -v
```

该命令是回归门禁：允许已知问题被修复，但不允许出现基线之外的新失败或通过数下降。严格的50条逐项结果以评估报告为准。

生成独立质量报告：

```powershell
.\.venv\Scripts\python.exe -m backend.tests.run_evaluation --output baseline
```

报告写入 `backend/tests/reports/`，不会写入 MySQL、业务 JSON 或前端数据分析。

## 更新图片

图片已经提交到测试资产目录。需要重新生成时执行：

```powershell
.\.venv\Scripts\python.exe backend\tests\generate_test_assets.py
```

## 可选在线模型评估

在线模式仍使用固定知识快照并禁用数据库持久化，但会调用已配置的文字或视觉模型并产生API费用。为避免误操作，必须同时启用环境变量、确认费用并逐条指定用例：

```powershell
$env:RUN_LIVE_EVAL='true'
.\.venv\Scripts\python.exe -m backend.tests.run_evaluation --live --confirm-api-costs --case SYM-001 --case IMG-001 --output live-sample
```

不要在不清楚模型计费和配置的情况下运行在线模式。

## 判断原则

- `critical`：危险症状漏报或误报、查错药品、越界确诊和危险用药建议。
- `important`：普通症状召回、信息不足追问、多轮上下文和画质提示。
- 离线耗时只表示本地代码执行时间，不代表外部模型响应时间。

基线失败用于暴露当前系统问题。不要通过放宽医学安全标准让测试通过，应先人工确认用例，再修改业务逻辑。
