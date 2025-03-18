 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - OCR 인식 플러그인
Tesseract OCR 기반 텍스트 인식 플러그인
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
import re
from PIL import Image
import numpy as np
import cv2
import pytesseract
from pytesseract import Output

from core.plugin_manager import PluginInterface

logger = logging.getLogger(__name__)

class OCRPlugin(PluginInterface):
    """Tesseract OCR 기반 텍스트 인식 플러그인"""
    
    plugin_type = "recognition"
    plugin_name = "ocr"
    plugin_version = "0.1.0"
    plugin_description = "Tesseract OCR 기반 텍스트 인식 플러그인"
    
    def __init__(self):
        super().__init__()
        self.debug_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "debug_ocr")
        
        # 설정 기본값
        self.config = {
            "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows 기본 경로
            "language": "kor+eng",  # 한국어+영어
            "oem": 3,  # OCR Engine Mode (3: 기본)
            "psm": 3,  # Page Segmentation Mode (3: 자동 페이지 세그먼테이션)
            "confidence_threshold": 60,  # 신뢰도 임계값 (0-100)
            "preprocessing": True,  # 전처리 활성화 여부
            "debug_mode": False,  # 디버그 모드
            "debug_output_dir": self.debug_dir
        }
        
        # 디버그 디렉토리 생성
        if self.config["debug_mode"]:
            os.makedirs(self.debug_dir, exist_ok=True)
    
    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            # Tesseract 경로 설정
            if self.config.get("tesseract_path"):
                pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_path"]
            
            # Tesseract 버전 확인
            try:
                tesseract_version = pytesseract.get_tesseract_version()
                logger.info(f"Tesseract OCR 버전: {tesseract_version}")
            except Exception as e:
                logger.error(f"Tesseract OCR 버전 확인 실패: {str(e)}")
                logger.warning("Tesseract OCR이 설치되어 있지 않거나 경로가 올바르지 않습니다.")
                return False
            
            # 디버그 디렉토리 생성
            if self.config.get("debug_mode", False):
                os.makedirs(self.config["debug_output_dir"], exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"OCR 플러그인 초기화 실패: {str(e)}")
            return False
    
    def shutdown(self) -> bool:
        """플러그인 종료"""
        return True
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """플러그인 설정"""
        try:
            self.config.update(config)
            
            # Tesseract 경로 설정
            if self.config.get("tesseract_path"):
                pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_path"]
            
            # 디버그 디렉토리 생성
            if self.config.get("debug_mode", False):
                os.makedirs(self.config["debug_output_dir"], exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"OCR 플러그인 설정 중 오류: {str(e)}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """플러그인이 제공하는 기능 목록"""
        return [
            "extract_text",
            "extract_text_by_region",
            "find_text",
            "find_all_text",
            "extract_text_with_layout",
            "extract_tables",
            "extract_text_from_pdf",
            "get_supported_languages",
            "preprocess_image"
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
    
    def preprocess_image(self, **kwargs) -> Dict[str, Any]:
        """OCR을 위한 이미지 전처리"""
        # 이미지
        image = kwargs.get("image")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        # 전처리 옵션
        grayscale = kwargs.get("grayscale", True)
        thresholding = kwargs.get("thresholding", True)
        noise_removal = kwargs.get("noise_removal", True)
        dilation = kwargs.get("dilation", True)
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 디버그 모드인 경우 원본 이미지 저장
        if self.config.get("debug_mode", False):
            self._save_debug_image(img, "ocr_original")
        
        # 그레이스케일 변환
        if grayscale:
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            if self.config.get("debug_mode", False):
                self._save_debug_image(img, "ocr_grayscale")
        
        # 노이즈 제거
        if noise_removal:
            if grayscale:
                img = cv2.GaussianBlur(img, (5, 5), 0)
            
            if self.config.get("debug_mode", False):
                self._save_debug_image(img, "ocr_noise_removed")
        
        # 이진화 (흑백 변환)
        if thresholding and grayscale:
            # 적응형 이진화
            img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
            
            if self.config.get("debug_mode", False):
                self._save_debug_image(img, "ocr_thresholded")
        
        # 팽창 (글자 두께 강화)
        if dilation and grayscale and thresholding:
            kernel = np.ones((2, 2), np.uint8)
            img = cv2.dilate(img, kernel, iterations=1)
            
            if self.config.get("debug_mode", False):
                self._save_debug_image(img, "ocr_dilated")
        
        # 결과 반환
        if kwargs.get("return_image", False):
            return {"image": img}
        
        # 전처리된 이미지를 임시 파일로 저장
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            cv2.imwrite(tmp_file.name, img)
            return {"processed_image_path": tmp_file.name}
    
    def extract_text(self, **kwargs) -> Dict[str, Any]:
        """이미지에서 텍스트 추출"""
        # 이미지
        image = kwargs.get("image")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        # OCR 옵션
        lang = kwargs.get("lang", self.config.get("language", "kor+eng"))
        config = kwargs.get("config", "")
        oem = kwargs.get("oem", self.config.get("oem", 3))
        psm = kwargs.get("psm", self.config.get("psm", 3))
        preprocessing = kwargs.get("preprocessing", self.config.get("preprocessing", True))
        confidence_threshold = kwargs.get("confidence_threshold", 
                                        self.config.get("confidence_threshold", 60))
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 이미지 전처리
        if preprocessing:
            result = self.preprocess_image(image=img, return_image=True)
            img = result["image"]
        
        # OCR 설정
        custom_config = f'--oem {oem} --psm {psm}'
        if config:
            custom_config += f' {config}'
        
        # OCR 실행
        text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
        
        # 텍스트 데이터 추출
        data = pytesseract.image_to_data(img, lang=lang, config=custom_config, output_type=Output.DICT)
        
        # 신뢰도 기준 필터링된 텍스트 추출
        filtered_text = ""
        confidence_values = []
        words = []
        
        for i in range(len(data["text"])):
            if int(data["conf"][i]) >= confidence_threshold:
                word = data["text"][i].strip()
                if word:
                    filtered_text += word + " "
                    confidence_values.append(int(data["conf"][i]))
                    words.append({
                        "text": word,
                        "confidence": int(data["conf"][i]),
                        "box": {
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i]
                        }
                    })
        
        # 평균 신뢰도 계산
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
        
        # 디버그 모드인 경우 결과 시각화
        if self.config.get("debug_mode", False) and words:
            debug_img = img.copy()
            if len(debug_img.shape) == 2:  # 그레이스케일인 경우 컬러로 변환
                debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)
            
            for word in words:
                box = word["box"]
                cv2.rectangle(debug_img, 
                             (box["x"], box["y"]), 
                             (box["x"] + box["width"], box["y"] + box["height"]), 
                             (0, 255, 0), 2)
                cv2.putText(debug_img, 
                           f"{word['text']} ({word['confidence']})", 
                           (box["x"], box["y"] - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            self._save_debug_image(debug_img, "ocr_result")
        
        return {
            "text": text.strip(),
            "filtered_text": filtered_text.strip(),
            "words": words,
            "confidence": avg_confidence,
            "languages": lang
        }
    
    def extract_text_by_region(self, **kwargs) -> Dict[str, Any]:
        """이미지의 특정 영역에서 텍스트 추출"""
        # 이미지 및 영역
        image = kwargs.get("image")
        region = kwargs.get("region")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if region is None:
            raise ValueError("영역이 지정되지 않았습니다")
        
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
        
        # 텍스트 추출
        return self.extract_text(image=region_img, **{k:v for k,v in kwargs.items() if k != 'image' and k != 'region'})
    
    def find_text(self, **kwargs) -> Dict[str, Any]:
        """이미지에서 특정 텍스트 찾기"""
        # 이미지 및 검색 텍스트
        image = kwargs.get("image")
        text = kwargs.get("text")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if text is None:
            raise ValueError("검색할 텍스트가 지정되지 않았습니다")
        
        # 검색 옵션
        case_sensitive = kwargs.get("case_sensitive", False)
        regex = kwargs.get("regex", False)
        confidence_threshold = kwargs.get("confidence_threshold", 
                                        self.config.get("confidence_threshold", 60))
        
        # 텍스트 추출
        ocr_result = self.extract_text(image=image, **{k:v for k,v in kwargs.items() if k != 'image' and k != 'text'})
        
        # 검색 텍스트 정규화
        search_text = text
        
        if not case_sensitive and not regex:
            search_text = search_text.lower()
        
        # 텍스트 검색
        found = False
        matches = []
        
        if regex:
            try:
                pattern = re.compile(search_text, flags=0 if case_sensitive else re.IGNORECASE)
                
                for word in ocr_result["words"]:
                    word_text = word["text"]
                    
                    if pattern.search(word_text):
                        found = True
                        matches.append(word)
                
            except re.error as e:
                logger.error(f"정규식 오류: {str(e)}")
                raise ValueError(f"정규식 오류: {str(e)}")
        else:
            for word in ocr_result["words"]:
                word_text = word["text"]
                
                if not case_sensitive:
                    word_text = word_text.lower()
                
                if word_text == search_text:
                    found = True
                    matches.append(word)
        
        # 디버그 모드인 경우 결과 시각화
        if self.config.get("debug_mode", False) and matches:
            img = self._load_image(image)
            debug_img = img.copy()
            
            if len(debug_img.shape) == 2:  # 그레이스케일인 경우 컬러로 변환
                debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)
            
            for match in matches:
                box = match["box"]
                cv2.rectangle(debug_img, 
                             (box["x"], box["y"]), 
                             (box["x"] + box["width"], box["y"] + box["height"]), 
                             (0, 0, 255), 2)
                cv2.putText(debug_img, 
                           f"{match['text']} ({match['confidence']})", 
                           (box["x"], box["y"] - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            self._save_debug_image(debug_img, "ocr_find_result")
        
        return {
            "found": found,
            "matches": matches,
            "match_count": len(matches),
            "text": text
        }
    
    def find_all_text(self, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """이미지에서 여러 텍스트 찾기"""
        # 이미지 및 검색 텍스트 목록
        image = kwargs.get("image")
        texts = kwargs.get("texts")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        if texts is None or not texts:
            raise ValueError("검색할 텍스트 목록이 지정되지 않았습니다")
        
        # 각 텍스트에 대해 검색 수행
        results = {}
        for text in texts:
            result = self.find_text(
                image=image,
                text=text,
                **{k:v for k,v in kwargs.items() if k != 'image' and k != 'texts'}
            )
            
            results[text] = result["matches"]
        
        return results
    
    def extract_text_with_layout(self, **kwargs) -> Dict[str, Any]:
        """레이아웃 정보를 포함한 텍스트 추출"""
        # 이미지
        image = kwargs.get("image")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        # OCR 옵션
        lang = kwargs.get("lang", self.config.get("language", "kor+eng"))
        oem = kwargs.get("oem", self.config.get("oem", 3))
        psm = kwargs.get("psm", self.config.get("psm", 3))
        preprocessing = kwargs.get("preprocessing", self.config.get("preprocessing", True))
        conf_threshold = kwargs.get("confidence_threshold", 
                                  self.config.get("confidence_threshold", 60))
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 이미지 전처리
        if preprocessing:
            result = self.preprocess_image(image=img, return_image=True)
            img = result["image"]
        
        # OCR 설정
        custom_config = f'--oem {oem} --psm {psm}'
        
        # OCR 실행
        data = pytesseract.image_to_data(img, lang=lang, config=custom_config, output_type=Output.DICT)
        
        # 블록, 단락, 줄 단위의 텍스트 그룹화
        blocks = []
        
        current_block = None
        current_paragraph = None
        current_line = None
        
        for i in range(len(data["text"])):
            if int(data["conf"][i]) < conf_threshold:
                continue
            
            word_text = data["text"][i].strip()
            if not word_text:
                continue
            
            block_num = data["block_num"][i]
            par_num = data["par_num"][i]
            line_num = data["line_num"][i]
            
            # 새 블록 시작
            if current_block is None or current_block["block_num"] != block_num:
                if current_block is not None:
                    blocks.append(current_block)
                
                current_block = {
                    "block_num": block_num,
                    "paragraphs": [],
                    "text": "",
                    "box": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i]
                    }
                }
                current_paragraph = None
                current_line = None
            
            # 새 단락 시작
            if current_paragraph is None or current_paragraph["par_num"] != par_num:
                if current_paragraph is not None:
                    current_block["paragraphs"].append(current_paragraph)
                
                current_paragraph = {
                    "par_num": par_num,
                    "lines": [],
                    "text": "",
                    "box": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i]
                    }
                }
                current_line = None
            
            # 새 줄 시작
            if current_line is None or current_line["line_num"] != line_num:
                if current_line is not None:
                    current_paragraph["lines"].append(current_line)
                
                current_line = {
                    "line_num": line_num,
                    "words": [],
                    "text": "",
                    "box": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i]
                    }
                }
            
            # 단어 정보 추가
            word = {
                "text": word_text,
                "confidence": int(data["conf"][i]),
                "box": {
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i]
                }
            }
            
            current_line["words"].append(word)
            
            # 박스 업데이트
            box = current_line["box"]
            word_box = word["box"]
            
            # 폭 업데이트
            right = max(box["x"] + box["width"], word_box["x"] + word_box["width"])
            box["width"] = right - box["x"]
            
            # 높이 업데이트
            bottom = max(box["y"] + box["height"], word_box["y"] + word_box["height"])
            box["height"] = bottom - box["y"]
            
            # 줄 텍스트 업데이트
            current_line["text"] += word_text + " "
        
        # 마지막 데이터 처리
        if current_line is not None:
            current_paragraph["lines"].append(current_line)
            current_paragraph["text"] = " ".join([line["text"].strip() for line in current_paragraph["lines"]])
            
            # 박스 업데이트
            box = current_paragraph["box"]
            for line in current_paragraph["lines"]:
                line_box = line["box"]
                
                # 폭 업데이트
                right = max(box["x"] + box["width"], line_box["x"] + line_box["width"])
                box["width"] = right - box["x"]
                
                # 높이 업데이트
                bottom = max(box["y"] + box["height"], line_box["y"] + line_box["height"])
                box["height"] = bottom - box["y"]
        
        if current_paragraph is not None:
            current_block["paragraphs"].append(current_paragraph)
            current_block["text"] = " ".join([par["text"].strip() for par in current_block["paragraphs"]])
            
            # 박스 업데이트
            box = current_block["box"]
            for paragraph in current_block["paragraphs"]:
                par_box = paragraph["box"]
                
                # 폭 업데이트
                right = max(box["x"] + box["width"], par_box["x"] + par_box["width"])
                box["width"] = right - box["x"]
                
                # 높이 업데이트
                bottom = max(box["y"] + box["height"], par_box["y"] + par_box["height"])
                box["height"] = bottom - box["y"]
        
        if current_block is not None:
            blocks.append(current_block)
        
        # 전체 텍스트
        full_text = " ".join([block["text"].strip() for block in blocks])
        
        # 디버그 모드인 경우 결과 시각화
        if self.config.get("debug_mode", False) and blocks:
            debug_img = img.copy()
            
            if len(debug_img.shape) == 2:  # 그레이스케일인 경우 컬러로 변환
                debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)
            
            # 블록 그리기
            for block in blocks:
                box = block["box"]
                cv2.rectangle(debug_img, 
                             (box["x"], box["y"]), 
                             (box["x"] + box["width"], box["y"] + box["height"]), 
                             (0, 0, 255), 2)
            
            # 줄 그리기
            for block in blocks:
                for paragraph in block["paragraphs"]:
                    for line in paragraph["lines"]:
                        box = line["box"]
                        cv2.rectangle(debug_img, 
                                     (box["x"], box["y"]), 
                                     (box["x"] + box["width"], box["y"] + box["height"]), 
                                     (0, 255, 0), 1)
            
            self._save_debug_image(debug_img, "ocr_layout")
        
        return {
            "text": full_text,
            "blocks": blocks,
            "block_count": len(blocks),
            "confidence": np.mean([word["confidence"] for block in blocks 
                                for paragraph in block["paragraphs"] 
                                for line in paragraph["lines"] 
                                for word in line["words"]])
        }
    
    def extract_tables(self, **kwargs) -> Dict[str, Any]:
        """이미지에서 테이블 구조 추출"""
        # 이미지
        image = kwargs.get("image")
        
        if image is None:
            raise ValueError("이미지가 지정되지 않았습니다")
        
        # 테이블 추출 옵션
        preprocessing = kwargs.get("preprocessing", True)
        confidence_threshold = kwargs.get("confidence_threshold", 
                                        self.config.get("confidence_threshold", 60))
        lang = kwargs.get("lang", self.config.get("language", "kor+eng"))
        
        # 이미지 로드
        img = self._load_image(image)
        
        if img is None:
            raise ValueError("이미지 로드 실패")
        
        # 이미지 전처리
        if preprocessing:
            # 그레이스케일 변환
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy()
            
            # 이진화
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # 선 감지용 커널
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
            
            # 수직선 감지
            vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=3)
            
            # 수평선 감지
            horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=3)
            
            # 디버그 모드인 경우 중간 결과 저장
            if self.config.get("debug_mode", False):
                self._save_debug_image(gray, "table_gray")
                self._save_debug_image(thresh, "table_thresh")
                self._save_debug_image(vertical_lines, "table_vertical")
                self._save_debug_image(horizontal_lines, "table_horizontal")
            
            # 선 합치기
            table_grid = cv2.add(vertical_lines, horizontal_lines)
            
            # 테이블 윤곽선 찾기
            contours, hierarchy = cv2.findContours(table_grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # 셀 후보 찾기
            cells = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # 최소 크기 이상의 직사각형만 셀로 간주
                if w > 20 and h > 10:
                    cells.append({
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h
                    })
            
            # 셀 정렬 (가장 왼쪽 상단 셀이 첫 번째)
            cells.sort(key=lambda c: (c["y"], c["x"]))
            
            # 각 셀에서 텍스트 추출
            for i, cell in enumerate(cells):
                cell_img = img[cell["y"]:cell["y"]+cell["height"], cell["x"]:cell["x"]+cell["width"]]
                
                try:
                    ocr_result = pytesseract.image_to_string(cell_img, lang=lang)
                    cell["text"] = ocr_result.strip()
                except Exception as e:
                    logger.error(f"셀 텍스트 추출 중 오류: {str(e)}")
                    cell["text"] = ""
            
            # 디버그 모드인 경우 셀 시각화
            if self.config.get("debug_mode", False) and cells:
                debug_img = img.copy()
                
                for i, cell in enumerate(cells):
                    cv2.rectangle(debug_img, 
                                 (cell["x"], cell["y"]), 
                                 (cell["x"] + cell["width"], cell["y"] + cell["height"]), 
                                 (0, 255, 0), 2)
                    cv2.putText(debug_img, 
                               f"{i}", 
                               (cell["x"] + 5, cell["y"] + 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                self._save_debug_image(debug_img, "table_cells")
            
            # 테이블 행/열 구조 추정
            if cells:
                # Y 좌표 그룹화 (행)
                y_positions = []
                for cell in cells:
                    y_center = cell["y"] + cell["height"] // 2
                    
                    # 유사한 Y 위치가 있는지 확인 (10픽셀 오차 허용)
                    found = False
                    for i, y_pos in enumerate(y_positions):
                        if abs(y_pos - y_center) < 15:  # 행 높이의 절반 정도
                            found = True
                            break
                    
                    if not found:
                        y_positions.append(y_center)
                
                y_positions.sort()
                
                # X 좌표 그룹화 (열)
                x_positions = []
                for cell in cells:
                    x_center = cell["x"] + cell["width"] // 2
                    
                    # 유사한 X 위치가 있는지 확인 (10픽셀 오차 허용)
                    found = False
                    for i, x_pos in enumerate(x_positions):
                        if abs(x_pos - x_center) < 15:  # 열 폭의 절반 정도
                            found = True
                            break
                    
                    if not found:
                        x_positions.append(x_center)
                
                x_positions.sort()
                
                # 행 수와 열 수
                rows = len(y_positions)
                cols = len(x_positions)
                
                # 테이블 구조를 2D 배열로 구성
                table = [[None for _ in range(cols)] for _ in range(rows)]
                
                # 각 셀을 테이블에 배치
                for cell in cells:
                    cell_center_y = cell["y"] + cell["height"] // 2
                    cell_center_x = cell["x"] + cell["width"] // 2
                    
                    # 가장 가까운 행/열 인덱스 찾기
                    row_idx = min(range(len(y_positions)), key=lambda i: abs(y_positions[i] - cell_center_y))
                    col_idx = min(range(len(x_positions)), key=lambda i: abs(x_positions[i] - cell_center_x))
                    
                    # 테이블에 셀 배치
                    table[row_idx][col_idx] = cell["text"]
                
                # 비어있는 셀 처리
                for i in range(rows):
                    for j in range(cols):
                        if table[i][j] is None:
                            table[i][j] = ""
                
                return {
                    "cells": cells,
                    "table": table,
                    "rows": rows,
                    "columns": cols
                }
            
            return {
                "cells": cells,
                "table": [],
                "rows": 0,
                "columns": 0
            }
            
        else:
            # 전처리 없이 OCR로 바로 처리
            # Tesseract에는 테이블 감지 기능이 없으므로, 텍스트 위치 기반으로 추정
            ocr_result = self.extract_text_with_layout(image=img, lang=lang, confidence_threshold=confidence_threshold)
            
            # 완벽한 테이블 구조를 추출하기는 어려움, 간단한 구조 추정만 제공
            return {
                "cells": [],
                "table": [block["text"] for block in ocr_result["blocks"]],
                "rows": len(ocr_result["blocks"]),
                "columns": 1,
                "is_approximation": True
            }
    
    def get_supported_languages(self, **kwargs) -> Dict[str, List[str]]:
        """지원되는 언어 목록 반환"""
        try:
            # Tesseract 언어 데이터 디렉토리 찾기
            if os.name == 'nt':  # Windows
                tesseract_path = self.config.get("tesseract_path", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
                tessdata_path = os.path.join(os.path.dirname(tesseract_path), "tessdata")
            else:  # Linux/Mac
                tessdata_path = "/usr/share/tesseract-ocr/4.00/tessdata"
                if not os.path.exists(tessdata_path):
                    tessdata_path = "/usr/share/tessdata"
            
            # 언어 파일 찾기
            languages = []
            
            if os.path.exists(tessdata_path):
                for file in os.listdir(tessdata_path):
                    if file.endswith('.traineddata'):
                        lang_code = file[:-12]  # Remove '.traineddata'
                        languages.append(lang_code)
            
            # 언어 코드 그룹화
            simple_langs = [lang for lang in languages if '+' not in lang and '-' not in lang]
            script_langs = [lang for lang in languages if '+' in lang or '-' in lang]
            
            return {
                "languages": sorted(languages),
                "simple_languages": sorted(simple_langs),
                "script_languages": sorted(script_langs),
                "tessdata_path": tessdata_path
            }
            
        except Exception as e:
            logger.error(f"지원 언어 목록 가져오기 실패: {str(e)}")
            return {
                "languages": ["eng"],  # 기본 영어
                "error": str(e)
            }