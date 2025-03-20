"""
PyAutoGUI 자동화 플러그인

이 모듈은 PyAutoGUI를 사용한 데스크톱 자동화 플러그인을 구현합니다.
마우스 및 키보드 조작, 화면 인식 등의 작업을 수행합니다.
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from core.plugin_system import PluginInfo, PluginType
from plugins.automation.base import ActionResult, AutomationPlugin

# PyAutoGUI 가져오기 (런타임에 설치)
try:
    import pyautogui
    import pyperclip  # 클립보드 작업용
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class PyAutoGUIPlugin(AutomationPlugin):
    """PyAutoGUI 자동화 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="pyautogui_automation",
            name="PyAutoGUI 자동화",
            description="PyAutoGUI를 사용한 데스크톱 자동화 플러그인",
            version="1.0.0",
            plugin_type=PluginType.AUTOMATION,
            priority=5,  # Playwright보다 낮은 우선순위
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 설정
        self._default_duration = 0.1  # 액션 지속 시간 (초)
        self._default_confidence = 0.9  # 이미지 인식 신뢰도
        self._screenshot_dir = None  # 스크린샷 디렉토리
        self._fail_safe = True  # 비상 탈출 기능 (화면 가장자리로 마우스 이동 시 예외 발생)
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        if not PYAUTOGUI_AVAILABLE:
            self.logger.error("PyAutoGUI를 찾을 수 없습니다. 'pip install pyautogui pyperclip' 명령으로 설치하세요.")
            return False
        
        super().initialize(config)
        
        # 설정 적용
        self._default_duration = self._config.get('duration', 0.1)
        self._default_confidence = self._config.get('confidence', 0.9)
        self._fail_safe = self._config.get('fail_safe', True)
        
        # 스크린샷 디렉토리 설정
        self._screenshot_dir = self._config.get('screenshot_dir')
        if self._screenshot_dir:
            os.makedirs(self._screenshot_dir, exist_ok=True)
        
        # PyAutoGUI 설정
        pyautogui.PAUSE = self._config.get('pause', 0.1)  # 각 함수 사이의 일시 중지 시간
        pyautogui.FAILSAFE = self._fail_safe
        
        self.logger.info("PyAutoGUI 초기화 완료")
        return True
    
    def cleanup(self) -> None:
        """플러그인 정리"""
        # 특별한 정리 작업 없음
        super().cleanup()
    
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
        
        try:
            if action_type == 'click':
                result = self._click(params)
            
            elif action_type == 'right_click':
                result = self._right_click(params)
            
            elif action_type == 'double_click':
                result = self._double_click(params)
            
            elif action_type == 'move_to':
                result = self._move_to(params)
            
            elif action_type == 'drag_to':
                result = self._drag_to(params)
            
            elif action_type == 'scroll':
                result = self._scroll(params)
            
            elif action_type == 'type':
                result = self._type(params)
            
            elif action_type == 'press':
                result = self._press(params)
            
            elif action_type == 'hotkey':
                result = self._hotkey(params)
            
            elif action_type == 'locate_on_screen':
                result = self._locate_on_screen(params)
            
            elif action_type == 'screenshot':
                result = self._screenshot(params)
            
            elif action_type == 'get_position':
                result = self._get_position(params)
            
            elif action_type == 'get_screen_size':
                result = self._get_screen_size(params)
            
            elif action_type == 'alert':
                result = self._alert(params)
            
            else:
                result = self._create_result(False, f"Unsupported action: {action_type}")
        
        except Exception as e:
            result = self._create_result(False, str(e))
            self.logger.error(f"액션 실행 중 오류 ({action_type}): {str(e)}")
        
        return result
    
    def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 클릭
        
        Args:
            params: 클릭 파라미터
            
        Returns:
            클릭 결과
        """
        # 위치 파라미터 확인
        x = params.get('x')
        y = params.get('y')
        position = params.get('position')
        image = params.get('image')
        
        if image:
            # 이미지 인식을 통한 클릭
            confidence = params.get('confidence', self._default_confidence)
            try:
                location = pyautogui.locateCenterOnScreen(image, confidence=confidence)
                if location:
                    x, y = location
                else:
                    return self._create_result(False, "Image not found on screen")
            except Exception as e:
                return self._create_result(False, f"Image recognition failed: {str(e)}")
        
        if position:
            # 위치 튜플
            x, y = position
        
        # 클릭 매개변수
        button = params.get('button', 'left')
        clicks = params.get('clicks', 1)
        interval = params.get('interval', 0.0)
        duration = params.get('duration', self._default_duration)
        
        if x is not None and y is not None:
            # 특정 위치 클릭
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button, duration=duration)
            return self._create_result(True, x=x, y=y)
        else:
            # 현재 위치 클릭
            pyautogui.click(clicks=clicks, interval=interval, button=button)
            x, y = pyautogui.position()
            return self._create_result(True, x=x, y=y)
    
    def _right_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 오른쪽 클릭
        
        Args:
            params: 클릭 파라미터
            
        Returns:
            클릭 결과
        """
        params['button'] = 'right'
        return self._click(params)
    
    def _double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 더블 클릭
        
        Args:
            params: 클릭 파라미터
            
        Returns:
            클릭 결과
        """
        params['clicks'] = 2
        return self._click(params)
    
    def _move_to(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 이동
        
        Args:
            params: 이동 파라미터
            
        Returns:
            이동 결과
        """
        # 위치 파라미터 확인
        x = params.get('x')
        y = params.get('y')
        position = params.get('position')
        image = params.get('image')
        
        if image:
            # 이미지 인식을 통한 이동
            confidence = params.get('confidence', self._default_confidence)
            try:
                location = pyautogui.locateCenterOnScreen(image, confidence=confidence)
                if location:
                    x, y = location
                else:
                    return self._create_result(False, "Image not found on screen")
            except Exception as e:
                return self._create_result(False, f"Image recognition failed: {str(e)}")
        
        if position:
            # 위치 튜플
            x, y = position
        
        # 이동 매개변수
        duration = params.get('duration', self._default_duration)
        
        if x is not None and y is not None:
            # 특정 위치로 이동
            pyautogui.moveTo(x, y, duration=duration)
            return self._create_result(True, x=x, y=y)
        else:
            return self._create_result(False, "Position not specified")
    
    def _drag_to(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 드래그
        
        Args:
            params: 드래그 파라미터
            
        Returns:
            드래그 결과
        """
        # 시작 위치 파라미터
        start_x = params.get('start_x')
        start_y = params.get('start_y')
        start_position = params.get('start_position')
        
        # 목표 위치 파라미터
        end_x = params.get('end_x')
        end_y = params.get('end_y')
        end_position = params.get('end_position')
        
        # 시작 위치 설정
        if start_position:
            start_x, start_y = start_position
        
        # 목표 위치 설정
        if end_position:
            end_x, end_y = end_position
        
        # 드래그 매개변수
        button = params.get('button', 'left')
        duration = params.get('duration', self._default_duration)
        
        # 시작 위치로 이동
        if start_x is not None and start_y is not None:
            pyautogui.moveTo(start_x, start_y)
        
        # 목표 위치로 드래그
        if end_x is not None and end_y is not None:
            pyautogui.dragTo(end_x, end_y, button=button, duration=duration)
            return self._create_result(True, start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y)
        else:
            return self._create_result(False, "End position not specified")
    
    def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 스크롤
        
        Args:
            params: 스크롤 파라미터
            
        Returns:
            스크롤 결과
        """
        # 스크롤 클릭
        clicks = params.get('clicks', 10)  # 양수: 위로, 음수: 아래로
        
        # 스크롤 위치 (선택 사항)
        x = params.get('x')
        y = params.get('y')
        
        # 스크롤 실행
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
            return self._create_result(True, clicks=clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)
            return self._create_result(True, clicks=clicks)
    
    def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 입력
        
        Args:
            params: 입력 파라미터
            
        Returns:
            입력 결과
        """
        # 입력 텍스트
        text = params.get('text')
        if not text:
            return self._create_result(False, "Text not specified")
        
        # 입력 매개변수
        interval = params.get('interval', 0.0)  # 각 문자 사이의 간격
        use_clipboard = params.get('use_clipboard', False)  # 클립보드 사용 여부 (한글 등 복잡한 텍스트용)
        
        try:
            if use_clipboard:
                # 클립보드 사용
                old_clipboard = pyperclip.paste()  # 이전 클립보드 저장
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                pyperclip.copy(old_clipboard)  # 이전 클립보드 복원
            else:
                # 직접 입력
                pyautogui.write(text, interval=interval)
            
            return self._create_result(True, text=text)
        except Exception as e:
            return self._create_result(False, f"Type failed: {str(e)}")
    
    def _press(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """키 누르기
        
        Args:
            params: 키 파라미터
            
        Returns:
            키 누르기 결과
        """
        # 키 이름
        key = params.get('key')
        if not key:
            return self._create_result(False, "Key not specified")
        
        # 키 누르기 매개변수
        presses = params.get('presses', 1)  # 누르는 횟수
        interval = params.get('interval', 0.0)  # 각 누름 사이의 간격
        
        # 키 누르기 실행
        pyautogui.press(key, presses=presses, interval=interval)
        return self._create_result(True, key=key, presses=presses)
    
    def _hotkey(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """단축키 입력
        
        Args:
            params: 단축키 파라미터
            
        Returns:
            단축키 결과
        """
        # 키 목록
        keys = params.get('keys')
        if not keys or not isinstance(keys, list):
            return self._create_result(False, "Keys not specified or not a list")
        
        # 단축키 실행
        pyautogui.hotkey(*keys)
        return self._create_result(True, keys=keys)
    
    def _locate_on_screen(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """화면에서 이미지 찾기
        
        Args:
            params: 이미지 인식 파라미터
            
        Returns:
            이미지 인식 결과
        """
        # 이미지 파일 경로
        image = params.get('image')
        if not image:
            return self._create_result(False, "Image not specified")
        
        # 인식 매개변수
        confidence = params.get('confidence', self._default_confidence)
        grayscale = params.get('grayscale', False)
        all_matches = params.get('all_matches', False)
        
        try:
            if all_matches:
                # 모든 일치 항목 찾기
                locations = list(pyautogui.locateAllOnScreen(
                    image, confidence=confidence, grayscale=grayscale
                ))
                
                if locations:
                    # 위치 목록 반환
                    location_list = [{'left': loc.left, 'top': loc.top, 'width': loc.width, 'height': loc.height}
                                    for loc in locations]
                    return self._create_result(True, found=True, locations=location_list, count=len(location_list))
                else:
                    return self._create_result(False, found=False, error="Image not found on screen")
            else:
                # 첫 번째 일치 항목 찾기
                location = pyautogui.locateOnScreen(image, confidence=confidence, grayscale=grayscale)
                
                if location:
                    # 위치 정보 반환
                    center_x, center_y = pyautogui.center(location)
                    return self._create_result(
                        True, found=True,
                        left=location.left, top=location.top,
                        width=location.width, height=location.height,
                        center_x=center_x, center_y=center_y
                    )
                else:
                    return self._create_result(False, found=False, error="Image not found on screen")
        except Exception as e:
            return self._create_result(False, found=False, error=f"Image recognition failed: {str(e)}")
    
    def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """스크린샷 촬영
        
        Args:
            params: 스크린샷 파라미터
            
        Returns:
            스크린샷 결과
        """
        # 파일 경로
        filename = params.get('filename')
        
        # 영역 지정 (선택 사항)
        region = params.get('region')  # (left, top, width, height)
        
        try:
            if filename:
                # 파일로 저장
                path = filename
                if self._screenshot_dir:
                    path = os.path.join(self._screenshot_dir, filename)
                
                if region:
                    pyautogui.screenshot(path, region=region)
                else:
                    pyautogui.screenshot(path)
                
                return self._create_result(True, path=path)
            else:
                # 이미지 객체 반환
                if region:
                    img = pyautogui.screenshot(region=region)
                else:
                    img = pyautogui.screenshot()
                
                # 임시 파일로 저장
                if self._screenshot_dir:
                    temp_path = os.path.join(self._screenshot_dir, f"temp_{int(time.time())}.png")
                    img.save(temp_path)
                    return self._create_result(True, path=temp_path, width=img.width, height=img.height)
                
                return self._create_result(True, width=img.width, height=img.height)
        except Exception as e:
            return self._create_result(False, error=f"Screenshot failed: {str(e)}")
    
    def _get_position(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """마우스 위치 가져오기
        
        Args:
            params: 위치 파라미터
            
        Returns:
            위치 결과
        """
        # 현재 마우스 위치 가져오기
        x, y = pyautogui.position()
        return self._create_result(True, x=x, y=y)
    
    def _get_screen_size(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """화면 크기 가져오기
        
        Args:
            params: 화면 크기 파라미터
            
        Returns:
            화면 크기 결과
        """
        # 화면 크기 가져오기
        width, height = pyautogui.size()
        return self._create_result(True, width=width, height=height)
    
    def _alert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """경고 메시지 표시
        
        Args:
            params: 경고 파라미터
            
        Returns:
            경고 결과
        """
        # 메시지 텍스트
        text = params.get('text', '')
        title = params.get('title', 'Alert')
        button = params.get('button', 'OK')
        
        # 경고 표시
        pyautogui.alert(text=text, title=title, button=button)
        return self._create_result(True)