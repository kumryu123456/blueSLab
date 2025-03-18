#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 유튜브 검색 및 정보 추출 작업
"""

import logging
import re
import os
import json
from datetime import datetime
from automation.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

class YouTubeSearchTask(BaseTask):
    """유튜브에서 동영상을 검색하고 정보를 추출하는 작업"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        
        # 작업 관련 키워드
        self.keywords = ["유튜브", "youtube", "동영상", "영상", "비디오", "채널"]
        
        # 매개변수 설정
        self.required_params = ["search_term"]
        self.optional_params = {
            "max_results": "5",
            "sort_by": "relevance",  # relevance, date, view_count
            "save_path": os.path.join(os.path.expanduser("~"), "Documents", "BlueAI")
        }
    
    def get_param_pattern(self, param):
        """유튜브 작업에 특화된 매개변수 추출 패턴"""
        if param == "search_term":
            # "X 검색" 또는 "X 찾아" 패턴 매칭
            return r'(?:유튜브에서|YouTube에서)?\s*([^\s,]+(?:\s+[^\s,]+)*)\s*(?:검색|찾아)'
        elif param == "max_results":
            # "상위 N개" 또는 "N개의 결과" 패턴 매칭
            return r'(?:상위|처음|앞의)?\s*(\d+)(?:개|건|편|영상)'
        elif param == "sort_by":
            # 정렬 방식 매칭
            return r'(?:정렬\s*(?:기준)?:?\s*|sort\s*(?:by)?:?\s*)(관련도|조회수|최신순|날짜|인기|relevant|view|date|new)'
        else:
            # 기본 패턴 사용
            return super().get_param_pattern(param)
    
    def extract_params(self, command):
        """명령어에서 매개변수 추출 - 유튜브 작업 특화"""
        params = super().extract_params(command)
        
        # 검색어가 없을 경우 일반적인 키워드 추출 시도
        if "search_term" not in params or not params["search_term"]:
            words = command.lower().split()
            
            # "유튜브" 또는 "youtube" 뒤에 나오는 단어들을 검색어로 추출
            for i, word in enumerate(words):
                if word in ["유튜브", "youtube"]:
                    if i < len(words) - 2:  # 최소한 2개 이상의 단어가 더 있어야 함
                        # "에서" 같은 단어를 건너뛰고 나머지를 검색어로 사용
                        if words[i+1] in ["에서", "에", "in", "on"]:
                            start_idx = i + 2
                        else:
                            start_idx = i + 1
                        
                        # "검색" 또는 "찾아" 앞까지의 단어들을 검색어로 사용
                        end_idx = len(words)
                        for j in range(start_idx, len(words)):
                            if words[j] in ["검색", "찾아", "찾기", "search", "find"]:
                                end_idx = j
                                break
                        
                        params["search_term"] = " ".join(words[start_idx:end_idx])
                        break
        
        # 정렬 방식 변환
        if "sort_by" in params:
            sort_val = params["sort_by"].lower()
            if any(term in sort_val for term in ["조회수", "인기", "view"]):
                params["sort_by"] = "view_count"
            elif any(term in sort_val for term in ["최신순", "날짜", "date", "new"]):
                params["sort_by"] = "date"
            else:
                params["sort_by"] = "relevance"
        
        # 숫자 형식 매개변수 변환
        if "max_results" in params:
            try:
                params["max_results"] = int(params["max_results"])
            except ValueError:
                params["max_results"] = 5
        
        return params
    
    def execute(self, params):
        """유튜브 검색 작업 실행"""
        logger.info(f"유튜브 검색 작업 실행: {params}")
        
        # 매개변수 검증
        self.validate_params(params)
        
        search_term = params["search_term"]
        max_results = int(params.get("max_results", 5))
        sort_by = params.get("sort_by", "relevance")
        save_path = params.get("save_path")
        
        # 저장 디렉토리 확인 및 생성
        os.makedirs(save_path, exist_ok=True)
        
        # 브라우저 초기화
        browser = self.browser_manager.get_browser()
        page = browser.new_page()
        
        try:
            # 유튜브 접속
            logger.info("유튜브 접속 중...")
            page.goto("https://www.youtube.com/")
            page.wait_for_load_state("networkidle")
            
            # 검색창 찾기 및 검색어 입력
            logger.info(f"검색어 입력: {search_term}")
            page.click('input#search')
            page.fill('input#search', search_term)
            
            # 검색 버튼 클릭
            page.click('button#search-icon-legacy')
            page.wait_for_load_state("networkidle")
            page.wait_for_selector('ytd-video-renderer, ytd-channel-renderer', timeout=10000)
            
            # 정렬 방식 적용
            if sort_by != "relevance":
                # 필터 버튼 클릭
                filter_button = page.query_selector('button#filter-button')
                if filter_button:
                    filter_button.click()
                    page.wait_for_selector('div#container.style-scope.ytd-search-sub-menu-renderer', timeout=5000)
                    
                    # 정렬 방식에 따른 메뉴 아이템 선택
                    if sort_by == "view_count":
                        page.click('yt-formatted-string:has-text("조회수")')
                    elif sort_by == "date":
                        page.click('yt-formatted-string:has-text("업로드 날짜")')
                    
                    page.wait_for_load_state("networkidle")
            
            # 검색 결과 추출
            logger.info("검색 결과 추출 중...")
            
            # 비디오 결과 추출
            video_results = []
            video_elements = page.query_selector_all('ytd-video-renderer')
            
            count = 0
            for video in video_elements:
                if count >= max_results:
                    break
                
                try:
                    # 비디오 제목
                    title_elem = video.query_selector('h3 a#video-title')
                    title = title_elem.get_attribute('title') if title_elem else "제목 없음"
                    
                    # 비디오 URL
                    url = title_elem.get_attribute('href') if title_elem else ""
                    if url:
                        url = f"https://www.youtube.com{url}"
                    
                    # 채널명
                    channel_elem = video.query_selector('div#channel-info a')
                    channel = channel_elem.inner_text().strip() if channel_elem else "채널명 없음"
                    
                    # 조회수 및 업로드 시간
                    meta_elem = video.query_selector('div#metadata-line')
                    views = ""
                    upload_time = ""
                    
                    if meta_elem:
                        meta_spans = meta_elem.query_selector_all('span')
                        if len(meta_spans) >= 1:
                            views = meta_spans[0].inner_text().strip()
                        if len(meta_spans) >= 2:
                            upload_time = meta_spans[1].inner_text().strip()
                    
                    # 썸네일 URL
                    thumbnail_elem = video.query_selector('img#img')
                    thumbnail_url = thumbnail_elem.get_attribute('src') if thumbnail_elem else ""
                    
                    # 비디오 길이
                    duration_elem = video.query_selector('span#text.ytd-thumbnail-overlay-time-status-renderer')
                    duration = duration_elem.inner_text().strip() if duration_elem else "알 수 없음"
                    
                    video_results.append({
                        "title": title,
                        "url": url,
                        "channel": channel,
                        "views": views,
                        "upload_time": upload_time,
                        "duration": duration,
                        "thumbnail_url": thumbnail_url
                    })
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"비디오 데이터 추출 중 오류: {str(e)}")
            
            # 결과가 없는 경우 처리
            if not video_results:
                logger.warning("검색 결과가 없습니다.")
                return {
                    "status": "error",
                    "message": "검색 결과가 없습니다.",
                    "search_term": search_term
                }
            
            # 결과를 JSON으로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"YouTube_{search_term.replace(' ', '_')}_{timestamp}.json"
            filepath = os.path.join(save_path, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(video_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"검색 결과가 {filepath}에 저장되었습니다.")
            
            # 첫 번째 비디오 링크를 텍스트 파일로도 저장
            if video_results:
                first_video = video_results[0]
                first_video_url = first_video["url"]
                
                text_filename = f"YouTube_{search_term.replace(' ', '_')}_link_{timestamp}.txt"
                text_filepath = os.path.join(save_path, text_filename)
                
                with open(text_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"제목: {first_video['title']}\n")
                    f.write(f"채널: {first_video['channel']}\n")
                    f.write(f"URL: {first_video_url}\n")
                    f.write(f"조회수: {first_video['views']}\n")
                    f.write(f"업로드: {first_video['upload_time']}\n")
                    f.write(f"길이: {first_video['duration']}\n")
                
                logger.info(f"첫 번째 비디오 정보가 {text_filepath}에 저장되었습니다.")
            
            # 메시지 구성
            video_summary = ""
            for i, video in enumerate(video_results[:3], 1):
                video_summary += f"\n{i}. {video['title']} ({video['channel']}) - {video['views']}, {video['duration']}"
            
            if len(video_results) > 3:
                video_summary += f"\n... 외 {len(video_results) - 3}개 영상"
            
            message = f"'{search_term}' 유튜브 검색 결과: {len(video_results)}개의 영상을 찾았습니다.{video_summary}"
            
            return {
                "status": "success",
                "message": message,
                "search_term": search_term,
                "results": video_results,
                "file_path": filepath,
                "first_video_link": video_results[0]["url"] if video_results else ""
            }
            
        except Exception as e:
            error_msg = f"유튜브 검색 작업 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        finally:
            # 페이지 닫기
            page.close()