 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 인터럽션 핸들러
자동화 작업 중 발생하는 팝업, 광고, 쿠키 동의 등의 인터럽션을 감지하고 처리
"""

import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from urllib.parse import urlparse
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class InterruptionPattern:
    """인터럽션 패턴 클래스"""
    
    def __init__(self, pattern_id: str, name: str, pattern_type: str, 
                 pattern_data: Dict[str, Any], domains: List[str] = None,
                 description: str = "", enabled: bool = True):
        self.pattern_id = pattern_id
        self.name = name
        self.pattern_type = pattern_type  # selector, template, ocr
        self.pattern_data = pattern_data
        self.domains = domains or []  # 적용할 도메인 목록
        self.description = description
        self.enabled = enabled
        self.last_applied = None  # 마지막 적용 시간
        self.success_count = 0  # 성공 횟수
        self.failure_count = 0  # 실패 횟수
    
    def to_dict(self) -> Dict[str, Any]:
        """패턴 정보를 딕셔너리로 변환"""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "pattern_data": self.pattern_data,
            "domains": self.domains,
            "description": self.description,
            "enabled": self.enabled,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterruptionPattern':
        """딕셔너리에서 패턴 정보 생성"""
        pattern = cls(
            pattern_id=data["pattern_id"],
            name=data["name"],
            pattern_type=data["pattern_type"],
            pattern_data=data["pattern_data"],
            domains=data.get("domains", []),
            description=data.get("description", ""),
            enabled=data.get("enabled", True)
        )
        
        if data.get("last_applied"):
            pattern.last_applied = datetime.fromisoformat(data["last_applied"])
        
        pattern.success_count = data.get("success_count", 0)
        pattern.failure_count = data.get("failure_count", 0)
        
        return pattern
    
    def matches_domain(self, url: str) -> bool:
        """URL의 도메인이 패턴의 도메인 목록과 일치하는지 확인"""
        if not self.domains:  # 도메인 목록이 비어있으면 모든 도메인에 적용
            return True
        
        try:
            domain = urlparse(url).netloc
            
            for pattern_domain in self.domains:
                # 정확한 도메인 일치
                if domain == pattern_domain:
                    return True
                
                # 와일드카드 도메인 일치 (*.example.com)
                if pattern_domain.startswith('*.') and domain.endswith(pattern_domain[1:]):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"도메인 확인 중 오류: {str(e)}")
            return False
    
    def increment_success(self):
        """성공 횟수 증가"""
        self.success_count += 1
        self.last_applied = datetime.now()
    
    def increment_failure(self):
        """실패 횟수 증가"""
        self.failure_count += 1
        self.last_applied = datetime.now()


class InterruptionAction:
    """인터럽션 조치 클래스"""
    
    def __init__(self, action_id: str, name: str, action_type: str,
                 action_data: Dict[str, Any], description: str = ""):
        self.action_id = action_id
        self.name = name
        self.action_type = action_type  # click, wait, keypress, js, etc.
        self.action_data = action_data
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """조치 정보를 딕셔너리로 변환"""
        return {
            "action_id": self.action_id,
            "name": self.name,
            "action_type": self.action_type,
            "action_data": self.action_data,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterruptionAction':
        """딕셔너리에서 조치 정보 생성"""
        return cls(
            action_id=data["action_id"],
            name=data["name"],
            action_type=data["action_type"],
            action_data=data["action_data"],
            description=data.get("description", "")
        )


class InterruptionRule:
    """인터럽션 규칙 클래스 - 패턴과 조치의 연결"""
    
    def __init__(self, rule_id: str, name: str, 
                 pattern: InterruptionPattern, actions: List[InterruptionAction],
                 priority: int = 0, enabled: bool = True, description: str = ""):
        self.rule_id = rule_id
        self.name = name
        self.pattern = pattern
        self.actions = actions
        self.priority = priority  # 우선순위 (높을수록 먼저 처리)
        self.enabled = enabled
        self.description = description
        self.last_triggered = None  # 마지막 트리거 시간
        self.trigger_count = 0  # 트리거 횟수
    
    def to_dict(self) -> Dict[str, Any]:
        """규칙 정보를 딕셔너리로 변환"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "pattern": self.pattern.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterruptionRule':
        """딕셔너리에서 규칙 정보 생성"""
        pattern = InterruptionPattern.from_dict(data["pattern"])
        actions = [InterruptionAction.from_dict(action_data) for action_data in data["actions"]]
        
        rule = cls(
            rule_id=data["rule_id"],
            name=data["name"],
            pattern=pattern,
            actions=actions,
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", "")
        )
        
        if data.get("last_triggered"):
            rule.last_triggered = datetime.fromisoformat(data["last_triggered"])
        
        rule.trigger_count = data.get("trigger_count", 0)
        
        return rule
    
    def increment_trigger(self):
        """트리거 횟수 증가"""
        self.trigger_count += 1
        self.last_triggered = datetime.now()


