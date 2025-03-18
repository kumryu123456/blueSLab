 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 팝업 처리 플러그인
웹 페이지의 팝업을 감지하고 자동으로 처리하는 플러그인
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re
from urllib.parse import urlparse

from core.plugin_manager import PluginInterface

logger = logging.getLogger(__name__)

class PopupHandlerPlugin(PluginInterface):
    """웹 페이지의 팝업 처리 플러그인"""
    
    plugin_type = "interruption"
    plugin_name = "popup_handler"
    plugin_version = "0.1.0"
    plugin_description = "웹 페이지의 팝업을 감지하고 자동으로 처리하는 플러그인"
    
    def __init__(self):
        super().__init__()
        self.patterns_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "patterns", "popup")
        self.stats_file = os.path.join(self.patterns_dir, "stats.json")
        
        # 설정 기본값
        self.config = {
            "enabled": True,
            "auto_detect": True,
            "close_selectors": [
                'button[aria-label="Close"]', 
                'button[title="Close"]', 
                '.modal-close', 
                '.popup-close',
                '.close-button',
                '.btn-close',
                '.modal .close',
                'button.close',
                '.dialog-close',
                'a[href="#close"]',
                '[data-dismiss="modal"]',
                '.modal-header .close',
                '.popover-close',
                'button:has(.close-icon)',
                'button:has(svg[aria-label="Close"])'
            ],
            "common_popup_selectors": [
                '.modal', 
                '.popup', 
                '.dialog',
                '.modal-dialog',
                '[role="dialog"]',
                '.popin',
                '.popover',
                '.overlay',
                '.lightbox',
                '.alert-box'
            ],
            "cookie_notice_selectors": [
                '#cookie-notice',
                '.cookie-banner',
                '.cookie-consent',
                '#cookieConsent',
                '.cookie-dialog',
                '[aria-label="Cookie Notice"]',
                '.cookie-policy',
                '.cookie-alert',
                '.cookie-message',
                '.cookie-notification'
            ],
            "accept_cookies_selectors": [
                'button:contains("Accept")',
                'button:contains("동의")',
                'button:contains("수락")',
                'button:contains("Allow")',
                'button:contains("I agree")',
                'a:contains("Accept")',
                '.accept-cookies',
                '.cookie-accept',
                '#accept-cookies',
                'button[data-action="accept-cookies"]'
            ],
            "whitelist_domains": [],
            "blacklist_domains": [],
            "max_attempts": 3,
            "attempt_delay": 0.5,
            "log_actions": True,
            "default_timeout": 5000
        }
        
        # 패턴 디렉토리 생성
        os.makedirs(self.patterns_dir, exist_ok=True)
        
        # 통계 데이터
        self.stats = {
            "popups_detected": 0,
            "popups_closed": 0,
            "cookies_accepted": 0,
            "patterns": {}
        }
        
        # 통계 로드
        self._load_stats()
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            # 통계 로드
            self._load_stats()
            
            # 패턴 로드
            self.patterns = self._load_patterns()
            
            logger.info(f"팝업 처리기 초기화 완료: {len(self.patterns)} 패턴 로드됨")
            return True
        except Exception as e:
            logger.error(f"팝업 처리기 초기화 실패: {str(e)}")
            return False
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        try:
            # 통계 저장
            self._save_stats()
            
            return True
        except Exception as e:
            logger.error(f"팝업 처리기 종료 중 오류: {str(e)}")
            return False
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        try:
            self.config.update(config)
            return True
        except Exception as e:
            logger.error(f"팝업 처리기 설정 중 오류: {str(e)}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return [
            "detect_popup",
            "close_popup",
            "handle_cookie_notice",
            "add_pattern",
            "remove_pattern",
            "list_patterns",
            "get_stats",
            "reset_stats",
            "is_domain_allowed",
            "add_whitelist_domain",
            "add_blacklist_domain",
            "handle_all_interruptions"
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """플러그인 액션 실행"""
        try:
            if action not in self.get_capabilities():
                raise ValueError(f"지원하지 않는 액션: {action}")
            
            # 플러그인이 비활성화된 경우 (enabled=False)
            if not self.config.get("enabled", True) and action not in [
                "list_patterns", "get_stats", "is_domain_allowed", 
                "add_whitelist_domain", "add_blacklist_domain"
            ]:
                logger.warning("팝업 처리기가 비활성화되어 있습니다.")
                return {"status": "disabled", "message": "팝업 처리기가 비활성화되어 있습니다."}
            
            # 메서드 호출
            method = getattr(self, action)
            return method(**params)
            
        except Exception as e:
            logger.error(f"액션 실행 중 오류: {action} - {str(e)}")
            raise
    
    def _load_stats(self) -> bool:
        """통계 데이터 로드"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                return True
            return False
        except Exception as e:
            logger.error(f"통계 로드 중 오류: {str(e)}")
            return False
    
    def _save_stats(self) -> bool:
        """통계 데이터 저장"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"통계 저장 중 오류: {str(e)}")
            return False
    
    def _load_patterns(self) -> List[Dict[str, Any]]:
        """팝업 처리 패턴 로드"""
        patterns = []
        
        try:
            for filename in os.listdir(self.patterns_dir):
                if filename.endswith('.json') and filename != 'stats.json':
                    try:
                        filepath = os.path.join(self.patterns_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            pattern = json.load(f)
                        
                        patterns.append(pattern)
                    except Exception as e:
                        logger.error(f"패턴 파일 로드 중 오류: {filename} - {str(e)}")
            
            return patterns
        except Exception as e:
            logger.error(f"패턴 로드 중 오류: {str(e)}")
            return []
    
    def _save_pattern(self, pattern: Dict[str, Any]) -> bool:
        """팝업 처리 패턴 저장"""
        try:
            pattern_id = pattern.get("id")
            if not pattern_id:
                pattern_id = f"pattern_{int(time.time())}"
                pattern["id"] = pattern_id
            
            filename = f"{pattern_id}.json"
            filepath = os.path.join(self.patterns_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(pattern, f, ensure_ascii=False, indent=2)
            
            # 패턴 목록 업데이트
            self.patterns = self._load_patterns()
            
            return True
        except Exception as e:
            logger.error(f"패턴 저장 중 오류: {str(e)}")
            return False
    
    def _is_domain_allowed(self, url: str) -> bool:
        """URL의 도메인이 허용되는지 확인"""
        try:
            domain = urlparse(url).netloc
            
            # 블랙리스트 확인
            for blacklisted in self.config.get("blacklist_domains", []):
                if domain == blacklisted or (blacklisted.startswith('*.') and domain.endswith(blacklisted[1:])):
                    logger.debug(f"블랙리스트 도메인: {domain}")
                    return False
            
            # 화이트리스트가 비어있으면 모든 도메인 허용
            whitelist = self.config.get("whitelist_domains", [])
            if not whitelist:
                return True
            
            # 화이트리스트 확인
            for whitelisted in whitelist:
                if domain == whitelisted or (whitelisted.startswith('*.') and domain.endswith(whitelisted[1:])):
                    return True
            
            # 화이트리스트에 없음
            logger.debug(f"화이트리스트에 없는 도메인: {domain}")
            return False
            
        except Exception as e:
            logger.error(f"도메인 확인 중 오류: {str(e)}")
            return True  # 오류 시 차단하지 않음
    
    def _update_pattern_stats(self, pattern_id: str, success: bool) -> None:
        """패턴 사용 통계 업데이트"""
        if pattern_id not in self.stats["patterns"]:
            self.stats["patterns"][pattern_id] = {
                "uses": 0,
                "successes": 0,
                "failures": 0,
                "last_used": None
            }
        
        self.stats["patterns"][pattern_id]["uses"] += 1
        if success:
            self.stats["patterns"][pattern_id]["successes"] += 1
        else:
            self.stats["patterns"][pattern_id]["failures"] += 1
        
        self.stats["patterns"][pattern_id]["last_used"] = datetime.now().isoformat()
        
        # 주기적으로 통계 저장
        if self.stats["popups_detected"] % 10 == 0:
            self._save_stats()
    
    def detect_popup(self, **kwargs) -> Dict[str, Any]:
        """팝업 감지"""
        # 페이지 객체
        page = kwargs.get("page")
        if not page:
            raise ValueError("페이지 객체가 필요합니다")
        
        # URL 확인
        url = page.url
        if not self._is_domain_allowed(url):
            return {"detected": False, "message": "도메인이 허용되지 않습니다"}
        
        try:
            # 팝업 셀렉터 목록
            popup_selectors = kwargs.get("popup_selectors", self.config.get("common_popup_selectors", []))
            
            # 쿠키 공지 셀렉터 목록
            cookie_selectors = kwargs.get("cookie_selectors", self.config.get("cookie_notice_selectors", []))
            
            # 모든 셀렉터 통합
            all_selectors = popup_selectors + cookie_selectors
            
            # 팝업 감지
            for selector in all_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        # 팝업 타입 결정
                        popup_type = "cookie_notice" if selector in cookie_selectors else "popup"
                        
                        # 통계 업데이트
                        self.stats["popups_detected"] += 1
                        
                        return {
                            "detected": True,
                            "type": popup_type,
                            "selector": selector,
                            "url": url
                        }
                except Exception as e:
                    logger.debug(f"셀렉터 감지 중 오류: {selector} - {str(e)}")
            
            # 커스텀 패턴 확인
            for pattern in self.patterns:
                if not pattern.get("enabled", True):
                    continue
                
                # 도메인 확인
                pattern_domains = pattern.get("domains", [])
                if pattern_domains:
                    domain_match = False
                    domain = urlparse(url).netloc
                    
                    for pattern_domain in pattern_domains:
                        if domain == pattern_domain or (pattern_domain.startswith('*.') and domain.endswith(pattern_domain[1:])):
                            domain_match = True
                            break
                    
                    if not domain_match:
                        continue
                
                # 패턴 셀렉터 확인
                pattern_selector = pattern.get("selector")
                if not pattern_selector:
                    continue
                
                try:
                    element = page.query_selector(pattern_selector)
                    if element and element.is_visible():
                        # 패턴 타입
                        pattern_type = pattern.get("type", "popup")
                        
                        # 통계 업데이트
                        self.stats["popups_detected"] += 1
                        self._update_pattern_stats(pattern["id"], True)
                        
                        return {
                            "detected": True,
                            "type": pattern_type,
                            "selector": pattern_selector,
                            "pattern_id": pattern["id"],
                            "pattern_name": pattern.get("name", "Custom Pattern"),
                            "url": url
                        }
                except Exception as e:
                    logger.debug(f"커스텀 패턴 감지 중 오류: {pattern_selector} - {str(e)}")
                    self._update_pattern_stats(pattern["id"], False)
            
            # 감지된 팝업 없음
            return {"detected": False}
            
        except Exception as e:
            logger.error(f"팝업 감지 중 오류: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    def close_popup(self, **kwargs) -> Dict[str, Any]:
        """팝업 닫기"""
        # 페이지 객체
        page = kwargs.get("page")
        if not page:
            raise ValueError("페이지 객체가 필요합니다")
        
        # 팝업 셀렉터
        popup_selector = kwargs.get("popup_selector")
        
        # URL 확인
        url = page.url
        if not self._is_domain_allowed(url):
            return {"success": False, "message": "도메인이 허용되지 않습니다"}
        
        try:
            # 닫기 셀렉터 목록
            close_selectors = kwargs.get("close_selectors", self.config.get("close_selectors", []))
            
            # 특정 패턴에 대한 닫기 셀렉터
            pattern_id = kwargs.get("pattern_id")
            
            if pattern_id:
                # 패턴 찾기
                pattern = next((p for p in self.patterns if p.get("id") == pattern_id), None)
                if pattern:
                    # 패턴의 닫기 셀렉터 추가
                    pattern_close_selector = pattern.get("close_selector")
                    if pattern_close_selector:
                        close_selectors = [pattern_close_selector] + close_selectors
                    
                    # 패턴의 닫기 작업 수행
                    pattern_action = pattern.get("action")
                    if pattern_action == "close":
                        # 이미 기본 닫기 동작을 수행할 것임
                        pass
                    elif pattern_action == "accept":
                        # 수락 버튼 클릭
                        accept_selectors = pattern.get("accept_selectors", [])
                        for selector in accept_selectors:
                            try:
                                element = page.query_selector(selector)
                                if element and element.is_visible():
                                    element.click()
                                    
                                    # 통계 업데이트
                                    self.stats["popups_closed"] += 1
                                    self._update_pattern_stats(pattern_id, True)
                                    
                                    return {
                                        "success": True,
                                        "action": "accept",
                                        "selector": selector,
                                        "pattern_id": pattern_id
                                    }
                            except Exception as e:
                                logger.debug(f"패턴 수락 버튼 클릭 중 오류: {selector} - {str(e)}")
                    elif pattern_action == "escape":
                        # ESC 키 누르기
                        try:
                            page.press("body", "Escape")
                            
                            # 통계 업데이트
                            self.stats["popups_closed"] += 1
                            self._update_pattern_stats(pattern_id, True)
                            
                            return {
                                "success": True,
                                "action": "escape",
                                "pattern_id": pattern_id
                            }
                        except Exception as e:
                            logger.debug(f"ESC 키 누르기 중 오류: {str(e)}")
                    elif pattern_action == "click_outside":
                        # 팝업 외부 클릭
                        try:
                            # 팝업 요소 찾기
                            if popup_selector:
                                popup_element = page.query_selector(popup_selector)
                                if popup_element and popup_element.is_visible():
                                    # 팝업 위치와 크기 가져오기
                                    bounds = popup_element.bounding_box()
                                    
                                    # 화면 크기 가져오기
                                    viewport_size = page.viewport_size
                                    
                                    # 팝업 외부 좌표 계산
                                    outside_x = bounds["x"] - 10
                                    if outside_x < 0:
                                        outside_x = bounds["x"] + bounds["width"] + 10
                                        if outside_x >= viewport_size["width"]:
                                            outside_x = viewport_size["width"] // 2
                                    
                                    outside_y = bounds["y"] - 10
                                    if outside_y < 0:
                                        outside_y = bounds["y"] + bounds["height"] + 10
                                        if outside_y >= viewport_size["height"]:
                                            outside_y = viewport_size["height"] // 2
                                    
                                    # 외부 클릭
                                    page.mouse.click(outside_x, outside_y)
                                    
                                    # 통계 업데이트
                                    self.stats["popups_closed"] += 1
                                    self._update_pattern_stats(pattern_id, True)
                                    
                                    return {
                                        "success": True,
                                        "action": "click_outside",
                                        "coordinates": {"x": outside_x, "y": outside_y},
                                        "pattern_id": pattern_id
                                    }
                        except Exception as e:
                            logger.debug(f"팝업 외부 클릭 중 오류: {str(e)}")
                    elif pattern_action == "custom_js":
                        # 커스텀 JavaScript 실행
                        try:
                            js_code = pattern.get("js_code", "")
                            if js_code:
                                page.evaluate(js_code)
                                
                                # 통계 업데이트
                                self.stats["popups_closed"] += 1
                                self._update_pattern_stats(pattern_id, True)
                                
                                return {
                                    "success": True,
                                    "action": "custom_js",
                                    "pattern_id": pattern_id
                                }
                        except Exception as e:
                            logger.debug(f"커스텀 JavaScript 실행 중 오류: {str(e)}")
            
            # 닫기 버튼 찾기
            for selector in close_selectors:
                for attempt in range(self.config.get("max_attempts", 3)):
                    try:
                        element = page.query_selector(selector)
                        if element and element.is_visible():
                            element.click()
                            
                            # 통계 업데이트
                            self.stats["popups_closed"] += 1
                            if pattern_id:
                                self._update_pattern_stats(pattern_id, True)
                            
                            return {
                                "success": True,
                                "action": "click",
                                "selector": selector,
                                "pattern_id": pattern_id if pattern_id else None
                            }
                    except Exception as e:
                        logger.debug(f"닫기 버튼 클릭 중 오류 (시도 {attempt+1}): {selector} - {str(e)}")
                        time.sleep(self.config.get("attempt_delay", 0.5))
            
            # 닫기 버튼을 찾지 못한 경우, ESC 키 시도
            try:
                page.press("body", "Escape")
                
                # ESC 키가 작동했는지 확인 (팝업이 사라졌는지)
                if popup_selector:
                    element = page.query_selector(popup_selector)
                    if not element or not element.is_visible():
                        # 통계 업데이트
                        self.stats["popups_closed"] += 1
                        if pattern_id:
                            self._update_pattern_stats(pattern_id, True)
                        
                        return {
                            "success": True,
                            "action": "escape",
                            "pattern_id": pattern_id if pattern_id else None
                        }
            except Exception as e:
                logger.debug(f"ESC 키 누르기 중 오류: {str(e)}")
            
            # 모든 방법이 실패
            if pattern_id:
                self._update_pattern_stats(pattern_id, False)
            
            return {
                "success": False,
                "message": "팝업을 닫을 수 없습니다"
            }
            
        except Exception as e:
            logger.error(f"팝업 닫기 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def handle_cookie_notice(self, **kwargs) -> Dict[str, Any]:
        """쿠키 동의 공지 처리"""
        # 페이지 객체
        page = kwargs.get("page")
        if not page:
            raise ValueError("페이지 객체가 필요합니다")
        
        # URL 확인
        url = page.url
        if not self._is_domain_allowed(url):
            return {"success": False, "message": "도메인이 허용되지 않습니다"}
        
        try:
            # 쿠키 공지 셀렉터 목록
            cookie_selectors = kwargs.get("cookie_selectors", self.config.get("cookie_notice_selectors", []))
            
            # 수락 버튼 셀렉터 목록
            accept_selectors = kwargs.get("accept_selectors", self.config.get("accept_cookies_selectors", []))
            
            # 쿠키 공지 찾기
            cookie_notice = None
            cookie_selector = None
            
            for selector in cookie_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        cookie_notice = element
                        cookie_selector = selector
                        break
                except Exception as e:
                    logger.debug(f"쿠키 공지 감지 중 오류: {selector} - {str(e)}")
            
            if not cookie_notice:
                return {"success": False, "message": "쿠키 공지를 찾을 수 없습니다"}
            
            # 수락 버튼 찾기
            for selector in accept_selectors:
                for attempt in range(self.config.get("max_attempts", 3)):
                    try:
                        element = page.query_selector(selector)
                        if element and element.is_visible():
                            element.click()
                            
                            # 통계 업데이트
                            self.stats["cookies_accepted"] += 1
                            
                            return {
                                "success": True,
                                "action": "accept",
                                "selector": selector
                            }
                    except Exception as e:
                        logger.debug(f"수락 버튼 클릭 중 오류 (시도 {attempt+1}): {selector} - {str(e)}")
                        time.sleep(self.config.get("attempt_delay", 0.5))
            
            # 수락 버튼을 찾지 못한 경우, 닫기 시도
            close_result = self.close_popup(
                page=page,
                popup_selector=cookie_selector
            )
            
            if close_result.get("success", False):
                # 통계 업데이트
                self.stats["cookies_accepted"] += 1
                
                return {
                    "success": True,
                    "action": "close",
                    "selector": close_result.get("selector")
                }
            
            return {
                "success": False,
                "message": "쿠키 공지를 처리할 수 없습니다"
            }
            
        except Exception as e:
            logger.error(f"쿠키 공지 처리 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_pattern(self, **kwargs) -> Dict[str, Any]:
        """팝업 처리 패턴 추가"""
        try:
            # 패턴 데이터
            pattern = kwargs.get("pattern", {})
            
            # 필수 필드 확인
            required_fields = ["type", "selector"]
            for field in required_fields:
                if field not in pattern:
                    raise ValueError(f"패턴에 필수 필드가 없습니다: {field}")
            
            # 패턴 ID 생성 (없는 경우)
            if "id" not in pattern:
                pattern["id"] = f"pattern_{int(time.time())}"
            
            # 패턴 이름 생성 (없는 경우)
            if "name" not in pattern:
                pattern["name"] = f"패턴 {pattern['id']}"
            
            # 패턴 활성화 상태 설정 (없는 경우)
            if "enabled" not in pattern:
                pattern["enabled"] = True
            
            # 생성 시간 설정
            pattern["created_at"] = datetime.now().isoformat()
            
            # 패턴 저장
            success = self._save_pattern(pattern)
            
            if success:
                return {
                    "success": True,
                    "pattern_id": pattern["id"],
                    "message": "패턴이 성공적으로 추가되었습니다"
                }
            else:
                return {
                    "success": False,
                    "message": "패턴 저장 중 오류가 발생했습니다"
                }
            
        except Exception as e:
            logger.error(f"패턴 추가 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def remove_pattern(self, **kwargs) -> Dict[str, Any]:
        """팝업 처리 패턴 제거"""
        try:
            # 패턴 ID
            pattern_id = kwargs.get("pattern_id")
            
            if not pattern_id:
                raise ValueError("패턴 ID가 필요합니다")
            
            # 패턴 파일 경로
            pattern_file = os.path.join(self.patterns_dir, f"{pattern_id}.json")
            
            # 파일 존재 확인
            if not os.path.exists(pattern_file):
                return {
                    "success": False,
                    "message": f"패턴을 찾을 수 없습니다: {pattern_id}"
                }
            
            # 파일 삭제
            os.remove(pattern_file)
            
            # 패턴 목록 업데이트
            self.patterns = self._load_patterns()
            
            # 통계에서 패턴 제거
            if pattern_id in self.stats["patterns"]:
                del self.stats["patterns"][pattern_id]
                self._save_stats()
            
            return {
                "success": True,
                "message": f"패턴이 성공적으로 제거되었습니다: {pattern_id}"
            }
            
        except Exception as e:
            logger.error(f"패턴 제거 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def list_patterns(self, **kwargs) -> Dict[str, Any]:
        """팝업 처리 패턴 목록 조회"""
        try:
            # 필터 옵션
            pattern_type = kwargs.get("type")
            enabled_only = kwargs.get("enabled_only", False)
            
            # 패턴 필터링
            filtered_patterns = []
            
            for pattern in self.patterns:
                # 타입 필터
                if pattern_type and pattern.get("type") != pattern_type:
                    continue
                
                # 활성화 상태 필터
                if enabled_only and not pattern.get("enabled", True):
                    continue
                
                # 패턴 통계 추가
                pattern_copy = pattern.copy()
                pattern_id = pattern.get("id")
                
                if pattern_id in self.stats["patterns"]:
                    pattern_copy["stats"] = self.stats["patterns"][pattern_id]
                
                filtered_patterns.append(pattern_copy)
            
            return {
                "patterns": filtered_patterns,
                "count": len(filtered_patterns),
                "total_patterns": len(self.patterns)
            }
            
        except Exception as e:
            logger.error(f"패턴 목록 조회 중 오류: {str(e)}")
            return {"patterns": [], "error": str(e)}
    
    def get_stats(self, **kwargs) -> Dict[str, Any]:
        """팝업 처리 통계 조회"""
        try:
            # 필터 옵션
            pattern_id = kwargs.get("pattern_id")
            
            # 특정 패턴의 통계만 조회
            if pattern_id:
                if pattern_id in self.stats["patterns"]:
                    return {"pattern_stats": self.stats["patterns"][pattern_id]}
                else:
                    return {"pattern_stats": None, "message": f"패턴 통계를 찾을 수 없습니다: {pattern_id}"}
            
            # 전체 통계 반환
            return self.stats
            
        except Exception as e:
            logger.error(f"통계 조회 중 오류: {str(e)}")
            return {"error": str(e)}
    
    def reset_stats(self, **kwargs) -> Dict[str, Any]:
        """팝업 처리 통계 초기화"""
        try:
            # 초기화 옵션
            pattern_id = kwargs.get("pattern_id")
            
            if pattern_id:
                # 특정 패턴의 통계만 초기화
                if pattern_id in self.stats["patterns"]:
                    self.stats["patterns"][pattern_id] = {
                        "uses": 0,
                        "successes": 0,
                        "failures": 0,
                        "last_used": None
                    }
                    
                    self._save_stats()
                    
                    return {
                        "success": True,
                        "message": f"패턴 통계가 초기화되었습니다: {pattern_id}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"패턴 통계를 찾을 수 없습니다: {pattern_id}"
                    }
            else:
                # 모든 통계 초기화
                self.stats = {
                    "popups_detected": 0,
                    "popups_closed": 0,
                    "cookies_accepted": 0,
                    "patterns": {}
                }
                
                self._save_stats()
                
                return {
                    "success": True,
                    "message": "모든 통계가 초기화되었습니다"
                }
            
        except Exception as e:
            logger.error(f"통계 초기화 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def is_domain_allowed(self, **kwargs) -> Dict[str, bool]:
        """URL의 도메인이 허용되는지 확인"""
        try:
            url = kwargs.get("url")
            
            if not url:
                raise ValueError("URL이 필요합니다")
            
            allowed = self._is_domain_allowed(url)
            
            return {"allowed": allowed}
            
        except Exception as e:
            logger.error(f"도메인 확인 중 오류: {str(e)}")
            return {"allowed": True, "error": str(e)}  # 오류 시 차단하지 않음
    
    def add_whitelist_domain(self, **kwargs) -> Dict[str, Any]:
        """화이트리스트에 도메인 추가"""
        try:
            domain = kwargs.get("domain")
            
            if not domain:
                raise ValueError("도메인이 필요합니다")
            
            # 화이트리스트 가져오기
            whitelist = self.config.get("whitelist_domains", [])
            
            # 이미 있는지 확인
            if domain in whitelist:
                return {
                    "success": True,
                    "message": f"도메인이 이미 화이트리스트에 있습니다: {domain}"
                }
            
            # 도메인 추가
            whitelist.append(domain)
            self.config["whitelist_domains"] = whitelist
            
            return {
                "success": True,
                "message": f"도메인이 화이트리스트에 추가되었습니다: {domain}"
            }
            
        except Exception as e:
            logger.error(f"화이트리스트 도메인 추가 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_blacklist_domain(self, **kwargs) -> Dict[str, Any]:
        """블랙리스트에 도메인 추가"""
        try:
            domain = kwargs.get("domain")
            
            if not domain:
                raise ValueError("도메인이 필요합니다")
            
            # 블랙리스트 가져오기
            blacklist = self.config.get("blacklist_domains", [])
            
            # 이미 있는지 확인
            if domain in blacklist:
                return {
                    "success": True,
                    "message": f"도메인이 이미 블랙리스트에 있습니다: {domain}"
                }
            
            # 도메인 추가
            blacklist.append(domain)
            self.config["blacklist_domains"] = blacklist
            
            return {
                "success": True,
                "message": f"도메인이 블랙리스트에 추가되었습니다: {domain}"
            }
            
        except Exception as e:
            logger.error(f"블랙리스트 도메인 추가 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def handle_all_interruptions(self, **kwargs) -> Dict[str, Any]:
        """모든 인터럽션 자동 처리"""
        # 페이지 객체
        page = kwargs.get("page")
        if not page:
            raise ValueError("페이지 객체가 필요합니다")
        
        # URL 확인
        url = page.url
        if not self._is_domain_allowed(url):
            return {"success": False, "message": "도메인이 허용되지 않습니다"}
        
        try:
            # 인터럽션 감지
            detection = self.detect_popup(page=page)
            
            if not detection.get("detected", False):
                return {"success": True, "message": "인터럽션이 감지되지 않았습니다"}
            
            # 인터럽션 타입에 따라 처리
            interruption_type = detection.get("type")
            selector = detection.get("selector")
            pattern_id = detection.get("pattern_id")
            
            if interruption_type == "cookie_notice":
                # 쿠키 공지 처리
                result = self.handle_cookie_notice(page=page)
                
                if result.get("success", False):
                    return {
                        "success": True,
                        "action": "cookie_accepted",
                        "selector": selector
                    }
            
            # 일반 팝업 처리
            result = self.close_popup(
                page=page,
                popup_selector=selector,
                pattern_id=pattern_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"인터럽션 처리 중 오류: {str(e)}")
            return {"success": False, "error": str(e)}