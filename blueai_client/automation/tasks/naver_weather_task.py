#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 네이버 날씨 검색 작업
"""

import logging
import re
import os
from datetime import datetime
from automation.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

class NaverWeatherTask(BaseTask):
    """네이버에서 날씨 정보를 검색하고 추출하는 작업"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        
        # 작업 관련 키워드
        self.keywords = ["날씨", "기온", "강수량", "네이버", "오늘", "내일", "주간"]
        
        # 매개변수 설정
        self.required_params = ["location"]
        self.optional_params = {
            "day": "today",  # today, tomorrow, week
            "details": "false"
        }
    
    def get_param_pattern(self, param):
        """네이버 날씨 작업에 특화된 매개변수 추출 패턴"""
        if param == "location":
            # "X 날씨" 또는 "X의 날씨" 패턴 매칭
            return r'(?:(.+?)(?:의|에서|지역|동네)?\s+날씨|날씨\s+(.+?)(?:에서|지역|동네)?)'
        elif param == "day":
            # "오늘", "내일", "이번주" 패턴 매칭
            return r'(오늘|금일|투데이|today|내일|tomorrow|모레|이번\s*주|주간|week)'
        elif param == "details":
            # "자세히", "상세" 패턴 매칭
            return r'(자세히|상세|details|detail)'
        else:
            # 기본 패턴 사용
            return super().get_param_pattern(param)
    
    def extract_params(self, command):
        """명령어에서 매개변수 추출 - 네이버 날씨 작업 특화"""
        params = super().extract_params(command)
        
        # 위치 매개변수 정리
        if "location" in params:
            location_match = re.search(self.get_param_pattern("location"), command)
            if location_match:
                # 정규식의 여러 그룹 중 값이 있는 첫 번째 그룹 선택
                location = next((g for g in location_match.groups() if g), None)
                if location:
                    params["location"] = location.strip()
        
        # 위치가 없으면 "서울" 기본값 사용
        if "location" not in params or not params["location"]:
            params["location"] = "서울"
        
        # 날짜 매개변수 정리
        if "day" in params:
            day_val = params["day"].lower()
            if any(term in day_val for term in ["내일", "tomorrow"]):
                params["day"] = "tomorrow"
            elif any(term in day_val for term in ["주간", "week", "이번주"]):
                params["day"] = "week"
            else:
                params["day"] = "today"
                
        # 상세 정보 매개변수 정리
        if "details" in params:
            details_val = params["details"].lower()
            params["details"] = "true" if any(term in details_val for term in ["자세히", "상세", "detail"]) else "false"
        
        return params
    
    def execute(self, params):
        """네이버 날씨 작업 실행"""
        logger.info(f"네이버 날씨 작업 실행: {params}")
        
        # 매개변수 검증
        self.validate_params(params)
        
        location = params["location"]
        day = params.get("day", "today")
        show_details = params.get("details") == "true"
        
        # 브라우저 초기화
        browser = self.browser_manager.get_browser()
        page = browser.new_page()
        
        try:
            # 네이버 접속
            logger.info("네이버 접속 중...")
            page.goto("https://www.naver.com/")
            page.wait_for_load_state("networkidle")
            
            # 검색창에 날씨 검색어 입력
            search_query = f"{location} 날씨"
            logger.info(f"검색어 입력: {search_query}")
            
            # 검색창 찾기 및 검색어 입력
            page.fill('input[name="query"]', search_query)
            
            # 검색 버튼 클릭
            page.click('button.btn_search')
            page.wait_for_load_state("networkidle")
            
            # 날씨 정보 추출
            logger.info("날씨 정보 추출 중...")
            
            # 기본 날씨 정보 (현재 기온, 상태 등)
            current_temp = page.query_selector(".temperature_text").inner_text().strip()
            weather_status = page.query_selector(".weather_main").inner_text().strip()
            
            # 상세 정보
            details = {}
            details_elements = page.query_selector_all(".temperature_info .detail_box .wrap_item")
            
            for element in details_elements:
                title_elem = element.query_selector(".item_title")
                value_elem = element.query_selector(".item_text")
                
                if title_elem and value_elem:
                    title = title_elem.inner_text().strip()
                    value = value_elem.inner_text().strip()
                    details[title] = value
            
            # 미세먼지 정보 추출
            dust_elements = page.query_selector_all(".report_card_wrap .item_today")
            dust_info = {}
            
            for element in dust_elements:
                title_elem = element.query_selector(".item_title")
                value_elem = element.query_selector(".item_num")
                
                if title_elem and value_elem:
                    title = title_elem.inner_text().strip()
                    value = value_elem.inner_text().strip()
                    dust_info[title] = value
            
            # 주간 예보 (필요한 경우)
            weekly_forecast = []
            
            if day == "week":
                week_elements = page.query_selector_all(".week_item")
                
                for element in week_elements:
                    day_elem = element.query_selector(".day_data")
                    temp_elem = element.query_selector(".cell_temperature")
                    weather_elem = element.query_selector(".weather_inner")
                    
                    if day_elem and temp_elem:
                        day_text = day_elem.inner_text().strip()
                        temp_text = temp_elem.inner_text().strip()
                        weather_text = weather_elem.inner_text().strip() if weather_elem else "정보 없음"
                        
                        weekly_forecast.append({
                            "날짜": day_text,
                            "기온": temp_text,
                            "날씨": weather_text
                        })
            
            # 결과 구성
            result = {
                "status": "success",
                "location": location,
                "current_temp": current_temp,
                "weather_status": weather_status,
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": details,
                "dust_info": dust_info
            }
            
            if day == "week" and weekly_forecast:
                result["weekly_forecast"] = weekly_forecast
            
            # 상세 정보 표시 여부에 따른 필터링
            if not show_details:
                if "details" in result:
                    del result["details"]
                if "dust_info" in result:
                    del result["dust_info"]
            
            # 메시지 구성
            message = f"{location}의 현재 날씨: {weather_status}, 기온: {current_temp}"
            
            if show_details and details:
                message += "\n상세 정보:"
                for key, value in details.items():
                    message += f"\n- {key}: {value}"
            
            if show_details and dust_info:
                message += "\n대기 상태:"
                for key, value in dust_info.items():
                    message += f"\n- {key}: {value}"
            
            result["message"] = message
            
            logger.info(f"날씨 정보 추출 완료: {location}")
            return result
            
        except Exception as e:
            error_msg = f"네이버 날씨 작업 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        finally:
            # 페이지 닫기
            page.close()