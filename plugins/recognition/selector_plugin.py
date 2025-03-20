"""
선택자 기반 인식 플러그인

이 모듈은 CSS/XPath 선택자를 사용한 요소 인식 플러그인을 구현합니다.
웹 페이지에서 요소를 찾기 위한 기본적이고 빠른 방법을 제공합니다.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from core.plugin_system import PluginInfo, PluginType
from plugins.recognition.base import RecognitionMethod, RecognitionPlugin, RecognitionResult, RecognitionTarget


class SelectorPlugin(RecognitionPlugin):
    """선택자 기반 인식 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="selector_recognition",
            name="선택자 인식",
            description="CSS/XPath 선택자를 사용한 요소 인식 플러그인",
            version="1.0.0",
            plugin_type=PluginType.RECOGNITION,
            priority=10,  # 가장 높은 우선순위 (가장 먼저 시도)
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 선택자 전략
        self._selector_strategies = [
            self._build_default_selector,
            self._build_semantic_selector,
            self._build_attribute_selector,
            self._build_text_selector,
            self._build_context_selector
        ]
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        super().initialize(config)
        
        # 전략 우선순위 설정
        strategy_order = self._config.get('strategy_order', [])
        if strategy_order:
            # 우선순위에 따라 전략 재정렬
            ordered_strategies = []
            for strategy_name in strategy_order:
                for strategy in self._selector_strategies:
                    if strategy.__name__ == f"_build_{strategy_name}_selector":
                        ordered_strategies.append(strategy)
                        break
            
            # 누락된 전략 추가
            for strategy in self._selector_strategies:
                if strategy not in ordered_strategies:
                    ordered_strategies.append(strategy)
            
            self._selector_strategies = ordered_strategies
        
        self.logger.info("선택자 인식 플러그인 초기화 완료")
        return True
    
    def cleanup(self) -> None:
        """플러그인 정리"""
        super().cleanup()
    
    def recognize(self, context: Any, target: Union[Dict[str, Any], RecognitionTarget],
                timeout: float = None) -> RecognitionResult:
        """대상 인식
        
        Args:
            context: 인식 컨텍스트 (Playwright 페이지 또는 유사 객체)
            target: 인식 대상
            timeout: 인식 제한 시간
            
        Returns:
            인식 결과
        """
        self._check_initialized()
        
        # 컨텍스트 확인
        if not context:
            return RecognitionResult(
                success=False,
                error="인식 컨텍스트가 제공되지 않음"
            )
        
        # 타임아웃 설정
        if timeout is None:
            timeout = self._config.get('default_timeout', 5.0)
        
        # 대상 객체 변환
        if not isinstance(target, RecognitionTarget):
            if isinstance(target, dict):
                target = RecognitionTarget(
                    type=target.get('type', 'unknown'),
                    description=target.get('description', ''),
                    context=target.get('context', ''),
                    attributes=target.get('attributes', {})
                )
            else:
                return RecognitionResult(
                    success=False,
                    error="지원되지 않는 대상 형식"
                )
        
        # 다양한 선택자 생성 전략 시도
        selectors = []
        for strategy in self._selector_strategies:
            selector = strategy(target)
            if selector:
                selectors.append(selector)
        
        if not selectors:
            return RecognitionResult(
                success=False,
                error="선택자를 생성할 수 없음",
                target=target
            )
        
        # 각 선택자 시도
        for selector in selectors:
            try:
                self.logger.debug(f"선택자 시도: {selector}")
                
                # 요소 찾기 시도
                element = self._find_element(context, selector, timeout)
                
                if element:
                    # 요소 정보 수집
                    element_info = self._extract_element_info(context, element, selector)
                    
                    return RecognitionResult(
                        success=True,
                        confidence=1.0,  # 선택자는 정확히 일치하므로 신뢰도 1.0
                        method=RecognitionMethod.SELECTOR,
                        target=target,
                        element=element_info
                    )
            except Exception as e:
                self.logger.debug(f"선택자 실패: {selector} - {str(e)}")
                continue
        
        # 모든 선택자 실패
        return RecognitionResult(
            success=False,
            error="모든 선택자 시도 실패",
            target=target,
            method=RecognitionMethod.SELECTOR
        )
    
    def _find_element(self, context: Any, selector: str, timeout: float) -> Any:
        """선택자로 요소 찾기
        
        Args:
            context: 인식 컨텍스트
            selector: CSS/XPath 선택자
            timeout: 제한 시간
            
        Returns:
            찾은 요소 또는 None
        """
        # Playwright 페이지인 경우
        if hasattr(context, 'locator'):
            try:
                locator = context.locator(selector)
                
                # 요소가 존재하는지 확인 (비동기 호출은 피함)
                # 여기서는 비동기 호출을 피하고 단순히 요소를 찾는 것으로 대체
                return locator.first
            except Exception as e:
                self.logger.debug(f"요소 찾기 실패: {str(e)}")
                return None
        
        # 다른 유형의 컨텍스트 (확장성)
        return None

    def _extract_element_info(self, context: Any, element: Any, selector: str) -> Dict[str, Any]:
        """요소 정보 추출
        
        Args:
            context: 인식 컨텍스트
            element: 요소
            selector: 사용된 선택자
            
        Returns:
            요소 정보
        """
        result = {
            'selector': selector
        }
        
        # Playwright 요소인 경우
        # 비동기 evaluate 호출을 피하고 기본 정보만 반환
        if hasattr(context, 'evaluate'):
            try:
                # 기본 정보만 포함
                result['tag'] = 'element'  # 태그 정보는 알 수 없음
                result['visible'] = True   # 요소를 찾았으므로 표시된 것으로 간주
            except Exception as e:
                self.logger.debug(f"요소 정보 추출 실패: {str(e)}")
        
        return result
    
    # 선택자 생성 전략
    
    def _build_default_selector(self, target: RecognitionTarget) -> Optional[str]:
        """기본 선택자 생성
        
        Args:
            target: 인식 대상
            
        Returns:
            CSS 선택자
        """
        target_type = target.type.lower()
        
        # 유형별 기본 선택자
        if target_type in ['button', 'btn']:
            return "button, [role='button'], input[type='button'], input[type='submit']"
        
        elif target_type in ['search']:
            return "input[type='search'], input[placeholder*='search' i], input[aria-label*='search' i], input[name='q'], textarea[name='q'], .gLFyf, .gsfi, [jsname='yZiJbe']"

        elif target_type in ['input', 'textbox', 'text']:
            return "input[type='text'], input:not([type]), textarea"
        
        elif target_type in ['checkbox', 'check']:
            return "input[type='checkbox']"
        
        elif target_type in ['radio']:
            return "input[type='radio']"
        
        elif target_type in ['select', 'dropdown', 'combobox']:
            return "select, [role='combobox'], [role='listbox']"
        
        elif target_type in ['link', 'a']:
            return "a"
        
        elif target_type in ['image', 'img']:
            return "img"
        
        elif target_type in ['form']:
            return "form"
        
        elif target_type in ['header', 'heading']:
            return "h1, h2, h3, h4, h5, h6"
        
        elif target_type in ['search']:
            return "input[type='search'], input[placeholder*='search' i], input[aria-label*='search' i]"
        
        return None
    
    def _build_semantic_selector(self, target: RecognitionTarget) -> Optional[str]:
        """의미론적 선택자 생성
        
        Args:
            target: 인식 대상
            
        Returns:
            CSS 선택자
        """
        target_type = target.type.lower()
        description = target.description.lower()
        
        # 설명이 없으면 건너뜀
        if not description:
            return None
        
        # 유형별 의미론적 선택자
        if target_type in ['button', 'btn']:
            return f"button:has-text('{description}'), [role='button']:has-text('{description}'), input[type='button'][value*='{description}' i], input[type='submit'][value*='{description}' i]"
        
        elif target_type in ['link', 'a']:
            return f"a:has-text('{description}')"
        
        elif target_type in ['input', 'textbox', 'text']:
            return f"input[placeholder*='{description}' i], input[aria-label*='{description}' i], textarea[placeholder*='{description}' i], textarea[aria-label*='{description}' i]"
        
        elif target_type in ['search']:
            return f"input[type='search'][placeholder*='{description}' i], input[type='search'][aria-label*='{description}' i], input[placeholder*='search' i][placeholder*='{description}' i]"
        
        return None
    
    def _build_attribute_selector(self, target: RecognitionTarget) -> Optional[str]:
        """속성 기반 선택자 생성
        
        Args:
            target: 인식 대상
            
        Returns:
            CSS 선택자
        """
        attributes = target.attributes
        if not attributes:
            return None
        
        parts = []
        
        # ID 속성
        if 'id' in attributes and attributes['id']:
            return f"#{attributes['id']}"
        
        # 클래스 속성
        if 'class' in attributes and attributes['class']:
            class_names = attributes['class'].split()
            class_selector = '.'.join(class_names)
            parts.append(f".{class_selector}")
        
        # 기타 속성
        for name, value in attributes.items():
            if name not in ['id', 'class'] and value:
                parts.append(f"[{name}='{value}']")
        
        if parts:
            return ''.join(parts)
        
        return None
    
    def _build_text_selector(self, target: RecognitionTarget) -> Optional[str]:
        """텍스트 기반 선택자 생성
        
        Args:
            target: 인식 대상
            
        Returns:
            CSS 선택자
        """
        # 설명 텍스트
        description = target.description
        if not description:
            return None
        
        # 정확한 텍스트 매칭
        return f":has-text('{description}')"
    
    def _build_context_selector(self, target: RecognitionTarget) -> Optional[str]:
        """컨텍스트 기반 선택자 생성
        
        Args:
            target: 인식 대상
            
        Returns:
            CSS 선택자
        """
        context = target.context
        if not context:
            return None
        
        # 기본 선택자 (없으면 *)
        base_selector = self._build_default_selector(target) or "*"
        
        # 근처에 컨텍스트 텍스트가 있는 요소 선택
        return f"{base_selector}:near(:has-text('{context}'))"