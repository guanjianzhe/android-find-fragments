# 插件参考与源码

本仓库目标：实现“当前页面 Activity/Fragment 定位”相关能力（Android Studio/IntelliJ 平台插件）。以下为已调研的参考插件、功能简介及对应源码地址，便于对齐能力与实现细节。

## 参考插件 1：Open current Activity
- 市场地址：https://plugins.jetbrains.com/plugin/7877-open-current-activity
- 功能简介：
  - 在连接了 ADB 的设备/模拟器上，打开当前显示页面对应的 Android Activity 类。
  - IDE 菜单路径：Navigate → Current Activity；默认快捷键：Windows/Linux 为 Ctrl+F10，macOS 为 ⌘F10。
- 源码地址：https://github.com/BoD/OpenCurrentActivityIntelliJPlugin

## 参考插件 2：FindActivityFragment
- 市场地址：https://plugins.jetbrains.com/plugin/25112-findactivityfragment
- 功能简介：
  - 当 ADB 可用时，定位 App 当前页面涉及的 Activity 以及内部 Fragment，适配 Android 7–14。
  - 使用方式：Code → FindFindActivity 菜单；Windows 快捷键 Alt+0（以插件说明为准）。
- 源码地址：https://github.com/yndongyong/FindActivityFragmentPlugin

## 使用建议
- 可对比两者对 ADB 命令、Activity/Fragment 解析策略与 IDE 集成方式（Action、菜单、快捷键、图标）等实现差异。
- 如在本仓库新增 Action 或 Service，请同步更新 `plugin.xml` 与相应单元测试。

## 命令行工具：快速查找当前页面 Fragment
- 命令：`acf`
- 功能：
  - 自动通过 ADB 获取当前前台 Activity 以及其包含的 Fragment 列表；
  - 在终端输出可点击的本地源码文件路径；支持交互选择或一键打开文件。
- 依赖：
  - 已配置并可执行的 `adb`（或使用 `--adb` 指定路径）；
  - 连接且已授权的真机/模拟器；
  - 将源码所在目录作为检索根目录（默认当前目录，可通过 `--search-roots` 指定，逗号分隔）。
- 用法示例：
  - `acf`
  - `acf --device emulator-5554`
  - `acf --search-roots /path/to/app,./external`
  - `acf --adb /Users/me/Library/Android/sdk/platform-tools/adb`
  - `acf --open`（交互选择并打开）
  - `acf --open-all`（打开所有定位到的文件）

## 测试
- 运行：`python3 -m unittest tools/tests/test_parsers.py`

## 安装与自动补全（推荐）
- 使用 pipx 可编辑安装（开发期快速迭代）：
  - 在仓库根目录执行：`pipx install --editable .`
  - 包名：`android-current-fragments`
- 安装后命令：`acf`
- 启用命令自动补全（argcomplete）：
  - Bash：
    - `register-python-argcomplete acf >> ~/.bashrc && source ~/.bashrc`
  - Zsh：
    - 在 `~/.zshrc` 添加：`eval "$(register-python-argcomplete acf)"`，然后 `source ~/.zshrc`
- 运行示例：
  - `acf --open --search-roots /path/to/app`
