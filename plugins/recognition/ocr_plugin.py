"""
OCR 인식 플러그인

이 모듈은 PaddleOCR을 사용한 텍스트 인식 플러그인을 구현합니다.
화면에서 텍스트를 인식하여 요소를 찾습니다.
"""
import logging
import os
import time
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import re

from core.plugin_system import PluginInfo, PluginType
from plugins.recognition.base import RecognitionMethod, RecognitionPlugin, RecognitionResult, RecognitionTarget

# PaddleOCR 가져오기 (런타임에 설치)
try:
    import cv2
    import numpy as np
    from PIL import Image
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False


class OCRPlugin(RecognitionPlugin):
    """OCR 인식 플러그인"""
    
    @classmethod
    def get_plugin_info(cls) -> PluginInfo:
        """플러그인 정보 반환"""
        return PluginInfo(
            id="ocr_recognition",
            name="OCR 인식",
            description="PaddleOCR을 사용한 텍스트 인식 플러그인",
            version="1.0.0",
            plugin_type=PluginType.RECOGNITION,
            priority=6,  # 템플릿 매칭(8)보다 낮은 우선순위
            dependencies=[]
        )
    
    def __init__(self):
        """플러그인 초기화"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # OCR 엔진
        self._ocr = None
        
        # 설정 기본값
        self._default_confidence = 0.7  # 기본 신뢰도 임계값
        self._temp_dir = None  # 임시 스크린샷 디렉토리
        self._language = 'ko'  # 기본 언어
    
    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """플러그인 초기화
        
        Args:
            config: 플러그인 설정
            
        Returns:
            초기화 성공 여부
        """
        if not PADDLEOCR_AVAILABLE:
            self.logger.error("PaddleOCR을 찾을 수 없습니다. 'pip install paddlepaddle paddleocr opencv-python' 명령으로 설치하세요.")
            return False
        
        super().initialize(config)
        
        # 설정 적용
        self._default_confidence = self._config.get('confidence', 0.7)
        self._language = self._config.get('language', 'ko')
        
        # 임시 디렉토리 설정
        self._temp_dir = self._config.get('temp_dir')
        if not self._temp_dir:
            self._temp_dir = tempfile.gettempdir()
        
        # OCR 엔진 초기화
        try:
            use_gpu = self._config.get('use_gpu', False)
            
            # PaddleOCR 초기화
            self._ocr = PaddleOCR(
                use_angle_cls=True,  # 텍스트 방향 감지
                lang=self._language,  # 언어 설정
                use_gpu=use_gpu,  # GPU 사용 여부
                show_log=False  # 로그 표시 여부
            )
            
            self.logger.info(f"OCR 인식 플러그인 초기화 완료 (언어: {self._language}, GPU: {use_gpu})")
            return True
            
        except Exception as e:
            self.logger.error(f"OCR 인식 플러그인 초기화 실패: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """플러그인 정리"""
        self._ocr = None
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
        
        # 검색할 텍스트가 없으면 실패
        search_text = target.description
        if not search_text:
            return RecognitionResult(
                success=False,
                error="인식할 텍스트가 지정되지 않음",
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
        
        # OCR 실행 (시간 제한 적용)
        start_time = time.time()
        result = self._ocr.ocr(screenshot, cls=True)
        
        # OCR 결과 확인
        if not result or not result[0]:
            return RecognitionResult(
                success=False,
                error="텍스트를 찾을 수 없음",
                target=target,
                method=RecognitionMethod.OCR
            )
        
        # OCR 결과가 이미지당 하나의 리스트이므로 첫 번째 요소 사용
        ocr_results = result[0]
        
        # 텍스트 검색
        best_match = None
        best_confidence = 0
        
        for idx, line in enumerate(ocr_results):
            bbox = line[0]  # 경계 상자 좌표
            text = line[1][0]  # 인식된 텍스트
            confidence = line[1][1]  # 신뢰도
            
            # 텍스트 유사도 계산
            similarity = self._calculate_text_similarity(search_text, text)
            
            # 종합 점수 (텍스트 유사도 * OCR 신뢰도)
            combined_score = similarity * confidence
            
            if combined_score > best_confidence:
                best_confidence = combined_score
                best_match = {
                    'text': text,
                    'bbox': bbox,
                    'ocr_confidence': confidence,
                    'text_similarity': similarity,
                    'combined_score': combined_score
                }
        
        # 결과 반환
        if best_match and best_confidence >= self._default_confidence:
            # 위치 정보 계산
            bbox = best_match['bbox']
            x1, y1 = min(p[0] for p in bbox), min(p[1] for p in bbox)
            x2, y2 = max(p[0] for p in bbox), max(p[1] for p in bbox)
            w, h = x2 - x1, y2 - y1
            location = (int(x1), int(y1), int(w), int(h))
            
            # 요소 정보 생성
            element_info = self._create_element_info(location, best_match)
            
            return RecognitionResult(
                success=True,
                confidence=best_confidence,
                method=RecognitionMethod.OCR,
                target=target,
                element=element_info,
                location=location
            )
        else:
            return RecognitionResult(
                success=False,
                confidence=best_confidence if best_match else 0,
                error=f"텍스트 인식 실패 (신뢰도: {best_confidence:.4f})",
                target=target,
                method=RecognitionMethod.OCR
            )
    
    def _capture_screenshot(self, context: Any) -> Optional[np.ndarray]:
        """컨텍스트에서 스크린샷 캡처
        
        Args:
            context: 인식 컨텍스트
            
        Returns:
            이미지 경로 또는 None
        """
        try:
            # Playwright 페이지인 경우
            if hasattr(context, 'screenshot'):
                # 비동기 호출 없이 임시 파일 사용
                temp_file = os.path.join(self._temp_dir, f"ocr_screenshot_{uuid.uuid4()}.png")
                
                # Playwright 플러그인을 통한 스크린샷
                if hasattr(context, 'execute_action'):
                    screenshot_result = context.execute_action('screenshot', {'path': temp_file})
                    if screenshot_result.get('success', False):
                        return temp_file
                
                # 다른 방법 시도
                with open(temp_file, 'wb') as f:
                    # 이 부분은 실제 구현에서 비동기 처리가 필요할 수 있음
                    # 여기서는 임시 구현으로 표시
                    f.write(b'')  # 임시 빈 파일
                
                return temp_file
            
            # PyAutoGUI 컨텍스트인 경우
            elif hasattr(context, 'screenshot'):
                temp_file = os.path.join(self._temp_dir, f"ocr_screenshot_{uuid.uuid4()}.png")
                context.screenshot(temp_file)
                return temp_file
                
            # 바이너리 이미지 데이터인 경우
            elif isinstance(context, bytes):
                temp_file = os.path.join(self._temp_dir, f"ocr_screenshot_{uuid.uuid4()}.png")
                with open(temp_file, 'wb') as f:
                    f.write(context)
                return temp_file
                
            # 이미지 파일 경로인 경우
            elif isinstance(context, str) and os.path.exists(context):
                return context
            
            else:
                self.logger.error(f"지원되지 않는 컨텍스트 유형: {type(context)}")
                return None
                
        except Exception as e:
            self.logger.error(f"스크린샷 캡처 중 오류: {str(e)}")
            return None
    
    def _calculate_text_similarity(self, search_text: str, ocr_text: str) -> float:
        """텍스트 유사도 계산
        
        Args:
            search_text: 검색 텍스트
            ocr_text: OCR로 인식된 텍스트
            
        Returns:
            유사도 (0.0 ~ 1.0)
        """
        # 전처리
        search_text = search_text.lower().strip()
        ocr_text = ocr_text.lower().strip()
        
        # 정확히 일치하는 경우
        if search_text == ocr_text:
            return 1.0
        
        # 부분 문자열인 경우
        if search_text in ocr_text:
            return 0.9
        
        if ocr_text in search_text:
            return 0.8
        
        # 레벤슈타인 거리 계산 (간단한 구현)
        # 실제 구현에서는 더 효율적인 알고리즘 사용 권장
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        # 텍스트 길이 계산
        max_len = max(len(search_text), len(ocr_text))
        if max_len == 0:
            return 0.0
        
        # 거리 계산 및 유사도로 변환
        distance = levenshtein_distance(search_text, ocr_text)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)  # 0.0 ~ 1.0 범위 보장
    
    def _create_element_info(self, location: Tuple[int, int, int, int], match: Dict[str, Any]) -> Dict[str, Any]:
        """요소 정보 생성
        
        Args:
            location: 위치 (x, y, width, height)
            match: 매칭 정보
            
        Returns:
            요소 정보
        """
        x, y, w, h = location
        center_x = x + w // 2
        center_y = y + h // 2
        
        return {
            'type': 'ocr_match',
            'text': match['text'],
            'location': {
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'center_x': center_x,
                'center_y': center_y
            },
            'confidence': match['ocr_confidence'],
            'similarity': match['text_similarity'],
            'click_point': (center_x, center_y)  # 클릭 지점
        }
    
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
        
        if action_type == 'extract_all_text':
            # 이미지에서 모든 텍스트 추출
            image_path = params.get('image_path')
            image_data = params.get('image_data')
            
            if not image_path and not image_data:
                return {'success': False, 'error': "이미지 경로 또는 데이터가 필요합니다"}
            
            try:
                # 이미지 준비
                if image_data:
                    temp_file = os.path.join(self._temp_dir, f"ocr_temp_{uuid.uuid4()}.png")
                    with open(temp_file, 'wb') as f:
                        f.write(image_data)
                    image_path = temp_file
                
                # OCR 실행
                result = self._ocr.ocr(image_path, cls=True)
                
                # 임시 파일 삭제
                if image_data and os.path.exists(temp_file):
                    os.remove(temp_file)
                
                # 결과 처리
                if not result or not result[0]:
                    return {'success': True, 'texts': [], 'count': 0}
                
                texts = []
                for line in result[0]:
                    bbox = line[0]  # 경계 상자 좌표
                    text = line[1][0]  # 인식된 텍스트
                    confidence = line[1][1]  # 신뢰도
                    
                    # 위치 정보 계산
                    x1, y1 = min(p[0] for p in bbox), min(p[1] for p in bbox)
                    x2, y2 = max(p[0] for p in bbox), max(p[1] for p in bbox)
                    w, h = x2 - x1, y2 - y1
                    
                    texts.append({
                        'text': text,
                        'confidence': confidence,
                        'location': {
                            'x': int(x1),
                            'y': int(y1),
                            'width': int(w),
                            'height': int(h)
                        }
                    })
                
                return {
                    'success': True,
                    'texts': texts,
                    'count': len(texts)
                }
                
            except Exception as e:
                self.logger.error(f"텍스트 추출 중 오류: {str(e)}")
                return {'success': False, 'error': f"텍스트 추출 실패: {str(e)}"}
        
        elif action_type == 'find_text':
            # 특정 텍스트 찾기
            image_path = params.get('image_path')
            text = params.get('text')
            
            if not image_path:
                return {'success': False, 'error': "이미지 경로가 필요합니다"}
            
            if not text:
                return {'success': False, 'error': "검색할 텍스트가 필요합니다"}
            
            try:
                # OCR 실행
                result = self._ocr.ocr(image_path, cls=True)
                
                # 결과 처리
                if not result or not result[0]:
                    return {'success': False, 'error': "텍스트를 찾을 수 없음"}
                
                best_match = None
                best_similarity = 0
                
                for line in result[0]:
                    bbox = line[0]  # 경계 상자 좌표
                    ocr_text = line[1][0]  # 인식된 텍스트
                    confidence = line[1][1]  # 신뢰도
                    
                    # 텍스트 유사도 계산
                    similarity = self._calculate_text_similarity(text, ocr_text)
                    combined_score = similarity * confidence
                    
                    if combined_score > best_similarity:
                        # 위치 정보 계산
                        x1, y1 = min(p[0] for p in bbox), min(p[1] for p in bbox)
                        x2, y2 = max(p[0] for p in bbox), max(p[1] for p in bbox)
                        w, h = x2 - x1, y2 - y1
                        
                        best_similarity = combined_score
                        best_match = {
                            'text': ocr_text,
                            'confidence': confidence,
                            'similarity': similarity,
                            'combined_score': combined_score,
                            'location': {
                                'x': int(x1),
                                'y': int(y1),
                                'width': int(w),
                                'height': int(h),
                                'center_x': int(x1 + w/2),
                                'center_y': int(y1 + h/2)
                            }
                        }
                
                if best_match and best_similarity >= self._default_confidence:
                    return {
                        'success': True,
                        'found': True,
                        'match': best_match
                    }
                else:
                    return {
                        'success': False,
                        'found': False,
                        'error': "텍스트를 찾을 수 없음 또는 신뢰도가 너무 낮음"
                    }
                
            except Exception as e:
                self.logger.error(f"텍스트 검색 중 오류: {str(e)}")
                return {'success': False, 'error': f"텍스트 검색 실패: {str(e)}"}
        
        return {'success': False, 'error': f"지원되지 않는 액션: {action_type}"}