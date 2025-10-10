# Android Current Fragments (ACF)

一个简洁高效的命令行工具，用于通过 ADB 快速定位当前 Android Activity 及其包含的 Fragments，并映射到本地源码文件。

## 特性

- **精确解析**：准确识别当前 Activity 的 Fragment，避免其他 Activity 的干扰
- **快速定位**：自动搜索本地源码文件，支持 Kotlin 和 Java
- **灵活配置**：支持多设备、自定义搜索路径、编辑器选择
- **广泛兼容**：支持 Android 11-15，自动适配不同版本的 dumpsys 格式
- **简洁易用**：KISS 设计原则，一键或交互式打开文件
- **调试支持**：内置详细调试模式和多设备测试工具

## 快速开始

### 安装

使用 pipx 安装（推荐）：

```bash
pipx install --editable .
```

或使用 pip：

```bash
pip install -e .
```

### 基本使用

```bash
# 查找当前 Activity 和 Fragments
acf

# 指定搜索路径
acf --search-roots /path/to/app,./external

# 交互式选择并打开文件
acf --open

# 打开所有找到的文件
acf --open-all

# 使用自定义编辑器
acf --editor "code" --open

# 使用 Android Studio 打开
acf --editor "/Applications/Android Studio.app" --open

# 使用 IntelliJ IDEA 打开
acf --editor "/Applications/IntelliJ IDEA.app" --open
```

## 详细用法

### 命令行参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `--adb` | ADB 可执行文件路径 | `adb` (PATH 中查找) |
| `--device` | 设备序列号 | 自动检测（需唯一设备） |
| `--search-roots` | 源码搜索根目录（逗号分隔） | 当前目录 |
| `--open` | 交互式选择并打开文件 | - |
| `--open-all` | 打开所有找到的文件 | - |
| `--editor` | 自定义编辑器命令（如：`code`、`/Applications/Android Studio.app`） | 系统默认 |

### 环境要求

- Python 3.8+
- ADB 已配置并可用
- 已连接且授权的 Android 设备或模拟器
- 本地源码文件（.kt 或 .java）

### 自动补全

启用命令自动补全：

```bash
# 安装依赖
pip install argcomplete

# Bash 配置
register-python-argcomplete acf >> ~/.bashrc && source ~/.bashrc

# Zsh 配置
echo 'if command -v register-python-argcomplete >/dev/null 2>&1; then
    eval "$(register-python-argcomplete acf)"
fi' >> ~/.zshrc && source ~/.zshrc
```

测试：输入 `acf <TAB>` 或 `acf --<TAB>` 查看补全效果。

## 测试

### 单元测试

运行测试套件：

```bash
# 运行所有测试
python -m pytest tools/tests/ -v

# 运行特定测试
python -m pytest tools/tests/test_parsers.py -v

# 使用 unittest
python -m unittest tools.tests.test_parsers -v
```

### 多设备兼容性测试

测试所有连接的设备：

```bash
# 运行多设备测试
python -m tools.test_devices

# 测试特定设备
acf --device <device_id> --verbose
```

### 调试模式

使用详细调试信息：

```bash
# 显示详细调试信息
acf --verbose

# 调试特定设备
acf --device <device_id> --verbose
```

### 版本兼容性

支持的 Android 版本：
- **Android 11**: 使用 `mResumedActivity` 解析
- **Android 12-15**: 使用 `topResumedActivity` 解析
- **Fragment 格式**: 自动适配 `#0:` 和 `#0` 两种格式

## 项目结构

```
tools/
├── __init__.py          # 包初始化
├── acf_cli.py          # 主 CLI 入口
├── adb_client.py       # ADB 客户端
├── parsers.py          # 解析器模块
├── file_finder.py      # 文件查找器
├── file_opener.py      # 文件打开器
├── fragment_finder.py  # Fragment 查找器
├── constants.py        # 常量定义
├── test_data.py        # 测试数据
├── test_devices.py     # 多设备测试工具
└── tests/              # 测试模块
    └── test_parsers.py # 解析器测试
```

## 开发

### 模块化设计

项目采用模块化设计，各模块职责清晰：

- **adb_client**: ADB 命令执行和设备信息获取
- **parsers**: dumpsys 输出解析逻辑
- **file_finder**: 源码文件搜索和映射
- **file_opener**: 文件打开和编辑器集成
- **fragment_finder**: Fragment 查找策略协调

### 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- 参考了 [OpenCurrentActivityIntelliJPlugin](https://github.com/BoD/OpenCurrentActivityIntelliJPlugin)
- 参考了 [FindActivityFragmentPlugin](https://github.com/yndongyong/FindActivityFragmentPlugin)