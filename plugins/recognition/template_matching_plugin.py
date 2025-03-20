"""
템플릿 매칭 인식 플러그인

이 모듈은 OpenCV를 사용한 템플릿 매칭 인식 플러그인을 구현합니다.
이미지 템플릿을 사용하여 화면 요소를 인식합니다.
"""
import logging
import os
import time
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from core.plugin_system import PluginInfo, PluginType
from plugins.recognition.base import RecognitionMethod, RecognitionPlugin, RecognitionResult, RecognitionTarget

# OpenCV 가져오기 (런타임에 설치)
try:
    import cv2
    import numpy as np
    from PIL import Image
    import io
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class TemplateMatchingPlugin(RecognitionPlugin):
    """템플릿 매칭 인식 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="template_matching_recognition",
            name="템플릿 매칭 인식",
            description="OpenCV를 사용한 템플릿 매칭 인식 플러그인",
            version="1.0.0",
            plugin_type=PluginType.RECOGNITION,
            priority=8,  # 선택자 기반(10)보다 낮은 우선순위
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 설정 기본값
        self._default_confidence = 0.8  # 기본 신뢰도 임계값
        self._template_dir = None  # 템플릿 이미지 디렉토리
        self._temp_dir = None  # 임시 스크린샷 디렉토리
        self._matching_methods = [cv2.TM_CCOEFF_NORMED]  # 기본 매칭 메서드
        self._resize_factors = [1.0]  # 기본 크기 조정 요소
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        if not OPENCV_AVAILABLE:
            self.logger.error("OpenCV를 찾을 수 없습니다. 'pip install opencv-python pillow' 명령으로 설치하세요.")
            return False
        
        super().initialize(config)
        
        # 설정 적용
        self._default_confidence = self._config.get('confidence', 0.8)
        
        # 템플릿 디렉토리 설정
        self._template_dir = self._config.get('template_dir')
        if self._template_dir:
            os.makedirs(self._template_dir, exist_ok=True)
        else:
            self._template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
            os.makedirs(self._template_dir, exist_ok=True)
        
        # 임시 디렉토리 설정
        self._temp_dir = self._config.get('temp_dir')
        if not self._temp_dir:
            self._temp_dir = tempfile.gettempdir()
        
        # 매칭 메서드 설정
        method_names = self._config.get('matching_methods', ['TM_CCOEFF_NORMED'])
        self._matching_methods = []
        method_map = {
            'TM_CCOEFF': cv2.TM_CCOEFF,
            'TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'TM_CCORR': cv2.TM_CCORR,
            'TM_CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'TM_SQDIFF': cv2.TM_SQDIFF,
            'TM_SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED
        }
        
        for method_name in method_names:
            if method_name in method_map:
                self._matching_methods.append(method_map[method_name])
        
        # 기본값이 없는 경우
        if not self._matching_methods:
            self._matching_methods = [cv2.TM_CCOEFF_NORMED]
        
        # 크기 조정 요소 설정
        self._resize_factors = self._config.get('resize_factors', [1.0, 0.9, 1.1])
        
        self.logger.info("템플릿 매칭 인식 플러그인 초기화 완료")
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
        
        # 이미지 템플릿 찾기
        template_paths = self._find_template_images(target)
        if not template_paths:
            return RecognitionResult(
                success=False,
                error="인식할 템플릿 이미지를 찾을 수 없음",
                target=target
            )
        
        # 스크린샷 캡처
        screenshot = self._capture_screenshot(context)
        if screenshot is None:
            return RecognitionResult(
                success=False,
                error="스크린샷 캡처 실패",
                target=target
            )
        
        # 템플릿 매칭 수행
        best_match = None
        best_confidence = 0
        best_location = None
        best_template_path = None
        
        for template_path in template_paths:
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                self.logger.warning(f"템플릿 이미지를 로드할 수 없음: {template_path}")
                continue
            
            for factor in self._resize_factors:
                resized_template = template
                if factor != 1.0:
                    new_width = int(template.shape[1] * factor)
                    new_height = int(template.shape[0] * factor)
                    resized_template = cv2.resize(template, (new_width, new_height))
                
                for method in self._matching_methods:
                    result = cv2.matchTemplate(screenshot, resized_template, method)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # 매칭 방법에 따라 최적의 위치와 값 결정
                    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                        confidence = 1 - min_val
                        loc = min_loc
                    else:
                        confidence = max_val
                        loc = max_loc
                    
                    # 최상의 매칭 업데이트
                    if confidence > best_confidence:
                        best_confidence = confidence
                        x, y = loc
                        w, h = resized_template.shape[1], resized_template.shape[0]
                        best_location = (x, y, w, h)
                        best_template_path = template_path
        
        # 결과 반환
        if best_confidence >= self._default_confidence:
            # 요소 정보 생성
            element_info = self._create_element_info(best_location, best_template_path)
            
            return RecognitionResult(
                success=True,
                confidence=best_confidence,
                method=RecognitionMethod.TEMPLATE,
                target=target,
                element=element_info,
                location=best_location
            )
        else:
            return RecognitionResult(
                success=False,
                confidence=best_confidence,
                error=f"템플릿 매칭 실패 (신뢰도: {best_confidence:.4f})",
                target=target,
                method=RecognitionMethod.TEMPLATE
            )
    
    def _find_template_images(self, target: RecognitionTarget) -> List[str]:
        """대상에 맞는 템플릿 이미지 찾기
        
        Args:
            target: 인식 대상
            
        Returns:
            템플릿 이미지 경로 목록
        """
        template_paths = []
        
        # 타입별 파일이름 패턴
        type_name = target.type.lower()
        description = target.description.lower()
        
        # 1. 속성에 이미지 경로가 제공된 경우
        if 'image_path' in target.attributes:
            image_path = target.attributes['image_path']
            if os.path.isabs(image_path):
                if os.path.exists(image_path):
                    template_paths.append(image_path)
            else:
                # 상대 경로는 템플릿 디렉토리에서 검색
                full_path = os.path.join(self._template_dir, image_path)
                if os.path.exists(full_path):
                    template_paths.append(full_path)
        
        # 2. 타입 및 설명을 기반으로 템플릿 찾기
        # 예: button_login.png, button_submit.png 등
        if type_name and description:
            pattern = f"{type_name}_{description.replace(' ', '_')}.png"
            path = os.path.join(self._template_dir, pattern)
            if os.path.exists(path):
                template_paths.append(path)
        
        # 3. 타입만으로 템플릿 찾기
        # 예: button_*.png
        if type_name:
            for filename in os.listdir(self._template_dir):
                if filename.startswith(f"{type_name}_") and filename.endswith(".png"):
                    template_paths.append(os.path.join(self._template_dir, filename))
        
        return template_paths
    
    def _capture_screenshot(self, context: Any) -> Optional[np.ndarray]:
        """컨텍스트에서 스크린샷 캡처
        
        Args:
            context: 인식 컨텍스트
            
        Returns:
            OpenCV 이미지 또는 None
        """
        try:
            # Playwright 페이지인 경우
            if hasattr(context, 'screenshot'):
                # 비동기 호출 없이 임시 파일 사용
                temp_file = os.path.join(self._temp_dir, f"screenshot_{uuid.uuid4()}.png")
                
                # Playwright 플러그인을 통한 스크린샷
                if hasattr(context, 'execute_action'):
                    screenshot_result = context.execute_action('screenshot', {'path': temp_file})
                    if screenshot_result.get('success', False):
                        screenshot = cv2.imread(temp_file, cv2.IMREAD_COLOR)
                        os.remove(temp_file)
                        return screenshot
                
                # 다른 방법 시도
                with open(temp_file, 'wb') as f:
                    # 이 부분은 실제 구현에서 비동기 처리가 필요할 수 있음
                    # 여기서는 임시 구현으로 표시
                    f.write(b'')  # 임시 빈 파일
                
                screenshot = cv2.imread(temp_file, cv2.IMREAD_COLOR)
                os.remove(temp_file)
                return screenshot
            
            # PyAutoGUI 컨텍스트인 경우
            elif hasattr(context, 'screenshot'):
                temp_file = os.path.join(self._temp_dir, f"screenshot_{uuid.uuid4()}.png")
                context.screenshot(temp_file)
                screenshot = cv2.imread(temp_file, cv2.IMREAD_COLOR)
                os.remove(temp_file)
                return screenshot
                
            # 바이너리 이미지 데이터인 경우
            elif isinstance(context, bytes):
                nparr = np.frombuffer(context, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
            # 이미지 파일 경로인 경우
            elif isinstance(context, str) and os.path.exists(context):
                return cv2.imread(context, cv2.IMREAD_COLOR)
            
            else:
                self.logger.error(f"지원되지 않는 컨텍스트 유형: {type(context)}")
                return None
                
        except Exception as e:
            self.logger.error(f"스크린샷 캡처 중 오류: {str(e)}")
            return None
    
    def _create_element_info(self, location: Tuple[int, int, int, int], template_path: str) -> Dict[str, Any]:
        """요소 정보 생성
        
        Args:
            location: 위치 (x, y, width, height)
            template_path: 사용된 템플릿 경로
            
        Returns:
            요소 정보
        """
        x, y, w, h = location
        center_x = x + w // 2
        center_y = y + h // 2
        
        return {
            'type': 'template_match',
            'location': {
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'center_x': center_x,
                'center_y': center_y
            },
            'template_path': template_path,
            'click_point': (center_x, center_y)  # 클릭 지점
        }

    def add_template(self, image_data: bytes, target_type: str, description: str = "") -> str:
        """템플릿 추가
        
        Args:
            image_data: 이미지 데이터
            target_type: 대상 유형
            description: 설명
            
        Returns:
            템플릿 파일 경로
        """
        try:
            # 파일명 생성
            if description:
                filename = f"{target_type}_{description.replace(' ', '_')}.png"
            else:
                filename = f"{target_type}_{uuid.uuid4()}.png"
            
            # 중복 방지
            filepath = os.path.join(self._template_dir, filename)
            counter = 1
            while os.path.exists(filepath):
                if description:
                    filename = f"{target_type}_{description.replace(' ', '_')}_{counter}.png"
                else:
                    filename = f"{target_type}_{uuid.uuid4()}.png"
                filepath = os.path.join(self._template_dir, filename)
                counter += 1
            
            # 이미지 저장
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            self.logger.info(f"템플릿 추가됨: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"템플릿 추가 중 오류: {str(e)}")
            return None
    
    def remove_template(self, template_path: str) -> bool:
        """템플릿 제거
        
        Args:
            template_path: 템플릿 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            if os.path.exists(template_path):
                os.remove(template_path)
                self.logger.info(f"템플릿 제거됨: {template_path}")
                return True
            else:
                self.logger.warning(f"템플릿을 찾을 수 없음: {template_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"템플릿 제거 중 오류: {str(e)}")
            return False
    
    def execute_action(self, action_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """액션 실행
        
        Args:
            action_type: 액션 유형
            params: 액션 파라미터
            
        Returns:
            액션 결과
        """
        super_result = super().execute_action(action_type, params)
        if super_result.get('success', False) or action_type == 'recognize':
            return super_result
        
        params = params or {}
        
        if action_type == 'add_template':
            # 템플릿 추가
            image_data = params.get('image_data')
            target_type = params.get('target_type')
            description = params.get('description', '')
            
            if not image_data or not target_type:
                return {'success': False, 'error': "이미지 데이터와 대상 유형이 필요합니다"}
            
            filepath = self.add_template(image_data, target_type, description)
            if filepath:
                return {'success': True, 'filepath': filepath}
            else:
                return {'success': False, 'error': "템플릿 추가 실패"}
        
        elif action_type == 'remove_template':
            # 템플릿 제거
            template_path = params.get('template_path')
            
            if not template_path:
                return {'success': False, 'error': "템플릿 경로가 필요합니다"}
            
            success = self.remove_template(template_path)
            if success:
                return {'success': True}
            else:
                return {'success': False, 'error': "템플릿 제거 실패"}
        
        return {'success': False, 'error': f"지원되지 않는 액션: {action_type}"}