class InterruptionHandler:
    """인터럽션 핸들러 - 인터럽션 감지 및 처리 관리"""
    
    def __init__(self, plugin_manager: Any, settings_manager: Any, 
                 rules_file: str = None):
        self.plugin_manager = plugin_manager
        self.settings_manager = settings_manager
        
        if rules_file is None:
            home_dir = Path.home()
            rules_dir = home_dir / "BlueAI" / "config"
            os.makedirs(rules_dir, exist_ok=True)
            rules_file = rules_dir / "interruption_rules.json"
        
        self.rules_file = str(rules_file)
        self.rules: Dict[str, InterruptionRule] = {}
        
        # 설정 옵저버 등록
        if settings_manager:
            settings_manager.register_observer(self)
        
        # 설정에서 인터럽션 처리 활성화 여부 확인
        self.enabled = True
        if settings_manager:
            self.enabled = settings_manager.get("interruption", "enabled", True)
        
        # 화이트리스트/블랙리스트 가져오기
        self.whitelist = set()
        self.blacklist = set()
        if settings_manager:
            self.whitelist = settings_manager.get_whitelist_domains()
            self.blacklist = settings_manager.get_blacklist_domains()
        
        # 규칙 로드
        self.load_rules()
    
    def on_settings_changed(self, section: str, key: str, value: Any):
        """설정 변경 이벤트 핸들러"""
        if section == "interruption":
            if key == "enabled":
                self.enabled = value
            elif key == "whitelist":
                self.whitelist = set(value)
            elif key == "blacklist":
                self.blacklist = set(value)
    
    def load_rules(self) -> bool:
        """규칙 파일에서 규칙 로드"""
        if not os.path.exists(self.rules_file):
            logger.info(f"규칙 파일이 존재하지 않음: {self.rules_file}")
            return False
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            self.rules = {}
            for rule_data in rules_data:
                rule = InterruptionRule.from_dict(rule_data)
                self.rules[rule.rule_id] = rule
            
            logger.info(f"규칙 {len(self.rules)}개 로드됨: {self.rules_file}")
            return True
            
        except Exception as e:
            logger.error(f"규칙 로드 중 오류: {str(e)}")
            return False
    
    def save_rules(self) -> bool:
        """규칙을 파일에 저장"""
        try:
            rules_data = [rule.to_dict() for rule in self.rules.values()]
            
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"규칙 {len(self.rules)}개 저장됨: {self.rules_file}")
            return True
            
        except Exception as e:
            logger.error(f"규칙 저장 중 오류: {str(e)}")
            return False
    
    def add_rule(self, rule: InterruptionRule) -> bool:
        """규칙 추가"""
        if rule.rule_id in self.rules:
            logger.warning(f"중복된 규칙 ID: {rule.rule_id}, 덮어쓰기")
        
        self.rules[rule.rule_id] = rule
        
        # 규칙 저장
        return self.save_rules()
    
    def remove_rule(self, rule_id: str) -> bool:
        """규칙 제거"""
        if rule_id not in self.rules:
            logger.warning(f"제거할 규칙을 찾을 수 없음: {rule_id}")
            return False
        
        del self.rules[rule_id]
        
        # 규칙 저장
        return self.save_rules()
    
    def update_rule(self, rule: InterruptionRule) -> bool:
        """규칙 업데이트"""
        if rule.rule_id not in self.rules:
            logger.warning(f"업데이트할 규칙을 찾을 수 없음: {rule.rule_id}")
            return False
        
        self.rules[rule.rule_id] = rule
        
        # 규칙 저장
        return self.save_rules()
    
    def get_rules(self) -> List[InterruptionRule]:
        """모든 규칙 반환"""
        # 우선순위 순으로 정렬
        return sorted(self.rules.values(), key=lambda r: r.priority, reverse=True)
    
    def get_rule(self, rule_id: str) -> Optional[InterruptionRule]:
        """지정된 ID의 규칙 반환"""
        return self.rules.get(rule_id)
    
    def is_url_allowed(self, url: str) -> bool:
        """URL이 화이트리스트/블랙리스트에 따라 허용되는지 확인"""
        try:
            domain = urlparse(url).netloc
            
            # 블랙리스트 확인
            for blacklisted in self.blacklist:
                if domain == blacklisted or (blacklisted.startswith('*.') and domain.endswith(blacklisted[1:])):
                    logger.debug(f"블랙리스트 도메인 차단됨: {domain}")
                    return False
            
            # 화이트리스트가 없으면 모두 허용
            if not self.whitelist:
                return True
            
            # 화이트리스트 확인
            for whitelisted in self.whitelist:
                if domain == whitelisted or (whitelisted.startswith('*.') and domain.endswith(whitelisted[1:])):
                    return True
            
            # 화이트리스트에 없고 설정된 경우 차단
            logger.debug(f"화이트리스트에 없는 도메인: {domain}")
            return False
            
        except Exception as e:
            logger.error(f"URL 확인 중 오류: {str(e)}")
            return True  # 오류 시 차단하지 않음
    
    def check_interruption(self, page: Any, context: Dict[str, Any] = None) -> Optional[InterruptionRule]:
        """인터럽션 감지"""
        if not self.enabled:
            return None
        
        if not page:
            logger.error("페이지 객체가 없음")
            return None
        
        try:
            url = page.url
            
            # URL 허용 여부 확인
            if not self.is_url_allowed(url):
                return None
            
            context = context or {}
            context['url'] = url
            
            # 우선순위 순으로 규칙 확인
            for rule in self.get_rules():
                if not rule.enabled or not rule.pattern.enabled:
                    continue
                
                # 도메인 확인
                if not rule.pattern.matches_domain(url):
                    continue
                
                # 패턴 타입에 따른 감지
                pattern_type = rule.pattern.pattern_type
                pattern_data = rule.pattern.pattern_data
                
                if pattern_type == "selector":
                    # 선택자 기반 감지
                    selector = pattern_data.get("selector")
                    if not selector:
                        continue
                    
                    visible_only = pattern_data.get("visible_only", True)
                    
                    try:
                        if visible_only:
                            element = page.query_selector(selector)
                            if element and element.is_visible():
                                rule.increment_trigger()
                                rule.pattern.increment_success()
                                return rule
                        else:
                            element = page.query_selector(selector)
                            if element:
                                rule.increment_trigger()
                                rule.pattern.increment_success()
                                return rule
                    except Exception as e:
                        logger.error(f"선택자 검색 중 오류: {selector} - {str(e)}")
                        rule.pattern.increment_failure()
                
                elif pattern_type == "template":
                    # 템플릿 매칭 기반 감지 (이미지)
                    if not self.plugin_manager:
                        continue
                    
                    template_path = pattern_data.get("template_path")
                    if not template_path or not os.path.exists(template_path):
                        continue
                    
                    threshold = pattern_data.get("threshold", 0.8)
                    
                    try:
                        # 스크린샷 캡처
                        screenshot = page.screenshot()
                        
                        # OpenCV 플러그인으로 템플릿 매칭
                        result = self.plugin_manager.execute_plugin(
                            "recognition", "template_matching", "match_template",
                            {
                                "image": screenshot,
                                "template_path": template_path,
                                "threshold": threshold
                            }
                        )
                        
                        if result and result.get("matches"):
                            rule.increment_trigger()
                            rule.pattern.increment_success()
                            return rule
                        
                    except Exception as e:
                        logger.error(f"템플릿 매칭 중 오류: {str(e)}")
                        rule.pattern.increment_failure()
                
                elif pattern_type == "ocr":
                    # OCR 기반 감지 (텍스트)
                    if not self.plugin_manager:
                        continue
                    
                    text_patterns = pattern_data.get("text_patterns", [])
                    if not text_patterns:
                        continue
                    
                    try:
                        # 스크린샷 캡처
                        screenshot = page.screenshot()
                        
                        # OCR 플러그인으로 텍스트 추출
                        result = self.plugin_manager.execute_plugin(
                            "recognition", "ocr", "extract_text",
                            {
                                "image": screenshot
                            }
                        )
                        
                        if result and result.get("text"):
                            extracted_text = result["text"]
                            
                            # 텍스트 패턴 매칭
                            for pattern_text in text_patterns:
                                if re.search(pattern_text, extracted_text, re.IGNORECASE):
                                    rule.increment_trigger()
                                    rule.pattern.increment_success()
                                    return rule
                        
                    except Exception as e:
                        logger.error(f"OCR 인식 중 오류: {str(e)}")
                        rule.pattern.increment_failure()
            
            return None
            
        except Exception as e:
            logger.error(f"인터럽션 감지 중 오류: {str(e)}")
            return None
    
    def handle_interruption(self, page: Any, rule: InterruptionRule, context: Dict[str, Any] = None) -> bool:
        """인터럽션 처리"""
        if not self.enabled or not page or not rule:
            return False
        
        logger.info(f"인터럽션 처리 중: {rule.name}")
        
        context = context or {}
        success = False
        
        try:
            # 순서대로 조치 실행
            for action in rule.actions:
                action_type = action.action_type
                action_data = action.action_data
                
                if action_type == "click":
                    # 클릭 액션
                    selector = action_data.get("selector")
                    if not selector:
                        continue
                    
                    force = action_data.get("force", False)
                    
                    try:
                        if force:
                            page.click(selector, force=True)
                        else:
                            page.click(selector)
                        
                        success = True
                        
                    except Exception as e:
                        logger.error(f"클릭 액션 실행 중 오류: {selector} - {str(e)}")
                
                elif action_type == "wait":
                    # 대기 액션
                    timeout = action_data.get("timeout", 5)
                    
                    try:
                        time.sleep(timeout)
                        success = True
                        
                    except Exception as e:
                        logger.error(f"대기 액션 실행 중 오류: {str(e)}")
                
                elif action_type == "keypress":
                    # 키 입력 액션
                    key = action_data.get("key")
                    if not key:
                        continue
                    
                    try:
                        page.press("body", key)
                        success = True
                        
                    except Exception as e:
                        logger.error(f"키 입력 액션 실행 중 오류: {key} - {str(e)}")
                
                elif action_type == "js":
                    # 자바스크립트 실행 액션
                    script = action_data.get("script")
                    if not script:
                        continue
                    
                    try:
                        page.evaluate(script)
                        success = True
                        
                    except Exception as e:
                        logger.error(f"자바스크립트 액션 실행 중 오류: {str(e)}")
                
                elif action_type == "fill":
                    # 입력 필드 채우기 액션
                    selector = action_data.get("selector")
                    value = action_data.get("value")
                    if not selector or value is None:
                        continue
                    
                    try:
                        page.fill(selector, str(value))
                        success = True
                        
                    except Exception as e:
                        logger.error(f"입력 필드 채우기 액션 실행 중 오류: {selector} - {str(e)}")
                
                elif action_type == "plugin":
                    # 플러그인 액션
                    if not self.plugin_manager:
                        continue
                    
                    plugin_type = action_data.get("plugin_type")
                    plugin_name = action_data.get("plugin_name")
                    plugin_action = action_data.get("action")
                    params = action_data.get("params", {})
                    
                    if not plugin_type or not plugin_name or not plugin_action:
                        continue
                    
                    try:
                        result = self.plugin_manager.execute_plugin(
                            plugin_type, plugin_name, plugin_action,
                            {**params, "page": page, **context}
                        )
                        
                        if result is not None:
                            success = True
                            
                    except Exception as e:
                        logger.error(f"플러그인 액션 실행 중 오류: {plugin_type}.{plugin_name}.{plugin_action} - {str(e)}")
            
            return success
            
        except Exception as e:
            logger.error(f"인터럽션 처리 중 오류: {str(e)}")
            return False
    
    def check_and_handle(self, page: Any, context: Dict[str, Any] = None) -> bool:
        """인터럽션 감지 및 처리를 한 번에 수행"""
        if not self.enabled or not page:
            return False
        
        # 인터럽션 감지
        rule = self.check_interruption(page, context)
        if not rule:
            return False
        
        # 인터럽션 처리
        return self.handle_interruption(page, rule, context)
    
    def register_pattern(self, pattern: InterruptionPattern) -> str:
        """새 인터럽션 패턴 등록"""
        # 새 규칙 생성
        rule = InterruptionRule(
            rule_id=f"rule_{pattern.pattern_id}",
            name=f"Rule for {pattern.name}",
            pattern=pattern,
            actions=[],
            priority=0,
            enabled=True,
            description=f"Auto-generated rule for pattern: {pattern.name}"
        )
        
        # 규칙 추가
        self.add_rule(rule)
        
        return rule.rule_id
    
    def learn_interruption(self, page: Any, action_sequence: List[Dict[str, Any]]) -> Optional[str]:
        """사용자 액션 시퀀스에서 인터럽션 패턴 학습"""
        if not page:
            return None
        
        try:
            url = page.url
            domain = urlparse(url).netloc
            
            # 패턴 ID 생성
            pattern_id = f"pattern_{int(time.time())}"
            
            # 선택자 패턴 생성
            selectors = []
            
            for action in action_sequence:
                action_type = action.get("type")
                selector = action.get("selector")
                
                if action_type in ["click", "fill"] and selector:
                    selectors.append(selector)
            
            if not selectors:
                logger.warning("학습할 선택자 없음")
                return None
            
            # 가장 구체적인 선택자 선택
            best_selector = max(selectors, key=lambda s: len(s))
            
            # 패턴 생성
            pattern = InterruptionPattern(
                pattern_id=pattern_id,
                name=f"Learned Pattern {pattern_id}",
                pattern_type="selector",
                pattern_data={"selector": best_selector, "visible_only": True},
                domains=[domain],
                description=f"학습된 패턴: {best_selector}",
                enabled=True
            )
            
            # 액션 생성
            actions = []
            for i, action in enumerate(action_sequence):
                action_type = action.get("type")
                
                if action_type == "click":
                    actions.append(InterruptionAction(
                        action_id=f"action_{pattern_id}_{i}",
                        name=f"Click {action.get('selector')}",
                        action_type="click",
                        action_data={"selector": action.get("selector"), "force": False},
                        description="클릭 액션"
                    ))
                
                elif action_type == "fill":
                    actions.append(InterruptionAction(
                        action_id=f"action_{pattern_id}_{i}",
                        name=f"Fill {action.get('selector')}",
                        action_type="fill",
                        action_data={"selector": action.get("selector"), "value": action.get("value", "")},
                        description="입력 필드 채우기 액션"
                    ))
                
                elif action_type == "keypress":
                    actions.append(InterruptionAction(
                        action_id=f"action_{pattern_id}_{i}",
                        name=f"Press {action.get('key')}",
                        action_type="keypress",
                        action_data={"key": action.get("key", "")},
                        description="키 입력 액션"
                    ))
                
                elif action_type == "wait":
                    actions.append(InterruptionAction(
                        action_id=f"action_{pattern_id}_{i}",
                        name=f"Wait {action.get('timeout')}s",
                        action_type="wait",
                        action_data={"timeout": action.get("timeout", 1)},
                        description="대기 액션"
                    ))
            
            # 규칙 생성
            rule = InterruptionRule(
                rule_id=f"rule_{pattern_id}",
                name=f"Learned Rule {pattern_id}",
                pattern=pattern,
                actions=actions,
                priority=10,  # 학습된 규칙은 우선순위 높게
                enabled=True,
                description=f"학습된 규칙: {domain}"
            )
            
            # 규칙 추가
            self.add_rule(rule)
            
            logger.info(f"인터럽션 패턴 학습됨: {pattern.name}, 액션 {len(actions)}개")
            return rule.rule_id
            
        except Exception as e:
            logger.error(f"인터럽션 학습 중 오류: {str(e)}")
            return None
    
    def import_rules(self, file_path: str) -> int:
        """외부 파일에서 규칙 가져오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            count = 0
            for rule_data in rules_data:
                try:
                    rule = InterruptionRule.from_dict(rule_data)
                    
                    # 중복 ID 방지
                    if rule.rule_id in self.rules:
                        rule.rule_id = f"{rule.rule_id}_{int(time.time())}"
                    
                    self.rules[rule.rule_id] = rule
                    count += 1
                    
                except Exception as e:
                    logger.error(f"규칙 가져오기 중 오류: {str(e)}")
            
            # 규칙 저장
            self.save_rules()
            
            logger.info(f"규칙 {count}개 가져옴: {file_path}")
            return count
            
        except Exception as e:
            logger.error(f"규칙 가져오기 중 오류: {file_path} - {str(e)}")
            return 0
    
    def export_rules(self, file_path: str) -> bool:
        """규칙을 외부 파일로 내보내기"""
        try:
            rules_data = [rule.to_dict() for rule in self.rules.values()]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"규칙 {len(self.rules)}개 내보냄: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"규칙 내보내기 중 오류: {file_path} - {str(e)}")
            return False