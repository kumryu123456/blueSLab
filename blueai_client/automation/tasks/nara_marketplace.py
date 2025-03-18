#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 나라장터 작업
"""

import logging
import re
import time
import os
from datetime import datetime
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

class NaraMarketplaceTask(BaseTask):
    """나라장터 공고 검색 및 데이터 추출 작업"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        
        # 작업 관련 키워드
        self.keywords = ["나라장터", "공고", "조달", "입찰", "RPA"]
        
        # 매개변수 설정
        self.required_params = ["search_term"]
        self.optional_params = {
            "max_items": "5",
            "save_path": os.path.join(os.path.expanduser("~"), "Documents", "BlueAI"),
        }
    
    def get_param_pattern(self, param):
        """나라장터 작업에 특화된 매개변수 추출 패턴"""
        if param == "search_term":
            # "~에서 X를 검색" 또는 "X 검색" 패턴 매칭
            return r'(?:나라장터에서|조달청에서)?\s*([^\s,]+(?:\s+[^\s,]+)*)\s*(?:공고|검색|찾아)'
        elif param == "max_items":
            # "상위 N개" 또는 "N개의 결과" 패턴 매칭
            return r'(?:상위|처음|앞의)?\s*(\d+)(?:개|건|항목)'
        else:
            # 기본 패턴 사용
            return super().get_param_pattern(param)
    
    def extract_params(self, command):
        """명령어에서 매개변수 추출 - 나라장터 작업 특화"""
        params = super().extract_params(command)
        
        # 검색어가 없으면 RPA 키워드 확인
        if "search_term" not in params or not params["search_term"]:
            if "rpa" in command.lower():
                params["search_term"] = "RPA"
            else:
                # 일반적인 키워드 추출 시도
                words = command.lower().split()
                for word in words:
                    if word not in ["나라장터", "공고", "검색", "해줘", "조달청", "조회"]:
                        params["search_term"] = word
                        break
        
        # 숫자 형식 매개변수 변환
        if "max_items" in params:
            try:
                params["max_items"] = int(params["max_items"])
            except ValueError:
                params["max_items"] = 5
        
        return params
    
    def execute(self, params):
        """나라장터 작업 실행"""
        logger.info(f"나라장터 작업 실행: {params}")
        
        # 매개변수 검증
        self.validate_params(params)
        
        search_term = params["search_term"]
        max_items = int(params.get("max_items", 5))
        save_path = params.get("save_path")
        
        # 저장 디렉토리 확인 및 생성
        os.makedirs(save_path, exist_ok=True)
        
        # 브라우저 초기화
        browser = self.browser_manager.get_browser()
        page = browser.new_page()
        
        try:
            # 나라장터 사이트 접속
            logger.info("나라장터 사이트 접속 중...")
            page.goto("https://www.g2b.go.kr/index.jsp")
            page.wait_for_load_state("networkidle")
            
            # 검색창 찾기 및 검색어 입력
            logger.info(f"검색어 입력: {search_term}")
            page.fill('input[name="bidNm"]', search_term)
            
            # 검색 버튼 클릭
            page.click('input[type="image"][alt="검색"]')
            page.wait_for_load_state("networkidle")
            
            # 검색 결과 추출
            logger.info("검색 결과 추출 중...")
            
            # 결과 데이터 저장용 리스트
            results = []
            
            # 결과 테이블 확인
            table_selector = 'table.list_Table'
            page.wait_for_selector(table_selector, timeout=10000)
            
            # 행 선택
            rows = page.query_selector_all(f'{table_selector} > tbody > tr')
            
            # 결과가 없는 경우 처리
            if not rows or len(rows) <= 1:
                logger.warning("검색 결과가 없습니다.")
                return {
                    "status": "error",
                    "message": "검색 결과가 없습니다.",
                    "search_term": search_term
                }
            
            # 결과 추출 (최대 max_items개)
            count = 0
            for row in rows:
                if count >= max_items:
                    break
                
                # 빈 행 건너뛰기
                if not row.query_selector('td'):
                    continue
                
                try:
                    # 공고 데이터 추출
                    cells = row.query_selector_all('td')
                    if len(cells) < 5:
                        continue
                    
                    bid_no = cells[0].inner_text().strip()
                    bid_name = cells[1].inner_text().strip()
                    org_name = cells[2].inner_text().strip()
                    bid_date = cells[3].inner_text().strip()
                    status = cells[4].inner_text().strip()
                    
                    results.append({
                        "공고번호": bid_no,
                        "공고명": bid_name,
                        "공고기관": org_name,
                        "입찰마감일시": bid_date,
                        "상태": status
                    })
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"행 데이터 추출 중 오류: {str(e)}")
            
            # 결과를 엑셀로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"나라장터_{search_term}_{timestamp}.xlsx"
            filepath = os.path.join(save_path, filename)
            
            # 데이터프레임 생성 및 저장
            df = pd.DataFrame(results)
            df.to_excel(filepath, index=False)
            
            logger.info(f"검색 결과가 {filepath}에 저장되었습니다.")
            
            return {
                "status": "success",
                "message": f"{len(results)}개의 검색 결과를 추출했습니다.",
                "search_term": search_term,
                "results": results,
                "file_path": filepath
            }
            
        except PlaywrightTimeoutError:
            error_msg = "페이지 로딩 시간 초과"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        except Exception as e:
            error_msg = f"나라장터 작업 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        finally:
            # 페이지 닫기
            page.close()