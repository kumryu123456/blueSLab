#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 나라장터 검색 예제 워크플로우
인터럽션 처리와 다단계 작업 흐름을 포함한 나라장터 검색 예제
"""

import os
import logging
import time
import json
from datetime import datetime
from pathlib import Path

from core.plugin_manager import PluginManager
from core.workflow_manager import WorkflowManager, Workflow, WorkflowStep
from core.settings_manager import SettingsManager
from core.interruption_handler import InterruptionHandler

logger = logging.getLogger(__name__)

def create_nara_marketplace_workflow(plugin_manager, settings_manager):
    """나라장터 검색 워크플로우 생성"""
    # 워크플로우 관리자 생성
    workflow_manager = WorkflowManager(
        checkpoint_dir=os.path.join(os.path.expanduser("~"), "BlueAI", "checkpoints"),
        plugin_manager=plugin_manager
    )
    
    # 인터럽션 핸들러 생성
    interruption_handler = InterruptionHandler(
        plugin_manager=plugin_manager,
        settings_manager=settings_manager
    )
    
    # 인터럽션 핸들러 설정
    playwright_plugin = plugin_manager.get_plugin("automation", "playwright")
    if playwright_plugin:
        playwright_plugin.set_interruption_handler(interruption_handler)
    
    # 워크플로우 생성
    workflow = workflow_manager.create_workflow(
        name="나라장터 검색 워크플로우",
        description="인터럽션 처리와 다단계 작업 흐름을 포함한 나라장터 검색 예제"
    )
    
    # 검색어 및 저장 경로 설정
    search_term = "RPA"
    max_items = 5
    save_path = os.path.join(os.path.expanduser("~"), "BlueAI", "data")
    os.makedirs(save_path, exist_ok=True)
    
    # 워크플로우에 변수 추가
    workflow.variables = {
        "search_term": search_term,
        "max_items": max_items,
        "save_path": save_path
    }
    
    # 단계 1: 브라우저 시작
    step1 = WorkflowStep(
        step_id="start_browser",
        name="브라우저 시작",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "launch_browser",
            "params": {
                "headless": False,
                "browser_type": "chromium"
            }
        }
    )
    workflow.add_step(step1)
    
    # 단계 2: 새 페이지 생성
    step2 = WorkflowStep(
        step_id="create_page",
        name="새 페이지 생성",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "new_page",
            "params": {}
        },
        dependencies=["start_browser"]
    )
    workflow.add_step(step2)
    
    # 단계 3: 나라장터 사이트 접속
    step3 = WorkflowStep(
        step_id="goto_nara",
        name="나라장터 사이트 접속",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "goto",
            "params": {
                "url": "https://www.g2b.go.kr/index.jsp"
            }
        },
        dependencies=["create_page"]
    )
    workflow.add_step(step3)
    
    # 단계 4: 인터럽션 처리
    step4 = WorkflowStep(
        step_id="handle_interruptions",
        name="인터럽션 처리",
        action={
            "plugin_type": "interruption",
            "plugin_name": "popup_handler",
            "action": "handle_all_interruptions",
            "params": {}
        },
        dependencies=["goto_nara"]
    )
    workflow.add_step(step4)
    
    # 단계 5: 검색어 입력
    step5 = WorkflowStep(
        step_id="input_search_term",
        name="검색어 입력",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "fill",
            "params": {
                "selector": 'input[name="bidNm"]',
                "value": "${search_term}"
            }
        },
        dependencies=["handle_interruptions"]
    )
    workflow.add_step(step5)
    
    # 단계 6: 검색 버튼 클릭
    step6 = WorkflowStep(
        step_id="click_search",
        name="검색 버튼 클릭",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "click",
            "params": {
                "selector": 'input[type="image"][alt="검색"]'
            }
        },
        dependencies=["input_search_term"]
    )
    workflow.add_step(step6)
    
    # 단계 7: 검색 결과 대기
    step7 = WorkflowStep(
        step_id="wait_for_results",
        name="검색 결과 대기",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "wait_for_selector",
            "params": {
                "selector": 'table.list_Table',
                "timeout": 10000
            }
        },
        dependencies=["click_search"]
    )
    workflow.add_step(step7)
    
    # 단계 8: 스크린샷 캡처
    step8 = WorkflowStep(
        step_id="take_screenshot",
        name="스크린샷 캡처",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "screenshot",
            "params": {
                "path": os.path.join(save_path, f"nara_search_{search_term}.png")
            }
        },
        dependencies=["wait_for_results"]
    )
    workflow.add_step(step8)
    
    # 단계 9: 검색 결과 추출
    step9 = WorkflowStep(
        step_id="extract_results",
        name="검색 결과 추출",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "evaluate",
            "params": {
                "expression": """() => {
                    // 결과 테이블 찾기
                    const table = document.querySelector('table.list_Table');
                    if (!table) return { error: '검색 결과 테이블을 찾을 수 없습니다.' };
                    
                    // 행 선택
                    const rows = table.querySelectorAll('tbody > tr');
                    if (!rows || rows.length <= 1) return { error: '검색 결과가 없습니다.' };
                    
                    // 결과 데이터 추출
                    const results = [];
                    const maxItems = """ + str(max_items) + """;
                    
                    let count = 0;
                    for (const row of rows) {
                        if (count >= maxItems) break;
                        
                        // 셀 데이터 추출
                        const cells = row.querySelectorAll('td');
                        if (!cells || cells.length < 5) continue;
                        
                        // 빈 행 건너뛰기
                        if (!cells[0].textContent.trim()) continue;
                        
                        results.push({
                            '공고번호': cells[0].textContent.trim(),
                            '공고명': cells[1].textContent.trim(),
                            '공고기관': cells[2].textContent.trim(),
                            '입찰마감일시': cells[3].textContent.trim(),
                            '상태': cells[4].textContent.trim()
                        });
                        
                        count++;
                    }
                    
                    return { 
                        results: results,
                        count: results.length
                    };
                }"""
            }
        },
        dependencies=["wait_for_results"]
    )
    workflow.add_step(step9)
    
    # 단계 10: 결과 저장
    step10 = WorkflowStep(
        step_id="save_results",
        name="결과 저장",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "evaluate",
            "params": {
                "expression": """(resultsJson) => {
                    // 결과 데이터를 JSON 형식으로 변환
                    const results = JSON.parse(resultsJson);
                    
                    // 오류 확인
                    if (results.error) {
                        return { error: results.error };
                    }
                    
                    // JSON 형식의 문자열 반환 (CSV로 변환하기 위해)
                    return JSON.stringify(results.results);
                }""",
                "arg": "${step_extract_results_result}"
            }
        },
        dependencies=["extract_results"]
    )
    workflow.add_step(step10)
    
    # 단계 11: CSV 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(save_path, f"나라장터_{search_term}_{timestamp}.csv")
    
    step11 = WorkflowStep(
        step_id="save_to_csv",
        name="CSV 파일로 저장",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "evaluate",
            "params": {
                "expression": """(params) => {
                    const { resultsJson, filePath } = JSON.parse(params);
                    const results = JSON.parse(resultsJson);
                    
                    if (!results || results.length === 0) {
                        return { error: '저장할 결과가 없습니다.' };
                    }
                    
                    // CSV 헤더 생성
                    const headers = Object.keys(results[0]);
                    
                    // CSV 데이터 생성
                    let csv = headers.join(',') + '\\n';
                    
                    for (const result of results) {
                        const row = headers.map(header => {
                            // 쉼표와 따옴표 처리
                            const cell = result[header] || '';
                            return '"' + cell.replace(/"/g, '""') + '"';
                        });
                        csv += row.join(',') + '\\n';
                    }
                    
                    // 파일 시스템은 브라우저에서 직접 접근할 수 없으므로,
                    // 데이터만 반환하고 실제 저장은 다른 방식으로 처리해야 함
                    return {
                        csv: csv,
                        filePath: filePath,
                        count: results.length
                    };
                }""",
                "arg": json.dumps({
                    "resultsJson": "${step_save_results_result}",
                    "filePath": file_path
                })
            }
        },
        dependencies=["save_results"]
    )
    workflow.add_step(step11)
    
    # 단계 12: CSV 파일 실제 저장 (외부 처리)
    step12 = WorkflowStep(
        step_id="handle_csv_save",
        name="CSV 파일 실제 저장",
        action={
            "plugin_type": "custom",
            "plugin_name": "file_handler",
            "action": "write_file",
            "params": {
                "file_path": "${step_save_to_csv_result.filePath}",
                "content": "${step_save_to_csv_result.csv}"
            }
        },
        dependencies=["save_to_csv"]
    )
    workflow.add_step(step12)
    
    # 단계 13: 브라우저 종료
    step13 = WorkflowStep(
        step_id="close_browser",
        name="브라우저 종료",
        action={
            "plugin_type": "automation",
            "plugin_name": "playwright",
            "action": "close_browser",
            "params": {}
        },
        dependencies=["handle_csv_save", "take_screenshot"]  # 모든 작업이 끝난 후 브라우저 종료
    )
    workflow.add_step(step13)
    
    # 워크플로우 단계 순서 설정
    workflow.set_step_order([
        "start_browser",
        "create_page",
        "goto_nara",
        "handle_interruptions",
        "input_search_term",
        "click_search",
        "wait_for_results",
        "take_screenshot",
        "extract_results",
        "save_results",
        "save_to_csv",
        "handle_csv_save",
        "close_browser"
    ])
    
    return workflow_manager, workflow

def run_example():
    """나라장터 검색 예제 실행"""
    # 기본 디렉토리 설정
    base_dir = os.path.join(os.path.expanduser("~"), "BlueAI")
    os.makedirs(base_dir, exist_ok=True)
    
    # 로깅 설정
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f"nara_example_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")),
            logging.StreamHandler()
        ]
    )
    
    try:
        # 플러그인 관리자 초기화
        plugin_manager = PluginManager("plugins")
        plugin_manager.load_all_plugins()
        plugin_manager.initialize_all_plugins()
        
        # 설정 관리자 초기화
        settings_manager = SettingsManager()
        
        # 나라장터 워크플로우 생성
        workflow_manager, workflow = create_nara_marketplace_workflow(plugin_manager, settings_manager)
        
        # 워크플로우 시작
        logger.info(f"워크플로우 시작: {workflow.name}")
        workflow_manager.start_workflow(workflow.workflow_id)
        
        # 워크플로우 완료 대기
        while workflow_manager.is_workflow_running(workflow.workflow_id):
            logger.info(f"워크플로우 실행 중... 현재 단계: {workflow.current_step_id}")
            time.sleep(2)
        
        # 워크플로우 결과 확인
        if workflow.status.value == "completed":
            logger.info(f"워크플로우 완료: {workflow.name}")
            # 결과 정보 출력
            for step_id, step in workflow.steps.items():
                if step.status.value == "completed" and step.result:
                    logger.info(f"단계 결과: {step.name} - {step.result}")
            
            return True, None
        else:
            error_msg = f"워크플로우 실패: {workflow.name} - {workflow.error}"
            logger.error(error_msg)
            return False, error_msg
        
    except Exception as e:
        error_msg = f"예제 실행 중 오류: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    
    finally:
        # 플러그인 종료
        if 'plugin_manager' in locals():
            plugin_manager.shutdown_all_plugins()

if __name__ == "__main__":
    success, error = run_example()
    
    if success:
        print("예제가 성공적으로 실행되었습니다.")
    else:
        print(f"예제 실행 실패: {error}")