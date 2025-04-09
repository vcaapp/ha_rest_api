"""Lovelace API implementation for Home Assistant REST API."""
import logging
import os
import json
from typing import Dict, Any

import voluptuous as vol
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.components.lovelace import dashboard
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.components.frontend import async_remove_panel, async_register_built_in_panel
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from ..const import (
    DOMAIN,
    SERVICE_GET_LOVELACE_CONFIG,
    SERVICE_SAVE_LOVELACE_CONFIG,
    SERVICE_UPSERT_LOVELACE_VIEW,
    SERVICE_DELETE_LOVELACE_VIEW,
    SERVICE_GET_LOVELACE_SECTION,
    SERVICE_SET_LOVELACE_SECTION,
    SERVICE_RESTART_HASS,
    SERVICE_GET_LOVELACE_LIST,
    LOVELACE_API_PATH,
    LOVELACE_SECTION_API_PATH,
    LOVELACE_SECTION_DELETE_API_PATH,
    LOVELACE_LIST_API_PATH,
    RESTART_HASS_API_PATH,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_CONFIG_SCHEMA = vol.Schema({
    vol.Optional("dashboard_id", default="lovelace"): cv.string,
})

SERVICE_SAVE_CONFIG_SCHEMA = vol.Schema({
    vol.Optional("dashboard_id", default="lovelace"): cv.string,
    vol.Required("config"): dict,
})

SERVICE_SECTION_ADD_SCHEMA = vol.Schema({
    vol.Optional("dashboard_id", default="lovelace"): cv.string,
    vol.Required("title"): cv.string,
    vol.Required("path"): cv.string,
})

SERVICE_SECTION_DELETE_SCHEMA = vol.Schema({
    vol.Optional("dashboard_id", default="lovelace"): cv.string,
    vol.Required("path"): cv.string,
})

class LovelaceAPI:
    """Class to handle Lovelace API functionality."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Lovelace API."""
        self.hass = hass
        
    async def handle_get_config_service(self, call: ServiceCall) -> None:
        """Handle the get_config service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        config = await self.get_lovelace_config(dashboard_id)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_lovelace_config"] = config
        
    async def handle_save_config_service(self, call: ServiceCall) -> None:
        """Handle the save_config service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        config = call.data.get("config", {})
        
        success = await self.save_lovelace_config(dashboard_id, config)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_lovelace_save_result"] = success
        
        # 如果保存成功，重新加载Lovelace配置
        if success:
            await self.reload_lovelace_resources(dashboard_id)
        
    async def handle_upsert_view_service(self, call: ServiceCall) -> None:
        """Handle the upsert_view service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        title = call.data.get("title")
        path = call.data.get("path")
        
        success = await self.upsert_lovelace_view(dashboard_id, title, path)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_view_upsert_result"] = success
        
        # 如果保存成功，重新加载Lovelace配置
        if success:
            await self.reload_lovelace_resources(dashboard_id)
        
    async def handle_delete_view_service(self, call: ServiceCall) -> None:
        """Handle the delete_view service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        path = call.data.get("path")
        
        success = await self.delete_lovelace_view(dashboard_id, path)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_view_delete_result"] = success
        
        # 如果保存成功，重新加载Lovelace配置
        if success:
            await self.reload_lovelace_resources(dashboard_id)
        
    async def get_lovelace_config(self, dashboard_id: str) -> Dict:
        """Get Lovelace configuration."""
        storage_file = self.hass.config.path(f".storage/lovelace")
        _LOGGER.debug("Reading Lovelace config from: %s", storage_file)
        
        if os.path.exists(storage_file):
            try:
                with open(storage_file, "r", encoding="utf-8") as file:
                    stored_data = json.load(file)
                    _LOGGER.debug("Raw stored data: %s", json.dumps(stored_data, indent=2))
                    config = stored_data.get("data", {}).get("config", {})
                    _LOGGER.debug("Extracted config: %s", json.dumps(config, indent=2))
                    return config
            except Exception as e:
                _LOGGER.error("Error reading Lovelace config from storage: %s", str(e))
        else:
            _LOGGER.error("Lovelace config file not found: %s", storage_file)
        
        return {"success": False, "error": "Could not retrieve Lovelace configuration"}

    async def save_lovelace_config(self, dashboard_id: str, config: Dict) -> bool:
        """Save Lovelace configuration."""
        storage_file = self.hass.config.path(f".storage/lovelace")
        
        try:
            # 读取现有文件以保留元数据
            existing_data = {
                "version": 1,
                "minor_version": 1,
                "key": "lovelace",
                "data": {
                    "config": {}
                }
            }
            
            if os.path.exists(storage_file):
                with open(storage_file, "r", encoding="utf-8") as file:
                    existing_data = json.load(file)
            
            # 更新配置部分
            existing_data["data"]["config"] = config
            
            # 写回文件
            with open(storage_file, "w", encoding="utf-8") as file:
                json.dump(existing_data, file, indent=2)
            
            return True
        except Exception as e:
            _LOGGER.error("Error saving Lovelace config to storage: %s", str(e))
            return False
    
    async def upsert_lovelace_view(self, dashboard_id: str, title: str, path: str) -> bool:
        """Add a new view or update an existing view in Lovelace configuration."""
        try:
            # 获取当前配置
            current_config = await self.get_lovelace_config(dashboard_id)
            if not isinstance(current_config, dict):
                _LOGGER.error("Invalid Lovelace configuration")
                return False
            
            # 确保config有views字段
            if "views" not in current_config:
                current_config["views"] = []
            
            # 查找是否已存在相同path的视图
            found = False
            for i, view in enumerate(current_config["views"]):
                if view.get("path") == path:
                    # 更新已存在的视图
                    _LOGGER.info(f"Updating existing view with path '{path}'")
                    current_config["views"][i]["title"] = title
                    found = True
                    break
            
            # 如果没找到，添加新视图
            if not found:
                _LOGGER.info(f"Adding new view with path '{path}'")
                new_view = {
                    "type": "sections",
                    "max_columns": 4,
                    "title": title,
                    "path": path,
                    "sections": [
                        {
                            "type": "grid",
                            "cards": [
                                {
                                    "type": "heading",
                                    "heading": "新建部件"
                                }
                            ]
                        }
                    ]
                }
                current_config["views"].append(new_view)
            
            # 保存更新后的配置
            success = await self.save_lovelace_config(dashboard_id, current_config)
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error upserting Lovelace view: {str(e)}")
            return False
    
    async def delete_lovelace_view(self, dashboard_id: str, path: str) -> bool:
        """Delete a view from Lovelace configuration by its path."""
        try:
            # 获取当前配置
            current_config = await self.get_lovelace_config(dashboard_id)
            if not isinstance(current_config, dict):
                _LOGGER.error("Invalid Lovelace configuration")
                return False
            
            # 确保config有views字段
            if "views" not in current_config:
                _LOGGER.warning("No views found in the configuration")
                return False
            
            # 寻找匹配path的视图
            original_count = len(current_config["views"])
            current_config["views"] = [view for view in current_config["views"] if view.get("path") != path]
            
            # 检查是否有删除操作
            if len(current_config["views"]) < original_count:
                _LOGGER.info(f"Deleted view with path '{path}'")
                # 保存更新后的配置
                success = await self.save_lovelace_config(dashboard_id, current_config)
                return success
            else:
                _LOGGER.warning(f"No view found with path '{path}'")
                return False
            
        except Exception as e:
            _LOGGER.error(f"Error deleting Lovelace view: {str(e)}")
            return False
    
    async def reload_lovelace_resources(self, dashboard_id: str = "lovelace") -> None:
        """Reload Lovelace resources to make changes take effect."""
        try:
            _LOGGER.info(f"Reloading Lovelace dashboard '{dashboard_id}'")
            
            # 使用 services.call 重新加载
            await self.hass.services.async_call("lovelace", "reload", {"force": True})
            
            # 发布自定义事件，用于前端监听和刷新
            self.hass.bus.async_fire("lovelace_updated", {"dashboard_id": dashboard_id})
            
            _LOGGER.info(f"Lovelace dashboard '{dashboard_id}' reload request sent")
            
        except Exception as e:
            _LOGGER.error(f"Error reloading Lovelace resources: {str(e)}")
    
    async def _call_websocket_api_raw(self, data: Dict) -> None:
        """Call WebSocket API with raw data."""
        try:
            # 获取所有活跃的WebSocket连接
            connections = self.hass.data.get("websocket_api", {}).get("connections", [])
            
            # 遍历连接发送消息
            for connection in connections:
                if hasattr(connection, "send_message"):
                    try:
                        await connection.send_message(data)
                    except Exception as e:
                        _LOGGER.error(f"Error sending message to connection: {str(e)}")
                        
        except Exception as e:
            _LOGGER.error(f"Error sending WebSocket message: {str(e)}")
            
    async def _call_websocket_api(self, command: str, data: Dict = None) -> Any:
        """Call WebSocket API and return result."""
        result = None
        connection = MockWebSocketConnection(self.hass)
        
        # Merge command and data
        ws_data = {"type": command}
        if data:
            ws_data.update(data)
            
        # Process message through WebSocket API
        try:
            await self.hass.components.websocket_api.async_register_command(connection)
            await connection.async_handle_message(ws_data)
            result = connection.last_result
        except Exception as e:
            _LOGGER.error("Error calling WebSocket API: %s", str(e))
            
        return result

    async def get_lovelace_section(self, dashboard_id: str, path: str) -> Dict:
        """Get a specific view from Lovelace configuration."""
        try:
            # 获取当前配置
            current_config = await self.get_lovelace_config(dashboard_id)
            if not isinstance(current_config, dict):
                _LOGGER.error("Invalid Lovelace configuration")
                return {"success": False, "error": "Invalid configuration"}
            
            # 查找指定path的视图
            for view in current_config.get("views", []):
                if view.get("path") == path:
                    return view
            
            return {"success": False, "error": f"View with path '{path}' not found"}
            
        except Exception as e:
            _LOGGER.error(f"Error getting Lovelace section: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def set_lovelace_section(self, dashboard_id: str, path: str, view_config: Dict) -> bool:
        """Set content for a specific view in Lovelace configuration."""
        try:
            # 获取当前配置
            current_config = await self.get_lovelace_config(dashboard_id)
            if not isinstance(current_config, dict):
                _LOGGER.error("Invalid Lovelace configuration")
                return False
            
            # 确保config有views字段
            if "views" not in current_config:
                current_config["views"] = []
            
            # 查找并更新指定path的视图
            found = False
            for i, view in enumerate(current_config["views"]):
                if view.get("path") == path:
                    # 保持原有path
                    view_config["path"] = path
                    current_config["views"][i] = view_config
                    found = True
                    break
            
            if not found:
                _LOGGER.warning(f"View with path '{path}' not found, creating new")
                view_config["path"] = path
                current_config["views"].append(view_config)
            
            # 保存更新后的配置
            success = await self.save_lovelace_config(dashboard_id, current_config)
            
            # 如果保存成功，重新加载Lovelace配置
            if success:
                await self.reload_lovelace_resources(dashboard_id)
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"Error setting Lovelace section: {str(e)}")
            return False
    
    async def handle_get_section_service(self, call: ServiceCall) -> None:
        """Handle the get_section service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        path = call.data.get("path")
        
        view = await self.get_lovelace_section(dashboard_id, path)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_section_get_result"] = view
        
    async def handle_set_section_service(self, call: ServiceCall) -> None:
        """Handle the set_section service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        path = call.data.get("path")
        view_config = call.data.get("view_config")
        
        success = await self.set_lovelace_section(dashboard_id, path, view_config)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_section_set_result"] = success
        
        # 如果保存成功，重新加载Lovelace配置
        if success:
            await self.reload_lovelace_resources(dashboard_id)

    async def get_lovelace_list(self, dashboard_id: str) -> list:
        """Get a simplified list of Lovelace views with just title and path."""
        try:
            # Get current config
            current_config = await self.get_lovelace_config(dashboard_id)
            if not isinstance(current_config, dict):
                _LOGGER.error("Invalid Lovelace configuration")
                return []
            
            # Extract title and path from each view
            view_list = []
            for view in current_config.get("views", []):
                if "path" in view and "title" in view:
                    view_list.append({
                        "title": view["title"],
                        "path": view["path"]
                    })
            
            return view_list
            
        except Exception as e:
            _LOGGER.error(f"Error getting Lovelace view list: {str(e)}")
            return []
    
    async def handle_get_list_service(self, call: ServiceCall) -> None:
        """Handle the get_list service call."""
        dashboard_id = call.data.get("dashboard_id", "lovelace")
        
        view_list = await self.get_lovelace_list(dashboard_id)
        
        # Store the result as service data
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN]["last_list_get_result"] = view_list


