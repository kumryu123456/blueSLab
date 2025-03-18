# main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 애플리케이션 진입점
"""

import sys
import argparse
import logging
from PyQt5.QtWidgets import QApplication

from config.logging import setup_logging
from ui.main_window import MainWindow
from automation.browser_manager import BrowserManager
from automation.task_parser import TaskParser

def parse_arguments():
    parser = argparse.ArgumentParser(description='BlueAI 클라이언트 애플리케이션')
    parser.add_argument('--headless', action='store_true', help='브라우저를 화면에 표시하지 않고 실행')
    parser.add_argument('--command', type=str, help='직접 명령어 실행 (GUI 없이 실행)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='로깅 레벨 설정')
    parser.add_argument('--server', type=str, help='BlueAI 서버 URL (예: http://localhost:8000)')
    return parser.parse_args()

def run_cli_mode(args):
    """CLI 모드로 애플리케이션 실행"""
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"CLI 모드로 실행: 명령어 '{args.command}'")
    
    # 브라우저 관리자 초기화
    browser_manager = BrowserManager(headless=args.headless)
    
    try:
        # 태스크 파서 초기화 및 명령어 실행
        task_parser = TaskParser(browser_manager)
        result = task_parser.parse_and_execute(args.command)
        
        logger.info(f"명령어 실행 결과: {result}")
        return 0
    except Exception as e:
        logger.error(f"명령어 실행 중 오류 발생: {str(e)}")
        return 1
    finally:
        browser_manager.close()

def run_gui_mode(args):
    """GUI 모드로 애플리케이션 실행"""
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("GUI 모드로 실행")
    
    app = QApplication(sys.argv)
    app.setApplicationName("BlueAI 클라이언트")
    
    # 브라우저 관리자 초기화
    browser_manager = BrowserManager(headless=args.headless)
    
    # 태스크 파서 초기화
    task_parser = TaskParser(browser_manager)
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow(browser_manager, task_parser, server_url=args.server)
    window.show()
    
    return app.exec_()

def main():
    args = parse_arguments()
    
    # CLI 모드인지 확인하고 실행
    if args.command:
        return run_cli_mode(args)
    
    # GUI 모드 실행
    return run_gui_mode(args)

if __name__ == "__main__":
    sys.exit(main())

# cli.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 명령줄 인터페이스
"""

import argparse
import sys
import logging
import json
import time
from pathlib import Path

from automation.browser_manager import BrowserManager
from automation.task_parser import TaskParser
from config.logging import setup_logging

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='BlueAI 클라이언트 명령줄 인터페이스')
    parser.add_argument('command', nargs='?', help='실행할 자동화 명령어')
    parser.add_argument('--headless', action='store_true', help='브라우저를 화면에 표시하지 않고 실행')
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], 
                       default='chromium', help='사용할 브라우저')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO', help='로깅 레벨 설정')
    parser.add_argument('--output', help='결과를 저장할 JSON 파일 경로')
    parser.add_argument('--interactive', '-i', action='store_true', help='대화형 모드 실행')
    
    return parser.parse_args()

def interactive_mode(browser_manager, task_parser):
    """대화형 모드 실행"""
    print("BlueAI 클라이언트 대화형 모드")
    print("종료하려면 'exit' 또는 'quit'를 입력하세요.")
    print()
    
    while True:
        try:
            command = input("BlueAI> ")
            command = command.strip()
            
            if not command:
                continue
            
            if command.lower() in ['exit', 'quit']:
                print("대화형 모드를 종료합니다.")
                break
            
            print(f"명령어 실행 중: {command}")
            start_time = time.time()
            
            result = task_parser.parse_and_execute(command)
            
            elapsed_time = time.time() - start_time
            print(f"실행 시간: {elapsed_time:.2f}초")
            
            # 결과 출력
            if isinstance(result, dict):
                if 'status' in result:
                    status = result['status']
                    message = result.get('message', '')
                    print(f"상태: {status} - {message}")
                
                if 'file_path' in result:
                    print(f"파일 저장됨: {result['file_path']}")
                
                # 세부 결과 출력
                if 'results' in result and isinstance(result['results'], list):
                    print(f"결과 항목 수: {len(result['results'])}")
                    for i, item in enumerate(result['results'][:3], 1):  # 처음 3개 항목만 표시
                        print(f"항목 {i}:", json.dumps(item, ensure_ascii=False))
                    
                    if len(result['results']) > 3:
                        print(f"... 외 {len(result['results']) - 3}개 항목")
            else:
                print("결과:", result)
            
            print()
            
        except KeyboardInterrupt:
            print("\n대화형 모드를 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {str(e)}")

def main():
    """CLI 메인 함수"""
    args = parse_arguments()
    
    # 로깅 설정
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("BlueAI 클라이언트 CLI 시작")
    
    try:
        # 브라우저 매니저 초기화
        browser_manager = BrowserManager(headless=args.headless)
        
        if args.browser != 'chromium':
            browser_manager.change_browser_type(args.browser)
        
        # 태스크 파서 초기화
        task_parser = TaskParser(browser_manager)
        
        # 대화형 모드
        if args.interactive:
            interactive_mode(browser_manager, task_parser)
            return 0
        
        # 명령어 모드
        if not args.command:
            logger.error("명령어가 제공되지 않았습니다. --interactive 옵션을 사용하거나 명령어를 제공하세요.")
            return 1
        
        # 명령어 실행
        logger.info(f"명령어 실행: {args.command}")
        result = task_parser.parse_and_execute(args.command)
        
        # 결과 출력
        if args.output:
            # 결과를 JSON 파일로 저장
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"결과가 {output_path}에 저장되었습니다.")
        else:
            # 콘솔에 결과 출력
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return 0
        
    except Exception as e:
        logger.error(f"CLI 실행 중 오류 발생: {str(e)}")
        return 1
    
    finally:
        # 브라우저 닫기
        if 'browser_manager' in locals():
            browser_manager.close()

if __name__ == "__main__":
    sys.exit(main())