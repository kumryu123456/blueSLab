#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 명령어 파서
"""

import re
import logging
import json
from pathlib import Path
import importlib

logger = logging.getLogger(__name__)

class TaskParser:
    """
    자연어 명령어를 해석하여 적절한 자동화 작업을 선택하고 실행하는 클래스
    """
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.tasks = {}
        self._load_tasks()
        
    def _load_tasks(self):
        """자동화 작업 모듈 동적 로드"""
        # 현재 디렉토리의 tasks 폴더에서 모든 파이썬 파일 찾기
        tasks_dir = Path(__file__).parent / "tasks"
        task_files = [f for f in tasks_dir.glob("*.py") if f.name != "__init__.py" and f.name != "base_task.py"]
        
        # 각 작업 파일 로드
        for task_file in task_files:
            module_name = f"automation.tasks.{task_file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # 모듈에서 Task 클래스 찾기
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.endswith('Task') and attr_name != 'BaseTask':
                        # 작업 인스턴스 생성 및 등록
                        task_instance = attr(self.browser_manager)
                        self.tasks[task_file.stem] = task_instance
                        logger.debug(f"작업 로드됨: {task_file.stem} ({attr_name})")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"작업 모듈 로드 중 오류 발생: {module_name} - {str(e)}")
        
    def get_task_for_command(self, command):
        """명령어에 맞는 작업 선택"""
        command = command.lower()
        
        # 각 작업의 키워드 매칭
        task_scores = {}
        
        for task_name, task in self.tasks.items():
            score = task.get_match_score(command)
            task_scores[task_name] = score
        
        # 가장 높은 점수의 작업 선택
        if not task_scores:
            return None
        
        best_match = max(task_scores.items(), key=lambda x: x[1])
        task_name, score = best_match
        
        # 최소 점수 임계값 확인
        if score < 0.3:  # 30% 미만 매칭 시 작업 선택하지 않음
            logger.warning(f"명령어에 맞는 작업을 찾을 수 없음: {command}")
            return None
        
        logger.info(f"선택된 작업: {task_name} (점수: {score:.2f})")
        return self.tasks[task_name]
        
    def parse_and_execute(self, command):
        """명령어 파싱 및 실행"""
        logger.info(f"명령어 파싱 시작: {command}")
        
        # 명령어에 맞는 작업 찾기
        task = self.get_task_for_command(command)
        
        if not task:
            raise ValueError(f"명령어를 처리할 수 있는 작업을 찾을 수 없습니다: {command}")
        
        # 작업 매개변수 추출
        params = task.extract_params(command)
        
        # 작업 실행
        logger.info(f"작업 실행: {task.__class__.__name__}, 매개변수: {params}")
        result = task.execute(params)
        
        return result