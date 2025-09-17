# 开发指南

## 项目架构

### 模块化设计

ACF 工具采用模块化设计，每个模块都有明确的职责：

- **`adb_client.py`**: ADB 命令执行和设备信息获取
- **`parsers.py`**: Android dumpsys 输出解析
- **`file_finder.py`**: 源码文件搜索和映射
- **`file_opener.py`**: 文件打开和编辑器集成
- **`fragment_finder.py`**: Fragment 查找策略协调
- **`constants.py`**: 常量和配置定义

### 核心流程

1. **设备验证**: 检查 ADB 连接和设备状态
2. **Activity 解析**: 从 dumpsys 获取当前 Activity
3. **Fragment 查找**: 使用多策略查找 Fragment
4. **文件映射**: 搜索本地源码文件
5. **结果展示**: 显示并可选打开文件

## 开发环境设置

### 依赖安装

```bash
# 开发依赖
pip install -e ".[dev]"

# 或手动安装
pip install pytest argcomplete
```

### 测试运行

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tools/tests/test_parsers.py -v

# 运行并显示覆盖率
pytest --cov=tools
```

## 代码规范

### 类型注解

所有公共函数都应包含类型注解：

```python
def find_fragments(adb: str, device: Optional[str], component: str) -> List[str]:
    """Find fragments for a specific activity component."""
    pass
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def parse_activity_component(dumpsys_text: str, prefer_top: bool = True) -> str:
    """Parse current activity component from dumpsys activities output.
    
    Args:
        dumpsys_text: Raw dumpsys activities output
        prefer_top: Whether to prefer topResumedActivity over mResumedActivity
        
    Returns:
        Activity component string in format "package/activity"
        
    Raises:
        RuntimeError: If no activity is found in dumpsys output
    """
    pass
```

### 错误处理

使用适当的异常类型和错误消息：

```python
if not devices:
    raise RuntimeError("未检测到设备，请连接设备并授权 ADB。")
```

## 测试指南

### 测试数据

测试数据统一放在 `test_data.py` 中，避免硬编码：

```python
from ..test_data import ANDROID11_SAMPLE, FRAGMENTS_SAMPLE
```

### 测试命名

使用描述性的测试方法名：

```python
def test_parse_activity_android_11(self):
    """Test parsing Android 11 activity format."""
    pass

def test_filter_system_fragments(self):
    """Test filtering out system fragments."""
    pass
```

### 测试覆盖

确保关键功能有测试覆盖：

- 解析器函数
- 文件查找逻辑
- 错误处理路径
- 边界条件

## 性能优化

### ADB 命令优化

- 优先使用最精确的 dumpsys 命令
- 实现多策略回退机制
- 避免不必要的全量 dumpsys

### 文件搜索优化

- 跳过构建目录和 VCS 目录
- 使用早期退出策略
- 缓存搜索结果

## 调试技巧

### 启用调试输出

在关键函数中添加调试信息：

```python
if debug:
    print(f"[DEBUG] Found {len(fragments)} fragments: {fragments}")
```

### 测试真实设备

使用真实设备测试不同 Android 版本：

```bash
# 测试不同设备
acf --device emulator-5554
acf --device emulator-5556
```

## 发布流程

### 版本管理

使用语义化版本号：

- `MAJOR`: 不兼容的 API 更改
- `MINOR`: 向后兼容的功能添加
- `PATCH`: 向后兼容的错误修复

### 发布检查

发布前确保：

- [ ] 所有测试通过
- [ ] 文档更新
- [ ] 版本号更新
- [ ] CHANGELOG 更新
