"""
플러그인 시스템 모듈

이 모듈은 자동화 시스템의 플러그인 아키텍처를 구현합니다.
다양한 자동화 엔진, 인식 시스템, 인터럽션 처리 등을 플러그인으로 관리합니다.
"""
import importlib
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Type, Union

# 플러그인 타입 정의
class PluginType(Enum):
    """플러그인 타입 정의"""
    AUTOMATION = auto()  # 자동화 엔진 (Playwright, PyAutoGUI 등)
    RECOGNITION = auto()  # 인식 시스템 (선택자, 템플릿 매칭, OCR 등)
    INTERRUPTION = auto()  # 인터럽션 처리 (광고, 팝업, 쿠키 등)
    WORKFLOW = auto()  # 작업 흐름 처리
    UI = auto()  # 사용자 인터페이스 관련

@dataclass
class PluginInfo:
    """플러그인 정보 클래스"""
    id: str  # 플러그인 고유 식별자
    name: str  # 플러그인 이름
    description: str  # 플러그인 설명
    version: str  # 플러그인 버전
    plugin_type: PluginType  # 플러그인 타입
    priority: int = 0  # 플러그인 우선순위 (높을수록 먼저 시도)
    dependencies: List[str] = None  # 플러그인 의존성

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class Plugin(ABC):
    """플러그인 기본 인터페이스"""
    
    @classmethod
    @abstractmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """플러그인 정리"""
        pass
    
    def match_criteria(self, criteria: Dict[str, Any]) -> bool:
        """지정된 기준에 플러그인이 일치하는지 확인
        
        Args:
            criteria: 일치 기준
            
        Returns:
            일치 여부
        """
        info = self.get_plugin_info()
        for key, value in criteria.items():
            if key == 'id' and info.id != value:
                return False
            elif key == 'name' and info.name != value:
                return False
            elif key == 'plugin_type' and info.plugin_type != value:
                return False
            elif key == 'min_priority' and info.priority < value:
                return False
        return True


