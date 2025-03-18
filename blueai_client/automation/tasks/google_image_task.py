#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 구글 이미지 검색 및 다운로드 작업
"""

import logging
import re
import os
import time
import requests
from urllib.parse import unquote
from datetime import datetime
from automation.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

class GoogleImageTask(BaseTask):
    """구글에서 이미지를 검색하고 다운로드하는 작업"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        
        # 작업 관련 키워드
        self.keywords = ["이미지", "사진", "구글", "검색", "다운로드", "저장"]
        
        # 매개변수 설정
        self.required_params = ["search_term"]
        self.optional_params = {
            "count": "1",  # 다운로드할 이미지 수
            "save_path": os.path.join(os.path.expanduser("~"), "Pictures", "BlueAI")
        }
    
    def get_param_pattern(self, param):
        """구글 이미지 작업에 특화된 매개변수 추출 패턴"""
        if param == "search_term":
            # "X 이미지" 또는 "X 사진" 패턴 매칭
            return r'(?:구글에서)?\s*([^\s,]+(?:\s+[^\s,]+)*)\s*(?:이미지|사진|그림)(?:\s+검색)?'
        elif param == "count":
            # "N개" 패턴 매칭
            return r'(?:(\d+)(?:개|장|번째|등))'
        else:
            # 기본 패턴 사용
            return super().get_param_pattern(param)
    
    def extract_params(self, command):
        """명령어에서 매개변수 추출 - 구글 이미지 작업 특화"""
        params = super().extract_params(command)
        
        # 검색어가 없을 경우 일반적인 키워드 추출 시도
        if "search_term" not in params or not params["search_term"]:
            # "이미지" 또는 "사진" 앞에 있는 단어 찾기
            words = command.split()
            for i, word in enumerate(words):
                if word in ["이미지", "사진", "그림"]:
                    if i > 0:
                        params["search_term"] = words[i-1]
                        break
        
        # "다운로드" 또는 "저장" 이 명령에 있는지 확인
        download_keywords = ["다운로드", "저장", "받아", "가져와", "download", "save"]
        has_download = any(keyword in command.lower() for keyword in download_keywords)
        
        # 다운로드 요청이 아니면 미리보기 모드로 설정
        if not has_download:
            params["preview_only"] = "true"
        else:
            params["preview_only"] = "false"
        
        # 숫자 형식 매개변수 변환
        if "count" in params:
            try:
                params["count"] = int(params["count"])
            except ValueError:
                params["count"] = 1
        
        return params
    
    def execute(self, params):
        """구글 이미지 작업 실행"""
        logger.info(f"구글 이미지 작업 실행: {params}")
        
        # 매개변수 검증
        self.validate_params(params)
        
        search_term = params["search_term"]
        count = int(params.get("count", 1))
        save_path = params.get("save_path")
        preview_only = params.get("preview_only", "false") == "true"
        
        # 저장 디렉토리 확인 및 생성
        if not preview_only:
            os.makedirs(save_path, exist_ok=True)
        
        # 브라우저 초기화
        browser = self.browser_manager.get_browser()
        page = browser.new_page()
        
        try:
            # 구글 이미지 검색 페이지 접속
            logger.info("구글 이미지 검색 페이지 접속 중...")
            page.goto("https://www.google.com/imghp")
            page.wait_for_load_state("networkidle")
            
            # 검색창 찾기 및 검색어 입력
            logger.info(f"검색어 입력: {search_term}")
            page.fill('input[name="q"]', search_term)
            
            # 검색 버튼 클릭
            page.press('input[name="q"]', 'Enter')
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('div[data-ri="0"]', timeout=10000)  # 첫 번째 이미지 결과 대기
            
            # 검색 결과 추출
            logger.info(f"이미지 검색 결과 추출 중... (최대 {count}개)")
            
            # 이미지 결과들 선택
            image_elements = page.query_selector_all('div[data-ri]')
            
            # 결과가 없는 경우 처리
            if not image_elements:
                logger.warning("이미지 검색 결과가 없습니다.")
                return {
                    "status": "error",
                    "message": "이미지 검색 결과가 없습니다.",
                    "search_term": search_term
                }
            
            # 결과 추출 (최대 count개)
            results = []
            saved_files = []
            
            for i, element in enumerate(image_elements[:count]):
                if i >= count:
                    break
                
                try:
                    # 이미지 클릭하여 상세 보기
                    element.click()
                    page.wait_for_selector('img.iPVvYb', timeout=5000)  # 큰 이미지 로딩 대기
                    
                    # 큰 이미지 URL 추출
                    large_img = page.query_selector('img.iPVvYb')
                    if not large_img:
                        continue
                    
                    img_url = large_img.get_attribute('src')
                    if not img_url or img_url.startswith('data:'):
                        # 다른 방식으로 이미지 URL 추출 시도
                        img_url = large_img.evaluate('el => getComputedStyle(el).backgroundImage')
                        img_url = img_url.replace('url("', '').replace('")', '')
                    
                    # 이미지 정보 추출
                    title_elem = page.query_selector('div.PUDfSe')
                    title = title_elem.inner_text().strip() if title_elem else f"Image {i+1}"
                    
                    # 이미지 크기 추출
                    size_elem = page.query_selector('div.P9KVBf')
                    size = size_elem.inner_text().strip() if size_elem else "Unknown size"
                    
                    # 이미지 호스트 추출
                    host_elem = page.query_selector('div.fYyStc')
                    host = host_elem.inner_text().strip() if host_elem else "Unknown source"
                    
                    results.append({
                        "title": title,
                        "url": img_url,
                        "size": size,
                        "source": host
                    })
                    
                    # 이미지 다운로드 (미리보기 모드가 아닌 경우)
                    if not preview_only and img_url:
                        try:
                            # URL에서 파일 확장자 추출 시도
                            url_path = unquote(img_url.split('?')[0])
                            file_ext = os.path.splitext(url_path)[1]
                            
                            # 확장자가 없거나 유효하지 않으면 .jpg를 기본값으로 사용
                            if not file_ext or file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                                file_ext = '.jpg'
                            
                            # 현재 시간을 기반으로 파일명 생성
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{search_term.replace(' ', '_')}_{i+1}_{timestamp}{file_ext}"
                            filepath = os.path.join(save_path, filename)
                            
                            # 이미지 다운로드
                            response = requests.get(img_url, stream=True, timeout=10)
                            response.raise_for_status()
                            
                            with open(filepath, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            
                            saved_files.append(filepath)
                            logger.info(f"이미지 저장됨: {filepath}")
                            
                        except Exception as e:
                            logger.error(f"이미지 다운로드 중 오류: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"이미지 처리 중 오류: {str(e)}")
            
            # 결과 메시지 구성
            if preview_only:
                message = f"'{search_term}' 검색 결과: {len(results)}개의 이미지를 찾았습니다."
            else:
                message = f"'{search_term}' 검색 결과: {len(saved_files)}개의 이미지를 다운로드했습니다."
            
            return {
                "status": "success",
                "message": message,
                "search_term": search_term,
                "results": results,
                "saved_files": saved_files if not preview_only else []
            }
            
        except Exception as e:
            error_msg = f"구글 이미지 작업 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        finally:
            # 페이지 닫기
            page.close()