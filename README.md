# Home Assistant REST API

这是一个Home Assistant自定义集成，提供多种REST API接口来访问和修改Home Assistant的各种配置和数据。目前主要实现了Lovelace面板配置的完整CRUD操作，未来可以扩展更多功能。

## 功能

### Lovelace API
- 获取Lovelace面板配置
- 保存完整的Lovelace面板配置
- 添加或更新单个Lovelace视图
- 删除单个Lovelace视图
- 获取单个Lovelace视图内容
- 设置单个Lovelace视图内容
- 提供Home Assistant服务接口和REST API接口

### 系统管理 API
- 重启 Home Assistant

## 安装

1. 将`ha_rest_api`文件夹复制到Home Assistant配置目录下的`custom_components`文件夹中
2. 在Home Assistant的`configuration.yaml`文件中添加以下配置：
   ```yaml
   ha_rest_api:
   ```
3. 重新启动Home Assistant
4. 集成将自动加载

## REST API 接口

### 获取Lovelace配置

```
GET /api/ha_rest_api/lovelace?dashboard_id=lovelace
```

**参数**：
- `dashboard_id`：（可选）要获取的面板ID，默认为"lovelace"

**响应示例**：
```json
{
  "title": "我的家",
  "views": [
    {
      "path": "default_view",
      "title": "主页",
      "cards": [...]
    }
  ]
}
```

### 保存Lovelace配置

```
POST /api/ha_rest_api/lovelace
```

**请求体**：
```json
{
  "dashboard_id": "lovelace",
  "config": {
    "title": "我的家",
    "views": [...]
  }
}
```

**参数**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `config`：（必需）新的Lovelace配置

**响应示例**：
```json
{
  "success": true
}
```

### 添加或更新Lovelace视图

```
POST /api/ha_rest_api/lovelace_section/upsert
```

**请求体**：
```json
{
  "dashboard_id": "lovelace",
  "title": "新视图",
  "path": "new_view"
}
```

**参数**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `title`：（必需）视图的标题
- `path`：（必需）视图的路径（唯一标识符）

**说明**：
- 如果指定`path`的视图不存在，将创建一个新的视图
- 如果指定`path`的视图已存在，将只更新视图的标题
- 新创建的视图将包含基本的结构和一个标题部件

**响应示例**：
```json
{
  "success": true
}
```

### 删除Lovelace视图

```
POST /api/ha_rest_api/lovelace_section/delete
```

**请求体**：
```json
{
  "dashboard_id": "lovelace",
  "path": "view_to_delete"
}
```

**参数**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `path`：（必需）要删除的视图的路径（唯一标识符）

**响应示例**：
```json
{
  "success": true
}
```

### 获取单个Lovelace视图内容

```
GET /api/ha_rest_api/lovelace_section?dashboard_id=lovelace&path=your_view_path
```

**参数**：
- `dashboard_id`：（可选）要获取的面板ID，默认为"lovelace"
- `path`：（必需）要获取的视图的路径（唯一标识符）

**响应示例**：
```json
{
  "path": "your_view_path",
  "title": "视图标题",
  "cards": [
    {
      "type": "markdown",
      "title": "标题",
      "content": "内容"
    }
  ]
}
```

### 设置单个Lovelace视图内容

```
POST /api/ha_rest_api/lovelace_section
```

**请求体**：
```json
{
  "dashboard_id": "lovelace",
  "path": "your_view_path",
  "view_config": {
    "title": "视图标题",
    "cards": [
      {
        "type": "markdown",
        "title": "标题",
        "content": "内容"
      }
    ]
  }
}
```

**参数**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `path`：（必需）要设置的视图的路径（唯一标识符）
- `view_config`：（必需）视图的完整配置

**响应示例**：
```json
{
  "success": true
}
```

### 重启 Home Assistant

```
POST /api/ha_rest_api/restart
```

**响应示例**：
```json
{
  "success": true
}
```

## Home Assistant服务

### ha_rest_api.get_lovelace_config

获取Lovelace面板配置。

**服务数据**：
- `dashboard_id`：（可选）要获取的面板ID，默认为"lovelace"

结果将存储在Home Assistant的数据存储中，可以通过开发者工具 > 状态 > `ha_rest_api` 查看。

### ha_rest_api.save_lovelace_config

保存Lovelace面板配置。

**服务数据**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `config`：（必需）新的Lovelace配置

