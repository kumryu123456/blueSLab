"""
인식 시스템 플러그인 기본 클래스

이 모듈은 인식 시스템 플러그인의 기본 인터페이스를 정의합니다.
모든 인식 시스템 플러그인(선택자, 템플릿 매칭, OCR 등)은 이 클래스를 상속받아야 합니다.
"""
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from core.plugin_system import Plugin, PluginInfo, PluginType


class RecognitionMethod(Enum):
    """인식 방법"""
    SELECTOR = "selector"  # CSS/XPath 선택자
    ARIA = "aria"  # ARIA/접근성 속성
    TEMPLATE = "template"  # 템플릿 매칭
    OCR = "ocr"  # 광학 문자 인식
    OBJECT = "object"  # 객체 인식


@dataclass
class RecognitionTarget:
    """인식 대상"""
    type: str  # 대상 유형 (button, input, text, image 등)
    description: str = ""  # 대상 설명
    context: str = ""  # 컨텍스트 정보
    attributes: Dict[str, str] = field(default_factory=dict)  # 속성 정보
    
    def to_dict(self) -> Dict[str, Any]:
        """사전으로 변환"""
        return {
            'type': self.type,
            'description': self.description,
            'context': self.context,
            'attributes': self.attributes
        }


@dataclass
class RecognitionResult:
    """인식 결과"""
    success: bool = False  # 성공 여부
    confidence: float = 0.0  # 신뢰도 (0.0 ~ 1.0)
    method: Optional[RecognitionMethod] = None  # 사용된 인식 방법
    target: Optional[RecognitionTarget] = None  # 인식 대상
    element: Optional[Dict[str, Any]] = None  # 인식된 요소 정보
    location: Optional[Tuple[int, int, int, int]] = None  # 위치 (x, y, width, height)
    error: Optional[str] = None  # 오류 메시지
    
    def to_dict(self) -> Dict[str, Any]:
        """사전으로 변환"""
        result = {
            'success': self.success,
            'confidence': self.confidence
        }
        
        if self.method:
            result['method'] = self.method.value
            
        if self.target:
            result['target'] = self.target.to_dict()
            
        if self.element:
            result['element'] = self.element
            
        if self.location:
            result['location'] = {
                'x': self.location[0],
                'y': self.location[1],
                'width': self.location[2],
                'height': self.location[3]
            }
            
        if self.error:
            result['error'] = self.error
            
        return result


class RecognitionPlugin(Plugin):
    """인식 시스템 플러그인 기본 클래스"""
    
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
    def recognize(self, context: Any, target: Union[Dict[str, Any], RecognitionTarget],
                timeout: float = None) -> RecognitionResult:
        """대상 인식
        
        Args:
            context: 인식 컨텍스트 (예: 페이지, 화면, 이미지 등)
            target: 인식 대상
            timeout: 인식 제한 시간
            
        Returns:
            인식 결과
        """
        pass
    
    def execute_action(self, action_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """액션 실행
        
        Args:
            action_type: 액션 유형
            params: 액션 파라미터
            
        Returns:
            액션 결과
        """
        if not self._initialized:
            return {'success': False, 'error': "Plugin not initialized"}
        
        params = params or {}
        
        if action_type == 'recognize':
            # 컨텍스트 및 대상 파라미터
            context = params.get('context')
            target_data = params.get('target')
            timeout = params.get('timeout')
            
            if not target_data:
                return {'success': False, 'error': "Recognition target not specified"}
            
            # 대상 객체 생성
            if isinstance(target_data, dict):
                target = RecognitionTarget(
                    type=target_data.get('type', 'unknown'),
                    description=target_data.get('description', ''),
                    context=target_data.get('context', ''),
                    attributes=target_data.get('attributes', {})
                )
            else:
                target = target_data
            
            # 인식 수행
            result = self.recognize(context, target, timeout)
            return result.to_dict()
        
        return {'success': False, 'error': f"Unsupported action: {action_type}"}
    
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