"""
Playwright 자동화 플러그인

이 모듈은 Playwright를 사용한 웹 자동화 플러그인을 구현합니다.
웹 페이지 탐색, 요소 조작, 스크린샷 등의 작업을 수행합니다.
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from core.plugin_system import PluginInfo, PluginType
from plugins.automation.base import ActionResult, AutomationPlugin

# Playwright 가져오기 (런타임에 설치)
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Locator
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightPlugin(AutomationPlugin):
    """Playwright 자동화 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="playwright_automation",
            name="Playwright 자동화",
            description="Playwright를 사용한 웹 자동화 플러그인",
            version="1.0.0",
            plugin_type=PluginType.AUTOMATION,
            priority=10,
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Playwright 상태
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        
        # 설정
        self._default_timeout = 30000  # ms
        self._browser_type = "chromium"  # chromium, firefox, webkit
        self._headless = False
        
        # 비동기 루프
        self._loop = None
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error("Playwright를 찾을 수 없습니다. 'pip install playwright' 명령으로 설치하세요.")
            return False
        
        super().initialize(config)
        
        # 설정 적용
        self._default_timeout = self._config.get('timeout', 30000)
        self._browser_type = self._config.get('browser_type', 'chromium')
        self._headless = self._config.get('headless', False)
        
        # 비동기 루프 생성
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # Playwright 초기화
        try:
            # asyncio.run() 대신 직접 호출하여 루프 재사용
            future = asyncio.ensure_future(self._initialize_playwright(), loop=self._loop)
            result = self._loop.run_until_complete(future)
            
            self.logger.info(f"Playwright 초기화 완료 (브라우저: {self._browser_type})")
            return result
        except Exception as e:
            self.logger.error(f"Playwright 초기화 실패: {str(e)}")
            return False
    
    async def _initialize_playwright(self) -> bool:
        """Playwright 비동기 초기화"""
        try:
            # 이미 활성화된 브라우저가 있는지 확인
            if self._playwright and self._browser and self._browser.is_connected():
                try:
                    # 이미 연결된 페이지가 있고 닫히지 않았는지 확인
                    if self._page and not self._page.is_closed():
                        self.logger.info("이미 실행 중인 브라우저 세션 재사용")
                        return True
                except Exception as e:
                    self.logger.warning(f"기존 브라우저 상태 확인 중 오류: {str(e)}")
                    # 오류 발생 시 기존 리소스 정리 후 새로 시작
                    await self._cleanup_playwright()
            
            # Playwright 시작
            self._playwright = await async_playwright().start()
            
            # 브라우저 유형 선택
            if self._browser_type == 'firefox':
                browser_module = self._playwright.firefox
            elif self._browser_type == 'webkit':
                browser_module = self._playwright.webkit
            else:
                # 기본값은 chromium
                browser_module = self._playwright.chromium
            
            # 봇 감지 회피 설정 추가
            browser_args = [
                '--disable-dev-shm-usage',  # 리소스 제한 방지
                '--disable-blink-features=AutomationControlled',  # 자동화 감지 비활성화
                '--disable-extensions',  # 확장 비활성화
                '--no-sandbox',  # 샌드박스 비활성화
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', # 일반적인 UA
            ]
            
            # Microsoft Edge를 사용할 경우 (chromium 기반)
            if self._config.get('use_edge', False):
                # Edge 실행 파일 경로 (Windows)
                edge_path = self._config.get('edge_path')
                if not edge_path:
                    # 기본 Edge 설치 경로 추정
                    import os
                    program_files = os.environ.get('PROGRAMFILES')
                    if program_files:
                        edge_path = os.path.join(program_files, 'Microsoft', 'Edge', 'Application', 'msedge.exe')
                
                if edge_path and os.path.exists(edge_path):
                    self.logger.info(f"Microsoft Edge 사용: {edge_path}")
                    # Edge 브라우저 실행
                    self._browser = await browser_module.launch_persistent_context(
                        user_data_dir=self._config.get('user_data_dir', './browser_data'),
                        executable_path=edge_path,
                        headless=self._headless,
                        args=browser_args
                    )
                    # Edge에서는 context가 바로 생성되므로 별도의 context 생성 안함
                    self._context = self._browser
                    self._page = await self._context.new_page()
                else:
                    self.logger.warning("Edge 실행 파일을 찾을 수 없음, 기본 브라우저 사용")
                    self._browser = await browser_module.launch_persistent_context(
                        user_data_dir=self._config.get('user_data_dir', './browser_data'),
                        headless=self._headless,  # 이 부분이 헤드리스 모드 설정
                        args=browser_args,
                        ignore_default_args=['--enable-automation']
                    )
                    self._context = await self._browser.new_context()
                    self._page = await self._context.new_page()
            else:
                # 기본 Chromium 브라우저 실행 - 로컬 사용자 데이터 저장소 추가
                self._browser = await browser_module.launch_persistent_context(
                    user_data_dir=self._config.get('user_data_dir', './browser_data'),
                    headless=self._headless,
                    args=browser_args,
                    ignore_default_args=['--enable-automation']  # 자동화 감지 플래그 제거
                )
                self._context = self._browser  # launch_persistent_context는 context를 직접 반환
                self._page = await self._context.new_page()
                
                # 봇 감지 스크립트 비활성화
                await self._page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                """)
            
            # 페이지 타임아웃 설정
            self._page.set_default_timeout(self._default_timeout)
            
            return True
        except Exception as e:
            self.logger.error(f"Playwright 비동기 초기화 실패: {str(e)}")
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            return False

    
    def cleanup(self) -> None:
        """플러그인 정리"""
        if self._loop and self._playwright:
            try:
                future = asyncio.ensure_future(self._cleanup_playwright(), loop=self._loop)
                self._loop.run_until_complete(future)
                self._loop.close()
            except Exception as e:
                self.logger.error(f"Playwright 정리 중 오류: {str(e)}")
        
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._loop = None
        
        super().cleanup()
    
    async def _cleanup_playwright(self) -> None:
        """Playwright 비동기 정리"""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
                self._page = None
                
            if self._context and self._context != self._browser:  # context가 browser와 같지 않은 경우에만
                await self._context.close()
                self._context = None
                
            if self._browser and self._browser.is_connected():
                await self._browser.close()
                self._browser = None
                
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
                
            self.logger.info("Playwright 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"Playwright 리소스 정리 중 오류: {str(e)}")
    
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
        result = None
        
        # 비동기 루프에서 액션 실행
        try:
            if action_type == 'navigate':
                future = asyncio.ensure_future(self._navigate(params), loop=self._loop)
                result = self._loop.run_until_complete(future)

            elif action_type == 'get_url':
                future = asyncio.ensure_future(self._get_url(params), loop=self._loop)
                result = self._loop.run_until_complete(future)

            elif action_type == 'type':
                future = asyncio.ensure_future(self._type(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'find_element':
                future = asyncio.ensure_future(self._find_element(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'click':
                future = asyncio.ensure_future(self._click(params), loop=self._loop)
                result = self._loop.run_until_complete(future)

            elif action_type == 'press':
                future = asyncio.ensure_future(self._press(params), loop=self._loop)
                result = self._loop.run_until_complete(future)

            elif action_type == 'keyboard_press':
                future = asyncio.ensure_future(self._keyboard_press(params), loop=self._loop)
                result = self._loop.run_until_complete(future)

            elif action_type == 'get_url':
                future = asyncio.ensure_future(self._get_url(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'fill':
                future = asyncio.ensure_future(self._fill(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'select':
                future = asyncio.ensure_future(self._select(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'get_text':
                future = asyncio.ensure_future(self._get_text(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'get_attribute':
                future = asyncio.ensure_future(self._get_attribute(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'evaluate':
                future = asyncio.ensure_future(self._evaluate(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
                        
            elif action_type == 'get_page':
                # 현재 페이지 반환
                return self._create_result(True, page=self._page)

            elif action_type == 'screenshot':
                future = asyncio.ensure_future(self._screenshot(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            elif action_type == 'wait_for_load':
                future = asyncio.ensure_future(self._wait_for_load(params), loop=self._loop)
                result = self._loop.run_until_complete(future)
            
            else:
                result = self._create_result(False, f"Unsupported action: {action_type}")
        
        except Exception as e:
            result = self._create_result(False, str(e))
            self.logger.error(f"액션 실행 중 오류 ({action_type}): {str(e)}")
        
        return result
    
    async def _navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """웹 페이지 탐색
        
        Args:
            params: 탐색 파라미터
            
        Returns:
            탐색 결과
        """
        url = params.get('url')
        if not url:
            return self._create_result(False, "URL이 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        wait_until = params.get('wait_until', 'load')  # load, domcontentloaded, networkidle
        
        try:
            response = await self._page.goto(url, timeout=timeout, wait_until=wait_until)
            
            return self._create_result(
                True,
                url=self._page.url,
                status=response.status if response else None,
                title=await self._page.title()
            )
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _find_element(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 찾기
        
        Args:
            params: 요소 파라미터
            
        Returns:
            요소 검색 결과
        """
        selector = params.get('selector')
        if not selector:
            return self._create_result(False, "선택자가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            # 요소 찾기 시도
            locator = self._page.locator(selector)
            
            # 요소가 존재하는지 확인
            is_visible = await locator.is_visible(timeout=timeout)
            count = await locator.count()
            
            if count == 0 or not is_visible:
                return self._create_result(False, "요소를 찾을 수 없음")
            
            # 여러 요소가 있는 경우 첫 번째 요소 반환
            element_handle = await locator.first.element_handle()
            
            # 요소 정보 수집
            tag_name = await self._page.evaluate("e => e.tagName.toLowerCase()", element_handle)
            
            return self._create_result(
                True,
                found=True,
                element={
                    'selector': selector,
                    'tag': tag_name,
                    'visible': is_visible,
                    'count': count
                }
            )
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 클릭
        
        Args:
            params: 클릭 파라미터
            
        Returns:
            클릭 결과
        """
        selector = params.get('selector')
        position = params.get('position')
        element = params.get('element')
        
        if not selector and not position and not element:
            return self._create_result(False, "선택자, 위치 또는 요소가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자로 요소 클릭
                await self._page.click(selector, timeout=timeout)
            elif position:
                # 위치 클릭
                x, y = position
                await self._page.mouse.click(x, y)
            elif element and element.get('selector'):
                # 요소 정보로 클릭
                await self._page.click(element['selector'], timeout=timeout)
            
            return self._create_result(True)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _fill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 채우기
        
        Args:
            params: 채우기 파라미터
            
        Returns:
            채우기 결과
        """
        selector = params.get('selector')
        text = params.get('text', '')
        element = params.get('element')
        
        if not selector and not element:
            return self._create_result(False, "선택자 또는 요소가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자로 요소 채우기
                await self._page.fill(selector, text, timeout=timeout)
            elif element and element.get('selector'):
                # 요소 정보로 채우기
                await self._page.fill(element['selector'], text, timeout=timeout)
            
            return self._create_result(True)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _select(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 선택
        
        Args:
            params: 선택 파라미터
            
        Returns:
            선택 결과
        """
        selector = params.get('selector')
        value = params.get('value')
        element = params.get('element')
        
        if not selector and not element:
            return self._create_result(False, "선택자 또는 요소가 지정되지 않음")
        
        if value is None:
            return self._create_result(False, "선택 값이 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자로 요소 선택
                values = await self._page.select_option(selector, value, timeout=timeout)
            elif element and element.get('selector'):
                # 요소 정보로 선택
                values = await self._page.select_option(element['selector'], value, timeout=timeout)
            
            return self._create_result(True, selected_values=values)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _get_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 텍스트 가져오기
        
        Args:
            params: 텍스트 파라미터
            
        Returns:
            텍스트 결과
        """
        selector = params.get('selector')
        element = params.get('element')
        
        if not selector and not element:
            return self._create_result(False, "선택자 또는 요소가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자로 요소 텍스트 가져오기
                text = await self._page.text_content(selector, timeout=timeout)
            elif element and element.get('selector'):
                # 요소 정보로 텍스트 가져오기
                text = await self._page.text_content(element['selector'], timeout=timeout)
            
            return self._create_result(True, text=text)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _get_attribute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 속성 가져오기
        
        Args:
            params: 속성 파라미터
            
        Returns:
            속성 결과
        """
        selector = params.get('selector')
        attribute = params.get('attribute')
        element = params.get('element')
        
        if not selector and not element:
            return self._create_result(False, "선택자 또는 요소가 지정되지 않음")
        
        if not attribute:
            return self._create_result(False, "속성 이름이 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자로 요소 속성 가져오기
                value = await self._page.get_attribute(selector, attribute, timeout=timeout)
            elif element and element.get('selector'):
                # 요소 정보로 속성 가져오기
                value = await self._page.get_attribute(element['selector'], attribute, timeout=timeout)
            
            return self._create_result(True, attribute=attribute, value=value)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _evaluate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """JavaScript 실행
        
        Args:
            params: 스크립트 파라미터
            
        Returns:
            실행 결과
        """
        script = params.get('script')
        if not script:
            return self._create_result(False, "스크립트가 지정되지 않음")
        
        try:
            result = await self._page.evaluate(script)
            return self._create_result(True, result=result)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """스크린샷 촬영
        
        Args:
            params: 스크린샷 파라미터
            
        Returns:
            스크린샷 결과
        """
        path = params.get('path')
        selector = params.get('selector')
        full_page = params.get('full_page', False)
        
        try:
            if selector:
                # 특정 요소 스크린샷
                locator = self._page.locator(selector)
                if path:
                    await locator.screenshot(path=path)
                else:
                    screenshot_bytes = await locator.screenshot()
                    return self._create_result(True, screenshot=screenshot_bytes)
            else:
                # 전체 페이지 스크린샷
                if path:
                    await self._page.screenshot(path=path, full_page=full_page)
                else:
                    screenshot_bytes = await self._page.screenshot(full_page=full_page)
                    return self._create_result(True, screenshot=screenshot_bytes)
            
            return self._create_result(True, path=path)
        except Exception as e:
            return self._create_result(False, str(e))
    
    async def _wait_for_load(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """페이지 로드 대기
        
        Args:
            params: 대기 파라미터
            
        Returns:
            대기 결과
        """
        state = params.get('state', 'load')  # load, domcontentloaded, networkidle
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            await self._page.wait_for_load_state(state, timeout=timeout)
            return self._create_result(True, state=state)
        except Exception as e:
            return self._create_result(False, str(e))
        
    async def _press(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소에 키 누르기 (수정된 버전)
        
        Args:
            params: 파라미터
            
        Returns:
            결과
        """
        selector = params.get('selector')
        key = params.get('key')
        
        if not key:
            return self._create_result(False, "키가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            if selector:
                # 선택자 존재 확인
                locator = self._page.locator(selector)
                is_visible = await locator.is_visible(timeout=timeout)
                
                if not is_visible:
                    return self._create_result(False, f"요소가 표시되지 않음: {selector}")
                
                # 요소 포커스 확보 후 키 누르기
                await locator.focus()
                await self._page.wait_for_timeout(100)  # 약간의 지연으로 안정성 확보
                
                # 특정 요소에 키 누르기
                await self._page.press(selector, key, timeout=timeout)
            else:
                # 전역 키보드에 키 누르기
                await self._page.keyboard.press(key)
            
            return self._create_result(True, key=key)
        except Exception as e:
            self.logger.error(f"키 누르기 실패: {str(e)}")
            return self._create_result(False, f"키 누르기 오류: {str(e)}")

    async def _keyboard_press(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """전역 키보드에 키 누르기 (수정된 버전)
        
        Args:
            params: 파라미터
            
        Returns:
            결과
        """
        key = params.get('key')
        
        if not key:
            return self._create_result(False, "키가 지정되지 않음")
        
        try:
            # 여러 키 조합 처리 (Ctrl+A 등)
            if '+' in key:
                key_parts = key.split('+')
                modifiers = key_parts[:-1]
                final_key = key_parts[-1]
                
                # 수정자 키 누르기
                for modifier in modifiers:
                    await self._page.keyboard.down(modifier.strip())
                
                # 최종 키 누르고 떼기
                await self._page.keyboard.press(final_key.strip())
                
                # 수정자 키 떼기 (역순)
                for modifier in reversed(modifiers):
                    await self._page.keyboard.up(modifier.strip())
            else:
                # 단일 키 누르기
                await self._page.keyboard.press(key)
            
            return self._create_result(True, key=key)
        except Exception as e:
            self.logger.error(f"키보드 키 누르기 실패: {str(e)}")
            return self._create_result(False, f"키보드 키 누르기 오류: {str(e)}")

    async def _fill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 채우기 (수정된 버전)
        
        Args:
            params: 채우기 파라미터
            
        Returns:
            채우기 결과
        """
        selector = params.get('selector')
        text = params.get('text', '')
        element = params.get('element')
        clear_first = params.get('clear_first', True)  # 먼저 지우기 여부
        
        if not selector and not element:
            return self._create_result(False, "선택자 또는 요소가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            use_selector = selector if selector else element.get('selector')
            
            if not use_selector:
                return self._create_result(False, "유효한 선택자를 찾을 수 없음")
            
            # 요소 존재 확인
            locator = self._page.locator(use_selector)
            is_visible = await locator.is_visible(timeout=timeout)
            
            if not is_visible:
                return self._create_result(False, f"요소가 표시되지 않음: {use_selector}")
            
            # 요소 태그 확인 및 최적의 입력 방법 선택
            element_handle = await locator.element_handle()
            tag_name = await self._page.evaluate("e => e.tagName.toLowerCase()", element_handle)
            
            if clear_first:
                # 기존 내용 지우기
                await locator.focus()
                await self._page.wait_for_timeout(50)
                
                if tag_name in ['input', 'textarea']:
                    # 전체 선택 후 삭제
                    await self._page.keyboard.press('Control+a')
                    await self._page.wait_for_timeout(50)
                    await self._page.keyboard.press('Backspace')
                    await self._page.wait_for_timeout(50)
            
            # 텍스트 입력
            if text:
                # 일반적인 fill 메서드 사용
                await self._page.fill(use_selector, text, timeout=timeout)
                
                # 입력 확인
                input_value = await self._page.evaluate(f"document.querySelector('{use_selector}').value")
                if input_value != text:
                    # fill 메서드가 실패한 경우 대체 방법 시도
                    self.logger.warning(f"Fill 메서드 실패, type 메서드로 재시도: {use_selector}")
                    await locator.focus()
                    await self._page.wait_for_timeout(50)
                    await self._page.keyboard.press('Control+a')
                    await self._page.wait_for_timeout(50)
                    await self._page.keyboard.press('Backspace')
                    await self._page.wait_for_timeout(50)
                    await self._page.type(use_selector, text, timeout=timeout)
            
            return self._create_result(True, text=text, selector=use_selector)
        except Exception as e:
            self.logger.error(f"텍스트 입력 실패: {str(e)}")
            return self._create_result(False, f"텍스트 입력 오류: {str(e)}")
        
    async def _get_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """현재 URL 가져오기
        
        Args:
            params: 파라미터
            
        Returns:
            결과
        """
        try:
            url = self._page.url
            return self._create_result(True, url=url)
        except Exception as e:
            return self._create_result(False, str(e))
        
    async def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 타이핑
        
        Args:
            params: 타이핑 파라미터
            
        Returns:
            타이핑 결과
        """
        selector = params.get('selector')
        text = params.get('text', '')
        delay = params.get('delay', 0)
        
        if not selector:
            return self._create_result(False, "선택자가 지정되지 않음")
        
        timeout = params.get('timeout', self._default_timeout)
        
        try:
            # 요소 존재 확인
            locator = self._page.locator(selector)
            is_visible = await locator.is_visible(timeout=timeout)
            
            if not is_visible:
                return self._create_result(False, f"요소가 표시되지 않음: {selector}")
            
            # 기존 텍스트 지우기 - 여기를 수정
            # 작은따옴표 이스케이프 처리
            escaped_selector = selector.replace("'", "\\'")
            await self._page.evaluate(f"""
                (() => {{
                    const el = document.querySelector('{escaped_selector}');
                    if(el) {{
                        el.value = "";
                        return true;
                    }}
                    return false;
                }})()
            """)
            
            # 포커스 설정
            await locator.focus()
            await self._page.wait_for_timeout(100)
            
            # 텍스트 입력
            await self._page.type(selector, text, delay=delay)
            
            return self._create_result(True, text=text, selector=selector)
        except Exception as e:
            self.logger.error(f"타이핑 실패: {str(e)}")
            return self._create_result(False, f"타이핑 오류: {str(e)}")