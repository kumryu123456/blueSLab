#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 로깅 설정
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(level_name='INFO', log_to_file=True):
    """로깅 시스템 설정

    Args:
        level_name (str): 로그 레벨 이름 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file (bool): 파일에 로그를 저장할지 여부
    """
    # 로그 레벨 변환
    level = getattr(logging, level_name)
    
    # 기본 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 핸들러 초기화
    root_logger.handlers = []
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (선택적)
    if log_to_file:
        # 로그 디렉토리 생성
        log_dir = Path.home() / "BlueAI" / "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 로그 파일명 생성 (날짜 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"blueai_client_{timestamp}.log"
        
        # 파일 핸들러 설정
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"로그 파일 경로: {log_file}")
    
    # 라이브러리 로깅 레벨 조정
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # 로그 레벨 정보 출력
    logging.info(f"로깅 레벨 설정됨: {level_name}")
    
    return root_logger