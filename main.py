#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 메인 애플리케이션
플러그인 기반 통합 자동화 시스템의 메인 실행 파일
"""

import os
import sys
import argparse
import logging
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from core.plugin_manager import PluginManager
from core.workflow_manager import WorkflowManager
from core.settings_manager import SettingsManager
from core.interruption_handler import InterruptionHandler
from ui.main_window import MainWindow  # UI가 구현되면 수정

# 로깅 설정
def setup_logging(level_name='INFO'):
    """로깅 시스템 설정"""
    # 로그 레벨 설정
    level = getattr(logging, level_name)
    
    # 로그 디렉토리 생성
    log_dir = os.path.join(os.path.expanduser("~"), "BlueAI", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"blueai_{timestamp}.log")
    
    # 로거 설정
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 외부 라이브러리 로깅 레벨 조정
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"로깅 시작 (레벨: {level_name})")
    logger.info(f"로그 파일: {log_file}")
    
    return logger

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='BlueAI 통합 자동화 시스템')
    
    # 모드 설정
    parser.add_argument('--headless', action='store_true', 
                      help='헤드리스 모드로 실행 (UI 없음)')
    parser.add_argument('--command', type=str, 
                      help='직접 명령어 실행 (예: "나라장터에서 RPA 공고 검색")')
    parser.add_argument('--workflow', type=str, 
                      help='워크플로우 파일 실행 (.json)')
    
    # 로깅 설정
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO', help='로깅 레벨 설정')
    
    # 서버 설정
    parser.add_argument('--server', type=str, 
                      help='서버 URL (예: http://localhost:8000)')
    parser.add_argument('--api-key', type=str, 
                      help='API 키')
    
    # 플러그인 설정
    parser.add_argument('--plugins-dir', type=str, default='plugins',
                      help='플러그인 디렉토리')
    
    return parser.parse_args()

def initialize_system(args):
    """시스템 초기화"""
    logger = logging.getLogger(__name__)
    logger.info("시스템 초기화 중...")
    
    # 기본 디렉토리 설정
    base_dir = os.path.join(os.path.expanduser("~"), "BlueAI")
    os.makedirs(base_dir, exist_ok=True)
    
    # 설정 관리자 초기화
    logger.info("설정 관리자 초기화 중...")
    settings_manager = SettingsManager()
    
    # 플러그인 관리자 초기화
    logger.info(f"플러그인 관리자 초기화 중... (디렉토리: {args.plugins_dir})")
    plugin_manager = PluginManager(args.plugins_dir)
    
    # 플러그인 로드
    logger.info("플러그인 로드 중...")
    loaded_plugins = plugin_manager.load_all_plugins()
    logger.info(f"로드된 플러그인: {loaded_plugins}")
    
    # 플러그인 초기화
    logger.info("플러그인 초기화 중...")
    init_results = plugin_manager.initialize_all_plugins()
    
    for plugin_name, success in init_results.items():
        if success:
            logger.info(f"플러그인 초기화 성공: {plugin_name}")
        else:
            logger.error(f"플러그인 초기화 실패: {plugin_name}")
    
    # 워크플로우 관리자 초기화
    logger.info("워크플로우 관리자 초기화 중...")
    workflow_manager = WorkflowManager(
        checkpoint_dir=os.path.join(base_dir, "checkpoints"),
        plugin_manager=plugin_manager
    )
    
    # 인터럽션 핸들러 초기화
    logger.info("인터럽션 핸들러 초기화 중...")
    interruption_handler = InterruptionHandler(
        plugin_manager=plugin_manager,
        settings_manager=settings_manager,
        rules_file=os.path.join(base_dir, "config", "interruption_rules.json")
    )
    
    # Playwright 플러그인에 인터럽션 핸들러 설정
    playwright_plugin = plugin_manager.get_plugin("automation", "playwright")
    if playwright_plugin:
        playwright_plugin.set_interruption_handler(interruption_handler)
    
    # 시스템 구성 요소 반환
    return {
        "settings_manager": settings_manager,
        "plugin_manager": plugin_manager,
        "workflow_manager": workflow_manager,
        "interruption_handler": interruption_handler
    }

def run_command(command, system_components):
    """명령어 직접 실행"""
    logger = logging.getLogger(__name__)
    logger.info(f"명령어 실행: {command}")
    
    plugin_manager = system_components["plugin_manager"]
    workflow_manager = system_components["workflow_manager"]
    
    try:
        # 현재는 간단한 워크플로우 생성 및 실행
        workflow = workflow_manager.create_workflow(
            name=f"명령어 워크플로우: {command}",
            description=f"명령어로 생성된 워크플로우: {command}"
        )
        
        # 명령어 종류에 따라 워크플로우 구성
        if "나라장터" in command.lower():
            # 간단한 나라장터 검색 워크플로우 구성
            from examples.nara_marketplace_example import create_nara_marketplace_workflow
            _, workflow = create_nara_marketplace_workflow(plugin_manager, system_components["settings_manager"])
        else:
            # 기본 브라우저 실행 워크플로우
            from core.workflow_manager import WorkflowStep
            
            # 브라우저 시작 단계
            step1 = WorkflowStep(
                step_id="start_browser",
                name="브라우저 시작",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "launch_browser",
                    "params": {
                        "headless": False,  # 명시적으로 False 설정
                        "browser_type": "chromium"
                    }
                }
            )
            workflow.add_step(step1)
            
            # 페이지 생성 단계
            step2 = WorkflowStep(
                step_id="create_page",
                name="페이지 생성",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "new_page",
                    "params": {}
                },
                dependencies=["start_browser"]
            )
            workflow.add_step(step2)
            
            # 구글 접속 단계
            step3 = WorkflowStep(
                step_id="goto_google",
                name="구글 접속",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "goto",
                    "params": {
                        "url": "https://www.google.com"
                    }
                },
                dependencies=["create_page"]
            )
            workflow.add_step(step3)
            
            # 검색어 입력 단계
            step4 = WorkflowStep(
                step_id="input_search",
                name="검색어 입력",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "fill",
                    "params": {
                        "selector": 'input[name="q"]',
                        "value": command
                    }
                },
                dependencies=["goto_google"]
            )
            workflow.add_step(step4)
            
            # 검색 버튼 클릭 단계
            step5 = WorkflowStep(
                step_id="click_search",
                name="검색 버튼 클릭",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "press_key",
                    "params": {
                        "selector": 'input[name="q"]',
                        "key": "Enter"
                    }
                },
                dependencies=["input_search"]
            )
            workflow.add_step(step5)
            
            # 스크린샷 캡처 단계
            step6 = WorkflowStep(
                step_id="take_screenshot",
                name="스크린샷 캡처",
                action={
                    "plugin_type": "automation",
                    "plugin_name": "playwright",
                    "action": "screenshot",
                    "params": {
                        "path": os.path.join(os.path.expanduser("~"), "BlueAI", "screenshots", f"search_{int(time.time())}.png")
                    }
                },
                dependencies=["click_search"]
            )
            workflow.add_step(step6)
            
            # 단계 순서 설정
            workflow.set_step_order([
                "start_browser",
                "create_page",
                "goto_google",
                "input_search",
                "click_search",
                "take_screenshot"
            ])
        
        # 워크플로우 실행
        logger.info(f"워크플로우 시작: {workflow.name}")
        workflow_manager.start_workflow(workflow.workflow_id)
        
        # 워크플로우 완료 대기
        while workflow_manager.is_workflow_running(workflow.workflow_id):
            logger.info(f"워크플로우 실행 중... 현재 단계: {workflow.current_step_id}")
            time.sleep(2)
        
        # 워크플로우 결과 확인
        if workflow.status.value == "completed":
            logger.info(f"워크플로우 완료: {workflow.name}")
            result = {}
            
            # 단계 결과 수집
            for step_id, step in workflow.steps.items():
                if step.status.value == "completed" and step.result:
                    result[step.name] = step.result
            
            return True, result
        else:
            error_msg = f"워크플로우 실패: {workflow.name} - {workflow.error}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        
    except Exception as e:
        error_msg = f"명령어 실행 중 오류: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}

def run_workflow_file(workflow_file, system_components):
    """워크플로우 파일 실행"""
    logger = logging.getLogger(__name__)
    logger.info(f"워크플로우 파일 실행: {workflow_file}")
    
    workflow_manager = system_components["workflow_manager"]
    
    try:
        # 워크플로우 파일 로드
        workflow_id = workflow_manager.load_workflow_from_file(workflow_file)
        
        if not workflow_id:
            raise ValueError(f"워크플로우 파일을 로드할 수 없습니다: {workflow_file}")
        
        # 워크플로우 실행
        workflow_manager.start_workflow(workflow_id)
        
        # 워크플로우 정보 가져오기
        workflow = workflow_manager.get_workflow(workflow_id)
        
        # 워크플로우 완료 대기
        while workflow_manager.is_workflow_running(workflow_id):
            logger.info(f"워크플로우 실행 중... 현재 단계: {workflow.current_step_id}")
            time.sleep(2)
        
        # 워크플로우 결과 확인
        if workflow.status.value == "completed":
            logger.info(f"워크플로우 완료: {workflow.name}")
            result = {}
            
            # 단계 결과 수집
            for step_id, step in workflow.steps.items():
                if step.status.value == "completed" and step.result:
                    result[step.name] = step.result
            
            return True, result
        else:
            error_msg = f"워크플로우 실패: {workflow.name} - {workflow.error}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        
    except Exception as e:
        error_msg = f"워크플로우 파일 실행 중 오류: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}

def run_gui_mode(args, system_components, app=None):
    """GUI 모드 실행"""
    logger = logging.getLogger(__name__)
    logger.info("GUI 모드 시작")
    
    try:
        # app이 이미 생성되어 있으면 재사용, 아니면 새로 생성
        if app is None:
            app = QApplication(sys.argv)
            app.setApplicationName("BlueAI 통합 자동화 시스템")
        
        # SafeUIUpdater로 진행하기 전에 기본 MainWindow 초기화가 성공하는지 확인
        try:
            window = MainWindow(
                plugin_manager=system_components["plugin_manager"],
                workflow_manager=system_components["workflow_manager"],
                settings_manager=system_components["settings_manager"],
                interruption_handler=system_components["interruption_handler"],
                server_url=args.server
            )
            
            # 초기화 이후 UI 속성 확인
            if not hasattr(window, 'workflow_status'):
                logger.error("MainWindow의 workflow_status 속성이 초기화되지 않았습니다.")
                return 1
                
            window.show()
            return app.exec_()
            
        except Exception as e:
            logger.error(f"MainWindow 초기화 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 1
        
    except Exception as e:
        logger.error(f"GUI 모드 실행 중 오류: {str(e)}")
        return 1

def main():
    # 명령줄 인수 파싱
    args = parse_arguments()
    
    # 로깅 설정
    logger = setup_logging(args.log_level)
    
    try:
        # QApplication 인스턴스를 시스템 초기화 전에 생성
        # (GUI 모드가 아니어도 Playwright용으로 필요)
        app = QApplication(sys.argv)
        app.setApplicationName("BlueAI 통합 자동화 시스템")
        
        # 시스템 초기화
        system_components = initialize_system(args)
        
        # 실행 모드 결정
        if args.command:
            # 명령어 직접 실행 모드
            success, result = run_command(args.command, system_components)
            # ...나머지 코드
        elif args.workflow:
            # 워크플로우 파일 실행 모드
            success, result = run_workflow_file(args.workflow, system_components)
            # ...나머지 코드
        else:
            # GUI 모드
            if args.headless:
                logger.error("헤드리스 모드에서는 명령어 또는 워크플로우 파일이 필요합니다.")
                return 1
            
            # GUI 모드 실행 (QApplication 인스턴스는 이미 생성됨)
            return run_gui_mode(args, system_components)
        
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        return 1
    
    finally:
        # 플러그인 종료
        try:
            if 'system_components' in locals() and 'plugin_manager' in system_components:
                plugin_manager = system_components["plugin_manager"]
                plugin_manager.shutdown_all_plugins()
                logger.info("모든 플러그인이 종료되었습니다.")
        except Exception as e:
            logger.error(f"플러그인 종료 중 오류: {str(e)}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)