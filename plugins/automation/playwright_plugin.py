 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - Playwright 자동화 플러그인
웹 브라우저 자동화를 위한 Playwright 기반 플러그인
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import greenlet  # 추가
from PyQt5.QtWidgets import QApplication  # 추가

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
from core.plugin_manager import PluginInterface
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG

logger = logging.getLogger(__name__)

class PlaywrightWorker(QObject):
    """메인 스레드에서 Playwright 작업을 실행하기 위한 작업자 클래스"""
    
    # 결과 및 오류 시그널
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __del__(self):
        # 연결된 모든 신호 연결 해제
        try:
            # Qt의 메인 스레드에서 실행 중인지 확인
            from PyQt5.QtCore import QThread
            if QThread.currentThread() == QApplication.instance().thread():
                self.result_signal.disconnect()
                self.error_signal.disconnect()
        except Exception:
            pass  # 오류 무시

    def __init__(self, playwright_plugin):
        super().__init__()
        self.playwright_plugin = playwright_plugin
    
    @pyqtSlot(str, object)
    def execute_action(self, action, params):
        """Playwright 액션 실행 (메인 스레드에서 호출됨)"""
        try:
            # 플러그인 내부 메서드 직접 호출
            method = getattr(self.playwright_plugin, "_" + action)
            result = method(**params)
            self.result_signal.emit(result)
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(error_details)

