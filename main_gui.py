"""
BlueAI 자동화 시스템 GUI

이 모듈은 BlueAI 자동화 시스템의 GUI를 구현합니다.
PyQt5를 사용하여 작업 계획 입력, 실행, 모니터링 기능을 제공합니다.
"""
import json
import logging
import os
import sys
import threading
import time
from typing import Dict, List, Any, Optional
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 현재 디렉토리를 sys.path에 추가하여 모듈 임포트 문제 해결
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# main.py에서 BlueAI 클래스 직접 임포트
try:
    from main import BlueAI
except ImportError:
    # 임포트 실패 시 임시 대체 클래스
    print("BlueAI 클래스를 가져올 수 없습니다. main.py 파일을 확인하세요.")
    class BlueAI:
        """BlueAI 클래스를 가져올 수 없는 경우 임시 대체 클래스"""
        def __init__(self, config_file=None):
            self.config_file = config_file
            
        def initialize(self):
            print("BlueAI 클래스를 가져올 수 없습니다. main.py 파일을 확인하세요.")
            return False
            
        def execute_command(self, command):
            return {"status": "failed", "error": "BlueAI 클래스를 가져올 수 없습니다."}
            
        def execute_workflow(self, workflow, settings=None):
            return {"status": "failed", "error": "BlueAI 클래스를 가져올 수 없습니다."}
            
        def cleanup(self):
            pass

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QTextEdit, QLineEdit, QTabWidget,
                                QComboBox, QCheckBox, QGroupBox, QGridLayout, QFileDialog,
                                QListWidget, QListWidgetItem, QSplitter, QMenu, QAction,
                                QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QEvent  # QEvent 추가
    from PyQt5.QtGui import QIcon, QFont, QTextCursor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class WorkerThread(QThread):
    """백그라운드 작업 스레드"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(dict)
    
    def __init__(self, blueai, command=None, workflow=None, settings=None):
        super().__init__()
        self.blueai = blueai
        self.command = command
        self.workflow = workflow
        self.settings = settings or {}
        self.is_command = command is not None
    
    def run(self):
        """스레드 실행"""
        try:
            if self.is_command:
                # 명령 실행
                self.progress.emit({"status": "실행 중", "message": f"명령 실행 중: {self.command}"})
                result = self.blueai.execute_command(self.command)
                self.finished.emit(result)
            else:
                # 워크플로우 실행
                self.progress.emit({"status": "실행 중", "message": f"워크플로우 실행 중: {self.workflow.get('id', 'unknown')}"})
                result = self.blueai.execute_workflow(self.workflow, self.settings)
                self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"status": "failed", "error": str(e)})


class LogHandler(logging.Handler):
    """로그 핸들러"""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def emit(self, record):
        log_entry = self.format(record)
        self.callback(log_entry)


class BlueAIGUI(QMainWindow):
    """BlueAI GUI 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.blueai = None
        self.worker = None
        self.current_workflow_id = None
        self.status_timer = None
        
        # 설정
        self.settings = QSettings("BlueAI", "Automation")
        
        # UI 초기화
        self.init_ui()
        
        # BlueAI 초기화
        self.initialize_blueai()
        
        # 로그 설정
        self.setup_logging()
    
    def init_ui(self):
        """UI 초기화"""
        # 메인 윈도우 설정
        self.setWindowTitle("BlueAI 자동화 시스템")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃 설정
        main_layout = QVBoxLayout(central_widget)
        
        # 탭 위젯 설정
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        
        # 탭 추가
        self.init_command_tab()
        self.init_workflow_tab()
        self.init_monitor_tab()
        self.init_settings_tab()
        self.init_log_tab()
        
        # 탭을 메인 레이아웃에 추가
        main_layout.addWidget(self.tabs)
        
        # 상태 표시줄 설정
        self.statusBar().showMessage("준비됨")
        
        # 스타일 설정
        self.set_styles()
    
    def init_command_tab(self):
        """명령 탭 초기화"""
        command_tab = QWidget()
        layout = QVBoxLayout(command_tab)
        
        # 상단 설명
        desc_label = QLabel("BlueAI에 자연어 명령을 입력하세요:")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 명령 입력 필드 - 먼저 생성
        self.command_input = QTextEdit()
        self.command_input.setPlaceholderText("예: 'Google에서 파이썬 검색하기'")
        self.command_input.setMinimumHeight(100)
        # 이벤트 필터 설치는 객체 생성 후에
        self.command_input.installEventFilter(self)
        layout.addWidget(self.command_input)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        # 실행 버튼
        self.run_button = QPushButton("실행")
        self.run_button.clicked.connect(self.execute_command)
        self.run_button.setMinimumWidth(100)
        button_layout.addWidget(self.run_button)
        
        # 중지 버튼
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_execution)
        self.stop_button.setMinimumWidth(100)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        # 저장 버튼
        self.save_button = QPushButton("명령 저장")
        self.save_button.clicked.connect(self.save_command)
        self.save_button.setMinimumWidth(100)
        button_layout.addWidget(self.save_button)
        
        # 로드 버튼
        self.load_button = QPushButton("명령 불러오기")
        self.load_button.clicked.connect(self.load_command)
        self.load_button.setMinimumWidth(100)
        button_layout.addWidget(self.load_button)
        
        layout.addLayout(button_layout)
        
        # 결과 표시 영역
        result_group = QGroupBox("실행 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        # 탭 추가
        self.tabs.addTab(command_tab, "자연어 명령")
    
    def eventFilter(self, obj, event):
        """이벤트 필터 - 키 이벤트 처리"""
        if obj == self.command_input and event.type() == QEvent.KeyPress:
            # Return과 Enter 키를 구분하여 하나만 처리
            if event.key() == Qt.Key_Return:
                # Shift+Return - 새 줄 추가
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                
                # Enter만 - 명령 실행
                self.confirm_execute()
                return True  # 이벤트 처리 완료
        
        return super().eventFilter(obj, event)

    def confirm_execute(self):
        """실행 확인 대화상자"""
        command = self.command_input.toPlainText().strip()
        if not command:
            return
        
        reply = QMessageBox.question(
            self, '명령 실행', f"다음 명령을 실행하시겠습니까?\n\n{command}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.execute_command()

    def init_workflow_tab(self):
        """워크플로우 탭 초기화"""
        workflow_tab = QWidget()
        layout = QVBoxLayout(workflow_tab)
        
        # 워크플로우 편집기
        editor_group = QGroupBox("워크플로우 편집기")
        editor_layout = QVBoxLayout(editor_group)
        
        # 워크플로우 JSON
        self.workflow_editor = QTextEdit()
        self.workflow_editor.setPlaceholderText("워크플로우 JSON을 입력하세요")
        self.workflow_editor.setMinimumHeight(400)
        editor_layout.addWidget(self.workflow_editor)
        
        # 버튼 영역
        workflow_buttons = QHBoxLayout()
        
        # 실행 버튼
        self.workflow_run_button = QPushButton("워크플로우 실행")
        self.workflow_run_button.clicked.connect(self.execute_workflow)
        workflow_buttons.addWidget(self.workflow_run_button)
        
        # 중지 버튼
        self.workflow_stop_button = QPushButton("중지")
        self.workflow_stop_button.clicked.connect(self.stop_execution)
        self.workflow_stop_button.setEnabled(False)
        workflow_buttons.addWidget(self.workflow_stop_button)
        
        # 저장 버튼
        self.workflow_save_button = QPushButton("저장")
        self.workflow_save_button.clicked.connect(self.save_workflow)
        workflow_buttons.addWidget(self.workflow_save_button)
        
        # 불러오기 버튼
        self.workflow_load_button = QPushButton("불러오기")
        self.workflow_load_button.clicked.connect(self.load_workflow)
        workflow_buttons.addWidget(self.workflow_load_button)
        
        # 검증 버튼
        self.workflow_validate_button = QPushButton("JSON 검증")
        self.workflow_validate_button.clicked.connect(self.validate_workflow)
        workflow_buttons.addWidget(self.workflow_validate_button)
        
        editor_layout.addLayout(workflow_buttons)
        layout.addWidget(editor_group)
        
        # 워크플로우 결과
        result_group = QGroupBox("워크플로우 실행 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.workflow_result_text = QTextEdit()
        self.workflow_result_text.setReadOnly(True)
        result_layout.addWidget(self.workflow_result_text)
        
        layout.addWidget(result_group)
        
        # 탭 추가
        self.tabs.addTab(workflow_tab, "워크플로우")
    
    def init_monitor_tab(self):
        """모니터링 탭 초기화"""
        monitor_tab = QWidget()
        layout = QVBoxLayout(monitor_tab)
        
        # 활성 워크플로우 테이블
        group_active = QGroupBox("활성 워크플로우")
        active_layout = QVBoxLayout(group_active)
        
        self.workflow_table = QTableWidget(0, 4)
        self.workflow_table.setHorizontalHeaderLabels(["ID", "상태", "완료 단계", "실행 시간"])
        self.workflow_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.workflow_table.setSelectionBehavior(QTableWidget.SelectRows)
        active_layout.addWidget(self.workflow_table)
        
        # 버튼 영역
        monitor_buttons = QHBoxLayout()
        
        # 새로고침 버튼
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_workflows)
        monitor_buttons.addWidget(self.refresh_button)
        
        # 워크플로우 정보 버튼
        self.workflow_info_button = QPushButton("워크플로우 정보")
        self.workflow_info_button.clicked.connect(self.show_workflow_info)
        monitor_buttons.addWidget(self.workflow_info_button)
        
        # 워크플로우 중지 버튼
        self.cancel_workflow_button = QPushButton("워크플로우 중지")
        self.cancel_workflow_button.clicked.connect(self.cancel_selected_workflow)
        monitor_buttons.addWidget(self.cancel_workflow_button)
        
        active_layout.addLayout(monitor_buttons)
        layout.addWidget(group_active)
        
        # 최근 실행 기록
        group_history = QGroupBox("최근 실행 기록")
        history_layout = QVBoxLayout(group_history)
        
        # 전체 선택 체크박스 추가
        select_all_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("전체 선택")
        self.select_all_checkbox.clicked.connect(self.toggle_select_all_history)
        select_all_layout.addWidget(self.select_all_checkbox)
        select_all_layout.addStretch()
        history_layout.addLayout(select_all_layout)

        # 기록 목록 설정
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QListWidget.ExtendedSelection)  # 다중 선택 모드 활성화
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        history_layout.addWidget(self.history_list)

        # 기록 관리 버튼 영역
        history_buttons = QHBoxLayout()
        
        # 기록 불러오기 버튼
        self.load_history_button = QPushButton("기록 불러오기")
        self.load_history_button.clicked.connect(self.load_history)
        history_buttons.addWidget(self.load_history_button)
        
        # 선택 삭제 버튼 추가
        self.delete_selected_button = QPushButton("선택 삭제")
        self.delete_selected_button.clicked.connect(self.delete_selected_history)
        history_buttons.addWidget(self.delete_selected_button)
        
        # 기록 지우기 버튼
        self.clear_history_button = QPushButton("기록 지우기")
        self.clear_history_button.clicked.connect(self.clear_history)
        history_buttons.addWidget(self.clear_history_button)
        
        history_layout.addLayout(history_buttons)
        layout.addWidget(group_history)
        
        # 탭 추가
        self.tabs.addTab(monitor_tab, "모니터링")

    def delete_selected_history(self):
        """선택된 기록 항목 삭제"""
        selected_items = []
        
        # 선택된 항목 찾기
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            widget = self.history_list.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox, "history_checkbox")
                if checkbox and checkbox.isChecked():
                    selected_items.append(item)
        
        if not selected_items:
            QMessageBox.information(self, "선택 삭제", "삭제할 항목을 선택해 주세요.")
            return
        
        # 삭제 확인
        reply = QMessageBox.question(
            self, '항목 삭제', f"선택한 {len(selected_items)}개 항목을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 선택된 항목 삭제
            for item in reversed(selected_items):  # 역순으로 삭제 (인덱스 변경 방지)
                row = self.history_list.row(item)
                self.history_list.takeItem(row)
            
            # 전체 선택 체크박스 해제
            self.select_all_checkbox.setChecked(False)
            
            # 변경사항 저장
            self.save_history()
            self.statusBar().showMessage(f"{len(selected_items)}개 항목이 삭제되었습니다.")
    
    def init_settings_tab(self):
        """설정 탭 초기화"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 자동화 옵션
        group_auto = QGroupBox("자동화 옵션")
        auto_layout = QGridLayout(group_auto)
        
        # 모드 선택
        auto_layout.addWidget(QLabel("실행 모드:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["신속 모드", "균형 모드", "정확도 모드"])
        self.mode_combo.setCurrentIndex(1)  # 기본값은 균형 모드
        auto_layout.addWidget(self.mode_combo, 0, 1)
        
        # 헤드리스 모드
        self.headless_check = QCheckBox("헤드리스 모드 (GUI 없이 실행)")
        auto_layout.addWidget(self.headless_check, 1, 0, 1, 2)

        # 작업 완료 시 자동 종료 추가
        self.auto_close_check = QCheckBox("작업 완료 시 브라우저 자동 종료")
        self.auto_close_check.setChecked(False)  # 기본값은 비활성화
        auto_layout.addWidget(self.auto_close_check, 2, 0, 1, 2)
        
        # 브라우저 선택
        auto_layout.addWidget(QLabel("브라우저:"), 3, 0)
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Edge", "Chrome", "Firefox"])
        auto_layout.addWidget(self.browser_combo, 3, 1)
        
        # 인터럽션 처리 옵션
        self.handle_cookies = QCheckBox("쿠키 알림 자동 처리")
        self.handle_cookies.setChecked(True)
        auto_layout.addWidget(self.handle_cookies, 4, 0, 1, 2)
        
        self.handle_popups = QCheckBox("팝업 자동 처리")
        self.handle_popups.setChecked(True)
        auto_layout.addWidget(self.handle_popups, 5, 0, 1, 2)
        
        self.handle_ads = QCheckBox("광고 자동 처리")
        self.handle_ads.setChecked(True)
        auto_layout.addWidget(self.handle_ads, 6, 0, 1, 2)
        
        # 타임아웃 설정
        auto_layout.addWidget(QLabel("탐색 타임아웃 (초):"), 7, 0)
        self.navigation_timeout = QLineEdit("30")
        auto_layout.addWidget(self.navigation_timeout, 7, 1)
        
        auto_layout.addWidget(QLabel("요소 타임아웃 (초):"), 8, 0)
        self.element_timeout = QLineEdit("5")
        auto_layout.addWidget(self.element_timeout, 8, 1)
        
        layout.addWidget(group_auto)
        
        # 인식 설정
        group_recog = QGroupBox("인식 설정")
        recog_layout = QGridLayout(group_recog)
        
        # 인식 시스템 활성화
        self.enable_selector = QCheckBox("선택자 기반 인식")
        self.enable_selector.setChecked(True)
        recog_layout.addWidget(self.enable_selector, 0, 0)
        
        self.enable_template = QCheckBox("템플릿 매칭 인식")
        self.enable_template.setChecked(True)
        recog_layout.addWidget(self.enable_template, 0, 1)
        
        self.enable_ocr = QCheckBox("OCR 인식")
        self.enable_ocr.setChecked(True)
        recog_layout.addWidget(self.enable_ocr, 1, 0)
        
        self.enable_aria = QCheckBox("ARIA 인식")
        self.enable_aria.setChecked(True)
        recog_layout.addWidget(self.enable_aria, 1, 1)
        
        layout.addWidget(group_recog)
        
        # 버튼 영역
        settings_buttons = QHBoxLayout()
        
        # 설정 저장 버튼
        self.save_settings_button = QPushButton("설정 저장")
        self.save_settings_button.clicked.connect(self.save_settings)
        settings_buttons.addWidget(self.save_settings_button)
        
        # 설정 불러오기 버튼
        self.load_settings_button = QPushButton("설정 불러오기")
        self.load_settings_button.clicked.connect(self.load_settings)
        settings_buttons.addWidget(self.load_settings_button)
        
        # 기본값 복원 버튼
        self.reset_settings_button = QPushButton("기본값 복원")
        self.reset_settings_button.clicked.connect(self.reset_settings)
        settings_buttons.addWidget(self.reset_settings_button)
        
        layout.addLayout(settings_buttons)
        
        # 남은 공간 채우기
        layout.addStretch()
        
        # 탭 추가
        self.tabs.addTab(settings_tab, "설정")
    
    def init_log_tab(self):
        """로그 탭 초기화"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        # 로그 표시 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont("Courier New", 9)
        self.log_text.setFont(font)
        layout.addWidget(self.log_text)
        
        # 버튼 영역
        log_buttons = QHBoxLayout()
        
        # 로그 지우기 버튼
        self.clear_log_button = QPushButton("로그 지우기")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons.addWidget(self.clear_log_button)
        
        # 로그 저장 버튼
        self.save_log_button = QPushButton("로그 저장")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons.addWidget(self.save_log_button)
        
        # 로그 레벨 선택
        log_buttons.addWidget(QLabel("로그 레벨:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentIndex(1)  # INFO
        self.log_level_combo.currentIndexChanged.connect(self.change_log_level)
        log_buttons.addWidget(self.log_level_combo)
        
        layout.addLayout(log_buttons)
        
        # 탭 추가
        self.tabs.addTab(log_tab, "로그")
    
    def set_styles(self):
        """스타일 설정"""
        # 기본 스타일시트
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
            QPushButton {
                background-color: #5c87b2;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a7196;
            }
            QPushButton:pressed {
                background-color: #3c5a7d;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QLineEdit, QTextEdit, QListWidget, QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                background-color: #ffffff;
            }
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                background-color: #ffffff;
            }
            QLabel {
                color: #333333;
            }
        """)
    
    def initialize_blueai(self):
        """BlueAI 초기화"""
        try:
            config_file = self.settings.value("config_file", None)
            self.blueai = BlueAI(config_file=config_file)
            
            # 자동 실행 상태 설정 - 클래스 변수 설정
            self.blueai.auto_execute = False
            
            # 초기화 호출
            success = self.blueai.initialize()
            
            if success:
                self.statusBar().showMessage("BlueAI 초기화 완료")
                self.log("BlueAI 초기화 완료", logging.INFO)
            else:
                self.statusBar().showMessage("BlueAI 초기화 실패")
                self.log("BlueAI 초기화 실패", logging.ERROR)
                QMessageBox.critical(self, "초기화 오류", "BlueAI 초기화에 실패했습니다.")
                
            return success
        except Exception as e:
            self.statusBar().showMessage(f"BlueAI 초기화 오류: {str(e)}")
            self.log(f"BlueAI 초기화 오류: {str(e)}", logging.ERROR)
            QMessageBox.critical(self, "초기화 오류", f"BlueAI 초기화 중 오류가 발생했습니다: {str(e)}")
            return False
    
    def setup_logging(self):
        """로그 설정"""
        # 로그 핸들러 설정
        self.log_handler = LogHandler(self.log)
        self.log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        
        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        
        # BlueAI 로거에 핸들러 추가
        blueai_logger = logging.getLogger('blueai')
        blueai_logger.addHandler(self.log_handler)
        
        # 초기 로그 메시지
        self.log("로그 시스템 초기화 완료", logging.INFO)
    
    def log(self, message, level=logging.INFO):
        """로그 표시
        
        Args:
            message: 로그 메시지
            level: 로그 레벨
        """
        # 로그 레벨에 따른 색상
        color = "black"
        if level == logging.DEBUG:
            color = "gray"
        elif level == logging.INFO:
            color = "black"
        elif level == logging.WARNING:
            color = "orange"
        elif level == logging.ERROR:
            color = "red"
        elif level == logging.CRITICAL:
            color = "darkred"
        
        # 로그 텍스트에 메시지 추가
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        level_name = logging.getLevelName(level)
        log_message = f"<font color='{color}'>{timestamp} - {level_name} - {message}</font><br>"
        
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(log_message)
        self.log_text.moveCursor(QTextCursor.End)
    
    def execute_command(self):
        """명령 실행"""
        command = self.command_input.toPlainText().strip()
        if not command:
            QMessageBox.warning(self, "입력 오류", "실행할 명령을 입력하세요.")
            return
        
        # 확인 대화상자 표시
        reply = QMessageBox.question(
            self, '명령 실행', f"다음 명령을 실행하시겠습니까?\n\n{command}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # UI 업데이트
        self.result_text.clear()
        self.result_text.setPlainText("명령 실행 중...")
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage(f"명령 실행 중: {command}")
        
        # 로그 메시지
        self.log(f"명령 실행: {command}", logging.INFO)
        
        try:
            # 명령 실행을 위해 auto_execute를 임시로 True로 설정
            original_auto_execute = getattr(self.blueai, 'auto_execute', True)
            self.blueai.auto_execute = True
            
            # 작업자 스레드 생성 및 실행
            self.worker = WorkerThread(self.blueai, command=command)
            
            # 완료 및 진행 이벤트에 래퍼 함수 연결
            def on_finished_wrapper(result):
                try:
                    # auto_execute 값 복원
                    self.blueai.auto_execute = original_auto_execute
                    self.on_command_finished(result)
                except Exception as e:
                    self.log(f"명령 완료 처리 중 오류: {str(e)}", logging.ERROR)
                    self.run_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
                    self.result_text.setPlainText(f"오류 발생: {str(e)}")
            
            def on_progress_wrapper(progress):
                try:
                    self.on_command_progress(progress)
                except Exception as e:
                    self.log(f"진행 처리 중 오류: {str(e)}", logging.ERROR)
            
            self.worker.finished.connect(on_finished_wrapper)
            self.worker.progress.connect(on_progress_wrapper)
            
            # 시작 전 BlueAI 초기화 확인
            if not hasattr(self.blueai, 'plugin_manager') or not self.blueai.plugin_manager.initialized_plugins:
                self.log("BlueAI 초기화 시작", logging.INFO)
                success = self.blueai.initialize()
                if not success:
                    self.log("BlueAI 초기화 실패", logging.ERROR)
                    self.result_text.setPlainText("초기화 실패: BlueAI 시스템을 초기화할 수 없습니다")
                    self.run_button.setEnabled(True)
                    self.stop_button.setEnabled(False)
                    return
            
            # 작업자 스레드 시작
            self.worker.start()
        except Exception as e:
            self.log(f"명령 실행 설정 중 오류: {str(e)}", logging.ERROR)
            self.result_text.setPlainText(f"오류 발생: {str(e)}")
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        
    def on_command_finished(self, result, original_auto_execute=False):
        """명령 실행 완료 핸들러"""
        # auto_execute 값 복원
        self.blueai.auto_execute = original_auto_execute
        
        # 나머지 코드는 그대로 유지
        # UI 업데이트
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 상태 표시
        status = result.get('status', 'unknown')
        if status == 'completed':
            self.statusBar().showMessage("명령 실행 완료")
            self.log("명령 실행 완료", logging.INFO)
        else:
            error = result.get('error', '알 수 없는 오류')
            self.statusBar().showMessage(f"명령 실행 실패: {error}")
            self.log(f"명령 실행 실패: {error}", logging.ERROR)
        
        # 결과 표시
        self.result_text.clear()
        self.result_text.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 기록에 추가
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        item_text = f"{timestamp} - 명령: {self.command_input.toPlainText()[:30]}..."
        
        data = {
            'type': 'command',
            'command': self.command_input.toPlainText(),
            'result': result,
            'timestamp': timestamp
        }
        
        self._add_history_item(item_text, data)
        # 작업 완료 후 자동 종료 옵션이 활성화된 경우 브라우저 종료
        if self.auto_close_check.isChecked() and hasattr(self.blueai, 'plugin_manager'):
            try:
                # Playwright 플러그인 찾기
                playwright_plugin = self.blueai.plugin_manager.get_plugin("playwright_automation")
                if playwright_plugin and playwright_plugin.get_plugin_info().id in self.blueai.plugin_manager.initialized_plugins:
                    # 브라우저 정리 수행
                    self.log("자동 종료 옵션에 따라 브라우저 정리 중...", logging.INFO)
                    self.blueai.plugin_manager.cleanup_plugin("playwright_automation")
            except Exception as e:
                self.log(f"브라우저 자동 종료 중 오류: {str(e)}", logging.ERROR)

    def _add_history_item(self, item_text, data):
        """기록에 항목 추가 (체크박스 포함)"""
        item = QListWidgetItem()
        self.history_list.insertItem(0, item)  # 최신 항목을 맨 위에 추가
        
        # 체크박스가 있는 위젯 생성
        history_widget = QWidget()
        layout = QHBoxLayout(history_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 체크박스 추가
        checkbox = QCheckBox()
        checkbox.setObjectName("history_checkbox")
        layout.addWidget(checkbox)
        
        # 텍스트 라벨 추가
        text_label = QLabel(item_text)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(text_label, 1)  # 1은 stretch factor
        
        # 데이터 설정
        item.setData(Qt.UserRole, data)
        
        # 위젯 크기 설정
        item.setSizeHint(history_widget.sizeHint())
        self.history_list.setItemWidget(item, history_widget)
    
        return item

    def on_command_progress(self, progress):
        """명령 실행 진행 핸들러
        
        Args:
            progress: 진행 정보
        """
        # 상태 표시
        status = progress.get('status', 'unknown')
        message = progress.get('message', '')
        
        if status and message:
            self.statusBar().showMessage(f"{status}: {message}")
            self.log(message, logging.INFO)
    
    def stop_execution(self):
        """실행 중지"""
        if self.worker and self.worker.isRunning():
            # 워커 스레드 종료
            self.worker.terminate()
            self.worker.wait()
            
            # UI 업데이트
            self.run_button.setEnabled(True)
            self.workflow_run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.workflow_stop_button.setEnabled(False)
            
            # 상태 표시
            self.statusBar().showMessage("실행 중지됨")
            self.log("실행이 사용자에 의해 중지되었습니다", logging.WARNING)
            
            # 워크플로우 취소
            if self.current_workflow_id:
                try:
                    self.blueai.workflow_manager.cancel_workflow(self.current_workflow_id)
                    self.current_workflow_id = None
                except Exception as e:
                    self.log(f"워크플로우 취소 중 오류: {str(e)}", logging.ERROR)
    
    def save_command(self):
        """명령 저장"""
        command = self.command_input.toPlainText().strip()
        if not command:
            QMessageBox.warning(self, "저장 오류", "저장할 명령이 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "명령 저장", "", "텍스트 파일 (*.txt);;모든 파일 (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(command)
                self.statusBar().showMessage(f"명령이 저장되었습니다: {file_path}")
                self.log(f"명령이 저장되었습니다: {file_path}", logging.INFO)
            except Exception as e:
                self.log(f"명령 저장 중 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "저장 오류", f"명령 저장 중 오류가 발생했습니다: {str(e)}")
    
    def load_command(self):
        """명령 불러오기"""
        file_path, _ = QFileDialog.getOpenFileName(self, "명령 불러오기", "", "텍스트 파일 (*.txt);;모든 파일 (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    command = f.read()
                self.command_input.setPlainText(command)
                self.statusBar().showMessage(f"명령이 로드되었습니다: {file_path}")
                self.log(f"명령이 로드되었습니다: {file_path}", logging.INFO)
            except Exception as e:
                self.log(f"명령 로드 중 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "로드 오류", f"명령 로드 중 오류가 발생했습니다: {str(e)}")
    
    def execute_workflow(self):
        """워크플로우 실행"""
        workflow_json = self.workflow_editor.toPlainText().strip()
        if not workflow_json:
            QMessageBox.warning(self, "입력 오류", "실행할 워크플로우를 입력하세요.")
            return
        
        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON 오류", f"워크플로우 JSON 형식이 잘못되었습니다: {str(e)}")
            self.log(f"워크플로우 JSON 파싱 오류: {str(e)}", logging.ERROR)
            return
        
        # 필수 필드 확인
        if 'id' not in workflow or 'steps' not in workflow:
            QMessageBox.warning(self, "워크플로우 오류", "워크플로우에 필수 필드(id, steps)가 없습니다.")
            return
        
        # 설정 준비
        settings = self.get_current_settings()
        
        # UI 업데이트
        self.workflow_result_text.clear()
        self.workflow_result_text.setPlainText("워크플로우 실행 중...")
        self.workflow_run_button.setEnabled(False)
        self.workflow_stop_button.setEnabled(True)
        self.statusBar().showMessage(f"워크플로우 실행 중: {workflow['id']}")
        
        # 로그 메시지
        self.log(f"워크플로우 실행: {workflow['id']}", logging.INFO)
        
        # 작업자 스레드 생성 및 실행
        self.worker = WorkerThread(self.blueai, workflow=workflow, settings=settings)
        self.worker.finished.connect(self.on_workflow_finished)
        self.worker.progress.connect(self.on_workflow_progress)
        self.current_workflow_id = workflow['id']
        self.worker.start()
        
        # 상태 모니터링 타이머 시작
        if self.status_timer is None:
            self.status_timer = QTimer(self)
            self.status_timer.timeout.connect(self.update_workflow_status)
            self.status_timer.start(2000)  # 2초마다 업데이트
    
    def on_workflow_finished(self, result):
        """워크플로우 실행 완료 핸들러
        
        Args:
            result: 실행 결과
        """
        # UI 업데이트
        self.workflow_run_button.setEnabled(True)
        self.workflow_stop_button.setEnabled(False)
        
        # 상태 표시
        status = result.get('status', 'unknown')
        if status == 'completed':
            self.statusBar().showMessage("워크플로우 실행 완료")
            self.log("워크플로우 실행 완료", logging.INFO)
        else:
            error = result.get('error', '알 수 없는 오류')
            self.statusBar().showMessage(f"워크플로우 실행 실패: {error}")
            self.log(f"워크플로우 실행 실패: {error}", logging.ERROR)
        
        # 결과 표시
        self.workflow_result_text.clear()
        self.workflow_result_text.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 워크플로우 ID 초기화
        self.current_workflow_id = None

        # 작업 완료 후 자동 종료 옵션이 활성화된 경우 브라우저 종료
        if self.auto_close_check.isChecked() and hasattr(self.blueai, 'plugin_manager'):
            try:
                # Playwright 플러그인 찾기
                playwright_plugin = self.blueai.plugin_manager.get_plugin("playwright_automation")
                if playwright_plugin and playwright_plugin.get_plugin_info().id in self.blueai.plugin_manager.initialized_plugins:
                    # 브라우저 정리 수행
                    self.log("자동 종료 옵션에 따라 브라우저 정리 중...", logging.INFO)
                    self.blueai.plugin_manager.cleanup_plugin("playwright_automation")
            except Exception as e:
                self.log(f"브라우저 자동 종료 중 오류: {str(e)}", logging.ERROR)
        
        # 기록에 추가
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            workflow_data = json.loads(self.workflow_editor.toPlainText())
            workflow_id = workflow_data.get('id', 'unknown')
            workflow_name = workflow_data.get('name', workflow_id)
            
            item_text = f"{timestamp} - 워크플로우: {workflow_name}"
            
            data = {
                'type': 'workflow',
                'workflow': workflow_data,
                'result': result,
                'timestamp': timestamp
            }
            
            # 체크박스가 있는 기록 항목 추가
            self._add_history_item(item_text, data)
            
        except Exception as e:
            self.log(f"기록 추가 중 오류: {str(e)}", logging.ERROR)
    
    def on_workflow_progress(self, progress):
        """워크플로우 실행 진행 핸들러
        
        Args:
            progress: 진행 정보
        """
        # 상태 표시
        status = progress.get('status', 'unknown')
        message = progress.get('message', '')
        
        if status and message:
            self.statusBar().showMessage(f"{status}: {message}")
            self.log(message, logging.INFO)
    
    def validate_workflow(self):
        """워크플로우 JSON 검증"""
        workflow_json = self.workflow_editor.toPlainText().strip()
        if not workflow_json:
            QMessageBox.warning(self, "검증 오류", "검증할 워크플로우를 입력하세요.")
            return
        
        try:
            workflow = json.loads(workflow_json)
            
            # 필수 필드 확인
            required_fields = ['id', 'steps']
            missing_fields = [field for field in required_fields if field not in workflow]
            
            if missing_fields:
                QMessageBox.warning(self, "검증 실패", f"워크플로우에 필수 필드가 없습니다: {', '.join(missing_fields)}")
                return
            
            # 단계 확인
            if not isinstance(workflow['steps'], list) or len(workflow['steps']) == 0:
                QMessageBox.warning(self, "검증 실패", "워크플로우에 유효한 단계가 없습니다.")
                return
            
            # 각 단계의 필수 필드 확인
            step_errors = []
            for i, step in enumerate(workflow['steps']):
                if 'id' not in step:
                    step_errors.append(f"단계 {i+1}: id 필드 없음")
                if 'type' not in step:
                    step_errors.append(f"단계 {i+1}: type 필드 없음")
            
            if step_errors:
                QMessageBox.warning(self, "검증 실패", "워크플로우 단계 오류:\n" + "\n".join(step_errors))
                return
            
            # 포매팅된 JSON으로 업데이트
            formatted_json = json.dumps(workflow, indent=2, ensure_ascii=False)
            self.workflow_editor.setPlainText(formatted_json)
            
            QMessageBox.information(self, "검증 성공", "워크플로우 JSON이 유효합니다.")
            self.log("워크플로우 JSON 검증 성공", logging.INFO)
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON 오류", f"워크플로우 JSON 형식이 잘못되었습니다:\n{str(e)}")
            self.log(f"워크플로우 JSON 파싱 오류: {str(e)}", logging.ERROR)
    
    def save_workflow(self):
        """워크플로우 저장"""
        workflow_json = self.workflow_editor.toPlainText().strip()
        if not workflow_json:
            QMessageBox.warning(self, "저장 오류", "저장할 워크플로우가 없습니다.")
            return
        
        # JSON 검증
        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON 오류", f"워크플로우 JSON 형식이 잘못되었습니다: {str(e)}")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(self, "워크플로우 저장", "", "JSON 파일 (*.json);;모든 파일 (*)")
        if file_path:
            try:
                # 포매팅된 JSON으로 저장
                formatted_json = json.dumps(workflow, indent=2, ensure_ascii=False)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_json)
                self.statusBar().showMessage(f"워크플로우가 저장되었습니다: {file_path}")
                self.log(f"워크플로우가 저장되었습니다: {file_path}", logging.INFO)
            except Exception as e:
                self.log(f"워크플로우 저장 중 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "저장 오류", f"워크플로우 저장 중 오류가 발생했습니다: {str(e)}")
    
    def convert_result_to_workflow(self, result_json):
        """실행 결과 JSON을 워크플로우 정의 형식으로 변환"""
        if not result_json:
            return None
            
        # 기본 워크플로우 구조 생성
        workflow = {
            "id": result_json.get("workflow_id", "unknown_workflow"),
            "name": result_json.get("workflow_id", "Unknown Workflow"),
            "description": "Generated from execution result",
            "steps": []
        }
        
        # 결과에서 단계 추출
        results = result_json.get("results", {})
        for step_id, step_data in results.items():
            step = {
                "id": step_id,
                "type": self._derive_step_type(step_id),  # 단계 ID에서 유형 유추
                "config": {}
            }
            
            # 출력에서 설정 추출
            output = step_data.get("output", {})
            for key, value in output.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    step["config"][key] = value
            
            workflow["steps"].append(step)
        
        return workflow

    def _derive_step_type(self, step_id):
        """단계 ID에서 단계 유형 유추"""
        mapping = {
            "navigate": "web_navigation",
            "handle_interruptions": "interruption_handling",
            "find_search_box": "element_recognition",
            "input_search_term": "input_text",
            "submit_search": "key_press",
            "wait_for_results": "wait_for_load"
        }
        return mapping.get(step_id, "unknown")

    def load_workflow(self):
        """워크플로우 불러오기"""
        file_path, _ = QFileDialog.getOpenFileName(self, "워크플로우 불러오기", "", "JSON 파일 (*.json);;모든 파일 (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_json = f.read()
                
                # JSON 검증
                workflow = json.loads(workflow_json)
                
                # 포매팅된 JSON으로 설정
                formatted_json = json.dumps(workflow, indent=2, ensure_ascii=False)
                self.workflow_editor.setPlainText(formatted_json)
                
                self.statusBar().showMessage(f"워크플로우가 로드되었습니다: {file_path}")
                self.log(f"워크플로우가 로드되었습니다: {file_path}", logging.INFO)
            except json.JSONDecodeError as e:
                self.log(f"워크플로우 JSON 파싱 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "로드 오류", f"워크플로우 JSON 형식이 잘못되었습니다: {str(e)}")
            except Exception as e:
                self.log(f"워크플로우 로드 중 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "로드 오류", f"워크플로우 로드 중 오류가 발생했습니다: {str(e)}")
    
    def update_workflow_status(self):
        """워크플로우 상태 업데이트"""
        self.refresh_workflows()
    
    def refresh_workflows(self):
        """워크플로우 목록 새로고침"""
        if not self.blueai or not hasattr(self.blueai, 'workflow_manager'):
            return
        
        # 테이블 초기화
        self.workflow_table.setRowCount(0)
        
        # 활성 워크플로우 가져오기
        active_workflows = self.blueai.workflow_manager.active_workflows
        
        if not active_workflows:
            return
        
        # 테이블에 추가
        for i, (workflow_id, context) in enumerate(active_workflows.items()):
            self.workflow_table.insertRow(i)
            
            # ID
            id_item = QTableWidgetItem(workflow_id)
            self.workflow_table.setItem(i, 0, id_item)
            
            # 상태
            status = context.status.value
            status_item = QTableWidgetItem(status)
            self.workflow_table.setItem(i, 1, status_item)
            
            # 완료 단계
            completed_steps = sum(1 for r in context.results.values() 
                               if r.status == self.blueai.workflow_manager.StepStatus.COMPLETED)
            total_steps = len(context.results)
            steps_item = QTableWidgetItem(f"{completed_steps}/{total_steps}")
            self.workflow_table.setItem(i, 2, steps_item)
            
            # 실행 시간
            execution_time = context.get_execution_time()
            time_item = QTableWidgetItem(f"{execution_time:.1f}초")
            self.workflow_table.setItem(i, 3, time_item)
    
    def show_workflow_info(self):
        """선택된 워크플로우 정보 표시"""
        selected_rows = self.workflow_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "정보", "워크플로우를 선택하세요.")
            return
        
        # 선택된 워크플로우 ID 가져오기
        row = selected_rows[0].row()
        workflow_id = self.workflow_table.item(row, 0).text()
        
        # 워크플로우 상태 가져오기
        status = self.blueai.workflow_manager.get_workflow_status(workflow_id)
        
        if not status:
            QMessageBox.warning(self, "정보 오류", f"워크플로우 정보를 가져올 수 없습니다: {workflow_id}")
            return
        
        # 정보 표시
        info_text = f"워크플로우 ID: {workflow_id}\n"
        info_text += f"상태: {status.get('status', 'unknown')}\n"
        info_text += f"실행 시간: {status.get('execution_time', 0):.1f}초\n"
        info_text += f"전체 단계: {status.get('step_count', 0)}\n"
        info_text += f"완료 단계: {status.get('completed_steps', 0)}\n"
        info_text += f"실패 단계: {status.get('failed_steps', 0)}\n"
        
        QMessageBox.information(self, f"워크플로우 정보: {workflow_id}", info_text)
    
    def cancel_selected_workflow(self):
        """선택된 워크플로우 취소"""
        selected_rows = self.workflow_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "취소", "취소할 워크플로우를 선택하세요.")
            return
        
        # 선택된 워크플로우 ID 가져오기
        row = selected_rows[0].row()
        workflow_id = self.workflow_table.item(row, 0).text()
        
        # 워크플로우 취소
        success = self.blueai.workflow_manager.cancel_workflow(workflow_id)
        
        if success:
            self.statusBar().showMessage(f"워크플로우가 취소되었습니다: {workflow_id}")
            self.log(f"워크플로우가 취소되었습니다: {workflow_id}", logging.INFO)
            
            # 테이블 새로고침
            self.refresh_workflows()
        else:
            QMessageBox.warning(self, "취소 오류", f"워크플로우를 취소할 수 없습니다: {workflow_id}")
    
    def load_history(self):
        """실행 기록 불러오기"""
        try:
            history_file = self.settings.value("history_file", None)
            if not history_file:
                history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueai_history.json")
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                # 기록 목록 초기화
                self.history_list.clear()
                
                # 기록 항목 추가
                for item_data in history_data:
                    timestamp = item_data.get('timestamp', '')
                    item_type = item_data.get('type', 'unknown')
                    
                    if item_type == 'command':
                        command = item_data.get('command', '')
                        item_text = f"{timestamp} - 명령: {command[:30]}..."
                    elif item_type == 'workflow':
                        workflow = item_data.get('workflow', {})
                        workflow_name = workflow.get('name', workflow.get('id', 'unknown'))
                        item_text = f"{timestamp} - 워크플로우: {workflow_name}"
                    else:
                        item_text = f"{timestamp} - {item_type}"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, item_data)
                    self.history_list.addItem(item)
                
                self.statusBar().showMessage(f"기록을 불러왔습니다: {history_file}")
                self.log(f"기록을 불러왔습니다: {history_file}", logging.INFO)
            else:
                self.log(f"기록 파일이 없습니다: {history_file}", logging.WARNING)
        except Exception as e:
            self.log(f"기록 불러오기 중 오류: {str(e)}", logging.ERROR)
            QMessageBox.warning(self, "기록 불러오기 오류", f"기록 불러오기 중 오류가 발생했습니다: {str(e)}")
    
    def save_history(self):
        """실행 기록 저장"""
        try:
            history_file = self.settings.value("history_file", None)
            if not history_file:
                history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueai_history.json")
            
            # 기록 데이터 수집
            history_data = []
            for i in range(self.history_list.count()):
                item = self.history_list.item(i)
                item_data = item.data(Qt.UserRole)
                if item_data:
                    history_data.append(item_data)
            
            # 파일 저장
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            self.statusBar().showMessage(f"기록을 저장했습니다: {history_file}")
            self.log(f"기록을 저장했습니다: {history_file}", logging.INFO)
        except Exception as e:
            self.log(f"기록 저장 중 오류: {str(e)}", logging.ERROR)
            QMessageBox.warning(self, "기록 저장 오류", f"기록 저장 중 오류가 발생했습니다: {str(e)}")
    
    def clear_history(self):
        """기록 지우기"""
        reply = QMessageBox.question(self, '기록 지우기', "정말로 모든 기록을 지우시겠습니까?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.history_list.clear()
            self.statusBar().showMessage("기록이 지워졌습니다.")
            self.log("기록이 지워졌습니다.", logging.INFO)
            
            # 기록 파일도 삭제
            history_file = self.settings.value("history_file", None)
            if history_file and os.path.exists(history_file):
                try:
                    os.remove(history_file)
                except Exception as e:
                    self.log(f"기록 파일 삭제 중 오류: {str(e)}", logging.ERROR)
    
    def get_current_settings(self) -> Dict[str, Any]:
        """현재 설정 가져오기
        
        Returns:
            설정 사전
        """
        # 실행 모드
        mode_map = {
            0: "fast",      # 신속 모드
            1: "balanced",  # 균형 모드
            2: "accurate"   # 정확도 모드
        }
        mode = mode_map.get(self.mode_combo.currentIndex(), "balanced")
        
        # 브라우저 설정
        browser_type_map = {
            0: "edge",      # Edge
            1: "chromium",  # Chrome
            2: "firefox"    # Firefox
        }
        browser_type = browser_type_map.get(self.browser_combo.currentIndex(), "chromium")
        
        # 타임아웃 설정
        try:
            navigation_timeout = float(self.navigation_timeout.text())
        except ValueError:
            navigation_timeout = 30.0
            
        try:
            element_timeout = float(self.element_timeout.text())
        except ValueError:
            element_timeout = 5.0
        
        # 브라우저 설정
        browser_config = {
            'browser_type': browser_type,
            'headless': self.headless_check.isChecked(),
            'auto_close': self.auto_close_check.isChecked(),
            'timeout': int(navigation_timeout * 1000),
            'use_edge': browser_type == "edge"
        }
        
        # 인터럽션 처리 설정
        interruption_types = []
        if self.handle_cookies.isChecked():
            interruption_types.append("cookies")
        if self.handle_popups.isChecked():
            interruption_types.append("popups")
        if self.handle_ads.isChecked():
            interruption_types.append("ads")
        
        # 인식 전략 설정
        recognition_strategies = []
        if self.enable_selector.isChecked():
            recognition_strategies.append("selector")
        if self.enable_template.isChecked():
            recognition_strategies.append("template")
        if self.enable_ocr.isChecked():
            recognition_strategies.append("ocr")
        if self.enable_aria.isChecked():
            recognition_strategies.append("aria")
        
        # 최종 설정
        settings = {
            'mode': mode,
            'browser_config': browser_config,
            'ignore_recognition_errors': mode == "fast",  # 신속 모드에서는 인식 오류 무시
            'timeouts': {
                'navigation': navigation_timeout,
                'element': element_timeout,
                'action': element_timeout / 2  # 액션 타임아웃은 요소 타임아웃의 절반
            },
            'interruption_types': interruption_types,
            'recognition_strategies': recognition_strategies
        }
        
        return settings
    
    def save_settings(self):
        """설정 저장"""
        # 현재 설정 가져오기
        settings = self.get_current_settings()
        
        # UI 설정 추가
        ui_settings = {
            'window_geometry': self.saveGeometry().toBase64().data().decode(),
            'window_state': self.saveState().toBase64().data().decode(),
            'mode_index': self.mode_combo.currentIndex(),
            'browser_index': self.browser_combo.currentIndex(),
            'headless': self.headless_check.isChecked(),
            'auto_close': self.auto_close_check.isChecked(),
            'handle_cookies': self.handle_cookies.isChecked(),
            'handle_popups': self.handle_popups.isChecked(),
            'handle_ads': self.handle_ads.isChecked(),
            'navigation_timeout': self.navigation_timeout.text(),
            'element_timeout': self.element_timeout.text(),
            'enable_selector': self.enable_selector.isChecked(),
            'enable_template': self.enable_template.isChecked(),
            'enable_ocr': self.enable_ocr.isChecked(),
            'enable_aria': self.enable_aria.isChecked(),
            'log_level': self.log_level_combo.currentText()
        }
        
        settings.update({'ui_settings': ui_settings})
        
        # 설정 파일 저장
        try:
            settings_file = self.settings.value("settings_file", None)
            if not settings_file:
                settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueai_settings.json")
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # QSettings에 저장
            self.settings.setValue("settings_file", settings_file)
            
            self.statusBar().showMessage(f"설정이 저장되었습니다: {settings_file}")
            self.log(f"설정이 저장되었습니다: {settings_file}", logging.INFO)
        except Exception as e:
            self.log(f"설정 저장 중 오류: {str(e)}", logging.ERROR)
            QMessageBox.critical(self, "설정 저장 오류", f"설정 저장 중 오류가 발생했습니다: {str(e)}")
    
    def load_settings(self):
        """설정 불러오기"""
        try:
            settings_file = self.settings.value("settings_file", None)
            if not settings_file:
                settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueai_settings.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # UI 설정 적용
                ui_settings = settings.get('ui_settings', {})
                
                # 윈도우 설정
                if 'window_geometry' in ui_settings:
                    self.restoreGeometry(bytes(ui_settings['window_geometry'], 'utf-8'))
                if 'window_state' in ui_settings:
                    self.restoreState(bytes(ui_settings['window_state'], 'utf-8'))
                
                # 콤보박스 설정
                if 'mode_index' in ui_settings:
                    self.mode_combo.setCurrentIndex(ui_settings['mode_index'])
                if 'browser_index' in ui_settings:
                    self.browser_combo.setCurrentIndex(ui_settings['browser_index'])
                
                # 체크박스 설정
                if 'headless' in ui_settings:
                    self.headless_check.setChecked(ui_settings['headless'])
                if 'auto_close' in ui_settings:
                    self.auto_close_check.setChecked(ui_settings['auto_close'])
                if 'handle_cookies' in ui_settings:
                    self.handle_cookies.setChecked(ui_settings['handle_cookies'])
                if 'handle_popups' in ui_settings:
                    self.handle_popups.setChecked(ui_settings['handle_popups'])
                if 'handle_ads' in ui_settings:
                    self.handle_ads.setChecked(ui_settings['handle_ads'])
                
                # 텍스트 필드 설정
                if 'navigation_timeout' in ui_settings:
                    self.navigation_timeout.setText(ui_settings['navigation_timeout'])
                if 'element_timeout' in ui_settings:
                    self.element_timeout.setText(ui_settings['element_timeout'])
                
                # 인식 설정
                if 'enable_selector' in ui_settings:
                    self.enable_selector.setChecked(ui_settings['enable_selector'])
                if 'enable_template' in ui_settings:
                    self.enable_template.setChecked(ui_settings['enable_template'])
                if 'enable_ocr' in ui_settings:
                    self.enable_ocr.setChecked(ui_settings['enable_ocr'])
                if 'enable_aria' in ui_settings:
                    self.enable_aria.setChecked(ui_settings['enable_aria'])
                
                # 로그 레벨 설정
                if 'log_level' in ui_settings:
                    index = self.log_level_combo.findText(ui_settings['log_level'])
                    if index >= 0:
                        self.log_level_combo.setCurrentIndex(index)
                
                self.statusBar().showMessage(f"설정을 불러왔습니다: {settings_file}")
                self.log(f"설정을 불러왔습니다: {settings_file}", logging.INFO)
            else:
                self.log(f"설정 파일이 없습니다: {settings_file}", logging.WARNING)
        except Exception as e:
            self.log(f"설정 불러오기 중 오류: {str(e)}", logging.ERROR)
            QMessageBox.warning(self, "설정 불러오기 오류", f"설정 불러오기 중 오류가 발생했습니다: {str(e)}")
    
    def reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(self, '설정 초기화', "정말로 모든 설정을 기본값으로 초기화하시겠습니까?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 모드 초기화
            self.mode_combo.setCurrentIndex(1)  # 균형 모드
            
            # 브라우저 초기화
            self.browser_combo.setCurrentIndex(0)  # Edge
            
            # 체크박스 초기화
            self.headless_check.setChecked(False)
            self.auto_close_check.setChecked(False)
            self.handle_cookies.setChecked(True)
            self.handle_popups.setChecked(True)
            self.handle_ads.setChecked(True)
            
            # 타임아웃 초기화
            self.navigation_timeout.setText("30")
            self.element_timeout.setText("5")
            
            # 인식 설정 초기화
            self.enable_selector.setChecked(True)
            self.enable_template.setChecked(True)
            self.enable_ocr.setChecked(True)
            self.enable_aria.setChecked(True)
            
            # 로그 레벨 초기화
            self.log_level_combo.setCurrentIndex(1)  # INFO
            
            self.statusBar().showMessage("설정이 초기화되었습니다.")
            self.log("설정이 초기화되었습니다.", logging.INFO)
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.clear()
        self.log("로그가 지워졌습니다.", logging.INFO)
    
    def save_log(self):
        """로그 저장"""
        file_path, _ = QFileDialog.getSaveFileName(self, "로그 저장", "", "텍스트 파일 (*.txt);;HTML 파일 (*.html);;모든 파일 (*)")
        if file_path:
            try:
                # 파일 확장자에 따라 저장 형식 결정
                if file_path.endswith('.html'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.log_text.toHtml())
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.log_text.toPlainText())
                
                self.statusBar().showMessage(f"로그가 저장되었습니다: {file_path}")
                self.log(f"로그가 저장되었습니다: {file_path}", logging.INFO)
            except Exception as e:
                self.log(f"로그 저장 중 오류: {str(e)}", logging.ERROR)
                QMessageBox.critical(self, "저장 오류", f"로그 저장 중 오류가 발생했습니다: {str(e)}")
    
    def change_log_level(self):
        """로그 레벨 변경"""
        level_name = self.log_level_combo.currentText()
        level = getattr(logging, level_name)
        
        # 로그 핸들러 레벨 설정
        self.log_handler.setLevel(level)
        
        self.statusBar().showMessage(f"로그 레벨이 변경되었습니다: {level_name}")
        self.log(f"로그 레벨이 변경되었습니다: {level_name}", logging.INFO)
    
    def closeEvent(self, event):
        """앱 종료 이벤트"""
        # 작업 중인 경우 경고
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(self, '종료 확인', "작업이 실행 중입니다. 정말로 종료하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # 작업 중지
            self.stop_execution()
        
        # 설정 저장
        try:
            self.save_settings()
            self.save_history()
        except Exception as e:
            self.log(f"설정 저장 중 오류: {str(e)}", logging.ERROR)
        
        # BlueAI 정리
        if self.blueai:
            try:
                self.blueai.cleanup()
            except Exception as e:
                self.log(f"BlueAI 정리 중 오류: {str(e)}", logging.ERROR)
        
        # 타이머 중지
        if self.status_timer:
            self.status_timer.stop()
        
        # 이벤트 수락
        event.accept()
    
    def on_history_item_clicked(self, item):
        """기록 항목 클릭 핸들러"""
        # 클릭 이벤트가 체크박스에서 발생한 경우 처리
        widget = self.history_list.itemWidget(item)
        if widget:
            checkbox = widget.findChild(QCheckBox, "history_checkbox")
            if checkbox:
                # Ctrl이나 Shift 키가 눌려있는지 확인 (QApplication에서 키보드 상태 가져오기)
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.ControlModifier or modifiers & Qt.ShiftModifier:
                    # 선택된 항목들의 체크박스 상태를 현재 클릭한 체크박스 상태로 변경
                    selected_items = self.history_list.selectedItems()
                    check_state = not checkbox.isChecked()  # 토글 상태
                    
                    for selected_item in selected_items:
                        selected_widget = self.history_list.itemWidget(selected_item)
                        if selected_widget:
                            selected_checkbox = selected_widget.findChild(QCheckBox, "history_checkbox")
                            if selected_checkbox:
                                selected_checkbox.setChecked(check_state)

    def toggle_select_all_history(self, checked):
        """전체 선택/해제 핸들러"""
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            widget = self.history_list.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox, "history_checkbox")
                if checkbox:
                    checkbox.setChecked(checked)


def main():
    """메인 함수"""
    if not PYQT_AVAILABLE:
        print("PyQt5를 찾을 수 없습니다. 'pip install PyQt5' 명령으로 설치하세요.")
        return 1
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 일관된 스타일
    
    # 앱 아이콘 설정 (옵션)
    # app.setWindowIcon(QIcon('blueai_icon.png'))
    
    window = BlueAIGUI()
    window.show()
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())