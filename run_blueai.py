#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 스레드 안전 실행 래퍼
"""

import os
import sys
import importlib.util
import traceback

# Qt 스레드 안전성 향상을 위한 환경 변수 설정
os.environ['QT_THREAD_UNSAFE'] = '1'

def main():
    """메인 함수"""
    # 현재 디렉토리를 Python 경로에 추가
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # 패치 모듈 가져오기 및 적용
        print("BlueAI 패치 적용 중...")
        import patches.main_patch
        
        # 원래 main.py 실행
        print("BlueAI 시스템 시작 중...")
        from main import main as original_main
        return original_main()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
