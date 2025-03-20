"""
인터럽션 처리 모듈

이 모듈은 자동화 과정에서 발생하는 방해 요소(광고, 팝업, 쿠키 알림 등)를 관리하고 처리합니다.
사용자 설정과 사이트별 패턴을 기반으로 적절한 처리 방법을 결정합니다.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from .plugin_system import PluginManager, PluginType


class InterruptionType(Enum):
    """인터럽션 유형"""
    AD = "ad"  # 광고
    POPUP = "popup"  # 팝업
    COOKIE = "cookie"  # 쿠키 알림
    LOGIN = "login"  # 로그인 프롬프트
    SURVEY = "survey"  # 설문 조사
    NOTIFICATION = "notification"  # 알림 요청
    CUSTOM = "custom"  # 사용자 정의


class InterruptionAction(Enum):
    """인터럽션 처리 액션"""
    CLOSE = "close"  # 닫기
    ACCEPT = "accept"  # 수락
    DECLINE = "decline"  # 거부
    IGNORE = "ignore"  # 무시
    CUSTOM = "custom"  # 사용자 정의


@dataclass
class InterruptionPattern:
    """인터럽션 패턴 정의"""
    id: str  # 패턴 ID
    type: InterruptionType  # 인터럽션 유형
    action: InterruptionAction  # 처리 액션
    selectors: List[str] = field(default_factory=list)  # 선택자 목록
    image_templates: List[str] = field(default_factory=list)  # 이미지 템플릿 목록
    ocr_patterns: List[str] = field(default_factory=list)  # OCR 패턴 목록
    domain_patterns: List[str] = field(default_factory=list)  # 도메인 패턴 목록
    priority: int = 0  # 우선순위 (높을수록 먼저 시도)
    custom_action: Dict[str, Any] = field(default_factory=dict)  # 사용자 정의 액션
    success_count: int = 0  # 성공 횟수
    last_success: float = 0  # 마지막 성공 시간


@dataclass
class SitePolicy:
    """사이트별 처리 정책"""
    domain: str  # 도메인
    whitelist: Set[InterruptionType] = field(default_factory=set)  # 화이트리스트 (처리 안 함)
    blacklist: Set[InterruptionType] = field(default_factory=set)  # 블랙리스트 (항상 처리)
    custom_patterns: List[str] = field(default_factory=list)  # 사용자 정의 패턴


class InterruptionHandler:
    """인터럽션 처리 클래스"""
    
    def __init__(self, plugin_manager: PluginManager, settings_file: str = "interruption_settings.json", logger=None):
        """인터럽션 처리 클래스 초기화
        
        Args:
            plugin_manager: 플러그인 관리자
            settings_file: 설정 파일 경로
            logger: 로거 객체
        """
        self.plugin_manager = plugin_manager
        self.settings_file = settings_file
        self.logger = logger or logging.getLogger(__name__)
        
        # 설정 및 패턴 로드
        self.settings = self._load_settings()
        self.patterns = self._load_patterns()
        self.site_policies = self._load_site_policies()
        
        # 패턴 사용 통계
        self.pattern_stats = {}
    
    def _load_settings(self) -> Dict[str, Any]:
        """설정 로드"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'enabled': True,
            'default_policy': {
                'ads': True,
                'popups': True,
                'cookies': True,
                'login_prompts': False,
                'surveys': False,
                'notifications': True
            },
            'mode_settings': {
                'speed': {
                    'max_wait_time': 1.0,
                    'max_retries': 1
                },
                'balanced': {
                    'max_wait_time': 3.0,
                    'max_retries': 2
                },
                'accuracy': {
                    'max_wait_time': 5.0,
                    'max_retries': 3
                }
            },
            'patterns_path': 'patterns.json',
            'site_policies_path': 'site_policies.json',
            'learning_enabled': True
        }
    
    def _load_patterns(self) -> Dict[str, InterruptionPattern]:
        """패턴 로드"""
        patterns = {}
        patterns_path = self.settings.get('patterns_path', 'patterns.json')
        
        try:
            with open(patterns_path, 'r', encoding='utf-8') as f:
                pattern_data = json.load(f)
                
                for p_data in pattern_data:
                    try:
                        pattern = InterruptionPattern(
                            id=p_data['id'],
                            type=InterruptionType(p_data['type']),
                            action=InterruptionAction(p_data['action']),
                            selectors=p_data.get('selectors', []),
                            image_templates=p_data.get('image_templates', []),
                            ocr_patterns=p_data.get('ocr_patterns', []),
                            domain_patterns=p_data.get('domain_patterns', []),
                            priority=p_data.get('priority', 0),
                            custom_action=p_data.get('custom_action', {}),
                            success_count=p_data.get('success_count', 0),
                            last_success=p_data.get('last_success', 0)
                        )
                        patterns[pattern.id] = pattern
                    except (KeyError, ValueError) as e:
                        self.logger.warning(f"패턴 로드 오류: {str(e)}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"패턴 파일 로드 실패: {str(e)}")
            # 기본 패턴 생성
            self._create_default_patterns(patterns)
        
        return patterns
    
    def _create_default_patterns(self, patterns: Dict[str, InterruptionPattern]) -> None:
        """기본 패턴 생성"""
        # 쿠키 알림 패턴
        cookie_pattern = InterruptionPattern(
            id="cookie_banner_1",
            type=InterruptionType.COOKIE,
            action=InterruptionAction.ACCEPT,
            selectors=[
                "button[aria-label*='accept' i]",
                "button[aria-label*='cookie' i]",
                "button:has-text('Accept')",
                "button:has-text('Accept All')",
                "button:has-text('Allow')"
            ],
            ocr_patterns=[
                r"accept(?:\s+all)?(?:\s+cookies)?",
                r"allow(?:\s+cookies)?",
                r"(?:i\s+)?agree"
            ],
            priority=10
        )
        patterns[cookie_pattern.id] = cookie_pattern
        
        # 팝업 패턴
        popup_pattern = InterruptionPattern(
            id="popup_1",
            type=InterruptionType.POPUP,
            action=InterruptionAction.CLOSE,
            selectors=[
                "button.close",
                "button[aria-label='Close']",
                ".modal button.btn-close",
                "button:has-text('Close')",
                "button:has-text('Skip')",
                "a:has-text('No thanks')"
            ],
            ocr_patterns=[
                r"close",
                r"skip",
                r"no\s+thanks"
            ],
            priority=5
        )
        patterns[popup_pattern.id] = popup_pattern
        
        # 광고 패턴
        ad_pattern = InterruptionPattern(
            id="ad_banner_1",
            type=InterruptionType.AD,
            action=InterruptionAction.CLOSE,
            selectors=[
                "div[id*='ad-'] .close",
                "div[class*='ad-'] .close",
                "div[aria-label*='advertisement'] button",
                "iframe[id*='google_ads'] + div button"
            ],
            priority=3
        )
        patterns[ad_pattern.id] = ad_pattern
    
    def _load_site_policies(self) -> Dict[str, SitePolicy]:
        """사이트 정책 로드"""
        policies = {}
        site_policies_path = self.settings.get('site_policies_path', 'site_policies.json')
        
        try:
            with open(site_policies_path, 'r', encoding='utf-8') as f:
                policy_data = json.load(f)
                
                for domain, p_data in policy_data.items():
                    try:
                        policy = SitePolicy(
                            domain=domain,
                            whitelist=set(InterruptionType(t) for t in p_data.get('whitelist', [])),
                            blacklist=set(InterruptionType(t) for t in p_data.get('blacklist', [])),
                            custom_patterns=p_data.get('custom_patterns', [])
                        )
                        policies[domain] = policy
                    except (KeyError, ValueError) as e:
                        self.logger.warning(f"사이트 정책 로드 오류: {str(e)}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"사이트 정책 파일 로드 실패: {str(e)}")
        
        return policies
    
    def save_settings(self) -> None:
        """설정 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.debug("설정 저장 완료")
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {str(e)}")
    
    def save_patterns(self) -> None:
        """패턴 저장"""
        patterns_path = self.settings.get('patterns_path', 'patterns.json')
        
        try:
            pattern_data = []
            for pattern in self.patterns.values():
                pattern_data.append({
                    'id': pattern.id,
                    'type': pattern.type.value,
                    'action': pattern.action.value,
                    'selectors': pattern.selectors,
                    'image_templates': pattern.image_templates,
                    'ocr_patterns': pattern.ocr_patterns,
                    'domain_patterns': pattern.domain_patterns,
                    'priority': pattern.priority,
                    'custom_action': pattern.custom_action,
                    'success_count': pattern.success_count,
                    'last_success': pattern.last_success
                })
            
            with open(patterns_path, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, indent=2)
            self.logger.debug("패턴 저장 완료")
        except Exception as e:
            self.logger.error(f"패턴 저장 실패: {str(e)}")
    
    def save_site_policies(self) -> None:
        """사이트 정책 저장"""
        site_policies_path = self.settings.get('site_policies_path', 'site_policies.json')
        
        try:
            policy_data = {}
            for domain, policy in self.site_policies.items():
                policy_data[domain] = {
                    'whitelist': [t.value for t in policy.whitelist],
                    'blacklist': [t.value for t in policy.blacklist],
                    'custom_patterns': policy.custom_patterns
                }
            
            with open(site_policies_path, 'w', encoding='utf-8') as f:
                json.dump(policy_data, f, indent=2)
            self.logger.debug("사이트 정책 저장 완료")
        except Exception as e:
            self.logger.error(f"사이트 정책 저장 실패: {str(e)}")
    
    def get_domain_from_url(self, url: str) -> str:
        """URL에서 도메인 추출
        
        Args:
            url: URL
            
        Returns:
            도메인
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # www 제거
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except Exception:
            return ""
    
    def is_interruption_enabled(self, int_type: Union[str, InterruptionType], domain: str = None) -> bool:
        """인터럽션 처리 활성화 여부 확인
        
        Args:
            int_type: 인터럽션 유형
            domain: 도메인 (선택 사항)
            
        Returns:
            활성화 여부
        """
        if not self.settings.get('enabled', True):
            return False
        
        # 문자열을 열거형으로 변환
        if isinstance(int_type, str):
            try:
                int_type = InterruptionType(int_type)
            except ValueError:
                return False
        
        # 도메인별 정책 체크
        if domain and domain in self.site_policies:
            policy = self.site_policies[domain]
            
            # 화이트리스트에 있으면 처리 안 함
            if int_type in policy.whitelist:
                return False
                
            # 블랙리스트에 있으면 항상 처리
            if int_type in policy.blacklist:
                return True
        
        # 기본 정책 사용
        default_policy = self.settings.get('default_policy', {})
        
        if int_type == InterruptionType.AD:
            return default_policy.get('ads', True)
        elif int_type == InterruptionType.POPUP:
            return default_policy.get('popups', True)
        elif int_type == InterruptionType.COOKIE:
            return default_policy.get('cookies', True)
        elif int_type == InterruptionType.LOGIN:
            return default_policy.get('login_prompts', False)
        elif int_type == InterruptionType.SURVEY:
            return default_policy.get('surveys', False)
        elif int_type == InterruptionType.NOTIFICATION:
            return default_policy.get('notifications', True)
        
        return False
    
    def get_enabled_interruption_types(self, domain: str = None) -> List[InterruptionType]:
        """활성화된 인터럽션 유형 목록 가져오기
        
        Args:
            domain: 도메인 (선택 사항)
            
        Returns:
            활성화된 인터럽션 유형 목록
        """
        enabled_types = []
        
        for int_type in InterruptionType:
            if int_type != InterruptionType.CUSTOM and self.is_interruption_enabled(int_type, domain):
                enabled_types.append(int_type)
        
        return enabled_types
    
    def get_patterns_for_domain(self, domain: str) -> List[InterruptionPattern]:
        """도메인에 대한 패턴 목록 가져오기
        
        Args:
            domain: 도메인
            
        Returns:
            패턴 목록
        """
        result = []
        
        for pattern in self.patterns.values():
            # 도메인 패턴 확인
            if pattern.domain_patterns:
                domain_match = False
                for domain_pattern in pattern.domain_patterns:
                    if re.search(domain_pattern, domain, re.IGNORECASE):
                        domain_match = True
                        break
                
                if not domain_match:
                    continue
            
            # 활성화 여부 확인
            if self.is_interruption_enabled(pattern.type, domain):
                result.append(pattern)
        
        # 우선순위에 따라 정렬
        result.sort(key=lambda p: p.priority, reverse=True)
        
        return result
    
    def handle_interruptions(self, automation_engine, url: str, mode: str = "balanced") -> Dict[str, Any]:
        """인터럽션 처리
        
        Args:
            automation_engine: 자동화 엔진
            url: 현재 URL
            mode: 처리 모드 (speed, balanced, accuracy)
            
        Returns:
            처리 결과
        """
        if not self.settings.get('enabled', True):
            return {'handled': False, 'reason': 'Interruption handling is disabled'}
        
        domain = self.get_domain_from_url(url)
        enabled_types = self.get_enabled_interruption_types(domain)
        
        if not enabled_types:
            return {'handled': False, 'reason': 'No enabled interruption types for this domain'}
        
        patterns = self.get_patterns_for_domain(domain)
        
        if not patterns:
            return {'handled': False, 'reason': 'No patterns available for this domain'}
        
        mode_settings = self.settings.get('mode_settings', {}).get(mode, {})
        max_wait_time = mode_settings.get('max_wait_time', 3.0)
        max_retries = mode_settings.get('max_retries', 2)
        
        # 인터럽션 처리
        handled_count = 0
        handled_patterns = []
        
        for attempt in range(max_retries):
            handled_in_attempt = 0
            
            for pattern in patterns:
                if pattern.type not in enabled_types:
                    continue
                
                try:
                    result = self._apply_pattern(automation_engine, pattern, max_wait_time)
                    
                    if result.get('success', False):
                        handled_count += 1
                        handled_in_attempt += 1
                        handled_patterns.append(pattern.id)
                        
                        # 패턴 통계 업데이트
                        pattern.success_count += 1
                        pattern.last_success = time.time()
                        
                        self.logger.info(f"인터럽션 처리 성공: {pattern.id} ({pattern.type.value})")
                except Exception as e:
                    self.logger.warning(f"인터럽션 처리 중 오류: {pattern.id} - {str(e)}")
            
            # 이번 시도에서 처리된 것이 없으면 중단
            if handled_in_attempt == 0:
                break
        
        # 학습 활성화된 경우 패턴 저장
        if self.settings.get('learning_enabled', True) and handled_count > 0:
            self.save_patterns()
        
        return {
            'handled': handled_count > 0,
            'count': handled_count,
            'patterns': handled_patterns
        }
    
    def _apply_pattern(self, automation_engine, pattern: InterruptionPattern, max_wait_time: float) -> Dict[str, Any]:
        """패턴 적용
        
        Args:
            automation_engine: 자동화 엔진
            pattern: 인터럽션 패턴
            max_wait_time: 최대 대기 시간
            
        Returns:
            적용 결과
        """
        # 선택자 기반 처리
        if pattern.selectors:
            for selector in pattern.selectors:
                try:
                    result = automation_engine.execute_action('find_element', {
                        'selector': selector,
                        'timeout': max_wait_time
                    })
                    
                    if result.get('found', False):
                        # 액션 실행
                        element = result.get('element')
                        action_result = self._execute_action(automation_engine, pattern.action, element, pattern.custom_action)
                        
                        if action_result.get('success', False):
                            return {'success': True, 'method': 'selector', 'selector': selector}
                except Exception:
                    continue
        
        # 이미지 템플릿 매칭
        recognition_plugins = self.plugin_manager.find_plugins(
            PluginType.RECOGNITION, {'name': 'template_matching'}
        )
        
        if pattern.image_templates and recognition_plugins:
            plugin = recognition_plugins[0]
            
            for template in pattern.image_templates:
                try:
                    result = plugin.execute_action('recognize', {
                        'template': template,
                        'threshold': 0.8,
                        'timeout': max_wait_time
                    })
                    
                    if result.get('success', False):
                        # 템플릿 위치 클릭 또는 액션 실행
                        location = result.get('location')
                        action_result = self._execute_action(automation_engine, pattern.action, location, pattern.custom_action)
                        
                        if action_result.get('success', False):
                            return {'success': True, 'method': 'template', 'template': template}
                except Exception:
                    continue
        
        # OCR 기반 인식
        ocr_plugins = self.plugin_manager.find_plugins(
            PluginType.RECOGNITION, {'name': 'ocr'}
        )
        
        if pattern.ocr_patterns and ocr_plugins:
            plugin = ocr_plugins[0]
            
            try:
                result = plugin.execute_action('recognize', {
                    'timeout': max_wait_time
                })
                
                if result.get('success', False):
                    texts = result.get('texts', [])
                    
                    for ocr_pattern in pattern.ocr_patterns:
                        for text_item in texts:
                            text = text_item.get('text', '')
                            
                            if re.search(ocr_pattern, text, re.IGNORECASE):
                                # 텍스트 위치 클릭 또는 액션 실행
                                location = text_item.get('location')
                                action_result = self._execute_action(
                                    automation_engine, pattern.action, location, pattern.custom_action
                                )
                                
                                if action_result.get('success', False):
                                    return {'success': True, 'method': 'ocr', 'pattern': ocr_pattern, 'text': text}
            except Exception:
                pass
        
        return {'success': False}
    
    def _execute_action(self, automation_engine, action: InterruptionAction, 
                        target: Any, custom_action: Dict[str, Any] = None) -> Dict[str, Any]:
        """액션 실행
        
        Args:
            automation_engine: 자동화 엔진
            action: 인터럽션 액션
            target: 대상 (요소 또는 위치)
            custom_action: 사용자 정의 액션
            
        Returns:
            실행 결과
        """
        if action == InterruptionAction.CLOSE:
            if hasattr(target, 'click'):
                return automation_engine.execute_action('click', {'element': target})
            else:
                return automation_engine.execute_action('click', {'position': target})
        
        elif action == InterruptionAction.ACCEPT:
            if hasattr(target, 'click'):
                return automation_engine.execute_action('click', {'element': target})
            else:
                return automation_engine.execute_action('click', {'position': target})
        
        elif action == InterruptionAction.DECLINE:
            if hasattr(target, 'click'):
                return automation_engine.execute_action('click', {'element': target})
            else:
                return automation_engine.execute_action('click', {'position': target})
        
        elif action == InterruptionAction.IGNORE:
            # 의도적으로 무시
            return {'success': True}
        
        elif action == InterruptionAction.CUSTOM and custom_action:
            action_type = custom_action.get('type')
            
            if action_type == 'click':
                if hasattr(target, 'click'):
                    return automation_engine.execute_action('click', {'element': target})
                else:
                    return automation_engine.execute_action('click', {'position': target})
            
            elif action_type == 'input':
                text = custom_action.get('text', '')
                if hasattr(target, 'fill'):
                    return automation_engine.execute_action('fill', {'element': target, 'text': text})
            
            elif action_type == 'select':
                value = custom_action.get('value', '')
                if hasattr(target, 'select'):
                    return automation_engine.execute_action('select', {'element': target, 'value': value})
            
            elif action_type == 'script':
                script = custom_action.get('script', '')
                return automation_engine.execute_action('evaluate', {'script': script})
        
        return {'success': False, 'error': 'Unsupported action'}
    
    def add_to_whitelist(self, domain: str, int_type: Union[str, InterruptionType]) -> bool:
        """화이트리스트에 추가
        
        Args:
            domain: 도메인
            int_type: 인터럽션 유형
            
        Returns:
            성공 여부
        """
        # 문자열을 열거형으로 변환
        if isinstance(int_type, str):
            try:
                int_type = InterruptionType(int_type)
            except ValueError:
                return False
        
        # 사이트 정책 가져오기 또는 생성
        if domain not in self.site_policies:
            self.site_policies[domain] = SitePolicy(domain=domain)
        
        policy = self.site_policies[domain]
        
        # 블랙리스트에서 제거
        if int_type in policy.blacklist:
            policy.blacklist.remove(int_type)
        
        # 화이트리스트에 추가
        policy.whitelist.add(int_type)
        
        # 저장
        self.save_site_policies()
        
        return True
    
    def add_to_blacklist(self, domain: str, int_type: Union[str, InterruptionType]) -> bool:
        """블랙리스트에 추가
        
        Args:
            domain: 도메인
            int_type: 인터럽션 유형
            
        Returns:
            성공 여부
        """
        # 문자열을 열거형으로 변환
        if isinstance(int_type, str):
            try:
                int_type = InterruptionType(int_type)
            except ValueError:
                return False
        
        # 사이트 정책 가져오기 또는 생성
        if domain not in self.site_policies:
            self.site_policies[domain] = SitePolicy(domain=domain)
        
        policy = self.site_policies[domain]
        
        # 화이트리스트에서 제거
        if int_type in policy.whitelist:
            policy.whitelist.remove(int_type)
        
        # 블랙리스트에 추가
        policy.blacklist.add(int_type)
        
        # 저장
        self.save_site_policies()
        
        return True
    
    def remove_from_lists(self, domain: str, int_type: Union[str, InterruptionType]) -> bool:
        """리스트에서 제거
        
        Args:
            domain: 도메인
            int_type: 인터럽션 유형
            
        Returns:
            성공 여부
        """
        # 문자열을 열거형으로 변환
        if isinstance(int_type, str):
            try:
                int_type = InterruptionType(int_type)
            except ValueError:
                return False
        
        if domain not in self.site_policies:
            return False
        
        policy = self.site_policies[domain]
        
        # 화이트리스트에서 제거
        if int_type in policy.whitelist:
            policy.whitelist.remove(int_type)
        
        # 블랙리스트에서 제거
        if int_type in policy.blacklist:
            policy.blacklist.remove(int_type)
        
        # 리스트가 비어있으면 정책 제거
        if not policy.whitelist and not policy.blacklist and not policy.custom_patterns:
            del self.site_policies[domain]
        
        # 저장
        self.save_site_policies()
        
        return True
    
    def add_pattern(self, pattern: InterruptionPattern) -> bool:
        """패턴 추가
        
        Args:
            pattern: 인터럽션 패턴
            
        Returns:
            성공 여부
        """
        if pattern.id in self.patterns:
            return False
        
        self.patterns[pattern.id] = pattern
        self.save_patterns()
        
        return True
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """패턴 제거
        
        Args:
            pattern_id: 패턴 ID
            
        Returns:
            성공 여부
        """
        if pattern_id not in self.patterns:
            return False
        
        del self.patterns[pattern_id]
        self.save_patterns()
        
        return True
    
    def update_pattern(self, pattern: InterruptionPattern) -> bool:
        """패턴 업데이트
        
        Args:
            pattern: 인터럽션 패턴
            
        Returns:
            성공 여부
        """
        if pattern.id not in self.patterns:
            return False
        
        self.patterns[pattern.id] = pattern
        self.save_patterns()
        
        return True
    
    def learn_pattern(self, automation_engine, int_type: InterruptionType, action: InterruptionAction,
                    element_info: Dict[str, Any], url: str) -> Optional[str]:
        """패턴 학습
        
        Args:
            automation_engine: 자동화 엔진
            int_type: 인터럽션 유형
            action: 인터럽션 액션
            element_info: 요소 정보
            url: 현재 URL
            
        Returns:
            생성된 패턴 ID 또는 None
        """
        if not self.settings.get('learning_enabled', True):
            return None
        
        domain = self.get_domain_from_url(url)
        
        # 패턴 ID 생성
        pattern_id = f"{int_type.value}_{domain}_{int(time.time())}"
        
        selectors = []
        if 'selector' in element_info:
            selectors.append(element_info['selector'])
        
        # 추가 선택자 생성 (예: ID, 클래스, 텍스트 등)
        if 'attributes' in element_info:
            attrs = element_info['attributes']
            
            if 'id' in attrs and attrs['id']:
                selectors.append(f"#{attrs['id']}")
            
            if 'class' in attrs and attrs['class']:
                selectors.append(f".{attrs['class'].replace(' ', '.')}")
            
            if 'text' in attrs and attrs['text']:
                selectors.append(f"*:has-text('{attrs['text']}')")
        
        ocr_patterns = []
        if 'text' in element_info and element_info['text']:
            text = element_info['text']
            # 간단한 정규식 패턴 생성
            pattern = re.escape(text.lower())
            ocr_patterns.append(pattern)
        
        # 패턴 생성
        pattern = InterruptionPattern(
            id=pattern_id,
            type=int_type,
            action=action,
            selectors=selectors,
            ocr_patterns=ocr_patterns,
            domain_patterns=[re.escape(domain)],
            priority=5,  # 중간 우선순위
            success_count=1,
            last_success=time.time()
        )
        
        # 패턴 추가
        self.add_pattern(pattern)
        
        self.logger.info(f"새 패턴 학습: {pattern_id}")
        
        return pattern_id