#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 브라우저 관리자
"""

import logging
import time
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class BrowserManager:
    """Playwright 브라우저 관리"""
    
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.browser_type = "chromium"  # chromium, firefox, webkit
        self._init_browser()
        
    def _init_browser(self):
        """브라우저 초기화"""
        try:
            logger.info(f"브라우저 초기화 중 (타입: {self.browser_type}, 헤드리스: {self.headless})")
            self.playwright = sync_playwright().start()
            
            browser_options = {
                "headless": self.headless,
                "slow_mo": 50
            }
            
            if self.browser_type == "chromium":
                self.browser = self.playwright.chromium.launch(**browser_options)
            elif self.browser_type == "firefox":
                self.browser = self.playwright.firefox.launch(**browser_options)
            elif self.browser_type == "webkit":
                self.browser = self.playwright.webkit.launch(**browser_options)
            else:
                raise ValueError(f"지원되지 않는 브라우저 타입: {self.browser_type}")
            
            logger.info("브라우저가 성공적으로 초기화되었습니다.")
            
        except Exception as e:
            logger.error(f"브라우저 초기화 중 오류 발생: {str(e)}")
            self.close()
            raise
        
    def get_browser(self):
        """브라우저 인스턴스 반환"""
        if not self.browser or not self.playwright:
            self._init_browser()
        return self.browser
        
    def new_context(self, viewport=None, locale=None):
        """새 브라우저 컨텍스트 생성"""
        browser = self.get_browser()
        context_options = {}
        
        if viewport:
            context_options["viewport"] = viewport
        
        if locale:
            context_options["locale"] = locale
        
        return browser.new_context(**context_options)
        
    def change_browser_type(self, browser_type):
        """브라우저 타입 변경"""
        if browser_type not in ["chromium", "firefox", "webkit"]:
            raise ValueError(f"지원되지 않는 브라우저 타입: {browser_type}")
        
        if self.browser_type != browser_type:
            logger.info(f"브라우저 타입 변경: {self.browser_type} -> {browser_type}")
            self.browser_type = browser_type
            
            # 기존 브라우저 종료 후 새 브라우저 초기화
            self.close()
            self._init_browser()
        
    def set_headless(self, headless):
        """헤드리스 모드 설정"""
        if self.headless != headless:
            logger.info(f"헤드리스 모드 변경: {self.headless} -> {headless}")
            self.headless = headless
            
            # 기존 브라우저 종료 후 새 브라우저 초기화
            self.close()
            self._init_browser()
        
    def close(self):
        """브라우저 및 Playwright 종료"""
        try:
            if self.browser:
                logger.info("브라우저 종료 중...")
                self.browser.close()
                self.browser = None
            
            if self.playwright:
                logger.info("Playwright 종료 중...")
                self.playwright.stop()
                self.playwright = None
            
            logger.info("브라우저가 성공적으로 종료되었습니다.")
            
        except Exception as e:
            logger.error(f"브라우저 종료 중 오류 발생: {str(e)}")