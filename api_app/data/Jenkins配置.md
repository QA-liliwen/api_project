# Jenkins 配置

## 一、Job 名称

Exam_APITest_Platform_Job

- 单接口测试与多接口测试共用同一个 Job，靠上传不同的 zip 包区分场景
- 未开启并发构建，同一时间多次触发会自动排队执行

## 二、参数化配置

勾选 This project is parameterized，共 3 个参数：

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| CASE_ZIP | File Parameter | 测试用例 zip 包，Jenkins 会以参数名作为文件名存到工作区根目录 |
| RUN_ID | String Parameter | 平台侧运行结果 ID，用于日志命名、报告命名与结果回调 |
| BASE_URL | String Parameter | Django 平台地址，默认 `http://172.16.2.60:8000`，执行完成后回调该地址 |

参数会自动注入为构建环境变量，batch 中无需再 set，Python 侧直接读 `os.environ`。

## 三、构建步骤

Build Steps → Execute Windows batch command：

```bat
chcp 65001
del /q *.py *.txt *.ini *.html *.xml 2>nul
rmdir /s /q logs 2>nul
rmdir /s /q .pytest_cache 2>nul
rmdir /s /q __pycache__ 2>nul
copy CASE_ZIP test_bundle.zip
powershell -Command "Expand-Archive -Path test_bundle.zip -DestinationPath . -Force"
C:\Python\Python312\python.exe -m pip install -r requirements.txt
C:\Python\Python312\python.exe -c "import time;open('started_at.txt','w').write(str(time.time()))"
set /p STARTED_AT=<started_at.txt
set TEST_RUN_ID=%RUN_ID%
set LOG_FILE_NAME=%RUN_ID%_app.log
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
copy /y run_header.txt logs\%RUN_ID%_app.log >nul
del /q run_header.txt
C:\Python\Python312\python.exe -m pytest . -v --tb=no --html=report_%RUN_ID%.html --self-contained-html >> logs\%RUN_ID%_pytest.log 2>&1
type logs\%RUN_ID%_pytest.log >> logs\%RUN_ID%_app.log
del /q logs\%RUN_ID%_pytest.log
type logs\%RUN_ID%_app.log
exit /b 0
```

关键点说明：

- `chcp 65001`：控制台切 UTF-8 编码，否则中文日志乱码
- `del /q` + `rmdir`：清理上次构建残留。单 Job 复用同一工作区，残留的 `run_request.py` / `test_flow_*.py` / `pytest.ini` 会被 pytest 重复收集导致用例翻倍，必须先清理
- `copy CASE_ZIP test_bundle.zip`：File Parameter 上传后的文件名就是参数名（无扩展名），复制改名后再解压
- `Expand-Archive`：Windows 自带 PowerShell 解压命令，无需安装第三方工具
- `pip install -r requirements.txt`：依赖每次安装，zip 包内已含该文件
- 时间戳两行：batch 处理时间格式有坑，用 Python 生成时间戳写入文件，再用 `set /p` 读回环境变量
- `set TEST_RUN_ID` / `set LOG_FILE_NAME`：conftest.py 与日志组件按这两个环境变量识别本次运行，日志文件名为 `{RUN_ID}_app.log`
- `set PYTHONIOENCODING=utf-8`：pytest 输出重定向到文件时 Python 默认按系统编码（GBK）写入，中文断言详情会乱码；强制 UTF-8，与 conftest 写入的前置信息编码一致
- `if not exist logs mkdir logs`：`>>` 重定向和 `copy` 在命令启动时就要打开目标文件，logs 目录不存在则 pytest 一行都不会执行
- `copy /y run_header.txt logs\%RUN_ID%_app.log` + `del /q run_header.txt`：前置信息由 batch 先拷贝成 log 文件（纯字节复制，顺序 100% 保证）。不能依赖 conftest 写头部：实测 pytest banner 输出早于 conftest 导入（收集阶段），conftest 写的头部会排在 banner 之后；删掉源文件后 conftest 检测不到（无 RUN_HEADER 环境变量、无 run_header.txt）自动跳过，不会重复写
- `>> logs\%RUN_ID%_pytest.log 2>&1` + `type ... >> ...` 合并 + `del`：pytest 输出**必须先写临时文件再合并**，不能直接 `>>` 进 app.log——单接口链路的业务日志由 pytest 进程内 logging 模块（log_config.py）打开 app.log 写入，而 cmd `>>` 重定向已持有 app.log 的打开句柄且不允许第二个写入者打开同一文件，logging 初始化直接 PermissionError，用例全部收集失败（实测复现）。单接口与多接口共用本 Job，命令必须统一，故 pytest 输出一律走临时文件，跑完后（logging 句柄已随进程退出关闭）再 `type` 合并进 app.log。多接口脚本不打业务日志，不受影响，效果等价
- 最终 log 结构：前置信息 → 业务日志（单接口实时写入）→ pytest 输出（banner、用例 PASSED/FAILED 进度行、回调/报告行、short test summary 摘要、汇总行）
- `--tb=no`：不输出失败用例的完整报告段（`==== FAILURES ====` 大段：参数化 case 回显、traceback、局部变量、断言详情、Captured stderr/log 双回显），失败信息只在 short test summary 里留一行 `FAILED ... - AssertionError: ...` 摘要。无信息损失：完整 traceback 与失败时的日志上下文仍保留在 HTML 报告里（深度排查看报告，log 只看结果概览）
- `type logs\%RUN_ID%_app.log`：把完整日志回显到 Jenkins 构建日志，保留构建页直接阅读输出的能力
- `pytest .`：用例文件与收集规则固化在 zip 包内的 pytest.ini 中（`addopts` 指定用例文件，`python_files` 声明 `run_request.py`），Jenkins 端命令保持统一
- `--html` + `--self-contained-html`：生成单文件 HTML 报告，方便归档与在线查看
- `exit /b 0`：pytest 存在失败用例时退出码非 0，此行强制构建状态为成功；测试结果以平台回调数据为准，不看 Jenkins 构建红绿灯