class PlaywrightPlugin(PluginInterface):
    """Playwright 기반 웹 브라우저 자동화 플러그인"""
    
    plugin_type = "automation"
    plugin_name = "playwright"
    plugin_version = "0.1.0"
    plugin_description = "Playwright 기반 웹 브라우저 자동화 플러그인"
    
    def __init__(self):
        super().__init__()
        self.playwright = None
        self.browser = None
        self.contexts = {}
        self.pages = {}
        self.screenshots_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "screenshots")
        self.downloads_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "downloads")
        self.current_context_id = None
        self.current_page_id = None
        self.interruption_handler = None
        self.browsers_by_thread = {}
        self.contexts_by_thread = {}
        self.pages_by_thread = {}
        self._playwright_greenlet = None
        
        # 메인 스레드에서 실행할 작업자 생성
        self.worker = PlaywrightWorker(self)
        
        # 설정 기본값
        self.config = {
            "browser_type": "chromium",
            "headless": False,
            "slow_mo": 50,
            "viewport_width": 1280,
            "viewport_height": 720,
            "user_agent": "",
            "timeout": 30000,
            "ignore_https_errors": True,
            "proxy": None,
            "auto_handle_interruptions": True,
            "capture_error_screenshots": True
        }
        
        # 스크린샷 디렉토리 생성
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # 다운로드 디렉토리 생성
        os.makedirs(self.downloads_dir, exist_ok=True)
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            # 메인 스레드에서 Playwright 초기화
            self.playwright = sync_playwright().start()
            
            # 현재 greenlet을 저장
            self._playwright_greenlet = greenlet.getcurrent()
            
            logger.info("Playwright 초기화됨")
            return True
        except Exception as e:
            logger.error(f"Playwright 초기화 실패: {str(e)}")
            return False

    def _ensure_same_greenlet(self):
        """현재 greenlet이 Playwright를 초기화한 greenlet과 동일한지 확인"""
        current = greenlet.getcurrent()
        if current != self._playwright_greenlet:
            raise RuntimeError(f"Playwright는 동일한 greenlet에서 실행되어야 합니다. 현재: {current}, 예상: {self._playwright_greenlet}")
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        try:
            # 모든 컨텍스트 닫기
            for context_id, context in list(self.contexts.items()):
                try:
                    context.close()
                except Exception as e:
                    logger.error(f"컨텍스트 닫기 실패: {context_id} - {str(e)}")
            
            # 브라우저 닫기
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.error(f"브라우저 닫기 실패: {str(e)}")
            
            # Playwright 종료
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.error(f"Playwright 종료 실패: {str(e)}")
            
            logger.info("Playwright 종료됨")
            return True
        except Exception as e:
            logger.error(f"Playwright 종료 중 오류: {str(e)}")
            return False
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        try:
            self.config.update(config)
            
            # 브라우저가 이미 실행 중이면 재시작
            if self.browser:
                self.restart_browser()
            
            return True
        except Exception as e:
            logger.error(f"Playwright 설정 중 오류: {str(e)}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return [
            "launch_browser",
            "create_context",
            "new_page",
            "close_page",
            "close_context",
            "close_browser",
            "goto",
            "wait_for_load",
            "wait_for_selector",
            "click",
            "fill",
            "press_key",
            "select_option",
            "check",
            "uncheck",
            "screenshot",
            "get_text",
            "get_attribute",
            "evaluate",
            "get_url",
            "get_title",
            "reload",
            "go_back",
            "go_forward",
            "handle_dialog",
            "wait_for_download",
            "wait_for_navigation",
            "handle_interruptions"
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """플러그인 액션 실행"""
        try:
            if action not in self.get_capabilities():
                raise ValueError(f"지원하지 않는 액션: {action}")
            
            # 메서드 호출
            method = getattr(self, action)
            return method(**params)
            
        except Exception as e:
            logger.error(f"액션 실행 중 오류: {action} - {str(e)}")
            
            # 오류 발생 시 스크린샷 캡처
            if self.config.get("capture_error_screenshots", True):
                self.capture_error_screenshot(action)
            
            raise
    
    def capture_error_screenshot(self, action: str) -> Optional[str]:
        """오류 발생 시 스크린샷 캡처"""
        try:
            if not self.current_page_id or self.current_page_id not in self.pages:
                return None
            
            page = self.pages[self.current_page_id]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{action}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            page.screenshot(path=filepath)
            logger.info(f"오류 스크린샷 저장됨: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"오류 스크린샷 캡처 실패: {str(e)}")
            return None
    
    def set_interruption_handler(self, handler: Any) -> bool:
        """인터럽션 핸들러 설정"""
        self.interruption_handler = handler
        return True
    
    def _handle_interruptions(self, page: Page) -> bool:
        """인터럽션 처리"""
        if not self.config.get("auto_handle_interruptions", True) or not self.interruption_handler:
            return False
        
        try:
            return self.interruption_handler.check_and_handle(page)
        except Exception as e:
            logger.error(f"인터럽션 처리 중 오류: {str(e)}")
            return False
    
    def _get_browser_instance(self) -> Browser:
        """브라우저 인스턴스 반환 (없으면 시작)"""
        if not self.browser:
            self.launch_browser()
        return self.browser
    
    def _get_current_context(self) -> BrowserContext:
        """현재 컨텍스트 반환"""
        if not self.current_context_id or self.current_context_id not in self.contexts:
            raise ValueError("활성화된 컨텍스트가 없습니다")
        
        return self.contexts[self.current_context_id]
    
    def _get_current_page(self) -> Page:
        """현재 페이지 반환"""
        if not self.current_page_id or self.current_page_id not in self.pages:
            raise ValueError("활성화된 페이지가 없습니다")
        
        return self.pages[self.current_page_id]
    
    

    def _launch_browser(self, **kwargs):
        """브라우저 시작 (내부 메서드)"""
        # 기존 브라우저 닫기
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.warning(f"기존 브라우저 닫기 실패: {str(e)}")
        
        # 설정 파라미터
        browser_type = kwargs.get("browser_type", self.config.get("browser_type", "chromium"))
        headless = kwargs.get("headless", self.config.get("headless", False))
        slow_mo = kwargs.get("slow_mo", self.config.get("slow_mo", 50))
        
        # 브라우저 실행 옵션
        browser_args = kwargs.get("browser_args", [])
        
        # ignore_https_errors 파라미터 제거 (문제가 되는 파라미터)
        if "ignore_https_errors" in kwargs:
            del kwargs["ignore_https_errors"]
        
        # 브라우저 타입에 따른 실행
        launch_options = {
            "headless": False,
            "slow_mo": slow_mo,
            "args": browser_args
        }
        
        if browser_type == "chromium":
            self.browser = self.playwright.chromium.launch(**launch_options)
        elif browser_type == "firefox":
            self.browser = self.playwright.firefox.launch(**launch_options)
        elif browser_type == "webkit":
            self.browser = self.playwright.webkit.launch(**launch_options)
        else:
            raise ValueError(f"지원하지 않는 브라우저 타입: {browser_type}")
        
        logger.info(f"브라우저 시작됨: {browser_type} (headless: {headless})")
        return "browser_started"

    def launch_browser(self, **kwargs):
        """브라우저 시작 (스레드 안전 래퍼)"""
        try:
            import threading
            logger.debug(f"launch_browser 호출됨, 스레드 ID: {threading.get_ident()}")
            
            # QApplication 인스턴스 확인
            from PyQt5.QtWidgets import QApplication
            if QApplication.instance() is not None:
                # 이벤트를 기다리기 위한 이벤트 루프 생성
                from PyQt5.QtCore import QEventLoop, QTimer
                loop = QEventLoop()
                result = [None]
                error = [None]
                
                # 결과 핸들러
                def handle_result(res):
                    result[0] = res
                    loop.quit()
                
                # 오류 핸들러
                def handle_error(err):
                    error[0] = err
                    loop.quit()
                
                # 신호 연결
                self.worker.result_signal.connect(handle_result)
                self.worker.error_signal.connect(handle_error)
                
                # 메인 스레드에서 실행
                QMetaObject.invokeMethod(
                    self.worker, 
                    "execute_action",
                    Qt.QueuedConnection,
                    Q_ARG(str, "launch_browser"),
                    Q_ARG(object, kwargs)
                )
                
                # 타임아웃 설정 (30초)
                QTimer.singleShot(30000, loop.quit)
                
                # 결과 대기
                loop.exec_()
                
                # 신호 연결 해제
                self.worker.result_signal.disconnect(handle_result)
                self.worker.error_signal.disconnect(handle_error)
                
                # 오류 확인
                if error[0] is not None:
                    raise Exception(error[0])
                
                return result[0]
            else:
                # QApplication이 없는 경우 (예: CLI 모드)는 직접 실행
                logger.warning("QApplication이 없어 동기 모드로 실행합니다.")
                return self._launch_browser(**kwargs)
        except Exception as e:
            logger.error(f"브라우저 시작 중 오류: {str(e)}")
            raise
    

    def restart_browser(self, **kwargs) -> str:
        """브라우저 재시작"""
        self.close_browser()
        return self.launch_browser(**kwargs)
    
    def create_context(self, **kwargs):
        """브라우저 컨텍스트 생성"""
        browser = self._get_browser_instance()
        
        # 설정 파라미터
        viewport_width = kwargs.get("viewport_width", self.config.get("viewport_width", 1280))
        viewport_height = kwargs.get("viewport_height", self.config.get("viewport_height", 720))
        user_agent = kwargs.get("user_agent", self.config.get("user_agent", ""))
        locale = kwargs.get("locale", "ko-KR")
        timezone_id = kwargs.get("timezone_id", "Asia/Seoul")
        
        # 기기 설정
        device_name = kwargs.get("device_name", "")
        
        # 저장 경로
        downloads_path = kwargs.get("downloads_path", self.downloads_dir)
        
        # 프록시 설정
        proxy = kwargs.get("proxy", self.config.get("proxy"))
        
        # 컨텍스트 옵션
        context_options = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "locale": locale,
            "timezone_id": timezone_id,
            "accept_downloads": True,
            "ignore_https_errors": kwargs.get("ignore_https_errors", 
                                getattr(self, "_ignore_https_errors", 
                                        self.config.get("ignore_https_errors", True)))
        }
        
        # 사용자 에이전트 설정
        if user_agent:
            context_options["user_agent"] = user_agent
        
        # 기기 에뮬레이션
        if device_name:
            device = self.playwright.devices.get(device_name)
            if device:
                context_options.update(device)
        
        # 다운로드 경로 설정
        if downloads_path:
            # 디렉토리 생성은 유지
            os.makedirs(downloads_path, exist_ok=True)
            
            # 'downloads_path' 매개변수 사용하지 않음 (이 부분 제거)
            # context_options["downloads_path"] = downloads_path
            
            # accept_downloads는 이미 true로 설정되어 있음
        
        # 프록시 설정
        if proxy:
            context_options["proxy"] = proxy
        
        # 컨텍스트 생성
        context = browser.new_context(**context_options)
        
        # 다운로드 이벤트 처리를 위한 이벤트 핸들러 등록
        if downloads_path:
            # 현대적인 방식으로 다운로드 처리
            def handle_download(download):
                suggested_filename = download.suggested_filename
                logger.info(f"파일 다운로드 시작: {suggested_filename}")
                download_path = os.path.join(downloads_path, suggested_filename)
                download.save_as(download_path)
                logger.info(f"파일 다운로드 완료: {download_path}")
            
            for page in context.pages:
                page.on("download", handle_download)
        
        # 컨텍스트 ID 생성 및 저장
        context_id = f"context_{len(self.contexts) + 1}_{int(time.time())}"
        self.contexts[context_id] = context
        self.current_context_id = context_id
        
        logger.info(f"브라우저 컨텍스트 생성됨: {context_id}")
        return context_id
    
    def new_page(self, **kwargs) -> str:
        """새 페이지 생성"""
        # 스레드 안전 처리를 위한 래퍼
        try:
            # QApplication이 있는 경우 메인 스레드에서 실행
            from PyQt5.QtWidgets import QApplication
            if QApplication.instance() is not None:
                # 새 작업자 스레드를 생성하고 거기서 실행
                from PyQt5.QtCore import QThread, pyqtSignal
                
                class PageCreatorThread(QThread):
                    result_signal = pyqtSignal(object)
                    error_signal = pyqtSignal(str)
                    
                    def __init__(self, plugin, params):
                        super().__init__()
                        self.plugin = plugin
                        self.params = params
                    
                    def run(self):
                        try:
                            # 이 스레드에서 새로운 sync_playwright 인스턴스 생성
                            with sync_playwright() as p:
                                # 브라우저 타입 결정
                                browser_type = self.params.get("browser_type", self.plugin.config.get("browser_type", "chromium"))
                                headless = self.params.get("headless", self.plugin.config.get("headless", False))
                                
                                # 브라우저 실행
                                if browser_type == "chromium":
                                    browser = p.chromium.launch(headless=headless)
                                elif browser_type == "firefox":
                                    browser = p.firefox.launch(headless=headless)
                                elif browser_type == "webkit":
                                    browser = p.webkit.launch(headless=headless)
                                
                                # 컨텍스트 생성
                                context = browser.new_context()
                                
                                # 페이지 생성
                                page = context.new_page()
                                
                                # 결과 반환 (페이지와 컨텍스트 ID 생성)
                                page_id = f"page_{int(time.time())}"
                                context_id = f"context_{int(time.time())}"
                                
                                # 이 스레드에서 생성된 객체를 저장
                                self.plugin.browsers_by_thread[self.currentThreadId()] = browser
                                self.plugin.contexts_by_thread[context_id] = context
                                self.plugin.pages_by_thread[page_id] = page
                                
                                self.result_signal.emit((page_id, context_id))
                        except Exception as e:
                            import traceback
                            self.error_signal.emit(f"{str(e)}\n{traceback.format_exc()}")
                
                # 스레드 생성 및 실행
                thread = PageCreatorThread(self, kwargs)
                
                # 결과 및 오류 처리
                result = [None]
                error = [None]
                
                # 이벤트 루프
                from PyQt5.QtCore import QEventLoop
                loop = QEventLoop()
                
                # 결과 핸들러
                def handle_result(res):
                    result[0] = res
                    loop.quit()
                
                # 오류 핸들러
                def handle_error(err):
                    error[0] = err
                    loop.quit()
                
                # 신호 연결
                thread.result_signal.connect(handle_result)
                thread.error_signal.connect(handle_error)
                thread.finished.connect(loop.quit)
                
                # 스레드 시작
                thread.start()
                
                # 결과 대기
                loop.exec_()
                
                # 오류 확인
                if error[0] is not None:
                    raise Exception(error[0])
                
                # 결과 처리
                page_id, context_id = result[0]
                
                # 현재 ID 업데이트
                self.current_page_id = page_id
                self.current_context_id = context_id
                
                return page_id
            else:
                # 클래식 모드 실행
                return self._new_page(**kwargs)
        except Exception as e:
            logger.error(f"새 페이지 생성 중 오류: {str(e)}")
            raise
    
    def close_page(self, **kwargs) -> bool:
        """페이지 닫기"""
        page_id = kwargs.get("page_id", self.current_page_id)
        
        if not page_id or page_id not in self.pages:
            logger.warning(f"닫을 페이지를 찾을 수 없음: {page_id}")
            return False
        
        try:
            self.pages[page_id].close()
            del self.pages[page_id]
            
            # 현재 페이지인 경우 초기화
            if self.current_page_id == page_id:
                self.current_page_id = None if not self.pages else next(iter(self.pages))
            
            logger.info(f"페이지 닫힘: {page_id}")
            return True
            
        except Exception as e:
            logger.error(f"페이지 닫기 실패: {page_id} - {str(e)}")
            return False
    
    def close_context(self, **kwargs) -> bool:
        """컨텍스트 닫기"""
        context_id = kwargs.get("context_id", self.current_context_id)
        
        if not context_id or context_id not in self.contexts:
            logger.warning(f"닫을 컨텍스트를 찾을 수 없음: {context_id}")
            return False
        
        try:
            # 해당 컨텍스트의 모든 페이지 찾기
            pages_to_close = []
            for page_id, page in self.pages.items():
                try:
                    # 페이지가 이 컨텍스트에 속하는지 확인 (컨텍스트가 다르면 예외 발생)
                    page.url()
                    page_context = page.context
                    
                    if page_context == self.contexts[context_id]:
                        pages_to_close.append(page_id)
                except:
                    pass
            
            # 페이지 목록에서 제거
            for page_id in pages_to_close:
                del self.pages[page_id]
                
                # 현재 페이지인 경우 초기화
                if self.current_page_id == page_id:
                    self.current_page_id = None
            
            # 컨텍스트 닫기
            self.contexts[context_id].close()
            del self.contexts[context_id]
            
            # 현재 컨텍스트인 경우 초기화
            if self.current_context_id == context_id:
                self.current_context_id = None if not self.contexts else next(iter(self.contexts))
            
            logger.info(f"컨텍스트 닫힘: {context_id}")
            return True
            
        except Exception as e:
            logger.error(f"컨텍스트 닫기 실패: {context_id} - {str(e)}")
            return False
    
    def close_browser(self, **kwargs) -> bool:
        """브라우저 닫기"""
        if not self.browser:
            logger.warning("닫을 브라우저가 없음")
            return False
        
        try:
            # 모든 컨텍스트 닫기
            for context_id in list(self.contexts.keys()):
                self.close_context(context_id=context_id)
            
            # 브라우저 닫기
            self.browser.close()
            self.browser = None
            
            logger.info("브라우저 닫힘")
            return True
            
        except Exception as e:
            logger.error(f"브라우저 닫기 실패: {str(e)}")
            return False
    
    def goto(self, **kwargs) -> Dict[str, Any]:
        """URL로 이동"""
        url = kwargs.get("url")
        if not url:
            raise ValueError("URL이 지정되지 않았습니다")
        
        # 디버깅을 위한 로그 추가
        logger.info(f"goto 호출됨, 현재 페이지 ID: {self.current_page_id}")
        logger.info(f"사용 가능한 페이지 ID 목록: {list(self.pages.keys())}")
        
        page_id = kwargs.get("page_id", self.current_page_id)
        logger.info(f"사용할 페이지 ID: {page_id}")
        
        # 페이지 ID가 없거나 찾을 수 없는 경우 새 페이지 생성
        if not page_id or page_id not in self.pages:
            logger.info(f"페이지 ID {page_id}를 찾을 수 없어 새 페이지를 생성합니다")
            page_id = self.new_page(**kwargs)
            logger.info(f"새 페이지 ID: {page_id}")
        
        # 페이지 ID가 여전히 self.pages에 없는 경우 명시적인 오류 메시지
        if page_id not in self.pages:
            avail_pages = list(self.pages.keys())
            error_msg = f"페이지 ID '{page_id}'를 찾을 수 없습니다. 사용 가능한 페이지: {avail_pages}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        page = self.pages[page_id]
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        wait_until = kwargs.get("wait_until", "load")  # load, domcontentloaded, networkidle
        
        logger.info(f"URL로 이동 시작: {url}")
        
        try:
            # 페이지 이동
            response = page.goto(url, timeout=timeout, wait_until=wait_until)
            
            # 결과 반환
            result = {
                "page_id": page_id,
                "url": page.url(),
                "status": response.status if response else None,
                "success": response.ok if response else False
            }
            
            # 인터럽션 처리
            if self.config.get("auto_handle_interruptions", True):
                self._handle_interruptions(page)
            
            logger.info(f"페이지 이동 성공: {url} (페이지: {page_id})")
            return result
        except Exception as e:
            logger.error(f"페이지 이동 실패: {url} - {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def wait_for_load(self, **kwargs) -> bool:
        """페이지 로드 완료 대기"""
        page = self._get_current_page()
        
        # 파라미터 설정
        state = kwargs.get("state", "networkidle")  # load, domcontentloaded, networkidle
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        
        # 로드 대기
        page.wait_for_load_state(state, timeout=timeout)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def wait_for_selector(self, **kwargs) -> bool:
        """선택자 대기"""
        selector = kwargs.get("selector")
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        state = kwargs.get("state", "visible")  # visible, hidden, attached, detached
        
        # 선택자 대기
        page.wait_for_selector(selector, state=state, timeout=timeout)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def click(self, **kwargs) -> bool:
        """요소 클릭"""
        selector = kwargs.get("selector")
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        button = kwargs.get("button", "left")  # left, right, middle
        click_count = kwargs.get("click_count", 1)
        delay = kwargs.get("delay", 0)
        position_x = kwargs.get("position_x", None)
        position_y = kwargs.get("position_y", None)
        force = kwargs.get("force", False)
        
        # 클릭 옵션
        click_options = {
            "button": button,
            "click_count": click_count,
            "delay": delay,
            "timeout": timeout,
            "force": force
        }
        
        # 특정 위치 클릭
        if position_x is not None and position_y is not None:
            click_options["position"] = {"x": position_x, "y": position_y}
        
        # 클릭 수행
        page.click(selector, **click_options)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def fill(self, **kwargs) -> bool:
        """입력 필드 채우기"""
        selector = kwargs.get("selector")
        value = kwargs.get("value", "")
        
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        
        # 필드 채우기
        page.fill(selector, str(value), timeout=timeout)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def press_key(self, **kwargs) -> bool:
        """키 입력"""
        selector = kwargs.get("selector", "body")
        key = kwargs.get("key")
        
        if not key:
            raise ValueError("키가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        delay = kwargs.get("delay", 0)
        
        # 키 입력
        page.press(selector, key, delay=delay, timeout=timeout)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def select_option(self, **kwargs) -> List[str]:
        """셀렉트 옵션 선택"""
        selector = kwargs.get("selector")
        
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        # 값, 라벨, 인덱스 중 하나를 사용
        values = kwargs.get("values", None)
        labels = kwargs.get("labels", None)
        indexes = kwargs.get("indexes", None)
        
        if values is None and labels is None and indexes is None:
            raise ValueError("values, labels, indexes 중 하나를 지정해야 합니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        
        # 옵션 선택
        select_options = {}
        if values is not None:
            select_options["values"] = values if isinstance(values, list) else [values]
        if labels is not None:
            select_options["labels"] = labels if isinstance(labels, list) else [labels]
        if indexes is not None:
            select_options["indexes"] = indexes if isinstance(indexes, list) else [indexes]
        
        selected = page.select_option(selector, **select_options, timeout=timeout)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return selected
    
    def check(self, **kwargs) -> bool:
        """체크박스 선택"""
        selector = kwargs.get("selector")
        
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        force = kwargs.get("force", False)
        
        # 체크박스 선택
        page.check(selector, timeout=timeout, force=force)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def uncheck(self, **kwargs) -> bool:
        """체크박스 선택 해제"""
        selector = kwargs.get("selector")
        
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        force = kwargs.get("force", False)
        
        # 체크박스 선택 해제
        page.uncheck(selector, timeout=timeout, force=force)
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return True
    
    def screenshot(self, **kwargs) -> str:
        """스크린샷 캡처"""
        page = self._get_current_page()
        
        # 파라미터 설정
        selector = kwargs.get("selector", None)
        full_page = kwargs.get("full_page", False)
        path = kwargs.get("path", None)
        
        # 파일 경로 설정
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            path = os.path.join(self.screenshots_dir, filename)
        
        # 캡처 옵션
        screenshot_options = {
            "path": path,
            "full_page": full_page
        }
        
        # 특정 요소 캡처
        if selector:
            element = page.query_selector(selector)
            if not element:
                raise ValueError(f"선택자에 해당하는 요소를 찾을 수 없음: {selector}")
            
            element.screenshot(**screenshot_options)
        else:
            # 전체 페이지 캡처
            page.screenshot(**screenshot_options)
        
        logger.info(f"스크린샷 저장됨: {path}")
        return path
    
    def get_text(self, **kwargs) -> str:
        """요소 텍스트 가져오기"""
        selector = kwargs.get("selector")
        
        if not selector:
            raise ValueError("선택자가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        
        # 요소 찾기
        element = page.wait_for_selector(selector, timeout=timeout)
        if not element:
            raise ValueError(f"선택자에 해당하는 요소를 찾을 수 없음: {selector}")
        
        # 텍스트 가져오기
        return element.inner_text()
    
    def get_attribute(self, **kwargs) -> str:
        """요소 속성 가져오기"""
        selector = kwargs.get("selector")
        attribute = kwargs.get("attribute")
        
        if not selector or not attribute:
            raise ValueError("선택자와 속성이 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        
        # 요소 찾기
        element = page.wait_for_selector(selector, timeout=timeout)
        if not element:
            raise ValueError(f"선택자에 해당하는 요소를 찾을 수 없음: {selector}")
        
        # 속성 가져오기
        return element.get_attribute(attribute)
    
    def evaluate(self, **kwargs) -> Any:
        """JavaScript 코드 실행"""
        expression = kwargs.get("expression")
        
        if not expression:
            raise ValueError("실행할 JavaScript 코드가 지정되지 않았습니다")
        
        page = self._get_current_page()
        
        # 파라미터 설정
        arg = kwargs.get("arg", None)
        
        # JavaScript 실행
        return page.evaluate(expression, arg)
    
    def get_url(self, **kwargs) -> str:
        """현재 URL 가져오기"""
        page = self._get_current_page()
        return page.url
    
    def get_title(self, **kwargs) -> str:
        """현재 페이지 제목 가져오기"""
        page = self._get_current_page()
        return page.title()
    
    def reload(self, **kwargs) -> Dict[str, Any]:
        """페이지 새로고침"""
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        wait_until = kwargs.get("wait_until", "load")  # load, domcontentloaded, networkidle, commit
        
        # 페이지 새로고침
        response = page.reload(timeout=timeout, wait_until=wait_until)
        
        # 결과 반환
        result = {
            "url": page.url(),
            "status": response.status if response else None,
            "success": response.ok if response else False
        }
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return result
    
    def go_back(self, **kwargs) -> Dict[str, Any]:
        """이전 페이지로 이동"""
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        wait_until = kwargs.get("wait_until", "load")  # load, domcontentloaded, networkidle, commit
        
        # 이전 페이지로 이동
        response = page.go_back(timeout=timeout, wait_until=wait_until)
        
        # 결과 반환
        result = {
            "url": page.url(),
            "status": response.status if response else None,
            "success": response.ok if response else False
        }
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return result
    
    def go_forward(self, **kwargs) -> Dict[str, Any]:
        """다음 페이지로 이동"""
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        wait_until = kwargs.get("wait_until", "load")  # load, domcontentloaded, networkidle, commit
        
        # 다음 페이지로 이동
        response = page.go_forward(timeout=timeout, wait_until=wait_until)
        
        # 결과 반환
        result = {
            "url": page.url(),
            "status": response.status if response else None,
            "success": response.ok if response else False
        }
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return result
    
    def handle_dialog(self, **kwargs) -> bool:
        """대화 상자 처리"""
        action = kwargs.get("action", "accept")  # accept, dismiss
        prompt_text = kwargs.get("prompt_text", "")
        
        page = self._get_current_page()
        
        # 대화 상자 핸들러 설정
        def dialog_handler(dialog):
            logger.info(f"대화 상자 감지: {dialog.type} - {dialog.message}")
            
            if action == "accept":
                if dialog.type == "prompt" and prompt_text:
                    dialog.accept(prompt_text)
                else:
                    dialog.accept()
            else:
                dialog.dismiss()
        
        # 핸들러 등록
        page.on("dialog", dialog_handler)
        
        return True
    
    def wait_for_download(self, **kwargs) -> Dict[str, Any]:
        """다운로드 대기"""
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        save_path = kwargs.get("save_path", self.downloads_dir)
        
        # 다운로드 이벤트 대기
        with page.expect_download(timeout=timeout) as download_info:
            # 다운로드 트리거 액션 (클릭)
            selector = kwargs.get("selector")
            if selector:
                page.click(selector)
        
        # 다운로드 정보
        download = download_info.value
        suggested_filename = download.suggested_filename
        
        # 저장 경로 설정
        if not os.path.exists(save_path):
            os.makedirs(save_path, exist_ok=True)
        
        file_path = os.path.join(save_path, suggested_filename)
        download.save_as(file_path)
        
        return {
            "filename": suggested_filename,
            "path": file_path
        }
    
    def wait_for_navigation(self, **kwargs) -> Dict[str, Any]:
        """페이지 이동 대기"""
        page = self._get_current_page()
        
        # 파라미터 설정
        timeout = kwargs.get("timeout", self.config.get("timeout", 30000))
        wait_until = kwargs.get("wait_until", "load")  # load, domcontentloaded, networkidle, commit
        url = kwargs.get("url", None)  # URL 패턴
        
        # 네비게이션 이벤트 대기
        with page.expect_navigation(timeout=timeout, wait_until=wait_until, url=url) as navigation_info:
            # 네비게이션 트리거 액션
            trigger_action = kwargs.get("trigger_action")
            trigger_selector = kwargs.get("trigger_selector")
            
            if trigger_action == "click" and trigger_selector:
                page.click(trigger_selector)
        
        # 네비게이션 정보
        response = navigation_info.value
        
        # 인터럽션 처리
        if self.config.get("auto_handle_interruptions", True):
            self._handle_interruptions(page)
        
        return {
            "url": page.url(),
            "status": response.status if response else None,
            "success": response.ok if response else False
        }
    
    def handle_interruptions(self, **kwargs) -> bool:
        """인터럽션 직접 처리"""
        page = self._get_current_page()
        
        if not self.interruption_handler:
            logger.warning("인터럽션 핸들러가 설정되지 않았습니다")
            return False
        
        return self._handle_interruptions(page)