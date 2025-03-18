 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - PyAutoGUI 자동화 플러그인
데스크톱 자동화를 위한 PyAutoGUI 기반 플러그인
"""

import logging
import os
import time
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
import json
import tempfile

import pyautogui
import pyperclip
from PIL import Image
import numpy as np

from core.plugin_manager import PluginInterface

logger = logging.getLogger(__name__)

class PyAutoGUIPlugin(PluginInterface):
    """PyAutoGUI 기반 데스크톱 자동화 플러그인"""
    
    plugin_type = "automation"
    plugin_name = "pyautogui"
    plugin_version = "0.1.0"
    plugin_description = "PyAutoGUI 기반 데스크톱 자동화 플러그인"
    
    def __init__(self):
        super().__init__()
        self.screenshots_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "screenshots")
        self.templates_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "templates")
        
        # 설정 기본값
        self.config = {
            "move_duration": 0.5,
            "click_delay": 0.1,
            "default_confidence": 0.9,
            "default_timeout": 30.0,
            "scroll_amount": 100,
            "screenshot_region": None,
            "safe_mode": True,
            "fail_safe": True
        }
        
        # 스크린샷 디렉토리 생성
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # 템플릿 디렉토리 생성
        os.makedirs(self.templates_dir, exist_ok=True)
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            # PyAutoGUI 기본 설정
            pyautogui.FAILSAFE = self.config.get("fail_safe", True)
            pyautogui.PAUSE = self.config.get("click_delay", 0.1)
            
            # 화면 크기 확인
            screen_width, screen_height = pyautogui.size()
            logger.info(f"화면 크기: {screen_width}x{screen_height}")
            
            return True
        except Exception as e:
            logger.error(f"PyAutoGUI 초기화 실패: {str(e)}")
            return False
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        try:
            return True
        except Exception as e:
            logger.error(f"PyAutoGUI 종료 중 오류: {str(e)}")
            return False
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        try:
            self.config.update(config)
            
            # PyAutoGUI 설정 업데이트
            pyautogui.FAILSAFE = self.config.get("fail_safe", True)
            pyautogui.PAUSE = self.config.get("click_delay", 0.1)
            
            return True
        except Exception as e:
            logger.error(f"PyAutoGUI 설정 중 오류: {str(e)}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return [
            "move_mouse",
            "click",
            "right_click",
            "double_click",
            "drag_mouse",
            "scroll",
            "mouse_position",
            "press_key",
            "type_text",
            "hotkey",
            "take_screenshot",
            "find_image",
            "wait_for_image",
            "get_pixel_color",
            "get_screen_size",
            "move_to_image",
            "click_image",
            "alert",
            "confirm",
            "prompt",
            "copy_to_clipboard",
            "paste_from_clipboard"
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
            self.capture_error_screenshot(action)
            
            raise
    
    def capture_error_screenshot(self, action: str) -> Optional[str]:
        """오류 발생 시 스크린샷 캡처"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{action}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            pyautogui.screenshot(filepath)
            logger.info(f"오류 스크린샷 저장됨: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"오류 스크린샷 캡처 실패: {str(e)}")
            return None
    
    # 액션 구현
    def move_mouse(self, **kwargs) -> Dict[str, Any]:
        """마우스 이동"""
        # x, y 좌표
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        if x is None or y is None:
            raise ValueError("x, y 좌표가 지정되지 않았습니다")
        
        # 이동 옵션
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 마우스 이동
        pyautogui.moveTo(x, y, duration=duration)
        
        return {
            "x": x,
            "y": y,
            "duration": duration
        }
    
    def click(self, **kwargs) -> Dict[str, Any]:
        """마우스 클릭"""
        # 클릭 위치
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        # 클릭 옵션
        button = kwargs.get("button", "left")  # left, right, middle
        clicks = kwargs.get("clicks", 1)
        interval = kwargs.get("interval", 0.0)
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 지정된 위치로 이동 후 클릭 또는 현재 위치에서 클릭
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button, duration=duration)
        else:
            pyautogui.click(clicks=clicks, interval=interval, button=button)
        
        # 현재 마우스 위치
        new_x, new_y = pyautogui.position()
        
        return {
            "x": new_x,
            "y": new_y,
            "button": button,
            "clicks": clicks
        }
    
    def right_click(self, **kwargs) -> Dict[str, Any]:
        """마우스 우클릭"""
        # 클릭 위치
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        # 클릭 옵션
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 지정된 위치로 이동 후 우클릭 또는 현재 위치에서 우클릭
        if x is not None and y is not None:
            pyautogui.rightClick(x, y, duration=duration)
        else:
            pyautogui.rightClick()
        
        # 현재 마우스 위치
        new_x, new_y = pyautogui.position()
        
        return {
            "x": new_x,
            "y": new_y,
            "button": "right"
        }
    
    def double_click(self, **kwargs) -> Dict[str, Any]:
        """마우스 더블클릭"""
        # 클릭 위치
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        # 클릭 옵션
        interval = kwargs.get("interval", 0.1)
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 지정된 위치로 이동 후 더블클릭 또는 현재 위치에서 더블클릭
        if x is not None and y is not None:
            pyautogui.doubleClick(x, y, interval=interval, duration=duration)
        else:
            pyautogui.doubleClick(interval=interval)
        
        # 현재 마우스 위치
        new_x, new_y = pyautogui.position()
        
        return {
            "x": new_x,
            "y": new_y,
            "clicks": 2
        }
    
    def drag_mouse(self, **kwargs) -> Dict[str, Any]:
        """마우스 드래그"""
        # 시작 위치
        start_x = kwargs.get("start_x")
        start_y = kwargs.get("start_y")
        
        # 끝 위치
        end_x = kwargs.get("end_x")
        end_y = kwargs.get("end_y")
        
        if start_x is None or start_y is None or end_x is None or end_y is None:
            raise ValueError("시작/끝 좌표가 지정되지 않았습니다")
        
        # 드래그 옵션
        button = kwargs.get("button", "left")  # left, right, middle
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 드래그 수행
        pyautogui.moveTo(start_x, start_y, duration=duration)
        pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
        
        return {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "button": button
        }
    
    def scroll(self, **kwargs) -> Dict[str, Any]:
        """스크롤"""
        # 스크롤 양
        clicks = kwargs.get("clicks", 1)  # 양수: 위로, 음수: 아래로
        
        # 스크롤 위치
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        # 스크롤 수행
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)
        
        return {
            "clicks": clicks,
            "direction": "up" if clicks > 0 else "down"
        }
    
    def mouse_position(self, **kwargs) -> Dict[str, Any]:
        """현재 마우스 위치 가져오기"""
        x, y = pyautogui.position()
        return {"x": x, "y": y}
    
    def press_key(self, **kwargs) -> bool:
        """키 입력"""
        # 키 이름
        key = kwargs.get("key")
        
        if not key:
            raise ValueError("키가 지정되지 않았습니다")
        
        # 키 입력 옵션
        presses = kwargs.get("presses", 1)
        interval = kwargs.get("interval", 0.0)
        
        # 키 입력
        pyautogui.press(key, presses=presses, interval=interval)
        
        return True
    
    def type_text(self, **kwargs) -> bool:
        """텍스트 입력"""
        # 입력할 텍스트
        text = kwargs.get("text")
        
        if text is None:
            raise ValueError("텍스트가 지정되지 않았습니다")
        
        # 텍스트 입력 옵션
        interval = kwargs.get("interval", 0.0)
        
        # 텍스트 입력
        pyautogui.write(text, interval=interval)
        
        return True
    
    def hotkey(self, **kwargs) -> bool:
        """단축키 입력"""
        # 키 조합
        keys = kwargs.get("keys")
        
        if not keys:
            raise ValueError("키 조합이 지정되지 않았습니다")
        
        # 단축키 입력
        pyautogui.hotkey(*keys)
        
        return True
    
    def take_screenshot(self, **kwargs) -> str:
        """스크린샷 캡처"""
        # 캡처 영역
        region = kwargs.get("region", self.config.get("screenshot_region"))
        
        # 파일 경로
        path = kwargs.get("path")
        
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            path = os.path.join(self.screenshots_dir, filename)
        
        # 스크린샷 캡처
        if region:
            pyautogui.screenshot(path, region=region)
        else:
            pyautogui.screenshot(path)
        
        logger.info(f"스크린샷 저장됨: {path}")
        return path
    
    def find_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """화면에서 이미지 찾기"""
        # 이미지 경로
        image_path = kwargs.get("image_path")
        
        if not image_path:
            raise ValueError("이미지 경로가 지정되지 않았습니다")
        
        # 검색 옵션
        confidence = kwargs.get("confidence", self.config.get("default_confidence", 0.9))
        region = kwargs.get("region")
        grayscale = kwargs.get("grayscale", False)
        
        # 이미지 찾기
        try:
            location = pyautogui.locateOnScreen(
                image_path,
                confidence=confidence,
                region=region,
                grayscale=grayscale
            )
            
            if location:
                center_x, center_y = pyautogui.center(location)
                return {
                    "found": True,
                    "x": center_x,
                    "y": center_y,
                    "left": location.left,
                    "top": location.top,
                    "width": location.width,
                    "height": location.height
                }
            else:
                return {"found": False}
                
        except Exception as e:
            logger.error(f"이미지 찾기 중 오류: {str(e)}")
            return {"found": False, "error": str(e)}
    
    def wait_for_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """이미지가 화면에 나타날 때까지 대기"""
        # 이미지 경로
        image_path = kwargs.get("image_path")
        
        if not image_path:
            raise ValueError("이미지 경로가 지정되지 않았습니다")
        
        # 대기 옵션
        timeout = kwargs.get("timeout", self.config.get("default_timeout", 30.0))
        confidence = kwargs.get("confidence", self.config.get("default_confidence", 0.9))
        region = kwargs.get("region")
        grayscale = kwargs.get("grayscale", False)
        interval = kwargs.get("interval", 0.5)
        
        # 이미지 대기
        start_time = time.time()
        while True:
            try:
                location = pyautogui.locateOnScreen(
                    image_path,
                    confidence=confidence,
                    region=region,
                    grayscale=grayscale
                )
                
                if location:
                    center_x, center_y = pyautogui.center(location)
                    return {
                        "found": True,
                        "x": center_x,
                        "y": center_y,
                        "left": location.left,
                        "top": location.top,
                        "width": location.width,
                        "height": location.height
                    }
                
                # 시간 초과 확인
                if time.time() - start_time > timeout:
                    logger.warning(f"이미지 대기 시간 초과: {image_path}")
                    return {"found": False, "timeout": True}
                
                # 잠시 대기
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"이미지 대기 중 오류: {str(e)}")
                return {"found": False, "error": str(e)}
    
    def get_pixel_color(self, **kwargs) -> Dict[str, Any]:
        """화면 특정 위치의 픽셀 색상 가져오기"""
        # 위치
        x = kwargs.get("x")
        y = kwargs.get("y")
        
        if x is None or y is None:
            raise ValueError("x, y 좌표가 지정되지 않았습니다")
        
        # 색상 가져오기
        color = pyautogui.pixel(x, y)
        
        return {
            "x": x,
            "y": y,
            "color": {
                "r": color[0],
                "g": color[1],
                "b": color[2],
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            }
        }
    
    def get_screen_size(self, **kwargs) -> Dict[str, Any]:
        """화면 크기 가져오기"""
        width, height = pyautogui.size()
        return {"width": width, "height": height}
    
    def move_to_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """이미지 위치로 마우스 이동"""
        # 이미지 경로
        image_path = kwargs.get("image_path")
        
        if not image_path:
            raise ValueError("이미지 경로가 지정되지 않았습니다")
        
        # 이동 옵션
        confidence = kwargs.get("confidence", self.config.get("default_confidence", 0.9))
        region = kwargs.get("region")
        grayscale = kwargs.get("grayscale", False)
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 이미지 찾기
        try:
            location = pyautogui.locateOnScreen(
                image_path,
                confidence=confidence,
                region=region,
                grayscale=grayscale
            )
            
            if location:
                center_x, center_y = pyautogui.center(location)
                pyautogui.moveTo(center_x, center_y, duration=duration)
                
                return {
                    "found": True,
                    "x": center_x,
                    "y": center_y
                }
            else:
                logger.warning(f"이미지를 찾을 수 없음: {image_path}")
                return {"found": False}
                
        except Exception as e:
            logger.error(f"이미지로 이동 중 오류: {str(e)}")
            return {"found": False, "error": str(e)}
    
    def click_image(self, **kwargs) -> Optional[Dict[str, Any]]:
        """이미지 클릭"""
        # 이미지 경로
        image_path = kwargs.get("image_path")
        
        if not image_path:
            raise ValueError("이미지 경로가 지정되지 않았습니다")
        
        # 클릭 옵션
        confidence = kwargs.get("confidence", self.config.get("default_confidence", 0.9))
        region = kwargs.get("region")
        grayscale = kwargs.get("grayscale", False)
        button = kwargs.get("button", "left")  # left, right, middle
        clicks = kwargs.get("clicks", 1)
        interval = kwargs.get("interval", 0.0)
        duration = kwargs.get("duration", self.config.get("move_duration", 0.5))
        
        # 이미지 찾기 및 클릭
        try:
            location = pyautogui.locateOnScreen(
                image_path,
                confidence=confidence,
                region=region,
                grayscale=grayscale
            )
            
            if location:
                center_x, center_y = pyautogui.center(location)
                pyautogui.click(
                    center_x, center_y,
                    clicks=clicks,
                    interval=interval,
                    button=button,
                    duration=duration
                )
                
                return {
                    "found": True,
                    "clicked": True,
                    "x": center_x,
                    "y": center_y,
                    "button": button,
                    "clicks": clicks
                }
            else:
                logger.warning(f"이미지를 찾을 수 없음: {image_path}")
                return {"found": False, "clicked": False}
                
        except Exception as e:
            logger.error(f"이미지 클릭 중 오류: {str(e)}")
            return {"found": False, "clicked": False, "error": str(e)}
    
    def alert(self, **kwargs) -> bool:
        """알림 메시지 표시"""
        # 메시지
        text = kwargs.get("text", "")
        title = kwargs.get("title", "알림")
        
        # 알림 표시
        pyautogui.alert(text=text, title=title)
        
        return True
    
    def confirm(self, **kwargs) -> bool:
        """확인 메시지 표시"""
        # 메시지
        text = kwargs.get("text", "")
        title = kwargs.get("title", "확인")
        
        # 확인 메시지 표시
        result = pyautogui.confirm(text=text, title=title, buttons=["OK", "Cancel"])
        
        return result == "OK"
    
    def prompt(self, **kwargs) -> str:
        """입력 메시지 표시"""
        # 메시지
        text = kwargs.get("text", "")
        title = kwargs.get("title", "입력")
        default = kwargs.get("default", "")
        
        # 입력 메시지 표시
        result = pyautogui.prompt(text=text, title=title, default=default)
        
        return result
    
    def copy_to_clipboard(self, **kwargs) -> bool:
        """클립보드에 텍스트 복사"""
        # 텍스트
        text = kwargs.get("text")
        
        if text is None:
            raise ValueError("텍스트가 지정되지 않았습니다")
        
        # 클립보드에 복사
        pyperclip.copy(text)
        
        return True
    
    def paste_from_clipboard(self, **kwargs) -> str:
        """클립보드에서 텍스트 붙여넣기"""
        return pyperclip.paste()