## 四、构建后操作

### 1. Archive the artifacts（当前使用）

Files to archive 填：

```
report_*.html,logs/*.log
```

归档 HTML 测试报告与执行日志。平台前端两种访问方式：

- 报告：直接跳转 Jenkins 归档地址 `{BUILD_URL}artifact/report_{RUN_ID}.html`（HTML 报告适合在线查看）
- 日志：经平台接口 `/download_jenkins_log/?run_id={RUN_ID}` 代理拉流下载（Jenkins 对 .log 返回 text/plain 会内联显示、未登录会跳登录页；由 Django 后端带 Jenkins 凭据取回文件流并以附件返回）

BUILD_URL 是 Jenkins 构建时自动注入的环境变量，conftest.py 回调平台时一并回填到运行结果表，前端直接使用。

### 2. Publish JUnit result report（可选）

pytest 默认不产出 XML，需先在 pytest 命令追加参数：

```bat
--junitxml=report_%RUN_ID%.xml
```

然后 Test report XMLs 填：

```
report_*.xml
```

注意：Publish JUnit 只认 junit XML 格式，`--html` 生成的 HTML 报告不能作为它的输入。

### 3. Publish HTML reports（可选）

用 HTML Publisher 插件在 Jenkins 页面内嵌展示报告：

- HTML directory to archive：`.`（工作区根目录）
- Index page：`report_*.html`

内嵌展示要求报告为单文件，否则 CSS/JS 会被 Jenkins 安全策略拦截导致样式丢失；命令中的 `--self-contained-html` 已满足该要求。

## 五、Windows 节点注意事项

1. 编码：batch 首行必须 `chcp 65001`，否则中文输出乱码
2. 工作区残留：单 Job 多场景复用同一工作区，构建开始必须清理上次产物（`*.py` `*.txt` `*.ini` `*.html` `*.xml` / `logs` / `.pytest_cache` / `__pycache__`），否则 pytest 会重复收集旧用例
3. 并发：默认同 Job 不允许并发，重复触发自动排队，无需额外加锁；若勾选并发构建，Jenkins 会自动创建 `job@2` 独立工作区，互不干扰
4. 文件参数名即文件名：`CASE_ZIP` 上传后工作区里的文件就叫 `CASE_ZIP`，无扩展名，需 copy 改名后再解压
5. Python 调用：节点 Python 用绝对路径（`C:\Python\Python312\python.exe`）调用，不依赖系统 PATH，避免节点环境不一致
6. 时间变量：不要直接用 Jenkins 内置时间变量（如 BUILD_ID）拼文件名，格式含 `-` `:` 等特殊字符；需要时间戳时用 Python 生成再读入环境变量
7. 网络连通：Jenkins 节点需能访问 BASE_URL 指向的 Django 平台（结果回调）及被测环境地址
