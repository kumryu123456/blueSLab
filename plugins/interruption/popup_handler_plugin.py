"""
인터럽션 처리 플러그인

이 모듈은 광고, 팝업, 쿠키 알림 등 방해 요소를 처리하는 플러그인을 구현합니다.
패턴 기반으로 방해 요소를 감지하고 자동으로 처리합니다.
"""
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.plugin_system import PluginInfo, PluginType, Plugin


class InterruptionType:
    """인터럽션 유형"""
    COOKIE = "cookie"
    AD = "ad"
    POPUP = "popup"
    NOTIFICATION = "notification"
    SURVEY = "survey"
    LOGIN = "login"
    PAYWALL = "paywall"
    GDPR = "gdpr"
    APP_PROMOTION = "app_promotion"
    NEWSLETTER = "newsletter"
    CUSTOM = "custom"


class InterruptionPattern:
    """인터럽션 패턴"""
    
    def __init__(self, 
                pattern_id: str,
                interruption_type: str,
                selectors: List[str] = None,
                actions: List[Dict[str, Any]] = None,
                keywords: List[str] = None,
                domains: List[str] = None,
                priority: int = 0,
                enabled: bool = True,
                description: str = "",
                metadata: Dict[str, Any] = None):
        """패턴 초기화
        
        Args:
            pattern_id: 패턴 ID
            interruption_type: 인터럽션 유형
            selectors: CSS 선택자 목록
            actions: 처리 액션 목록
            keywords: 키워드 목록
            domains: 적용 도메인 목록
            priority: 우선순위
            enabled: 활성화 여부
            description: 설명
            metadata: 추가 메타데이터
        """
        self.id = pattern_id
        self.type = interruption_type
        self.selectors = selectors or []
        self.actions = actions or []
        self.keywords = keywords or []
        self.domains = domains or []
        self.priority = priority
        self.enabled = enabled
        self.description = description
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """사전으로 변환"""
        return {
            'id': self.id,
            'type': self.type,
            'selectors': self.selectors,
            'actions': self.actions,
            'keywords': self.keywords,
            'domains': self.domains,
            'priority': self.priority,
            'enabled': self.enabled,
            'description': self.description,
            'metadata': self.metadata
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'InterruptionPattern':
        """사전에서 패턴 생성
        
        Args:
            data: 패턴 사전
            
        Returns:
            생성된 패턴
        """
        return InterruptionPattern(
            pattern_id=data.get('id', ''),
            interruption_type=data.get('type', InterruptionType.CUSTOM),
            selectors=data.get('selectors', []),
            actions=data.get('actions', []),
            keywords=data.get('keywords', []),
            domains=data.get('domains', []),
            priority=data.get('priority', 0),
            enabled=data.get('enabled', True),
            description=data.get('description', ''),
            metadata=data.get('metadata', {})
        )


class InterruptionHandlerPlugin(Plugin):
    """인터럽션 처리 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="interruption_handler",
            name="인터럽션 처리기",
            description="광고, 팝업, 쿠키 알림 등 방해 요소 처리 플러그인",
            version="1.0.0",
            plugin_type=PluginType.INTERRUPTION,
            priority=10,
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._config = {}
        
        # 패턴 관리
        self._patterns: Dict[str, InterruptionPattern] = {}
        self._patterns_by_type: Dict[str, List[InterruptionPattern]] = {}
        self._patterns_by_domain: Dict[str, List[InterruptionPattern]] = {}
        
        # 설정 파일
        self._patterns_file = None
        
        # 처리된 인터럽션
        self._handled_interruptions: Set[str] = set()
        
        # 자동화 플러그인 참조
        self._automation_plugin = None
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        self._config = config or {}
        
        # 패턴 파일 설정
        self._patterns_file = self._config.get('patterns_file')
        if not self._patterns_file:
            # 기본 패턴 파일 설정
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._patterns_file = os.path.join(base_dir, 'config', 'interruption_patterns.json')
        
        # 패턴 로드
        self._load_patterns()
        
        # 기본 패턴 추가
        self._add_default_patterns()
        
        self._initialized = True
        self.logger.info("인터럽션 처리 플러그인 초기화 완료")
        return True
    
    def cleanup(self) -> None:
        """플러그인 정리"""
        # 변경된 패턴 저장
        self._save_patterns()
        self._initialized = False
    
    def _load_patterns(self) -> None:
        """패턴 로드"""
        if os.path.exists(self._patterns_file):
            try:
                with open(self._patterns_file, 'r', encoding='utf-8') as f:
                    patterns_data = json.load(f)
                
                for pattern_data in patterns_data:
                    pattern = InterruptionPattern.from_dict(pattern_data)
                    self._add_pattern(pattern)
                
                self.logger.info(f"{len(self._patterns)} 개의 패턴 로드 완료")
            except Exception as e:
                self.logger.error(f"패턴 로드 중 오류: {str(e)}")
        else:
            self.logger.warning(f"패턴 파일이 존재하지 않음: {self._patterns_file}")
    
    def _save_patterns(self) -> None:
        """패턴 저장"""
        try:
            # 파일 디렉토리 확인
            os.makedirs(os.path.dirname(self._patterns_file), exist_ok=True)
            
            patterns_data = [pattern.to_dict() for pattern in self._patterns.values()]
            with open(self._patterns_file, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"{len(patterns_data)} 개의 패턴 저장 완료")
        except Exception as e:
            self.logger.error(f"패턴 저장 중 오류: {str(e)}")
    
    def _add_pattern(self, pattern: InterruptionPattern) -> None:
        """패턴 추가
        
        Args:
            pattern: 인터럽션 패턴
        """
        self._patterns[pattern.id] = pattern
        
        # 유형별 패턴 추가
        if pattern.type not in self._patterns_by_type:
            self._patterns_by_type[pattern.type] = []
        self._patterns_by_type[pattern.type].append(pattern)
        
        # 도메인별 패턴 추가
        for domain in pattern.domains:
            if domain not in self._patterns_by_domain:
                self._patterns_by_domain[domain] = []
            self._patterns_by_domain[domain].append(pattern)
    
    def _add_default_patterns(self) -> None:
        """기본 패턴 추가"""
        # 쿠키 알림 처리 패턴
        cookie_patterns = [
            InterruptionPattern(
                pattern_id="cookie_accept_buttons",
                interruption_type=InterruptionType.COOKIE,
                selectors=[
                    "button[aria-label*='accept' i]", 
                    "button[aria-label*='cookie' i]",
                    "button:has-text('Accept')",
                    "button:has-text('Accept All')",
                    "button:has-text('Accept Cookies')",
                    "button:has-text('동의')",
                    "button:has-text('수락')",
                    "button:has-text('확인')",
                    ".cookie-consent button",
                    "#cookie-banner button",
                    "[data-testid='cookie-policy-banner'] button",
                    ".cookie-banner__accept",
                    "#gdpr-consent-notice button",
                    "#onetrust-accept-btn-handler"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "cookie", "cookies", "consent", "쿠키", "동의", "수락", "gdpr"
                ],
                domains=[],  # 모든 도메인
                priority=10,
                description="쿠키 수락 버튼 처리"
            ),
            InterruptionPattern(
                pattern_id="cookie_close_buttons",
                interruption_type=InterruptionType.COOKIE,
                selectors=[
                    ".cookie-banner__close",
                    ".cookie-consent__close",
                    ".cookie-notice__close",
                    ".cookie-policy-close",
                    ".cookie-modal button.close"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "cookie", "cookies", "쿠키"
                ],
                priority=5,
                description="쿠키 알림 닫기 버튼 처리"
            )
        ]
        
        # 팝업 처리 패턴
        popup_patterns = [
            InterruptionPattern(
                pattern_id="popup_close_buttons",
                interruption_type=InterruptionType.POPUP,
                selectors=[
                    ".popup-close", 
                    ".modal-close", 
                    ".close-popup", 
                    ".close-modal",
                    "button.close", 
                    "button[aria-label='Close']",
                    "button[aria-label='닫기']",
                    ".modal button[class*='close']",
                    ".popup button[class*='close']",
                    "button:has-text('닫기')",
                    "button:has-text('Close')",
                    ".modal .btn-close",
                    ".modal__close",
                    ".modal-content .close",
                    ".modal-header .close"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "close", "닫기", "창닫기", "팝업", "modal", "popup"
                ],
                priority=8,
                description="팝업 닫기 버튼 처리"
            )
        ]
        
        # 광고 처리 패턴
        ad_patterns = [
            InterruptionPattern(
                pattern_id="ad_close_buttons",
                interruption_type=InterruptionType.AD,
                selectors=[
                    ".ad-close-button", 
                    ".advertisement-close", 
                    ".ad-container button[class*='close']",
                    "button[aria-label='광고 닫기']",
                    "button[aria-label='Close ad']",
                    ".sa_ad .sa_closeBtn",
                    "#ad-close-button",
                    ".interstitial-close-button",
                    ".dismiss-button",
                    ".ad-overlay-close-button"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "광고", "닫기", "ad", "advertisement", "close ad"
                ],
                priority=9,
                description="광고 닫기 버튼 처리"
            )
        ]
        
        # 알림 요청 처리 패턴
        notification_patterns = [
            InterruptionPattern(
                pattern_id="notification_deny_buttons",
                interruption_type=InterruptionType.NOTIFICATION,
                selectors=[
                    "button:has-text('나중에')",
                    "button:has-text('아니오')",
                    "button:has-text('거부')",
                    "button:has-text('Never')",
                    "button:has-text('Later')",
                    "button:has-text('No')",
                    "button:has-text('Not Now')",
                    "button:has-text('Deny')",
                    ".notification-prompt button[class*='deny']",
                    ".notification-prompt button[class*='no']",
                    ".notification-prompt button[class*='cancel']",
                    ".notification-prompt button[class*='later']"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "notification", "알림", "허용", "나중에", "거부"
                ],
                priority=7,
                description="알림 요청 거부 버튼 처리"
            )
        ]
        
        # GDPR 처리 패턴
        gdpr_patterns = [
            InterruptionPattern(
                pattern_id="gdpr_reject_buttons",
                interruption_type=InterruptionType.GDPR,
                selectors=[
                    "button:has-text('Reject All')",
                    "button:has-text('Reject')",
                    "button:has-text('Manage Preferences')",
                    "button:has-text('Reject non-essential')",
                    ".reject-button",
                    "#reject-all-button",
                    ".gdpr-banner__reject",
                    "#gdpr-reject"
                ],
                actions=[
                    {'action': 'click'}
                ],
                keywords=[
                    "gdpr", "reject", "privacy", "consent", "manage", "preferences"
                ],
                priority=9,
                description="GDPR 거부 버튼 처리"
            )
        ]
        
        # 모든 기본 패턴 추가
        for pattern in cookie_patterns + popup_patterns + ad_patterns + notification_patterns + gdpr_patterns:
            if pattern.id not in self._patterns:
                self._add_pattern(pattern)
    
    def set_automation_plugin(self, plugin: Any) -> None:
        """자동화 플러그인 설정
        
        Args:
            plugin: 자동화 플러그인
        """
        self._automation_plugin = plugin
    
    def handle_interruptions(self, context: Any, url: str = None, 
                           interruption_types: List[str] = None) -> Dict[str, Any]:
        """인터럽션 처리
        
        Args:
            context: 페이지 컨텍스트 (Playwright 페이지 등)
            url: 현재 URL
            interruption_types: 처리할 인터럽션 유형 목록
            
        Returns:
            처리 결과
        """
        self._check_initialized()
        
        if not context:
            return {'success': False, 'error': "컨텍스트가 제공되지 않음"}
        
        # 처리할 인터럽션 유형 설정
        if not interruption_types:
            interruption_types = [
                InterruptionType.COOKIE,
                InterruptionType.POPUP,
                InterruptionType.AD,
                InterruptionType.NOTIFICATION,
                InterruptionType.GDPR
            ]
        
        # 자동화 플러그인 확인
        if not self._automation_plugin and hasattr(context, 'execute_action'):
            self._automation_plugin = context
        
        if not self._automation_plugin:
            return {'success': False, 'error': "자동화 플러그인이 설정되지 않음"}
        
        # 도메인 추출
        domain = None
        if url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
            except Exception:
                self.logger.warning(f"URL에서 도메인 추출 실패: {url}")
        
        # 처리할 패턴 선택
        patterns_to_check = []
        
        # 도메인별 패턴
        if domain and domain in self._patterns_by_domain:
            patterns_to_check.extend(self._patterns_by_domain[domain])
        
        # 유형별 패턴
        for interruption_type in interruption_types:
            if interruption_type in self._patterns_by_type:
                for pattern in self._patterns_by_type[interruption_type]:
                    if pattern not in patterns_to_check:
                        patterns_to_check.append(pattern)
        
        # 우선순위에 따라 정렬
        patterns_to_check.sort(key=lambda p: p.priority, reverse=True)
        
        # 처리 결과
        handled = []
        
        # 각 패턴 확인 및 처리
        for pattern in patterns_to_check:
            if not pattern.enabled:
                continue
            
            # 이미 처리된 패턴인지 확인
            if pattern.id in self._handled_interruptions:
                continue
            
            result = self._check_and_handle_pattern(context, pattern)
            if result.get('handled', False):
                handled.append({
                    'pattern_id': pattern.id,
                    'type': pattern.type,
                    'action': result.get('action')
                })
                self._handled_interruptions.add(pattern.id)
        
        return {
            'success': True,
            'handled': handled,
            'count': len(handled)
        }
    
    def _check_and_handle_pattern(self, context: Any, pattern: InterruptionPattern) -> Dict[str, Any]:
        """패턴 확인 및 처리
        
        Args:
            context: 페이지 컨텍스트 (Playwright 페이지 등)
            pattern: 인터럽션 패턴
            
        Returns:
            처리 결과
        """
        for selector in pattern.selectors:
            try:
                # 요소 찾기
                find_result = self._automation_plugin.execute_action('find_element', {
                    'selector': selector,
                    'timeout': 1000  # 1초 타임아웃 (빠른 검색)
                })
                
                if not find_result.get('success', False) or not find_result.get('found', False):
                    continue
                
                # 요소 발견, 액션 실행
                for action_data in pattern.actions:
                    action_type = action_data.get('action', 'click')
                    action_params = action_data.copy()
                    action_params.pop('action', None)
                    
                    # 선택자 추가
                    action_params['selector'] = selector
                    
                    # 액션 실행
                    action_result = self._automation_plugin.execute_action(action_type, action_params)
                    
                    if action_result.get('success', False):
                        self.logger.info(f"인터럽션 처리 성공: {pattern.id} - {selector} ({action_type})")
                        return {
                            'handled': True,
                            'pattern_id': pattern.id,
                            'selector': selector,
                            'action': action_type
                        }
                    else:
                        self.logger.warning(f"인터럽션 액션 실패: {pattern.id} - {selector} ({action_type})")
                        
            except Exception as e:
                self.logger.error(f"인터럽션 처리 중 오류: {pattern.id} - {selector} - {str(e)}")
        
        return {'handled': False}
    
    def add_pattern(self, pattern: Union[InterruptionPattern, Dict[str, Any]]) -> bool:
        """패턴 추가
        
        Args:
            pattern: 인터럽션 패턴 또는 패턴 사전
            
        Returns:
            성공 여부
        """
        self._check_initialized()
        
        # 사전에서 패턴 생성
        if isinstance(pattern, dict):
            pattern = InterruptionPattern.from_dict(pattern)
        
        # 기존 패턴 덮어쓰기
        if pattern.id in self._patterns:
            self.logger.warning(f"기존 패턴 덮어쓰기: {pattern.id}")
        
        # 패턴 추가
        self._add_pattern(pattern)
        
        # 패턴 저장
        self._save_patterns()
        
        return True
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """패턴 제거
        
        Args:
            pattern_id: 패턴 ID
            
        Returns:
            성공 여부
        """
        self._check_initialized()
        
        if pattern_id not in self._patterns:
            self.logger.warning(f"제거할 패턴을 찾을 수 없음: {pattern_id}")
            return False
        
        pattern = self._patterns[pattern_id]
        
        # 패턴 제거
        del self._patterns[pattern_id]
        
        # 유형별 패턴 제거
        if pattern.type in self._patterns_by_type:
            self._patterns_by_type[pattern.type] = [p for p in self._patterns_by_type[pattern.type] if p.id != pattern_id]
        
        # 도메인별 패턴 제거
        for domain in pattern.domains:
            if domain in self._patterns_by_domain:
                self._patterns_by_domain[domain] = [p for p in self._patterns_by_domain[domain] if p.id != pattern_id]
        
        # 처리된 인터럽션에서 제거
        if pattern_id in self._handled_interruptions:
            self._handled_interruptions.remove(pattern_id)
        
        # 패턴 저장
        self._save_patterns()
        
        return True
    
    def get_patterns(self, interruption_type: str = None, domain: str = None) -> List[Dict[str, Any]]:
        """패턴 가져오기
        
        Args:
            interruption_type: 인터럽션 유형 (선택 사항)
            domain: 도메인 (선택 사항)
            
        Returns:
            패턴 목록
        """
        self._check_initialized()
        
        patterns = []
        
        if interruption_type and domain:
            # 유형 및 도메인별 패턴
            if interruption_type in self._patterns_by_type and domain in self._patterns_by_domain:
                type_patterns = set(self._patterns_by_type[interruption_type])
                domain_patterns = set(self._patterns_by_domain[domain])
                patterns = list(type_patterns.intersection(domain_patterns))
        elif interruption_type:
            # 유형별 패턴
            if interruption_type in self._patterns_by_type:
                patterns = self._patterns_by_type[interruption_type]
        elif domain:
            # 도메인별 패턴
            if domain in self._patterns_by_domain:
                patterns = self._patterns_by_domain[domain]
        else:
            # 모든 패턴
            patterns = list(self._patterns.values())
        
        # 사전 변환
        return [pattern.to_dict() for pattern in patterns]
    
    def clear_handled_interruptions(self) -> None:
        """처리된 인터럽션 초기화"""
        self._handled_interruptions.clear()
    
    def execute_action(self, action_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """액션 실행
        
        Args:
            action_type: 액션 유형
            params: 액션 파라미터
            
        Returns:
            액션 결과
        """
        self._check_initialized()
        
        params = params or {}
        
        if action_type == 'handle_interruptions':
            # 인터럽션 처리
            context = params.get('context')
            url = params.get('url')
            interruption_types = params.get('types')
            
            return self.handle_interruptions(context, url, interruption_types)
        
        elif action_type == 'add_pattern':
            # 패턴 추가
            pattern = params.get('pattern')
            
            if not pattern:
                return {'success': False, 'error': "패턴이 지정되지 않음"}
            
            success = self.add_pattern(pattern)
            if success:
                return {'success': True}
            else:
                return {'success': False, 'error': "패턴 추가 실패"}
        
        elif action_type == 'remove_pattern':
            # 패턴 제거
            pattern_id = params.get('pattern_id')
            
            if not pattern_id:
                return {'success': False, 'error': "패턴 ID가 지정되지 않음"}
            
            success = self.remove_pattern(pattern_id)
            if success:
                return {'success': True}
            else:
                return {'success': False, 'error': "패턴 제거 실패"}
        
        elif action_type == 'get_patterns':
            # 패턴 가져오기
            interruption_type = params.get('type')
            domain = params.get('domain')
            
            patterns = self.get_patterns(interruption_type, domain)
            return {'success': True, 'patterns': patterns, 'count': len(patterns)}
        
        elif action_type == 'clear_handled_interruptions':
            # 처리된 인터럽션 초기화
            self.clear_handled_interruptions()
            return {'success': True}
        
        return {'success': False, 'error': f"지원되지 않는 액션: {action_type}"}
    
    def _check_initialized(self) -> None:
        """초기화 상태 확인"""
        if not self._initialized:
            raise RuntimeError("Plugin not initialized")