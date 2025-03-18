 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 템플릿 매칭 인식 플러그인
OpenCV 기반 템플릿 매칭을 이용한 이미지 인식 플러그인
"""

import logging
import os
import time
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
import json
import tempfile
import base64
import io
from PIL import Image
import numpy as np
import cv2

from core.plugin_manager import PluginInterface

logger = logging.getLogger(__name__)

class TemplateMatchingPlugin(PluginInterface):
    """OpenCV 기반 템플릿 매칭 이미지 인식 플러그인"""
    
    plugin_type = "recognition"
    plugin_name = "template_matching"
    plugin_version = "0.1.0"
    plugin_description = "OpenCV 기반 템플릿 매칭 이미지 인식 플러그인"
    
    def __init__(self):
        super().__init__()
        self.templates_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "templates")
        
        # 설정 기본값
        self.config = {
            "default_threshold": 0.8,
            "default_method": cv2.TM_CCOEFF_NORMED,
            "max_results": 10,
            "debug_mode": False,
            "debug_output_dir": os.path.join(os.path.expanduser("~"), "BlueAI", "debug")
        }
        
        # 템플릿 디렉토리 생성
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 디버그 출력 디렉토리 생성
        if self.config["debug_mode"]:
            os.makedirs(self.config["debug_output_dir"], exist_ok=True)
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            # OpenCV 버전 확인
            logger.info(f"OpenCV 버전: {cv2.__version__}")
            return True
        except Exception as e:
            logger.error(f"템플릿 매칭 플러그인 초기화 실패: {str(e)}")
            return False
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        return True
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        try:
            self.config.update(config)
            
            # 디버그 모드가 활성화된 경우 디렉토리 생성
            if self.config.get("debug_mode", False):
                os.makedirs(self.config["debug_output_dir"], exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"템플릿 매칭 플러그인 설정 중 오류: {str(e)}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return [
            "match_template",
            "find_all_templates",
            "save_template",
            "create_template_from_region",
            "load_template",
            "delete_template",
            "list_templates",
            "create_template_from_base64",
            "match_multiple_templates",
            "feature_matching"
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
            raise
    
    def _load_image(self, image_data: Any) -> np.ndarray:
        """이미지 데이터 로드"""
        try:
            # 파일 경로인 경우
            if isinstance(image_data, str) and os.path.exists(image_data):
                return cv2.imread(image_data)
            
            # PIL Image 인스턴스인 경우
            if hasattr(image_data, 'mode') and hasattr(image_data, 'size'):
                return cv2.cvtColor(np.array(image_data), cv2.COLOR_RGB2BGR)
            
            # 이미 NumPy 배열인 경우
            if isinstance(image_data, np.ndarray):
                return image_data
            
            # base64 문자열인 경우
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                # base64 데이터 URI에서 인코딩된 부분 추출
                encoded_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(encoded_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 바이트 배열인 경우
            if isinstance(image_data, bytes):
                nparr = np.frombuffer(image_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            raise TypeError(f"지원하지 않는 이미지 데이터 타입: {type(image_data)}")
            
        except Exception as e:
            logger.error(f"이미지 로드 중 오류: {str(e)}")
            raise
    
    def _save_debug_image(self, image: np.ndarray, name: str) -> str:
        """디버그 이미지 저장"""
        if not self.config.get("debug_mode", False):
            return ""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.config["debug_output_dir"], filename)
            
            cv2.imwrite(filepath, image)
            logger.debug(f"디버그 이미지 저장됨: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"디버그 이미지 저장 중 오류: {str(e)}")
            return ""
    
    def match_template(self, **kwargs) -> Dict[str, Any]:
        """템플릿 매칭 수행"""
        # 이미지 및 템플릿
        image = kwargs.get("image")
        template_path = kwargs.get("template_path")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if template_path is None:
            raise ValueError("템플릿 경로가 지정되지 않았습니다")
        
        # 매칭 옵션
        threshold = kwargs.get("threshold", self.config.get("default_threshold", 0.8))
        method = kwargs.get("method", self.config.get("default_method", cv2.TM_CCOEFF_NORMED))
        
        # 이미지 로드
        img = self._load_image(image)
        template = self._load_image(template_path)
        
        # 이미지 및 템플릿 검증
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        if template is None:
            raise ValueError("템플릿 로드 실패")
        
        # 이미지 및 템플릿 크기 확인
        img_height, img_width = img.shape[:2]
        template_height, template_width = template.shape[:2]
        
        if template_height > img_height or template_width > img_width:
            raise ValueError("템플릿이 이미지보다 큽니다")
        
        # 디버그 모드인 경우 이미지 저장
        if self.config.get("debug_mode", False):
            self._save_debug_image(img, "source")
            self._save_debug_image(template, "template")
        
        # 템플릿 매칭 수행
        result = cv2.matchTemplate(img, template, method)
        
        # 최대값/최소값 및 위치 찾기
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 매칭 방법에 따라 최적 위치 결정
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            match_val = 1.0 - min_val  # 값 반전 (작을수록 좋음 -> 클수록 좋음)
            match_loc = min_loc
        else:
            match_val = max_val
            match_loc = max_loc
        
        # 임계값 확인
        matches = []
        if match_val >= threshold:
            # 매칭 영역 좌표
            top_left = match_loc
            bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
            center = (top_left[0] + template_width // 2, top_left[1] + template_height // 2)
            
            matches.append({
                "top_left": {"x": top_left[0], "y": top_left[1]},
                "bottom_right": {"x": bottom_right[0], "y": bottom_right[1]},
                "center": {"x": center[0], "y": center[1]},
                "confidence": float(match_val)
            })
            
            # 디버그 모드인 경우 결과 표시
            if self.config.get("debug_mode", False):
                debug_img = img.copy()
                cv2.rectangle(debug_img, top_left, bottom_right, (0, 255, 0), 2)
                cv2.circle(debug_img, center, 5, (0, 0, 255), -1)
                self._save_debug_image(debug_img, "match_result")
        
        return {
            "matches": matches,
            "best_match": matches[0] if matches else None,
            "match_count": len(matches)
        }
    
    def find_all_templates(self, **kwargs) -> Dict[str, Any]:
        """모든 템플릿 매칭 찾기"""
        # 이미지 및 템플릿
        image = kwargs.get("image")
        template_path = kwargs.get("template_path")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if template_path is None:
            raise ValueError("템플릿 경로가 지정되지 않았습니다")
        
        # 매칭 옵션
        threshold = kwargs.get("threshold", self.config.get("default_threshold", 0.8))
        method = kwargs.get("method", self.config.get("default_method", cv2.TM_CCOEFF_NORMED))
        max_results = kwargs.get("max_results", self.config.get("max_results", 10))
        
        # 이미지 로드
        img = self._load_image(image)
        template = self._load_image(template_path)
        
        # 이미지 및 템플릿 검증
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        if template is None:
            raise ValueError("템플릿 로드 실패")
        
        # 이미지 및 템플릿 크기 확인
        img_height, img_width = img.shape[:2]
        template_height, template_width = template.shape[:2]
        
        if template_height > img_height or template_width > img_width:
            raise ValueError("템플릿이 이미지보다 큽니다")
        
        # 디버그 모드인 경우 이미지 저장
        if self.config.get("debug_mode", False):
            self._save_debug_image(img, "source")
            self._save_debug_image(template, "template")
        
        # 템플릿 매칭 수행
        result = cv2.matchTemplate(img, template, method)
        
        # 매칭 방법에 따라 임계값 처리
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            # SQDIFF 방법은 값이 작을수록 유사, 임계값 반전 필요
            threshold_mask = result <= (1.0 - threshold)
        else:
            threshold_mask = result >= threshold
        
        # 비최대 억제 적용 (겹치는 검출 제거)
        matches = []
        
        # 결과 복사 및 마스킹
        result_copy = result.copy()
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            # SQDIFF 방법은 값이 작을수록 유사, 값 반전
            result_copy = 1.0 - result_copy
        
        result_copy[~threshold_mask] = 0
        
        # 디버그 이미지
        debug_img = None
        if self.config.get("debug_mode", False):
            debug_img = img.copy()
        
        # 최대 결과 개수만큼 반복
        for i in range(min(max_results, np.sum(threshold_mask))):
            # 최대값/위치 찾기
            _, max_val, _, max_loc = cv2.minMaxLoc(result_copy)
            
            if max_val <= 0:
                break
            
            # 매칭 영역 좌표
            top_left = max_loc
            bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
            center = (top_left[0] + template_width // 2, top_left[1] + template_height // 2)
            
            matches.append({
                "top_left": {"x": top_left[0], "y": top_left[1]},
                "bottom_right": {"x": bottom_right[0], "y": bottom_right[1]},
                "center": {"x": center[0], "y": center[1]},
                "confidence": float(max_val)
            })
            
            # 디버그 이미지에 표시
            if debug_img is not None:
                cv2.rectangle(debug_img, top_left, bottom_right, (0, 255, 0), 2)
                cv2.circle(debug_img, center, 5, (0, 0, 255), -1)
                cv2.putText(debug_img, f"{max_val:.2f}", top_left, 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # 현재 매칭 주변 영역 제거 (겹침 방지)
            x1, y1 = max(0, top_left[0] - template_width // 4), max(0, top_left[1] - template_height // 4)
            x2, y2 = min(result_copy.shape[1], bottom_right[0] + template_width // 4), min(result_copy.shape[0], bottom_right[1] + template_height // 4)
            result_copy[y1:y2, x1:x2] = 0
        
        # 디버그 모드인 경우 결과 표시
        if debug_img is not None:
            self._save_debug_image(debug_img, "all_matches")
        
        return {
            "matches": matches,
            "best_match": matches[0] if matches else None,
            "match_count": len(matches)
        }
    
    def save_template(self, **kwargs) -> Dict[str, Any]:
        """템플릿 저장"""
        # 이미지 및 이름
        image = kwargs.get("image")
        name = kwargs.get("name")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if name is None:
            raise ValueError("템플릿 이름이 지정되지 않았습니다")
        
        # 유효한 파일명 생성
        valid_name = "".join(c for c in name if c.isalnum() or c in "._- ")
        if not valid_name:
            valid_name = f"template_{int(time.time())}"
        
        # 파일 확장자 확인
        if not valid_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            valid_name += '.png'
        
        # 저장 경로
        template_path = os.path.join(self.templates_dir, valid_name)
        
        # 이미지 로드 및 저장
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        cv2.imwrite(template_path, img)
        
        logger.info(f"템플릿 저장됨: {template_path}")
        return {
            "name": valid_name,
            "path": template_path
        }
    
    def create_template_from_region(self, **kwargs) -> Dict[str, Any]:
        """이미지의 특정 영역에서 템플릿 생성"""
        # 이미지 및 영역
        image = kwargs.get("image")
        region = kwargs.get("region")
        name = kwargs.get("name")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if region is None:
            raise ValueError("영역이 지정되지 않았습니다")
        
        if name is None:
            name = f"region_template_{int(time.time())}"
        
        # 영역 파라미터 추출
        x, y, width, height = region
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 영역 검증
        img_height, img_width = img.shape[:2]
        
        if x < 0 or y < 0 or x + width > img_width or y + height > img_height:
            raise ValueError("영역이 이미지 범위를 벗어납니다")
        
        # 영역 추출
        region_img = img[y:y+height, x:x+width]
        
        # 템플릿 저장
        return self.save_template(image=region_img, name=name)
    
    def load_template(self, **kwargs) -> Dict[str, Any]:
        """템플릿 로드"""
        # 템플릿 이름 또는 경로
        name = kwargs.get("name")
        path = kwargs.get("path")
        
        if name is None and path is None:
            raise ValueError("템플릿 이름 또는 경로가 지정되지 않았습니다")
        
        # 템플릿 경로 결정
        if path is None:
            path = os.path.join(self.templates_dir, name)
        
        # 템플릿 존재 확인
        if not os.path.exists(path):
            raise ValueError(f"템플릿 파일을 찾을 수 없음: {path}")
        
        # 템플릿 로드
        template = cv2.imread(path)
        
        if template is None:
            raise ValueError(f"템플릿 로드 실패: {path}")
        
        # 템플릿 정보 반환
        height, width = template.shape[:2]
        return {
            "path": path,
            "name": os.path.basename(path),
            "width": width,
            "height": height
        }
    
    def delete_template(self, **kwargs) -> bool:
        """템플릿 삭제"""
        # 템플릿 이름 또는 경로
        name = kwargs.get("name")
        path = kwargs.get("path")
        
        if name is None and path is None:
            raise ValueError("템플릿 이름 또는 경로가 지정되지 않았습니다")
        
        # 템플릿 경로 결정
        if path is None:
            path = os.path.join(self.templates_dir, name)
        
        # 템플릿 존재 확인
        if not os.path.exists(path):
            raise ValueError(f"템플릿 파일을 찾을 수 없음: {path}")
        
        # 템플릿 삭제
        os.remove(path)
        
        logger.info(f"템플릿 삭제됨: {path}")
        return True
    
    def list_templates(self, **kwargs) -> List[Dict[str, Any]]:
        """모든 템플릿 목록 가져오기"""
        # 검색 패턴
        pattern = kwargs.get("pattern", "")
        
        # 템플릿 디렉토리 검색
        templates = []
        
        for filename in os.listdir(self.templates_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # 패턴 필터링
                if pattern and pattern not in filename:
                    continue
                
                filepath = os.path.join(self.templates_dir, filename)
                
                try:
                    # 템플릿 정보 추출
                    img = cv2.imread(filepath)
                    if img is not None:
                        height, width = img.shape[:2]
                        
                        templates.append({
                            "name": filename,
                            "path": filepath,
                            "width": width,
                            "height": height,
                            "size": os.path.getsize(filepath),
                            "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                        })
                except Exception as e:
                    logger.error(f"템플릿 정보 추출 중 오류: {filename} - {str(e)}")
        
        # 파일명으로 정렬
        templates.sort(key=lambda x: x["name"])
        
        return templates
    
    def create_template_from_base64(self, **kwargs) -> Dict[str, Any]:
        """Base64 인코딩된 이미지에서 템플릿 생성"""
        # Base64 데이터 및 이름
        base64_data = kwargs.get("base64_data")
        name = kwargs.get("name")
        
        if base64_data is None:
            raise ValueError("Base64 데이터가 지정되지 않았습니다")
        
        if name is None:
            name = f"base64_template_{int(time.time())}"
        
        # Base64 디코딩 및 이미지 변환
        try:
            # 헤더가 있으면 제거
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            image_bytes = base64.b64decode(base64_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Base64 데이터에서 이미지 변환 실패")
            
            # 템플릿 저장
            return self.save_template(image=img, name=name)
            
        except Exception as e:
            logger.error(f"Base64 데이터에서 템플릿 생성 중 오류: {str(e)}")
            raise
    
    def match_multiple_templates(self, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """여러 템플릿 동시 매칭"""
        # 이미지 및 템플릿 목록
        image = kwargs.get("image")
        template_paths = kwargs.get("template_paths")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if template_paths is None or not template_paths:
            raise ValueError("템플릿 경로 목록이 지정되지 않았습니다")
        
        # 매칭 옵션
        threshold = kwargs.get("threshold", self.config.get("default_threshold", 0.8))
        method = kwargs.get("method", self.config.get("default_method", cv2.TM_CCOEFF_NORMED))
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 각 템플릿에 대해 매칭 수행
        results = {}
        for template_path in template_paths:
            try:
                template_name = os.path.basename(template_path)
                match_result = self.match_template(
                    image=img,
                    template_path=template_path,
                    threshold=threshold,
                    method=method
                )
                
                results[template_name] = match_result["matches"]
                
            except Exception as e:
                logger.error(f"템플릿 매칭 중 오류: {template_path} - {str(e)}")
                results[os.path.basename(template_path)] = []
        
        return results
    
    def feature_matching(self, **kwargs) -> Dict[str, Any]:
        """특징점 기반 매칭"""
        # 이미지 및 템플릿
        image = kwargs.get("image")
        template_path = kwargs.get("template_path")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if template_path is None:
            raise ValueError("템플릿 경로가 지정되지 않았습니다")
        
        # 매칭 옵션
        min_match_count = kwargs.get("min_match_count", 10)
        
        # 이미지 로드
        img = self._load_image(image)
        template = self._load_image(template_path)
        
        # 이미지 및 템플릿 검증
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        if template is None:
            raise ValueError("템플릿 로드 실패")
        
        # 그레이스케일 변환
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # SIFT 특징점 추출기 생성
        sift = cv2.SIFT_create()
        
        # 이미지 및 템플릿의 특징점 및 기술자 추출
        kp1, des1 = sift.detectAndCompute(template_gray, None)
        kp2, des2 = sift.detectAndCompute(img_gray, None)
        
        # FLANN 매칭 파라미터 설정
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        
        # FLANN 매처 생성
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        # 특징점 매칭
        matches = []
        if des1 is not None and des2 is not None and len(des1) > 0 and len(des2) > 0:
            matches = flann.knnMatch(des1, des2, k=2)
        
        # 좋은 매칭만 선택 (Lowe의 비율 테스트)
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
        
        # 디버그 이미지
        if self.config.get("debug_mode", False):
            debug_img = cv2.drawMatches(template, kp1, img, kp2, good_matches, None, flags=2)
            self._save_debug_image(debug_img, "feature_matches")
        
        # 충분한 매칭이 있는지 확인
        if len(good_matches) >= min_match_count:
            # 매칭된 특징점의 좌표 추출
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # 호모그래피 계산
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            matches_mask = mask.ravel().tolist()
            
            # 템플릿 영역 계산
            h, w = template.shape[:2]
            pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
            dst = cv2.perspectiveTransform(pts, M)
            
            # 영역 좌표 계산
            corners = np.int32(dst).reshape(4, 2)
            
            # 영역 중심 계산
            center = np.mean(corners, axis=0).astype(int)
            
            # 영역 경계 계산
            x_min = np.min(corners[:, 0])
            y_min = np.min(corners[:, 1])
            x_max = np.max(corners[:, 0])
            y_max = np.max(corners[:, 1])
            
            # 디버그 이미지에 영역 표시
            if self.config.get("debug_mode", False):
                debug_img = img.copy()
                cv2.polylines(debug_img, [np.int32(dst)], True, (0, 255, 0), 3)
                cv2.circle(debug_img, tuple(center), 5, (0, 0, 255), -1)
                self._save_debug_image(debug_img, "feature_region")
            
            return {
                "found": True,
                "match_count": len(good_matches),
                "center": {"x": int(center[0]), "y": int(center[1])},
                "top_left": {"x": x_min, "y": y_min},
                "bottom_right": {"x": x_max, "y": y_max},
                "confidence": len(good_matches) / len(kp1) if len(kp1) > 0 else 0
            }
        else:
            return {
                "found": False,
                "match_count": len(good_matches),
                "confidence": 0
            }