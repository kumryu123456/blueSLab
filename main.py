"""
BlueAI 자동화 시스템 메인 애플리케이션

이 모듈은 자동화 시스템의 진입점입니다.
플러그인을 초기화하고 설정을 로드하며 시스템을 구성합니다.
"""
import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Any
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 코어 모듈 가져오기
from core.plugin_system import PluginManager, PluginType
from core.workflow_manager import WorkflowManager
from core.interruption_handler import InterruptionHandler
from core.settings_manager import SettingsManager, AutomationMode

# 플러그인 가져오기
from plugins.automation.playwright_plugin import PlaywrightPlugin
from plugins.automation.pyautogui_plugin import PyAutoGUIPlugin
from plugins.recognition.selector_plugin import SelectorPlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class BlueAI:
    """BlueAI 자동화 시스템"""
    
    def __init__(self, config_file: str = None):
        """BlueAI 초기화
        
        Args:
            config_file: 설정 파일 경로
        """
        # 로거 설정
        self.logger = self._setup_logger()
        
        # 설정 디렉토리
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = os.path.join(self.base_dir, 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 설정 파일
        self.config_file = config_file or os.path.join(self.config_dir, 'config.json')
        
        # 설정 로드
        self.config = self._load_config()
        
        # 자동 명령 실행 여부
        self.auto_execute = True
        
        # 설정 관리자
        self.settings_manager = SettingsManager(
            settings_dir=self.config.get('settings_dir', os.path.join(self.base_dir, 'settings'))
        )
        
        # 플러그인 디렉토리
        self.plugin_dirs = self.config.get('plugin_dirs', [os.path.join(self.base_dir, 'plugins')])
        
        # 플러그인 관리자
        self.plugin_manager = PluginManager(
            plugin_dirs=self.plugin_dirs,
            logger=self.logger
        )
        
        # 워크플로우 관리자
        self.workflow_manager = WorkflowManager(
            plugin_manager=self.plugin_manager,
            logger=self.logger
        )
        
        # 인터럽션 처리자
        self.interruption_handler = InterruptionHandler(
            plugin_manager=self.plugin_manager,
            settings_file=os.path.join(self.config_dir, 'interruption_settings.json'),
            logger=self.logger
        )
    
    def _setup_logger(self) -> logging.Logger:
        """로거 설정
        
        Returns:
            로거 객체
        """
        logger = logging.getLogger('blueai')
        logger.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 로드
        
        Returns:
            설정 사전
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"설정 파일 로드 실패: {str(e)}")
        
        # 기본 설정
        return {
            'settings_dir': os.path.join(self.base_dir, 'settings'),
            'plugin_dirs': [os.path.join(self.base_dir, 'plugins')],
            'default_mode': 'balanced',
            'logging': {
                'level': 'INFO',
                'file': os.path.join(self.base_dir, 'logs', 'blueai.log'),
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            }
        }
    
    def _save_config(self) -> None:
        """설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"설정 파일 저장 실패: {str(e)}")
    
    def initialize(self) -> bool:
        """시스템 초기화
        
        Returns:
            초기화 성공 여부
        """
        self.logger.info("BlueAI 시스템 초기화 시작")
        
        # 기본 플러그인 등록
        self._register_default_plugins()
        
        # 플러그인 검색 및 로드
        self.plugin_manager.discover_plugins()
        
        self.logger.info("BlueAI 시스템 초기화 완료")
        return True
    
    def _register_default_plugins(self) -> None:
        """기본 플러그인 등록"""
        # 자동화 엔진 플러그인
        self.plugin_manager.register_plugin(PlaywrightPlugin())
        self.plugin_manager.register_plugin(PyAutoGUIPlugin())
        
        # 인식 시스템 플러그인
        self.plugin_manager.register_plugin(SelectorPlugin())
        
        self.logger.info("기본 플러그인 등록 완료")
    
    def execute_workflow(self, workflow_plan: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """워크플로우 실행
        
        Args:
            workflow_plan: 워크플로우 계획
            settings: 실행 설정
            
        Returns:
            실행 결과
        """
        # 설정 준비
        if settings is None:
            settings = {}
        
        # 모드 설정
        if 'mode' not in settings:
            settings['mode'] = self.settings_manager.get_mode().value
        
        # 워크플로우 설정 저장
        settings['workflow_plan'] = workflow_plan
        
        # 워크플로우 생성 및 실행
        workflow_id = self.workflow_manager.create_workflow(workflow_plan, settings)
        result = self.workflow_manager.execute_workflow(workflow_id)
        
        # 워크플로우 정리
        self.workflow_manager.cleanup_workflow(workflow_id)
        
        return result
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """자연어 명령 실행
        
        Args:
            command: 자연어 명령
            
        Returns:
            실행 결과
        """
        # 브라우저 컨텍스트 확인 및 필요시 재초기화
        playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
        if playwright_plugin and playwright_plugin.get_plugin_info().id in self.plugin_manager.initialized_plugins:
            # 이전 실행으로 브라우저가 닫혔는지 확인
            if not playwright_plugin._browser or not playwright_plugin._browser.is_connected():
                self.logger.info("브라우저 재초기화 필요")
                self.plugin_manager.cleanup_plugin("playwright_automation")
                self.plugin_manager.initialize_plugin(playwright_plugin.get_plugin_info().id)
        # 자동 실행 비활성화된 경우 무시
        if not getattr(self, 'auto_execute', True):
            self.logger.info(f"자동 실행 비활성화됨, 명령 무시: {command}")
            return {"status": "ignored", "message": "자동 실행이 비활성화되어 있습니다."}
        
        self.logger.info(f"명령 실행: {command}")
        
        # 브라우저 설정 (Microsoft Edge 사용)
        browser_config = {
            'use_edge': True,  # Edge 브라우저 사용
            'headless': False,  # 화면에 표시
            'timeout': 30000,  # 타임아웃 (ms)
            'user_data_dir': os.path.join(self.base_dir, 'browser_data')  # 브라우저 데이터 저장 경로
        }
        
        # 테스트 워크플로우: 웹 페이지 열기
        workflow_plan = {
            "id": "simple_workflow",
            "name": "간단한 워크플로우",
            "description": f"명령에서 생성된 워크플로우: {command}",
            "steps": [
                {
                    "id": "navigate",
                    "type": "web_navigation",
                    "params": {"url": "https://www.google.com"},
                    "checkpoint": True
                },
                {
                    "id": "handle_interruptions",
                    "type": "interruption_handling",
                    "params": {"types": ["ads", "popups", "cookies"]}
                },
                {
                    "id": "find_search_box",
                    "type": "element_recognition",
                    "params": {
                        "target": {
                            "type": "search",
                            "description": "검색"
                        },
                        "strategies": ["selector"]
                    }
                },
                {
                    "id": "input_search_term",
                    "type": "input_text",
                    "params": {
                        "text": "파이썬",
                        "element_from_step": "find_search_box"
                    }
                },
                {
                    "id": "submit_search",
                    "type": "key_press",
                    "params": {
                        "key": "Enter",
                        "element_from_step": "find_search_box"
                    }
                },
                {
                    "id": "wait_for_results",
                    "type": "wait_for_load",
                    "params": {
                        "timeout": 5.0
                    }
                }
            ]
        }
        
        # 작업 실행 설정
        settings = {
            'mode': self.settings_manager.get_mode().value,
            'browser_config': browser_config,  # 브라우저 설정 추가
            'ignore_recognition_errors': True,  # 인식 오류 무시 (테스트용)
            'timeouts': {
                'navigation': 30.0,
                'element': 5.0,
                'action': 3.0
            }
        }
        
        return self.execute_workflow(workflow_plan, settings)
    
    def cleanup(self) -> None:
        """시스템 정리"""
        self.logger.info("BlueAI 시스템 정리 시작")
        
        # 모든 플러그인 정리
        self.plugin_manager.cleanup_all()
        
        self.logger.info("BlueAI 시스템 정리 완료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='BlueAI 자동화 시스템')
    parser.add_argument('--config', help='설정 파일 경로')
    parser.add_argument('--command', help='자연어 명령')
    
    args = parser.parse_args()
    
    # BlueAI 인스턴스 생성
    blueai = BlueAI(config_file=args.config)
    
    try:
        # 시스템 초기화
        if not blueai.initialize():
            print("시스템 초기화 실패")
            return 1
        
        # 명령 실행
        if args.command:
            result = blueai.execute_command(args.command)
            print(f"실행 결과: {json.dumps(result, indent=2)}")
        else:
            print("명령이 지정되지 않았습니다. --command 옵션을 사용하세요.")
    finally:
        # 정리
        blueai.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())