class PluginManager:
    """플러그인 관리자 클래스"""
    
    def __init__(self, plugin_dirs: List[str] = None, logger=None):
        """플러그인 관리자 초기화
        
        Args:
            plugin_dirs: 플러그인 디렉토리 목록
            logger: 로거 객체
        """
        self.logger = logger or logging.getLogger(__name__)
        self.plugin_dirs = plugin_dirs or []
        self.plugins: Dict[PluginType, List[Plugin]] = {
            plugin_type: [] for plugin_type in PluginType
        }
        self.plugin_instances: Dict[str, Plugin] = {}  # id -> instance
        self.initialized_plugins: Set[str] = set()
    
    def discover_plugins(self) -> None:
        """플러그인 디렉토리에서 플러그인 발견"""
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                self.logger.warning(f"플러그인 디렉토리가 존재하지 않습니다: {plugin_dir}")
                continue
                
            sys.path.insert(0, os.path.abspath(os.path.dirname(plugin_dir)))
            
            for root, _, files in os.walk(plugin_dir):
                for file in files:
                    if file.endswith('_plugin.py'):
                        module_path = os.path.join(root, file)
                        relative_path = os.path.relpath(module_path, os.path.dirname(plugin_dir))
                        module_name = os.path.splitext(relative_path)[0].replace(os.path.sep, '.')
                        
                        try:
                            module = importlib.import_module(module_name)
                            for name, obj in inspect.getmembers(module):
                                if (inspect.isclass(obj) and issubclass(obj, Plugin) and
                                    obj is not Plugin and not inspect.isabstract(obj)):
                                    self._register_plugin_class(obj)
                        except Exception as e:
                            self.logger.error(f"플러그인 로드 중 오류: {module_name} - {str(e)}")
    
    def _register_plugin_class(self, plugin_class: Type[Plugin]) -> None:
        """플러그인 클래스 등록
        
        Args:
            plugin_class: 플러그인 클래스
        """
        try:
            info = plugin_class.get_plugin_info()
            if info.id in self.plugin_instances:
                self.logger.warning(f"중복된 플러그인 ID: {info.id}")
                return
                
            plugin_instance = plugin_class()
            self.plugin_instances[info.id] = plugin_instance
            self.plugins[info.plugin_type].append(plugin_instance)
            
            # 우선순위에 따라 정렬
            self.plugins[info.plugin_type].sort(
                key=lambda p: p.get_plugin_info().priority, 
                reverse=True
            )
            
            self.logger.info(f"플러그인 등록: {info.name} (ID: {info.id}, 타입: {info.plugin_type.name})")
        except Exception as e:
            self.logger.error(f"플러그인 등록 중 오류: {plugin_class.__name__} - {str(e)}")
    
    def register_plugin(self, plugin: Plugin) -> None:
        """플러그인 인스턴스 등록
        
        Args:
            plugin: 플러그인 인스턴스
        """
        info = plugin.get_plugin_info()
        if info.id in self.plugin_instances:
            self.logger.warning(f"중복된 플러그인 ID: {info.id}")
            return
            
        self.plugin_instances[info.id] = plugin
        self.plugins[info.plugin_type].append(plugin)
        
        # 우선순위에 따라 정렬
        self.plugins[info.plugin_type].sort(
            key=lambda p: p.get_plugin_info().priority, 
            reverse=True
        )
        
        self.logger.info(f"플러그인 등록: {info.name} (ID: {info.id}, 타입: {info.plugin_type.name})")
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """ID로 플러그인 가져오기
        
        Args:
            plugin_id: 플러그인 ID
            
        Returns:
            플러그인 인스턴스 또는 None
        """
        return self.plugin_instances.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """유형별 모든 플러그인 가져오기
        
        Args:
            plugin_type: 플러그인 타입
            
        Returns:
            플러그인 인스턴스 목록
        """
        return self.plugins.get(plugin_type, [])
    
    def find_plugins(self, plugin_type: PluginType, criteria: Dict[str, Any]) -> List[Plugin]:
        """기준에 맞는 플러그인 찾기
        
        Args:
            plugin_type: 플러그인 타입
            criteria: 일치 기준
            
        Returns:
            플러그인 인스턴스 목록
        """
        result = []
        for plugin in self.plugins.get(plugin_type, []):
            if plugin.match_criteria(criteria):
                result.append(plugin)
        return result
    
    def initialize_plugin(self, plugin_id: str, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            plugin_id: 플러그인 ID
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        if plugin_id in self.initialized_plugins:
            return True
            
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            self.logger.error(f"플러그인을 찾을 수 없음: {plugin_id}")
            return False
            
        # 의존성 확인 및 초기화
        info = plugin.get_plugin_info()
        for dep_id in info.dependencies:
            if not self.initialize_plugin(dep_id, config):
                self.logger.error(f"의존성 초기화 실패: {dep_id} (필요: {plugin_id})")
                return False
                
        try:
            success = plugin.initialize(config)
            if success:
                self.initialized_plugins.add(plugin_id)
                self.logger.info(f"플러그인 초기화 성공: {plugin_id}")
            else:
                self.logger.error(f"플러그인 초기화 실패: {plugin_id}")
            return success
        except Exception as e:
            self.logger.error(f"플러그인 초기화 중 오류: {plugin_id} - {str(e)}")
            return False
    
    def cleanup_plugin(self, plugin_id: str) -> None:
        """플러그인 정리
        
        Args:
            plugin_id: 플러그인 ID
        """
        if plugin_id not in self.initialized_plugins:
            return
            
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return
            
        try:
            plugin.cleanup()
            self.initialized_plugins.remove(plugin_id)
            self.logger.info(f"플러그인 정리 완료: {plugin_id}")
        except Exception as e:
            self.logger.error(f"플러그인 정리 중 오류: {plugin_id} - {str(e)}")
    
    def cleanup_all(self) -> None:
        """모든 초기화된 플러그인 정리"""
        for plugin_id in list(self.initialized_plugins):
            self.cleanup_plugin(plugin_id)


class PluginError(Exception):
    """플러그인 관련 오류"""
    pass