class LovelaceAPIView(HomeAssistantView):
    """View to handle Lovelace API requests."""

    url = LOVELACE_API_PATH
    name = "api:ha_rest_api:lovelace"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        """Initialize the Lovelace API view."""
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for Lovelace configuration."""
        try:
            dashboard_id = request.query.get("dashboard_id", "lovelace")
            config = await self.lovelace_api.get_lovelace_config(dashboard_id)
            return self.json(config)
        except Exception as e:
            _LOGGER.error("Error getting Lovelace config: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to update Lovelace configuration."""
        try:
            data = await request.json()
            dashboard_id = data.get("dashboard_id", "lovelace")
            config = data.get("config")
            
            if not config:
                return self.json(
                    {"success": False, "error": "No config provided"}, 
                    status_code=400
                )
            
            success = await self.lovelace_api.save_lovelace_config(dashboard_id, config)
            
            # 如果保存成功，重新加载Lovelace配置
            if success:
                await self.lovelace_api.reload_lovelace_resources(dashboard_id)
                
            return self.json({"success": success})
        except Exception as e:
            _LOGGER.error("Error updating Lovelace config: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class LovelateSectionAPIView(HomeAssistantView):
    """View to handle Lovelace section API requests."""

    url = LOVELACE_SECTION_API_PATH
    name = "api:ha_rest_api:lovelace_section"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        """Initialize the Lovelace section API view."""
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for a specific Lovelace view."""
        try:
            dashboard_id = request.query.get("dashboard_id", "lovelace")
            path = request.query.get("path")
            
            if not path:
                return self.json(
                    {"success": False, "error": "Path is required"}, 
                    status_code=400
                )
            
            view = await self.lovelace_api.get_lovelace_section(dashboard_id, path)
            return self.json(view)
        except Exception as e:
            _LOGGER.error("Error getting Lovelace section: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to set a Lovelace view's content."""
        try:
            data = await request.json()
            dashboard_id = data.get("dashboard_id", "lovelace")
            path = data.get("path")
            view_config = data.get("view_config")
            
            if not path or not view_config:
                return self.json(
                    {"success": False, "error": "Path and view_config are required"}, 
                    status_code=400
                )
            
            success = await self.lovelace_api.set_lovelace_section(dashboard_id, path, view_config)
            
            # 如果保存成功，重新加载Lovelace配置
            if success:
                await self.lovelace_api.reload_lovelace_resources(dashboard_id)
                
            return self.json({"success": success})
        except Exception as e:
            _LOGGER.error("Error setting Lovelace section: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class LovelateSectionUpsertAPIView(HomeAssistantView):
    """View to handle Lovelace section upsert API requests."""

    url = LOVELACE_SECTION_API_PATH + "/upsert"
    name = "api:ha_rest_api:lovelace_section_upsert"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        """Initialize the Lovelace section upsert API view."""
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to add/update a Lovelace view."""
        try:
            data = await request.json()
            dashboard_id = data.get("dashboard_id", "lovelace")
            title = data.get("title")
            path = data.get("path")
            
            if not title or not path:
                return self.json(
                    {"success": False, "error": "Title and path are required"}, 
                    status_code=400
                )
            
            success = await self.lovelace_api.upsert_lovelace_view(dashboard_id, title, path)
            
            # 如果保存成功，重新加载Lovelace配置
            if success:
                await self.lovelace_api.reload_lovelace_resources(dashboard_id)
                
            return self.json({"success": success})
        except Exception as e:
            _LOGGER.error("Error upserting Lovelace view: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class LovelaceSectionDeleteAPIView(HomeAssistantView):
    """View to handle Lovelace section delete API requests."""

    url = LOVELACE_SECTION_DELETE_API_PATH
    name = "api:ha_rest_api:lovelace_section_delete"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        """Initialize the Lovelace section delete API view."""
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to delete a Lovelace view."""
        try:
            data = await request.json()
            dashboard_id = data.get("dashboard_id", "lovelace")
            path = data.get("path")
            
            if not path:
                return self.json(
                    {"success": False, "error": "Path is required"}, 
                    status_code=400
                )
            
            success = await self.lovelace_api.delete_lovelace_view(dashboard_id, path)
            
            # 如果保存成功，重新加载Lovelace配置
            if success:
                await self.lovelace_api.reload_lovelace_resources(dashboard_id)
                
            return self.json({"success": success})
        except Exception as e:
            _LOGGER.error("Error deleting Lovelace view: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class RestartHassAPIView(HomeAssistantView):
    """View to handle Home Assistant restart requests."""

    url = RESTART_HASS_API_PATH
    name = "api:ha_rest_api:restart"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def post(self, request: web.Request) -> web.Response:
        """Handle POST request to restart Home Assistant."""
        try:
            await self.hass.services.async_call("homeassistant", "restart")
            return self.json({"success": True})
        except Exception as e:
            _LOGGER.error("Error restarting Home Assistant: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class LovelaceListAPIView(HomeAssistantView):
    """View to handle Lovelace list API requests."""

    url = LOVELACE_LIST_API_PATH
    name = "api:ha_rest_api:lovelace_list"

    def __init__(self, lovelace_api: LovelaceAPI) -> None:
        """Initialize the Lovelace list API view."""
        self.lovelace_api = lovelace_api
        self.hass = lovelace_api.hass

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for Lovelace views list."""
        try:
            dashboard_id = request.query.get("dashboard_id", "lovelace")
            view_list = await self.lovelace_api.get_lovelace_list(dashboard_id)
            return self.json(view_list)
        except Exception as e:
            _LOGGER.error("Error getting Lovelace views list: %s", str(e))
            return self.json({"success": False, "error": str(e)}, status_code=500)


class MockWebSocketConnection:
    """Mock WebSocket connection to call internal APIs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the connection."""
        self.hass = hass
        self.last_result = None

    async def async_handle_message(self, msg: Dict) -> None:
        """Handle a message."""
        self.last_result = None
        
        # Find the right handler for this message type
        handlers = self.hass.data.get("websocket_api", {}).get("commands", {})
        handler = handlers.get(msg["type"])
        
        if handler:
            # Call the handler
            result = await handler(self.hass, self, msg)
            if result and isinstance(result, dict) and result.get("type") == TYPE_RESULT:
                self.last_result = result.get("result")
                
    async def send_message(self, msg: Dict) -> None:
        """Store the result message."""
        if msg.get("type") == TYPE_RESULT:
            self.last_result = msg.get("result")

    async def async_send_result(self, msg_id: int, result: Any = None) -> None:
        """Store the result."""
        self.last_result = result


async def async_setup_lovelace_api(hass: HomeAssistant) -> None:
    """Set up the Lovelace API."""
    lovelace_api = LovelaceAPI(hass)
    
    # Register the API endpoints
    hass.http.register_view(LovelaceAPIView(lovelace_api))
    hass.http.register_view(LovelateSectionAPIView(lovelace_api))
    hass.http.register_view(LovelateSectionUpsertAPIView(lovelace_api))
    hass.http.register_view(LovelaceSectionDeleteAPIView(lovelace_api))
    hass.http.register_view(RestartHassAPIView(lovelace_api))
    hass.http.register_view(LovelaceListAPIView(lovelace_api))
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LOVELACE_CONFIG,
        lovelace_api.handle_get_config_service,
        schema=SERVICE_GET_CONFIG_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_LOVELACE_CONFIG,
        lovelace_api.handle_save_config_service,
        schema=SERVICE_SAVE_CONFIG_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPSERT_LOVELACE_VIEW,
        lovelace_api.handle_upsert_view_service,
        schema=SERVICE_SECTION_ADD_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_LOVELACE_VIEW,
        lovelace_api.handle_delete_view_service,
        schema=SERVICE_SECTION_DELETE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_HASS,
        lambda call: hass.services.async_call("homeassistant", "restart"),
        schema=vol.Schema({})
    )
    
    # Register services for get/set section
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LOVELACE_SECTION,
        lovelace_api.handle_get_section_service,
        schema=SERVICE_SECTION_DELETE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LOVELACE_SECTION,
        lovelace_api.handle_set_section_service,
        schema=vol.Schema({
            vol.Optional("dashboard_id", default="lovelace"): cv.string,
            vol.Required("path"): cv.string,
            vol.Required("view_config"): dict,
        })
    )
    
    # Register service for getting view list
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LOVELACE_LIST,
        lovelace_api.handle_get_list_service,
        schema=SERVICE_GET_CONFIG_SCHEMA
    )
    
    _LOGGER.info("Lovelace API endpoints registered")
