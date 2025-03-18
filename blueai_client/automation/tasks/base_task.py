#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 기본 작업 클래스
"""

import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTask(ABC):
    """모든 자동화 작업의 기본 클래스"""
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.keywords = []  # 작업과 관련된 키워드
        self.required_params = []  # 필수 매개변수
        self.optional_params = {}  # 선택적 매개변수와 기본값
        
    def get_match_score(self, command):
        """명령어가 이 작업과 얼마나 일치하는지 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0
        command = command.lower()
        
        # 키워드 매칭
        for keyword in self.keywords:
            if keyword.lower() in command:
                score += 0.2  # 각 키워드 매치마다 점수 추가
        
        # 필수 매개변수 매칭
        for param in self.required_params:
            param_pattern = self.get_param_pattern(param)
            if re.search(param_pattern, command):
                score += 0.1  # 각 매개변수 패턴 매치마다 점수 추가
        
        return min(score, 1.0)  # 최대 1.0 반환
        
    def extract_params(self, command):
        """명령어에서 매개변수 추출"""
        params = {}
        command = command.lower()
        
        # 필수 매개변수 추출
        for param in self.required_params:
            param_pattern = self.get_param_pattern(param)
            match = re.search(param_pattern, command)
            if match:
                params[param] = match.group(1).strip()
            else:
                logger.warning(f"필수 매개변수를 찾을 수 없음: {param}")
        
        # 선택적 매개변수 추출
        for param, default_value in self.optional_params.items():
            param_pattern = self.get_param_pattern(param)
            match = re.search(param_pattern, command)
            if match:
                params[param] = match.group(1).strip()
            else:
                params[param] = default_value
        
        return params
        
    def get_param_pattern(self, param):
        """매개변수 추출을 위한 정규식 패턴 생성"""
        # 기본 구현은 "param: value" 또는 "param value" 패턴 매칭
        return fr'{param}[\s:]+([^,]+)'
        
    def validate_params(self, params):
        """매개변수 검증"""
        missing_params = []
        
        for param in self.required_params:
            if param not in params or not params[param]:
                missing_params.append(param)
        
        if missing_params:
            raise ValueError(f"필수 매개변수가 누락되었습니다: {', '.join(missing_params)}")
        
        return True
        
    @abstractmethod
    def execute(self, params):
        """작업 실행 (하위 클래스에서 구현)"""
        pass