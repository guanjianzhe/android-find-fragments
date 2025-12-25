# 技术方案与代码理解指南

本文档概述 ACF 工具的技术方案，帮助快速理解核心流程、模块职责以及关键策略。阅读顺序遵循 CLI 执行路径，适合希望迅速熟悉代码的开发者。

## 目标与范围

- **定位当前 Activity 与 Fragment**：通过 ADB 拉取 dumpsys 输出并解析。
- **映射本地源码**：按类名搜索 Kotlin/Java 文件并支持打开编辑器。
- **兼顾性能与稳健性**：提供优化路径并保留回退方案，覆盖 Android 11-15。

## 高层流程

1. **参数解析与设备确认**：`acf_cli.main()` 通过 `argparse` 读取参数后，调用 `validate_device()` 选择或验证设备序列号【F:tools/acf_cli.py†L92-L117】【F:tools/acf_cli.py†L146-L191】。
2. **Activity 解析（优化优先）**：`get_current_activity_optimized()` 先尝试基于 shell grep 的快速路径，失败时回退到全量 dumpsys + 解析。【F:tools/acf_cli.py†L320-L333】
3. **Fragment 解析（严格过滤）**：`find_fragments_for_activity_optimized()` 先尝试包级 dumpsys + 严格解析，若无结果再回退到逐 Activity dumpsys。【F:tools/fragment_finder.py†L10-L52】
4. **源码定位与展示**：`find_source_files()` 在搜索根目录中查找匹配类名的 `.kt/.java` 文件，`display_results()` 以交互或非交互方式输出。【F:tools/file_finder.py†L21-L67】【F:tools/acf_cli.py†L337-L374】
5. **可选文件打开**：根据 `--open`/`--open-all` 触发 `open_file()`，支持自定义编辑器命令。【F:tools/acf_cli.py†L376-L430】【F:tools/file_opener.py†L25-L68】
6. **实时监控（可选）**：`watch_mode()` 每 2 秒轮询状态变化并累积输出，支持 `q`/`Ctrl+C` 退出。【F:tools/acf_cli.py†L193-L288】

## 模块职责速览

| 模块 | 职责 | 关键点 |
| ---- | ---- | ------ |
| `adb_client.py` | 构建并执行 ADB 命令；提供版本、dumpsys、活动组件快速定位接口 | 快速路径 `get_current_activity_fast()` 通过 shell grep 提升性能【F:tools/adb_client.py†L71-L109】 |
| `parsers.py` | 解析 dumpsys 输出的 Activity/Fragment 信息 | `parse_activity_component()` 兼容 `topResumedActivity` 与 `mResumedActivity`【F:tools/parsers.py†L8-L60】；`parse_fragments_strict()` 针对当前 Activity 做范围收窄【F:tools/parsers.py†L94-L181】 |
| `fragment_finder.py` | 协调 Fragment 查找策略与回退逻辑 | 优先包级 dumpsys，失败后改用 activity dumpsys【F:tools/fragment_finder.py†L10-L52】 |
| `file_finder.py` | 搜索源码文件并跳过构建目录 | 使用早期退出，目录黑名单由 `SKIP_DIRECTORIES` 定义【F:tools/file_finder.py†L21-L67】【F:tools/constants.py†L47-L54】 |
| `file_opener.py` | 解析编辑器命令并打开文件 | 自动适配 macOS/Linux/Windows 默认打开方式【F:tools/file_opener.py†L12-L68】 |
| `acf_cli.py` | CLI 入口、参数解析、结果展示、实时监控 | 组合上述模块以完成端到端流程【F:tools/acf_cli.py†L13-L433】 |

## 关键策略与回退

- **Activity 解析回退**：快速路径依赖版本判断与 grep，若无结果则通过 `get_activities_dump()` + `parse_activity_component()` 做完整解析，避免漏报。【F:tools/acf_cli.py†L320-L333】【F:tools/acf_cli.py†L303-L318】
- **Fragment 解析回退**：包级 dumpsys 速度更快，但可能缺少特定 activity 内容；`find_fragments_for_activity()` 通过逐 Activity dumpsys 保障准确性。【F:tools/fragment_finder.py†L10-L52】
- **范围收敛解析**：`parse_fragments_strict()` 先定位包含目标组件的 `ACTIVITY` 段，再仅解析后续的 `Added/Active Fragments` 区块，减少误匹配。【F:tools/parsers.py†L109-L165】
- **系统 Fragment 过滤**：统一在 `SYSTEM_FRAGMENTS` 集合中过滤常见系统/库 fragment，避免噪声。【F:tools/constants.py†L28-L44】
- **目录过滤与早退**：文件搜索中剔除构建/VCS 目录，并在所有目标类名找到后提前退出遍历。【F:tools/file_finder.py†L29-L67】

## 运行模式要点

- **默认模式**：单次获取当前 Activity/Fragment，展示并可选打开文件。【F:tools/acf_cli.py†L335-L433】
- **实时监控模式**：使用 `State = Tuple[str, List[str]]` 记录状态，通过 `compare_states()` 检测变化并附带时间戳输出，适合调试时持续观察。【F:tools/acf_cli.py†L193-L288】

## 扩展建议

- **新增输出格式**：如需兼容新的 dumpsys 结构，可在 `ACTIVITY_KEYS`、`FRAGMENT_ANCHORS` 或解析函数中添加模式，同时在 `tools/tests` 中补充样例。
- **自定义搜索策略**：可在 `find_source_files()` 中增加语言或路径过滤参数，或引入缓存层以加速重复查询。
- **编辑器适配**：`parse_editor_command()` 已支持字符串拆分；如需特殊 IDE 启动参数，可在 CLI 层添加预设模板。
