# 保存搜索字段状态功能说明

## 功能描述

应用现在能够自动保存上一次搜索使用的所有字段，并在重新启动时恢复这些字段。

## 实现细节

### 修改的文件

#### 1. src/config_manager.py
- 扩展默认配置结构，添加 `last_search_state` 字段
- 新增 `save_last_search_state(folder_path, keywords, extensions, exclude_keywords)` 方法
  - 保存最后一次搜索的字段状态
  - 包含文件夹路径、关键字、后缀名过滤、排除关键字

- 新增 `get_last_search_state()` 方法
  - 获取上次保存的搜索状态
  - 如果未曾保存，返回空状态

#### 2. src/app.py
- 修改 `load_config()` 方法
  - 从 `last_search_state` 中恢复所有字段值
  - 字段被填充到相应的输入框和下拉框

- 修改 `save_config()` 方法
  - 每次保存时，调用 `save_last_search_state()` 记录当前字段值
  - 确保每次搜索/关闭窗口时都会更新状态

## 工作流程

```
启动应用
    ↓
load_config() 被调用
    ↓
从 last_search_state 恢复字段
    ↓
用户进行搜索或关闭窗口
    ↓
save_config() 被调用
    ↓
save_last_search_state() 保存当前字段
    ↓
配置文件更新
    ↓
下次启动时重复上述过程
```

## 配置文件格式

```json
{
  "search_history": [...],
  "folder_history": [...],
  "extension_history": [...],
  "exclude_history": [...],
  "exclude_keywords": "",
  "last_search_state": {
    "folder_path": "C:\\Users\\Documents",
    "keywords": "python",
    "extensions": ".py",
    "exclude_keywords": "__pycache__"
  }
}
```

## 使用体验

1. 用户打开应用，输入搜索条件并执行搜索
2. 用户关闭应用
3. 下次打开应用时，所有之前使用的字段会自动填充
4. 用户可以直接按 Enter 或点击搜索按钮继续搜索
5. 如果需要修改，可以直接编辑字段值

## 测试

已通过以下测试：
- ✓ 保存搜索状态
- ✓ 恢复搜索状态
- ✓ 默认值处理（新用户或首次使用）
- ✓ 配置文件持久化

## 注意事项

- 空字段值（""）也会被保存，以区分"未设置"和"设置为空"
- 历史记录（search_history、folder_history 等）仍然分开保存
- last_search_state 只保存最后一次的状态，不是历史记录
