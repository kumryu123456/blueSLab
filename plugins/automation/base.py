"""
자동화 엔진 플러그인 기본 클래스

이 모듈은 자동화 엔진 플러그인의 기본 인터페이스를 정의합니다.
모든 자동화 엔진 플러그인(Playwright, PyAutoGUI 등)은 이 클래스를 상속받아야 합니다.
"""
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from core.plugin_system import Plugin, PluginInfo, PluginType


@dataclass
class ActionResult:
    """액션 실행 결과"""
    success: bool = False  # 성공 여부
    error: Optional[str] = None  # 오류 메시지
    data: Dict[str, Any] = field(default_factory=dict)  # 결과 데이터
    
    @property
    def failed(self) -> bool:
        """실패 여부"""
        return not self.success
    
    def to_dict(self) -> Dict[str, Any]:
        """사전으로 변환"""
        result = {
            'success': self.success
        }
        
        if self.error:
            result['error'] = self.error
            
        result.update(self.data)
        
        return result


class AutomationPlugin(Plugin):
    """자동화 엔진 플러그인 기본 클래스"""
    
    def __init__(self):
        """플러그인 초기화"""
        self._initialized = False
        self._config = {}
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        self._config = config or {}
        self._initialized = True
        return True
    
    @abstractmethod
    def cleanup(self) -> None:
        """플러그인 정리"""
        self._initialized = False
    
    @abstractmethod
    def execute_action(self, action_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """액션 실행
        
        Args:
            action_type: 액션 유형
            params: 액션 파라미터
            
        Returns:
            액션 결과
        """
        if not self._initialized:
            return ActionResult(False, "Plugin not initialized").to_dict()
        
        # 각 플러그인에서 구현해야 함
        raise NotImplementedError
    
    def _check_initialized(self) -> None:
        """초기화 상태 확인"""
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")
    
    def _get_param(self, params: Dict[str, Any], key: str, default: Any = None) -> Any:
        """파라미터 가져오기
        
        Args:
            params: 파라미터 사전
            key: 키
            default: 기본값
            
        Returns:
            파라미터 값
        """
        return params.get(key, default) if params else default
    
    def _create_result(self, success: bool, error: str = None, **kwargs) -> Dict[str, Any]:
        """결과 생성
        
        Args:
            success: 성공 여부
            error: 오류 메시지
            **kwargs: 추가 데이터
            
        Returns:
            결과 사전
        """
        return ActionResult(success, error, kwargs).to_dict()