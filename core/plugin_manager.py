 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 플러그인 관리자
"""

import os
import sys
import logging
import importlib
import inspect
from typing import Dict, List, Type, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PluginInterface:
    """모든 플러그인의 기본 인터페이스"""
    
    plugin_type = "base"  # 플러그인 타입 (automation, recognition, interruption 등)
    plugin_name = "base"  # 플러그인 이름
    plugin_version = "0.1.0"  # 플러그인 버전
    plugin_description = "Base plugin interface"  # 플러그인 설명
    
    def __init__(self):
        self.enabled = True
        self.config = {}
        logger.debug(f"플러그인 초기화: {self.plugin_name} ({self.plugin_type})")
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        return True
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        return True
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        self.config.update(config)
        return True
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return []
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """플러그인 액션 실행"""
        raise NotImplementedError("플러그인 액션 실행 기능이 구현되지 않았습니다.")
    
    def is_enabled(self) -> bool:
        """플러그인 활성화 상태"""
        return self.enabled
    
    def enable(self) -> bool:
        """플러그인 활성화"""
        self.enabled = True
        return True
    
    def disable(self) -> bool:
        """플러그인 비활성화"""
        self.enabled = False
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """플러그인 상태 정보"""
        return {
            "type": self.plugin_type,
            "name": self.plugin_name,
            "version": self.plugin_version,
            "description": self.plugin_description,
            "enabled": self.enabled,
            "capabilities": self.get_capabilities()
        }
    
    def __str__(self) -> str:
        return f"{self.plugin_name} ({self.plugin_type}) v{self.plugin_version}"


class PluginManager:
    """플러그인 관리자 - 플러그인 로드, 관리 및 실행을 담당"""
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, Dict[str, PluginInterface]] = {}  # {plugin_type: {plugin_name: plugin_instance}}
        self.plugin_classes: Dict[str, Type[PluginInterface]] = {}  # {plugin_name: plugin_class}
        self.dependencies = {}  # {plugin_name: [dependency_names]}
        
        # 플러그인 디렉토리가 없으면 생성
        if not self.plugin_dir.exists():
            logger.info(f"플러그인 디렉토리 생성: {self.plugin_dir}")
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """플러그인 디렉토리 탐색하여 플러그인 찾기"""
        discovered_plugins = []
        
        for plugin_type_dir in self.plugin_dir.iterdir():
            if not plugin_type_dir.is_dir() or plugin_type_dir.name.startswith('__'):
                continue
            
            plugin_type = plugin_type_dir.name
            logger.debug(f"플러그인 타입 디렉토리 검색: {plugin_type}")
            
            for plugin_file in plugin_type_dir.glob('*_plugin.py'):
                plugin_name = plugin_file.stem
                module_path = f"plugins.{plugin_type}.{plugin_name}"
                
                logger.debug(f"플러그인 발견: {module_path}")
                discovered_plugins.append(module_path)
        
        return discovered_plugins
    
    def load_plugin(self, module_path: str) -> Optional[Type[PluginInterface]]:
        """지정된 모듈 경로에서 플러그인 로드"""
        try:
            # 모듈 로드
            module = importlib.import_module(module_path)
            
            # 모듈에서 PluginInterface 상속 클래스 찾기
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, PluginInterface) 
                        and obj is not PluginInterface):
                    logger.info(f"플러그인 클래스 로드됨: {name} from {module_path}")
                    self.plugin_classes[obj.plugin_name] = obj
                    return obj
            
            logger.warning(f"플러그인 클래스를 찾을 수 없음: {module_path}")
            return None
            
        except Exception as e:
            logger.error(f"플러그인 로드 중 오류: {module_path} - {str(e)}")
            return None
    
    def load_all_plugins(self) -> List[str]:
        """모든 플러그인 로드"""
        loaded_plugins = []
        
        # 플러그인 발견
        discovered_plugins = self.discover_plugins()
        
        # 각 플러그인 로드
        for module_path in discovered_plugins:
            plugin_class = self.load_plugin(module_path)
            if plugin_class:
                loaded_plugins.append(plugin_class.plugin_name)
        
        logger.info(f"로드된 플러그인: {loaded_plugins}")
        return loaded_plugins
    
    def initialize_plugin(self, plugin_name: str) -> bool:
        """플러그인 초기화 및 등록"""
        if plugin_name not in self.plugin_classes:
            logger.error(f"초기화 실패: 플러그인 클래스를 찾을 수 없음 - {plugin_name}")
            return False
        
        try:
            # 플러그인 인스턴스 생성
            plugin_class = self.plugin_classes[plugin_name]
            plugin = plugin_class()
            
            # 플러그인 초기화
            if not plugin.initialize():
                logger.error(f"플러그인 초기화 실패: {plugin_name}")
                return False
            
            # 플러그인 등록
            plugin_type = plugin.plugin_type
            if plugin_type not in self.plugins:
                self.plugins[plugin_type] = {}
            
            self.plugins[plugin_type][plugin_name] = plugin
            logger.info(f"플러그인 초기화 완료: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"플러그인 초기화 중 오류: {plugin_name} - {str(e)}")
            return False
    
    def initialize_all_plugins(self) -> Dict[str, bool]:
        """모든 플러그인 초기화"""
        results = {}
        
        for plugin_name in self.plugin_classes:
            results[plugin_name] = self.initialize_plugin(plugin_name)
        
        return results
    
    def get_plugin(self, plugin_type: str, plugin_name: str) -> Optional[PluginInterface]:
        """지정된 타입과 이름의 플러그인 인스턴스 반환"""
        if plugin_type not in self.plugins or plugin_name not in self.plugins[plugin_type]:
            return None
        
        return self.plugins[plugin_type][plugin_name]
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginInterface]:
        """지정된 타입의 모든 플러그인 인스턴스 반환"""
        if plugin_type not in self.plugins:
            return {}
        
        return self.plugins[plugin_type]
    
    def get_all_plugins(self) -> Dict[str, Dict[str, PluginInterface]]:
        """모든 플러그인 인스턴스 반환"""
        return self.plugins
    
    def execute_plugin(self, plugin_type: str, plugin_name: str, 
                      action: str, params: Dict[str, Any]) -> Any:
        """플러그인 액션 실행"""
        plugin = self.get_plugin(plugin_type, plugin_name)
        if not plugin:
            logger.error(f"플러그인을 찾을 수 없음: {plugin_type}.{plugin_name}")
            return None
        
        if not plugin.is_enabled():
            logger.warning(f"플러그인이 비활성화됨: {plugin_type}.{plugin_name}")
            return None
        
        try:
            logger.debug(f"플러그인 실행: {plugin_type}.{plugin_name}.{action}({params})")
            return plugin.execute(action, params)
        except Exception as e:
            logger.error(f"플러그인 실행 중 오류: {plugin_type}.{plugin_name}.{action} - {str(e)}")
            return None
    
    def shutdown_plugin(self, plugin_type: str, plugin_name: str) -> bool:
        """플러그인 종료"""
        plugin = self.get_plugin(plugin_type, plugin_name)
        if not plugin:
            logger.error(f"종료할 플러그인을 찾을 수 없음: {plugin_type}.{plugin_name}")
            return False
        
        try:
            result = plugin.shutdown()
            if result:
                # 플러그인 목록에서 제거
                del self.plugins[plugin_type][plugin_name]
                logger.info(f"플러그인 종료됨: {plugin_type}.{plugin_name}")
            return result
        except Exception as e:
            logger.error(f"플러그인 종료 중 오류: {plugin_type}.{plugin_name} - {str(e)}")
            return False
    
    def shutdown_all_plugins(self) -> Dict[str, bool]:
        """모든 플러그인 종료"""
        results = {}
        
        for plugin_type, plugins in self.plugins.items():
            for plugin_name in list(plugins.keys()):  # list()로 복사해서 순회 중 삭제 가능하게
                results[f"{plugin_type}.{plugin_name}"] = self.shutdown_plugin(plugin_type, plugin_name)
        
        return results