### ha_rest_api.upsert_lovelace_view

添加新视图或更新现有视图。

**服务数据**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `title`：（必需）视图的标题
- `path`：（必需）视图的路径（唯一标识符）

### ha_rest_api.delete_lovelace_view

删除指定的视图。

**服务数据**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `path`：（必需）要删除的视图的路径（唯一标识符）

### ha_rest_api.restart_hass

重启 Home Assistant 实例。

**服务数据**：
无需参数

### ha_rest_api.get_lovelace_section

获取单个Lovelace视图的内容。

**服务数据**：
- `dashboard_id`：（可选）要获取的面板ID，默认为"lovelace"
- `path`：（必需）要获取的视图的路径（唯一标识符）

### ha_rest_api.set_lovelace_section

设置单个Lovelace视图的内容。

**服务数据**：
- `dashboard_id`：（可选）要更新的面板ID，默认为"lovelace"
- `path`：（必需）要设置的视图的路径（唯一标识符）
- `view_config`：（必需）视图的完整配置

## 使用示例

### 使用curl

#### 获取Lovelace配置
```bash
curl -X GET "http://your-home-assistant:8123/api/ha_rest_api/lovelace?dashboard_id=lovelace" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN"
```

#### 保存Lovelace配置
```bash
curl -X POST "http://your-home-assistant:8123/api/ha_rest_api/lovelace" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dashboard_id": "lovelace", "config": {"title": "我的家", "views": [...]}}'
```

#### 添加/更新视图
```bash
curl -X POST "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section/upsert" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "新视图", "path": "new_view"}'
```

#### 删除视图
```bash
curl -X POST "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section/delete" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "view_to_delete"}'
```

#### 获取单个视图内容
```bash
curl -X GET "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section?path=your_view_path" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN"
```

#### 设置单个视图内容
```bash
curl -X POST "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "your_view_path",
    "view_config": {
      "title": "视图标题",
      "cards": [
        {
          "type": "markdown",
          "title": "标题",
          "content": "内容"
        }
      ]
    }
  }'
```

#### 重启 Home Assistant
```bash
curl -X POST "http://your-home-assistant:8123/api/ha_rest_api/restart" \
  -H "Authorization: Bearer YOUR_LONG_LIVED_ACCESS_TOKEN"
```

### 使用Python

#### 获取Lovelace配置
```python
import requests

url = "http://your-home-assistant:8123/api/ha_rest_api/lovelace"
headers = {
    "Authorization": "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN"
}

response = requests.get(url, headers=headers)
config = response.json()
print(config)
```

#### 保存Lovelace配置
```python
import requests

url = "http://your-home-assistant:8123/api/ha_rest_api/lovelace"
headers = {
    "Authorization": "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "dashboard_id": "lovelace",
    "config": {
        "title": "我的家",
        "views": [...]
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

#### 获取单个视图内容
```python
import requests

url = "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section"
headers = {
    "Authorization": "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN"
}
params = {
    "path": "your_view_path"
}

response = requests.get(url, headers=headers, params=params)
view_config = response.json()
print(view_config)
```

#### 设置单个视图内容
```python
import requests

url = "http://your-home-assistant:8123/api/ha_rest_api/lovelace_section"
headers = {
    "Authorization": "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "path": "your_view_path",
    "view_config": {
        "title": "视图标题",
        "cards": [
            {
                "type": "markdown",
                "title": "标题",
                "content": "内容"
            }
        ]
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

#### 重启 Home Assistant
```python
import requests

url = "http://your-home-assistant:8123/api/ha_rest_api/restart"
headers = {
    "Authorization": "Bearer YOUR_LONG_LIVED_ACCESS_TOKEN",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers)
print(response.json())
```

## 扩展开发

本插件设计为可扩展的架构，可以轻松添加更多API端点：

1. 在`api`目录下创建新的模块文件
2. 实现相应的API类和视图
3. 在`__init__.py`中导入并调用新API的setup函数
4. 在`const.py`中添加相关常量
5. 在`services.yaml`中添加新服务定义

## 注意事项

- 此集成需要访问Home Assistant的内部API，可能会随着Home Assistant的更新而需要调整
- 确保使用长期访问令牌进行API认证
- 修改配置时请小心，错误的配置可能会导致UI显示问题
- 删除视图后不可恢复，请提前备份重要配置
