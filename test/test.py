import asyncio
import json
import aiohttp

class HAWebsocket:
    def __init__(self, host, access_token):
        self.host = host
        self.access_token = access_token
        self.websocket = None
        self.id = 1

    async def connect(self):
        url = f"ws://{self.host}/api/websocket"
        self.websocket = await aiohttp.ClientSession().ws_connect(url)
        
        # 等待auth_required消息
        auth_message = await self.websocket.receive_json()
        if auth_message["type"] != "auth_required":
            raise Exception("Unexpected message")

        # 发送认证
        await self.websocket.send_json({
            "type": "auth",
            "access_token": self.access_token
        })

        # 验证认证结果
        auth_result = await self.websocket.receive_json()
        if auth_result["type"] != "auth_ok":
            raise Exception("Authentication failed")

    async def call_service(self, domain, service, service_data=None):
        msg_id = self.id
        self.id += 1

        await self.websocket.send_json({
            "id": msg_id,
            "type": "call_service",
            "domain": domain,
            "service": service,
            "service_data": service_data or {}
        })

        response = await self.websocket.receive_json()
        return response

    async def close(self):
        if self.websocket:
            await self.websocket.close()

    async def get_lovelace_config(self):
        msg_id = self.id
        self.id += 1
        
        await self.websocket.send_json({
            "id": msg_id,
            "type": "lovelace/config",
            "url_path": "lovelace"  # 使用默认 dashboard
        })
        
        response = await self.websocket.receive_json()
        if not response.get("success"):
            print(f"获取配置失败: {response.get('error', {}).get('message')}")
        return response

    async def save_lovelace_config(self, config):
        msg_id = self.id
        self.id += 1
        
        await self.websocket.send_json({
            "id": msg_id,
            "type": "lovelace/config/save",
            "url_path": "lovelace",  # 使用默认 dashboard
            "config": config
        })
        
        return await self.websocket.receive_json()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class HARestAPI:
    def __init__(self, host, access_token):
        self.host = host
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.base_url = f"http://{host}"

    async def get_lovelace_config(self, dashboard_id="lovelace"):
        url = f"{self.base_url}/api/ha_rest_api/lovelace"
        params = {"dashboard_id": dashboard_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                return await response.json()

    async def save_lovelace_config(self, config, dashboard_id="lovelace"):
        url = f"{self.base_url}/api/ha_rest_api/lovelace"
        data = {
            "dashboard_id": dashboard_id,
            "config": config
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                return await response.json()
                
    async def upsert_lovelace_view(self, title, path, dashboard_id="lovelace"):
        """调用添加或更新 Lovelace 视图的 API"""
        url = f"{self.base_url}/api/ha_rest_api/lovelace_section/upsert"
        data = {
            "dashboard_id": dashboard_id,
            "title": title,
            "path": path
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                return await response.json()
    
    async def delete_lovelace_view(self, path, dashboard_id="lovelace"):
        """调用删除 Lovelace 视图的 API"""
        url = f"{self.base_url}/api/ha_rest_api/lovelace_section/delete"
        data = {
            "dashboard_id": dashboard_id,
            "path": path
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                return await response.json()

    async def restart_hass(self):
        """调用重启 Home Assistant 的 API"""
        url = f"{self.base_url}/api/ha_rest_api/restart"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers) as response:
                return await response.json()

    async def get_lovelace_section(self, path, dashboard_id="lovelace"):
        """获取单个 Lovelace 视图内容"""
        url = f"{self.base_url}/api/ha_rest_api/lovelace_section"
        params = {
            "dashboard_id": dashboard_id,
            "path": path
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                return await response.json()

    async def get_lovelace_list(self, dashboard_id="lovelace"):
        """获取Lovelace视图列表（仅包含title和path）"""
        url = f"{self.base_url}/api/ha_rest_api/lovelace_list"
        params = {"dashboard_id": dashboard_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                return await response.json()

    async def set_lovelace_section(self, path, view_config, dashboard_id="lovelace"):
        """设置单个 Lovelace 视图内容"""
        url = f"{self.base_url}/api/ha_rest_api/lovelace_section"
        data = {
            "dashboard_id": dashboard_id,
            "path": path,
            "view_config": view_config
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                return await response.json()

async def test_upsert_lovelace_view():
    host = "192.168.1.91:8123"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMTE5MTFiZmQzYmQ0ZjU5YWQxMGFkZTg2ODM5ODRhZSIsImlhdCI6MTc0MzY3Mzc5NywiZXhwIjoyMDU5MDMzNzk3fQ.7LC1ZXDUqOoTI1rqQhjKm9CfujqUtfdSfkp5zHeyClU"
    
    api = HARestAPI(host, token)
    
    # 1. 先获取当前配置
    print("\n1. 获取当前 Lovelace 配置:")
    config = await api.get_lovelace_config()
    if isinstance(config, dict) and "views" in config:
        print(f"当前视图数量: {len(config['views'])}")
        for view in config["views"]:
            print(f"- {view.get('title', '无标题')} (path: {view.get('path', '无路径')})")
    else:
        print("无法获取配置或格式不正确")
    
    # 2. 添加新视图
    test_views = [
        {"title": "测试视图1", "path": "test_view1"},
        {"title": "测试视图2", "path": "test_view2"}
    ]
    
    for view in test_views:
        print(f"\n2. 创建新视图 '{view['title']}' (path: {view['path']}):")
        result = await api.upsert_lovelace_view(view["title"], view["path"])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 3. 验证结果
    print("\n3. 验证添加结果:")
    updated_config = await api.get_lovelace_config()
    if isinstance(updated_config, dict) and "views" in updated_config:
        print(f"更新后视图数量: {len(updated_config['views'])}")
        for view in updated_config["views"]:
            print(f"- {view.get('title', '无标题')} (path: {view.get('path', '无路径')})")
    else:
        print("无法获取更新后的配置")
    
    # 4. 更新已存在的视图
    print("\n4. 更新已存在的视图:")
    update_result = await api.upsert_lovelace_view("修改后的视图", "test_view1")
    print(json.dumps(update_result, indent=2, ensure_ascii=False))
    
    # 5. 最终验证
    print("\n5. 最终验证结果:")
    final_config = await api.get_lovelace_config()
    if isinstance(final_config, dict) and "views" in final_config:
        for view in final_config["views"]:
            if view.get("path") == "test_view1":
                print(f"视图 'test_view1' 的标题已更新为: {view.get('title')}")
                break

async def test_delete_lovelace_view():
    host = "192.168.1.91:8123"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMTE5MTFiZmQzYmQ0ZjU5YWQxMGFkZTg2ODM5ODRhZSIsImlhdCI6MTc0MzY3Mzc5NywiZXhwIjoyMDU5MDMzNzk3fQ.7LC1ZXDUqOoTI1rqQhjKm9CfujqUtfdSfkp5zHeyClU"
    
    api = HARestAPI(host, token)
    
    # 1. 先获取当前配置
    print("\n1. 获取当前 Lovelace 配置:")
    config = await api.get_lovelace_config()
    if isinstance(config, dict) and "views" in config:
        print(f"当前视图数量: {len(config['views'])}")
        for view in config["views"]:
            print(f"- {view.get('title', '无标题')} (path: {view.get('path', '无路径')})")
    else:
        print("无法获取配置或格式不正确")
        return
    
    # 2. 创建一个临时视图用于测试删除
    test_path = "test_to_delete"
    print(f"\n2. 创建临时视图 (path: {test_path}):")
    create_result = await api.upsert_lovelace_view("临时视图", test_path)
    print(json.dumps(create_result, indent=2, ensure_ascii=False))
    
    # 3. 验证视图已创建
    print("\n3. 验证视图已创建:")
    mid_config = await api.get_lovelace_config()
    if isinstance(mid_config, dict) and "views" in mid_config:
        found = False
        for view in mid_config["views"]:
            if view.get("path") == test_path:
                found = True
                print(f"找到临时视图: {view.get('title')} (path: {view.get('path')})")
                break
        
        if not found:
            print(f"未找到临时视图 {test_path}")
            return
    else:
        print("无法获取配置")
        return
    
    # 4. 删除视图
    print(f"\n4. 删除视图 (path: {test_path}):")
    delete_result = await api.delete_lovelace_view(test_path)
    print(json.dumps(delete_result, indent=2, ensure_ascii=False))
    
    # 5. 验证视图已删除
    print("\n5. 验证视图已删除:")
    final_config = await api.get_lovelace_config()
    if isinstance(final_config, dict) and "views" in final_config:
        found = False
        for view in final_config["views"]:
            if view.get("path") == test_path:
                found = True
                print(f"视图仍然存在: {view.get('title')} (path: {view.get('path')})")
                break
        
        if not found:
            print(f"视图 {test_path} 已成功删除")
        
        print(f"当前视图数量: {len(final_config['views'])}")
    else:
        print("无法获取配置")
    

async def test_restart_hass():
    host = "192.168.1.91:8123"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMTE5MTFiZmQzYmQ0ZjU5YWQxMGFkZTg2ODM5ODRhZSIsImlhdCI6MTc0MzY3Mzc5NywiZXhwIjoyMDU5MDMzNzk3fQ.7LC1ZXDUqOoTI1rqQhjKm9CfujqUtfdSfkp5zHeyClU"
    
    api = HARestAPI(host, token)
    
    # 测试重启
    print("\n测试重启 Home Assistant:")
    result = await api.restart_hass()
    print(json.dumps(result, indent=2, ensure_ascii=False))

async def test_lovelace_section_apis():
    host = "192.168.1.91:8123"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMTE5MTFiZmQzYmQ0ZjU5YWQxMGFkZTg2ODM5ODRhZSIsImlhdCI6MTc0MzY3Mzc5NywiZXhwIjoyMDU5MDMzNzk3fQ.7LC1ZXDUqOoTI1rqQhjKm9CfujqUtfdSfkp5zHeyClU"
    
    api = HARestAPI(host, token)
    test_path = "test_section"
    
    # 1. 创建一个测试视图
    print("\n1. 创建测试视图:")
    create_result = await api.upsert_lovelace_view("测试视图", test_path)
    print(json.dumps(create_result, indent=2, ensure_ascii=False))
    
    # 2. 获取视图内容
    print("\n2. 获取视图内容:")
    view = await api.get_lovelace_section(test_path)
    print(json.dumps(view, indent=2, ensure_ascii=False))
    
    # 3. 修改视图内容
    print("\n3. 修改视图内容:")
    new_view_config = {
        "type": "sections",
        "max_columns": 4,
        "title": "修改后的视图",
        "path": test_path,
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "markdown",
                        "title": "测试标题",
                        "content": "这是一个测试内容"
                    },
                    {
                        "type": "button",
                        "name": "测试按钮",
                        "icon": "mdi:power",
                        "tap_action": {
                            "action": "toggle"
                        }
                    }
                ]
            }
        ],
        "cards": [],
        "badges": []
    }
    update_result = await api.set_lovelace_section(test_path, new_view_config)
    print(json.dumps(update_result, indent=2, ensure_ascii=False))
    
    # 4. 验证修改结果
    print("\n4. 验证修改结果:")
    updated_view = await api.get_lovelace_section(test_path)
    print(json.dumps(updated_view, indent=2, ensure_ascii=False))
    
    # 5. 清理：删除测试视图
    print("\n5. 清理测试视图:")
    delete_result = await api.delete_lovelace_view(test_path)
    print(json.dumps(delete_result, indent=2, ensure_ascii=False))

async def test_get_lovelace_list():
    host = "192.168.1.91:8123"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlMTE5MTFiZmQzYmQ0ZjU5YWQxMGFkZTg2ODM5ODRhZSIsImlhdCI6MTc0MzY3Mzc5NywiZXhwIjoyMDU5MDMzNzk3fQ.7LC1ZXDUqOoTI1rqQhjKm9CfujqUtfdSfkp5zHeyClU"
    
    api = HARestAPI(host, token)
    
    # 1. 获取当前视图列表
    print("\n1. 获取当前Lovelace视图列表:")
    view_list = await api.get_lovelace_list()
    print(json.dumps(view_list, indent=2, ensure_ascii=False))
    
    # 2. 创建一个新视图
    test_title = "测试视图列表API"
    test_path = "test_list_api"
    print(f"\n2. 创建新视图 '{test_title}' (path: {test_path}):")
    create_result = await api.upsert_lovelace_view(test_title, test_path)
    print(json.dumps(create_result, indent=2, ensure_ascii=False))
    
    # 3. 再次获取视图列表，验证新视图已添加
    print("\n3. 验证新视图已添加到列表:")
    updated_list = await api.get_lovelace_list()
    print(json.dumps(updated_list, indent=2, ensure_ascii=False))
    
    # 4. 对比前后视图数量变化
    print(f"\n4. 视图数量变化: {len(view_list)} -> {len(updated_list)}")
    
    # 5. 清理：删除测试视图
    print("\n5. 清理测试视图:")
    delete_result = await api.delete_lovelace_view(test_path)
    print(json.dumps(delete_result, indent=2, ensure_ascii=False))
    
    # 6. 最终验证
    print("\n6. 最终验证:")
    final_list = await api.get_lovelace_list()
    print(json.dumps(final_list, indent=2, ensure_ascii=False))
    print(f"最终视图数量: {len(final_list)}")

async def main():
    # await test_upsert_lovelace_view()
    # await test_delete_lovelace_view()
    # await test_lovelace_section_apis()
    # await test_restart_hass()
    await test_get_lovelace_list()

if __name__ == "__main__":
    asyncio.run(main())
