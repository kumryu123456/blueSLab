#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 메인 윈도우 UI
"""

import logging
import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QTextEdit, QTextBrowser,
                            QStatusBar, QComboBox, QAction, QMenu, QSystemTrayIcon,
                            QMessageBox, QInputDialog, QFileDialog, QTabWidget,
                            QListWidget, QListWidgetItem, QSplitter, QProgressBar,
                            QToolBar, QDockWidget, QTreeWidget, QTreeWidgetItem,
                            QDialogButtonBox, QDialog, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt, QMetaObject, QSize, pyqtSlot, QThread, pyqtSignal, QTimer, QEvent, QObject, Q_ARG
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor, QPalette

from core.plugin_manager import PluginManager
from core.workflow_manager import WorkflowManager, Workflow, WorkflowStatus
from core.settings_manager import SettingsManager
from core.interruption_handler import InterruptionHandler

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class LogViewer(QTextBrowser):
    # 로그 메시지를 위한 시그널 추가
    log_signal = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        
        # 로그 레벨별 색상
        self.log_colors = {
            "DEBUG": QColor(100, 100, 100),  # 회색
            "INFO": QColor(0, 0, 0),         # 검정
            "WARNING": QColor(255, 165, 0),  # 주황
            "ERROR": QColor(255, 0, 0),      # 빨강
            "CRITICAL": QColor(128, 0, 0)    # 어두운 빨강
        }
        
        # 최대 로그 라인 수
        self.max_lines = 1000
        
        # 시그널 연결
        self.log_signal.connect(self._append_log_safe)
    
    def append_log(self, message, level="INFO"):
        """로그 메시지 추가 (스레드 안전)"""
        # 시그널을 통해 메인 스레드에서 처리
        self.log_signal.emit(message, level)
    
    @pyqtSlot(str, str)
    def _append_log_safe(self, message, level):
        """메인 UI 스레드에서 실행되는 실제 로그 추가 메서드"""
        # 현재 시간
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 메시지 형식
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        # 색상 설정
        color = self.log_colors.get(level, QColor(0, 0, 0))
        
        # HTML 태그로 색상 설정
        html = f'<span style="color:{color.name()};">{formatted_message}</span><br>'
        
        # 메시지 추가
        self.append(html)
        
        # 최대 라인 수 제한
        if self.document().lineCount() > self.max_lines:
            cursor = QTextCursor(self.document())
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                              self.document().lineCount() - self.max_lines)
            cursor.removeSelectedText()

class SafeUIUpdater(QObject):
    """UI 업데이트 작업을 메인 스레드에서 안전하게 처리하기 위한 클래스"""
    
    # 시그널 정의
    update_workflow_status_signal = pyqtSignal(object)
    log_message_signal = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def connect_signals(self, main_window):
        """시그널-슬롯 연결 (속성 존재 확인 후)"""
        if hasattr(main_window, 'workflow_status') and hasattr(main_window.workflow_status, 'update_status'):
            self.update_workflow_status_signal.connect(main_window.workflow_status.update_status)
        else:
            logger.warning("workflow_status 또는 update_status 메서드를 찾을 수 없습니다")
            
        if hasattr(main_window, 'log_viewer') and hasattr(main_window.log_viewer, 'append_log'):
            self.log_message_signal.connect(main_window.log_viewer.append_log)
        else:
            logger.warning("log_viewer 또는 append_log 메서드를 찾을 수 없습니다")

class WorkflowStatusWidget(QWidget):
    """워크플로우 상태 표시 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 상태 헤더
        header_layout = QHBoxLayout()
        self.status_label = QLabel("워크플로우 상태: 없음")
        self.status_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)
        header_layout.addWidget(self.progress_bar)
        
        layout.addLayout(header_layout)
        
        # 워크플로우 트리
        self.step_tree = QTreeWidget()
        self.step_tree.setHeaderLabels(["단계", "상태", "시작 시간", "완료 시간", "소요 시간"])
        self.step_tree.setColumnWidth(0, 150)
        self.step_tree.setColumnWidth(1, 100)
        self.step_tree.setColumnWidth(2, 150)
        self.step_tree.setColumnWidth(3, 150)
        layout.addWidget(self.step_tree)
        
        # 결과 영역
        result_layout = QHBoxLayout()
        self.result_label = QLabel("결과:")
        result_layout.addWidget(self.result_label)
        
        result_layout.addStretch()
        
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_status)
        result_layout.addWidget(self.refresh_button)
        
        layout.addLayout(result_layout)
        
        self.result_browser = QTextBrowser()
        layout.addWidget(self.result_browser)
    
    @pyqtSlot(object)
    def update_status(self, workflow: Optional[Workflow] = None):
        """워크플로우 상태 업데이트"""
        if workflow is None:
            self.status_label.setText("워크플로우 상태: 없음")
            self.progress_bar.setValue(0)
            self.step_tree.clear()
            self.result_browser.clear()
            return
        
        # 상태 라벨 업데이트
        status_text = f"워크플로우 상태: {workflow.name} - {workflow.status.value}"
        self.status_label.setText(status_text)
        
        # 상태에 따른 색상
        if workflow.status == WorkflowStatus.COMPLETED:
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.progress_bar.setValue(100)
        elif workflow.status == WorkflowStatus.FAILED:
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.progress_bar.setValue(0)
        elif workflow.status == WorkflowStatus.RUNNING:
            self.status_label.setStyleSheet("font-weight: bold; color: blue;")
            # 진행률 계산
            total_steps = len(workflow.steps)
            completed_steps = sum(1 for step in workflow.steps.values() 
                                if step.status.value in ["completed", "skipped"])
            progress = int(completed_steps / total_steps * 100) if total_steps > 0 else 0
            self.progress_bar.setValue(progress)
        else:
            self.status_label.setStyleSheet("font-weight: bold;")
            self.progress_bar.setValue(0)
        
        # 트리 업데이트
        self.step_tree.clear()
        
        for step_id in workflow.step_order:
            step = workflow.steps.get(step_id)
            if not step:
                continue
            
            item = QTreeWidgetItem([
                step.name,
                step.status.value,
                step.start_time.strftime("%Y-%m-%d %H:%M:%S") if step.start_time else "",
                step.end_time.strftime("%Y-%m-%d %H:%M:%S") if step.end_time else "",
                str(step.end_time - step.start_time).split('.')[0] if step.start_time and step.end_time else ""
            ])
            
            # 상태에 따른 색상
            if step.status.value == "completed":
                item.setForeground(1, QColor(0, 128, 0))  # 초록
            elif step.status.value == "failed":
                item.setForeground(1, QColor(255, 0, 0))  # 빨강
            elif step.status.value == "running":
                item.setForeground(1, QColor(0, 0, 255))  # 파랑
            
            self.step_tree.addTopLevelItem(item)
        
        # 결과 또는 오류 표시
        self.result_browser.clear()
        
        if workflow.error:
            self.result_browser.setTextColor(QColor(255, 0, 0))
            self.result_browser.append(f"오류: {workflow.error}")
        
        # 완료된 단계의 결과 표시
        for step_id, step in workflow.steps.items():
            if step.status.value == "completed" and step.result:
                self.result_browser.setTextColor(QColor(0, 0, 0))
                try:
                    # JSON 형식일 경우 예쁘게 포맷팅
                    if isinstance(step.result, (dict, list)):
                        result_text = json.dumps(step.result, ensure_ascii=False, indent=2)
                    else:
                        result_text = str(step.result)
                    
                    self.result_browser.append(f"{step.name} 결과:\n{result_text}\n")
                except:
                    self.result_browser.append(f"{step.name} 결과: {step.result}\n")
    
    @pyqtSlot()
    def refresh_status(self):
        """상태 새로고침 (외부에서 워크플로우 객체 전달 필요)"""
        self.parent().refresh_workflow_status()

class MainWindow(QMainWindow):
    """BlueAI 통합 자동화 시스템 메인 윈도우"""
    
    def __init__(self, plugin_manager, workflow_manager, settings_manager, interruption_handler, server_url=None):
        super().__init__()
        
        self.plugin_manager = plugin_manager
        self.workflow_manager = workflow_manager
        self.settings_manager = settings_manager
        self.interruption_handler = interruption_handler
        self.server_url = server_url
        
        # 현재 활성화된 워크플로우
        self.current_workflow_id = None
        
        # UI 컴포넌트 초기화 (이 단계에서 self.workflow_status가 생성됨)
        self.setup_ui()
        
        # UI 타이머 (주기적 업데이트용)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_workflow_status)
        
        # SafeUIUpdater 초기화
        self.ui_updater = SafeUIUpdater(self)
        
        # 이벤트 연결 (workflow_status가 존재하는지 확인 후 연결)
        if hasattr(self, 'workflow_status'):
            self.ui_updater.connect_signals(self)
        else:
            logger.error("workflow_status가 초기화되지 않았습니다")
        
        # 나머지 연결 설정
        self.setup_connections()
        
        # 플러그인 목록 업데이트
        self.update_plugin_list()
        
        # 타이머 시작
        self.update_timer.start(2000)  # 2초마다 업데이트
        
        logger.info("메인 윈도우 초기화 완료")
    
    def setup_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BlueAI 통합 자동화 시스템")
        self.setMinimumSize(1200, 800)
        
        # 중앙 위젯 및 레이아웃
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 명령어 입력 영역
        command_layout = QHBoxLayout()
        
        command_label = QLabel("명령어:")
        command_layout.addWidget(command_label)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("자동화 명령어 입력 (예: 나라장터에서 RPA 공고 검색)")
        command_layout.addWidget(self.command_input, 1)
        
        self.execute_button = QPushButton("실행")
        self.execute_button.clicked.connect(self.execute_command)
        command_layout.addWidget(self.execute_button)
        
        main_layout.addLayout(command_layout)
        
        # 메인 탭 영역
        self.tab_widget = QTabWidget()
        
        # 워크플로우 탭
        self.workflow_tab = QWidget()
        workflow_layout = QVBoxLayout(self.workflow_tab)
        
        # 워크플로우 상태 위젯
        self.workflow_status = WorkflowStatusWidget()
        workflow_layout.addWidget(self.workflow_status)
        
        self.tab_widget.addTab(self.workflow_tab, "워크플로우")
        
        # 로그 탭
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        
        self.log_viewer = LogViewer()
        log_layout.addWidget(self.log_viewer)
        
        self.tab_widget.addTab(self.log_tab, "로그")
        
        # 플러그인 탭
        self.plugin_tab = QWidget()
        plugin_layout = QVBoxLayout(self.plugin_tab)
        
        self.plugin_tree = QTreeWidget()
        self.plugin_tree.setHeaderLabels(["플러그인", "타입", "버전", "상태"])
        self.plugin_tree.setColumnWidth(0, 200)
        self.plugin_tree.setColumnWidth(1, 150)
        self.plugin_tree.setColumnWidth(2, 100)
        plugin_layout.addWidget(self.plugin_tree)
        
        plugin_button_layout = QHBoxLayout()
        
        self.refresh_plugins_button = QPushButton("새로고침")
        self.refresh_plugins_button.clicked.connect(self.update_plugin_list)
        plugin_button_layout.addWidget(self.refresh_plugins_button)
        
        plugin_button_layout.addStretch()
        
        self.manage_plugin_button = QPushButton("플러그인 관리")
        self.manage_plugin_button.clicked.connect(self.show_plugin_manager)
        plugin_button_layout.addWidget(self.manage_plugin_button)
        
        plugin_layout.addLayout(plugin_button_layout)
        
        self.tab_widget.addTab(self.plugin_tab, "플러그인")
        
        # 설정 탭
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        
        settings_form = QFormLayout()
        
        # 헤드리스 모드 설정
        self.headless_checkbox = QCheckBox("헤드리스 모드")
        self.headless_checkbox.setChecked(self.settings_manager.get("system", "headless_mode", False))
        settings_form.addRow("브라우저 설정:", self.headless_checkbox)
        
        # 브라우저 타입 선택
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["chromium", "firefox", "webkit"])
        browser_type = self.settings_manager.get("automation", "browser_type", "chromium")
        self.browser_combo.setCurrentText(browser_type)
        settings_form.addRow("브라우저 타입:", self.browser_combo)
        
        # 인터럽션 처리 설정
        self.interruption_checkbox = QCheckBox("인터럽션 자동 처리")
        self.interruption_checkbox.setChecked(self.settings_manager.get("interruption", "enabled", True))
        settings_form.addRow("인터럽션 설정:", self.interruption_checkbox)
        
        # 쿠키 처리 설정
        self.cookie_checkbox = QCheckBox("쿠키 공지 자동 수락")
        self.cookie_checkbox.setChecked(self.settings_manager.get("interruption", "cookie_handling", True))
        settings_form.addRow("", self.cookie_checkbox)
        
        # 광고 차단 설정
        self.ad_block_checkbox = QCheckBox("광고 자동 차단")
        self.ad_block_checkbox.setChecked(self.settings_manager.get("interruption", "ad_blocking", True))
        settings_form.addRow("", self.ad_block_checkbox)
        
        settings_layout.addLayout(settings_form)
        
        # 도메인 설정
        domains_group_layout = QVBoxLayout()
        domains_group_layout.addWidget(QLabel("도메인 관리"))
        
        domains_layout = QHBoxLayout()
        
        # 화이트리스트
        whitelist_layout = QVBoxLayout()
        whitelist_layout.addWidget(QLabel("화이트리스트:"))
        
        self.whitelist_widget = QListWidget()
        whitelist_domains = self.settings_manager.get_whitelist_domains()
        for domain in whitelist_domains:
            self.whitelist_widget.addItem(domain)
        whitelist_layout.addWidget(self.whitelist_widget)
        
        whitelist_buttons = QHBoxLayout()
        
        self.add_whitelist_button = QPushButton("추가")
        self.add_whitelist_button.clicked.connect(self.add_whitelist_domain)
        whitelist_buttons.addWidget(self.add_whitelist_button)
        
        self.remove_whitelist_button = QPushButton("제거")
        self.remove_whitelist_button.clicked.connect(self.remove_whitelist_domain)
        whitelist_buttons.addWidget(self.remove_whitelist_button)
        
        whitelist_layout.addLayout(whitelist_buttons)
        
        domains_layout.addLayout(whitelist_layout)
        
        # 블랙리스트
        blacklist_layout = QVBoxLayout()
        blacklist_layout.addWidget(QLabel("블랙리스트:"))
        
        self.blacklist_widget = QListWidget()
        blacklist_domains = self.settings_manager.get_blacklist_domains()
        for domain in blacklist_domains:
            self.blacklist_widget.addItem(domain)
        blacklist_layout.addWidget(self.blacklist_widget)
        
        blacklist_buttons = QHBoxLayout()
        
        self.add_blacklist_button = QPushButton("추가")
        self.add_blacklist_button.clicked.connect(self.add_blacklist_domain)
        blacklist_buttons.addWidget(self.add_blacklist_button)
        
        self.remove_blacklist_button = QPushButton("제거")
        self.remove_blacklist_button.clicked.connect(self.remove_blacklist_domain)
        blacklist_buttons.addWidget(self.remove_blacklist_button)
        
        blacklist_layout.addLayout(blacklist_buttons)
        
        domains_layout.addLayout(blacklist_layout)
        
        domains_group_layout.addLayout(domains_layout)
        
        settings_layout.addLayout(domains_group_layout)
        
        # 저장 버튼
        settings_buttons = QHBoxLayout()
        settings_buttons.addStretch()
        
        self.save_settings_button = QPushButton("설정 저장")
        self.save_settings_button.clicked.connect(self.save_settings)
        settings_buttons.addWidget(self.save_settings_button)
        
        settings_layout.addLayout(settings_buttons)
        
        self.tab_widget.addTab(self.settings_tab, "설정")
        
        main_layout.addWidget(self.tab_widget)
        
        self.setCentralWidget(central_widget)
        
        # 상태바
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("준비")
        
        # 메뉴바 설정
        self.setup_menubar()
        
        # 툴바 설정
        self.setup_toolbar()
    
    def setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        new_action = QAction("새 워크플로우", self)
        new_action.triggered.connect(self.create_new_workflow)
        file_menu.addAction(new_action)
        
        open_action = QAction("워크플로우 열기", self)
        open_action.triggered.connect(self.open_workflow)
        file_menu.addAction(open_action)
        
        save_action = QAction("워크플로우 저장", self)
        save_action.triggered.connect(self.save_workflow)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 실행 메뉴
        run_menu = menubar.addMenu("실행")
        
        run_action = QAction("워크플로우 실행", self)
        run_action.triggered.connect(self.run_workflow)
        run_menu.addAction(run_action)
        
        pause_action = QAction("일시중지", self)
        pause_action.triggered.connect(self.pause_workflow)
        run_menu.addAction(pause_action)
        
        resume_action = QAction("재개", self)
        resume_action.triggered.connect(self.resume_workflow)
        run_menu.addAction(resume_action)
        
        stop_action = QAction("중지", self)
        stop_action.triggered.connect(self.stop_workflow)
        run_menu.addAction(stop_action)
        
        # 플러그인 메뉴
        plugin_menu = menubar.addMenu("플러그인")
        
        reload_plugins_action = QAction("플러그인 새로고침", self)
        reload_plugins_action.triggered.connect(self.reload_plugins)
        plugin_menu.addAction(reload_plugins_action)
        
        manage_plugins_action = QAction("플러그인 관리", self)
        manage_plugins_action.triggered.connect(self.show_plugin_manager)
        plugin_menu.addAction(manage_plugins_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """툴바 설정"""
        toolbar = QToolBar("메인 툴바")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 워크플로우 실행 관련 액션
        run_action = QAction("실행", self)
        run_action.triggered.connect(self.run_workflow)
        toolbar.addAction(run_action)
        
        pause_action = QAction("일시중지", self)
        pause_action.triggered.connect(self.pause_workflow)
        toolbar.addAction(pause_action)
        
        resume_action = QAction("재개", self)
        resume_action.triggered.connect(self.resume_workflow)
        toolbar.addAction(resume_action)
        
        stop_action = QAction("중지", self)
        stop_action.triggered.connect(self.stop_workflow)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        # 새로고침 액션
        refresh_action = QAction("새로고침", self)
        refresh_action.triggered.connect(self.refresh_workflow_status)
        toolbar.addAction(refresh_action)
    
    def setup_connections(self):
        """이벤트 연결"""
        # 명령어 입력 엔터 처리
        self.command_input.returnPressed.connect(self.execute_command)
        
        # 워크플로우 관리자 콜백 등록
        self.workflow_manager.register_callback("workflow_started", self.on_workflow_started)
        self.workflow_manager.register_callback("workflow_completed", self.on_workflow_completed)
        self.workflow_manager.register_callback("workflow_failed", self.on_workflow_failed)
        self.workflow_manager.register_callback("workflow_canceled", self.on_workflow_canceled)
        self.workflow_manager.register_callback("step_started", self.on_step_started)
        self.workflow_manager.register_callback("step_completed", self.on_step_completed)
        self.workflow_manager.register_callback("step_failed", self.on_step_failed)
        self.workflow_manager.register_callback("step_skipped", self.on_step_skipped)
    
    def execute_command(self):
        """명령어 실행"""
        command = self.command_input.text().strip()
        if not command:
            self.statusBar.showMessage("명령어를 입력하세요")
            return
        
        self.log_viewer.append_log(f"명령어 실행: {command}")
        self.statusBar.showMessage(f"명령어 실행 중: {command}")
        
        try:
            # 워크플로우 생성
            workflow = self.workflow_manager.create_workflow(
                name=f"명령어 워크플로우: {command}",
                description=f"명령어로 생성된 워크플로우: {command}"
            )
            
            # 임시 워크플로우 ID 저장
            self.current_workflow_id = workflow.workflow_id
            
            # 탭 전환
            self.tab_widget.setCurrentWidget(self.workflow_tab)
            
            # 명령어 종류에 따라 워크플로우 구성
            if "나라장터" in command.lower():
                # 나라장터 예제 실행
                import examples.nara_marketplace_example as nara_example
                
                # 나라장터 워크플로우 생성
                _, workflow = nara_example.create_nara_marketplace_workflow(
                    self.plugin_manager, self.settings_manager
                )
                
                # 생성된 워크플로우 ID 업데이트
                self.current_workflow_id = workflow.workflow_id
                self.workflow_manager.workflows[workflow.workflow_id] = workflow
                
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
                            "headless": self.settings_manager.get("system", "headless_mode", False),
                            "browser_type": self.settings_manager.get("automation", "browser_type", "chromium")
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
                
                # 인터럽션 처리 단계
                if self.settings_manager.get("interruption", "enabled", True):
                    step6 = WorkflowStep(
                        step_id="handle_interruptions",
                        name="인터럽션 처리",
                        action={
                            "plugin_type": "interruption",
                            "plugin_name": "popup_handler",
                            "action": "handle_all_interruptions",
                            "params": {}
                        },
                        dependencies=["click_search"]
                    )
                    workflow.add_step(step6)
                    dependencies = ["handle_interruptions"]
                else:
                    dependencies = ["click_search"]
                
                # 스크린샷 캡처 단계
                step7 = WorkflowStep(
                    step_id="take_screenshot",
                    name="스크린샷 캡처",
                    action={
                        "plugin_type": "automation",
                        "plugin_name": "playwright",
                        "action": "screenshot",
                        "params": {
                            "path": os.path.join(os.path.expanduser("~"), "BlueAI", "screenshots", 
                                              f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                        }
                    },
                    dependencies=dependencies
                )
                workflow.add_step(step7)
                
                # 단계 순서 설정
                step_order = ["start_browser", "create_page", "goto_google", "input_search", "click_search"]
                
                if self.settings_manager.get("interruption", "enabled", True):
                    step_order.append("handle_interruptions")
                
                step_order.append("take_screenshot")
                
                workflow.set_step_order(step_order)
            
            # 워크플로우 실행
            self.workflow_manager.start_workflow(self.current_workflow_id)
            
            # 워크플로우 상태 업데이트
            self.update_workflow_status()
            
        except Exception as e:
            error_msg = f"명령어 실행 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def update_workflow_status(self):
        """워크플로우 상태 주기적 업데이트 (스레드 안전)"""
        if not self.current_workflow_id:
            return

        workflow = self.workflow_manager.get_workflow(self.current_workflow_id)
        if workflow and hasattr(self, 'ui_updater'):
            # 스레드 안전한 방식으로 업데이트
            self.ui_updater.update_workflow_status_signal.emit(workflow)
        
        workflow = self.workflow_manager.get_workflow(self.current_workflow_id)
        if workflow:
            # QMetaObject.invokeMethod를 사용하여 메인 스레드에서 업데이트
            QMetaObject.invokeMethod(self.workflow_status, "update_status",
                                    Qt.QueuedConnection,
                                    Q_ARG(object, workflow))
    
    def refresh_workflow_status(self):
        """워크플로우 상태 새로고침"""
        self.update_workflow_status()
    
    def create_new_workflow(self):
        """새 워크플로우 생성"""
        try:
            # 간단한 워크플로우 생성
            name, ok = QInputDialog.getText(self, "새 워크플로우", "워크플로우 이름:")
            if ok and name:
                workflow = self.workflow_manager.create_workflow(name=name)
                self.current_workflow_id = workflow.workflow_id
                
                self.log_viewer.append_log(f"새 워크플로우 생성됨: {name}")
                
                # 워크플로우 상태 업데이트
                self.update_workflow_status()
                
                # 탭 전환
                self.tab_widget.setCurrentWidget(self.workflow_tab)
                
        except Exception as e:
            error_msg = f"워크플로우 생성 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def open_workflow(self):
        """워크플로우 파일 열기"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "워크플로우 열기", 
                os.path.join(os.path.expanduser("~"), "BlueAI", "workflows"),
                "워크플로우 파일 (*.json)"
            )
            
            if file_path:
                workflow_id = self.workflow_manager.load_workflow_from_file(file_path)
                if workflow_id:
                    self.current_workflow_id = workflow_id
                    
                    self.log_viewer.append_log(f"워크플로우 로드됨: {file_path}")
                    
                    # 워크플로우 상태 업데이트
                    self.update_workflow_status()
                    
                    # 탭 전환
                    self.tab_widget.setCurrentWidget(self.workflow_tab)
                else:
                    self.log_viewer.append_log(f"워크플로우 로드 실패: {file_path}", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 열기 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def save_workflow(self):
        """워크플로우 파일 저장"""
        if not self.current_workflow_id:
            self.statusBar.showMessage("저장할 워크플로우가 없습니다")
            return
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "워크플로우 저장", 
                os.path.join(os.path.expanduser("~"), "BlueAI", "workflows"),
                "워크플로우 파일 (*.json)"
            )
            
            if file_path:
                if not file_path.endswith('.json'):
                    file_path += '.json'
                
                success = self.workflow_manager.save_workflow_to_file(self.current_workflow_id, file_path)
                
                if success:
                    self.log_viewer.append_log(f"워크플로우 저장됨: {file_path}")
                else:
                    self.log_viewer.append_log(f"워크플로우 저장 실패: {file_path}", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 저장 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def run_workflow(self):
        """현재 워크플로우 실행"""
        if not self.current_workflow_id:
            self.statusBar.showMessage("실행할 워크플로우가 없습니다")
            return
        
        try:
            success = self.workflow_manager.start_workflow(self.current_workflow_id)
            
            if success:
                self.log_viewer.append_log(f"워크플로우 실행 시작됨")
                # 상태 업데이트
                self.update_workflow_status()
            else:
                self.log_viewer.append_log(f"워크플로우 실행 실패", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 실행 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def pause_workflow(self):
        """현재 워크플로우 일시중지"""
        if not self.current_workflow_id:
            self.statusBar.showMessage("일시중지할 워크플로우가 없습니다")
            return
        
        try:
            success = self.workflow_manager.pause_workflow(self.current_workflow_id)
            
            if success:
                self.log_viewer.append_log(f"워크플로우 일시중지됨")
                # 상태 업데이트
                self.update_workflow_status()
            else:
                self.log_viewer.append_log(f"워크플로우 일시중지 실패", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 일시중지 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def resume_workflow(self):
        """일시중지된 워크플로우 재개"""
        if not self.current_workflow_id:
            self.statusBar.showMessage("재개할 워크플로우가 없습니다")
            return
        
        try:
            success = self.workflow_manager.resume_workflow(self.current_workflow_id)
            
            if success:
                self.log_viewer.append_log(f"워크플로우 재개됨")
                # 상태 업데이트
                self.update_workflow_status()
            else:
                self.log_viewer.append_log(f"워크플로우 재개 실패", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 재개 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def stop_workflow(self):
        """현재 워크플로우 중지"""
        if not self.current_workflow_id:
            self.statusBar.showMessage("중지할 워크플로우가 없습니다")
            return
        
        try:
            success = self.workflow_manager.cancel_workflow(self.current_workflow_id)
            
            if success:
                self.log_viewer.append_log(f"워크플로우 중지됨")
                # 상태 업데이트
                self.update_workflow_status()
            else:
                self.log_viewer.append_log(f"워크플로우 중지 실패", "ERROR")
            
        except Exception as e:
            error_msg = f"워크플로우 중지 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def update_plugin_list(self):
        """플러그인 목록 업데이트"""
        self.plugin_tree.clear()
        
        plugin_types = {}
        
        # 플러그인 데이터 수집
        all_plugins = self.plugin_manager.get_all_plugins()
        for plugin_type, plugins in all_plugins.items():
            plugin_types[plugin_type] = QTreeWidgetItem([plugin_type, "", "", ""])
            self.plugin_tree.addTopLevelItem(plugin_types[plugin_type])
            
            for plugin_name, plugin in plugins.items():
                status = plugin.get_status()
                
                plugin_item = QTreeWidgetItem([
                    plugin_name,
                    status.get("type", ""),
                    status.get("version", ""),
                    "활성화" if status.get("enabled", False) else "비활성화"
                ])
                
                # 상태에 따른 색상
                if status.get("enabled", False):
                    plugin_item.setForeground(3, QColor(0, 128, 0))  # 초록
                else:
                    plugin_item.setForeground(3, QColor(128, 128, 128))  # 회색
                
                plugin_types[plugin_type].addChild(plugin_item)
            
            plugin_types[plugin_type].setExpanded(True)
    
    def reload_plugins(self):
        """플러그인 재로드"""
        try:
            # 플러그인 재로드
            loaded_plugins = self.plugin_manager.load_all_plugins()
            init_results = self.plugin_manager.initialize_all_plugins()
            
            # 로그에 결과 출력
            self.log_viewer.append_log(f"플러그인 로드됨: {loaded_plugins}")
            
            for plugin_name, success in init_results.items():
                if success:
                    self.log_viewer.append_log(f"플러그인 초기화 성공: {plugin_name}")
                else:
                    self.log_viewer.append_log(f"플러그인 초기화 실패: {plugin_name}", "ERROR")
            
            # 플러그인 목록 업데이트
            self.update_plugin_list()
            
        except Exception as e:
            error_msg = f"플러그인 재로드 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def show_plugin_manager(self):
        """플러그인 관리 다이얼로그 표시"""
        # 플러그인 관리 다이얼로그 구현
        msg = QMessageBox()
        msg.setWindowTitle("플러그인 관리")
        msg.setText("플러그인 관리 기능은 아직 구현되지 않았습니다.")
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
    
    def add_whitelist_domain(self):
        """화이트리스트에 도메인 추가"""
        domain, ok = QInputDialog.getText(self, "도메인 추가", "화이트리스트에 추가할 도메인:")
        if ok and domain:
            success = self.settings_manager.add_to_whitelist(domain)
            if success:
                self.whitelist_widget.addItem(domain)
                self.log_viewer.append_log(f"화이트리스트에 도메인 추가됨: {domain}")
            else:
                self.log_viewer.append_log(f"화이트리스트 도메인 추가 실패: {domain}", "ERROR")
    
    def remove_whitelist_domain(self):
        """화이트리스트에서 도메인 제거"""
        selected_items = self.whitelist_widget.selectedItems()
        if not selected_items:
            return
        
        domain = selected_items[0].text()
        success = self.settings_manager.remove_from_whitelist(domain)
        if success:
            row = self.whitelist_widget.row(selected_items[0])
            self.whitelist_widget.takeItem(row)
            self.log_viewer.append_log(f"화이트리스트에서 도메인 제거됨: {domain}")
        else:
            self.log_viewer.append_log(f"화이트리스트 도메인 제거 실패: {domain}", "ERROR")
    
    def add_blacklist_domain(self):
        """블랙리스트에 도메인 추가"""
        domain, ok = QInputDialog.getText(self, "도메인 추가", "블랙리스트에 추가할 도메인:")
        if ok and domain:
            success = self.settings_manager.add_to_blacklist(domain)
            if success:
                self.blacklist_widget.addItem(domain)
                self.log_viewer.append_log(f"블랙리스트에 도메인 추가됨: {domain}")
            else:
                self.log_viewer.append_log(f"블랙리스트 도메인 추가 실패: {domain}", "ERROR")
    
    def remove_blacklist_domain(self):
        """블랙리스트에서 도메인 제거"""
        selected_items = self.blacklist_widget.selectedItems()
        if not selected_items:
            return
        
        domain = selected_items[0].text()
        success = self.settings_manager.remove_from_blacklist(domain)
        if success:
            row = self.blacklist_widget.row(selected_items[0])
            self.blacklist_widget.takeItem(row)
            self.log_viewer.append_log(f"블랙리스트에서 도메인 제거됨: {domain}")
        else:
            self.log_viewer.append_log(f"블랙리스트 도메인 제거 실패: {domain}", "ERROR")
    
    def save_settings(self):
        """설정 저장"""
        try:
            # 시스템 설정
            self.settings_manager.set("system", "headless_mode", self.headless_checkbox.isChecked())
            
            # 자동화 설정
            self.settings_manager.set("automation", "browser_type", self.browser_combo.currentText())
            
            # 인터럽션 설정
            self.settings_manager.set("interruption", "enabled", self.interruption_checkbox.isChecked())
            self.settings_manager.set("interruption", "cookie_handling", self.cookie_checkbox.isChecked())
            self.settings_manager.set("interruption", "ad_blocking", self.ad_block_checkbox.isChecked())
            
            # 설정 파일 저장
            success = self.settings_manager.save_settings()
            
            if success:
                self.log_viewer.append_log("설정이 저장되었습니다.")
                self.statusBar.showMessage("설정 저장됨")
            else:
                self.log_viewer.append_log("설정 저장 실패", "ERROR")
            
        except Exception as e:
            error_msg = f"설정 저장 중 오류: {str(e)}"
            self.log_viewer.append_log(error_msg, "ERROR")
            self.statusBar.showMessage(error_msg)
    
    def show_about(self):
        """정보 다이얼로그 표시"""
        msg = QMessageBox()
        msg.setWindowTitle("정보")
        msg.setText("BlueAI 통합 자동화 시스템")
        msg.setInformativeText("버전: 0.1.0\n\n플러그인 기반 통합 자동화 시스템")
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
    
    # 워크플로우 이벤트 핸들러
    def on_workflow_started(self, workflow_id, workflow_name):
        """워크플로우 시작 이벤트 처리"""
        # UI 스레드 안전한 로그 업데이트
        self.ui_updater.log_message_signal.emit(f"워크플로우 시작됨: {workflow_name}", "INFO")
        self.statusBar.showMessage(f"워크플로우 실행 중: {workflow_name}")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, dict)
    def on_workflow_completed(self, workflow_id, workflow_name, results):
        """워크플로우 완료 이벤트 처리"""
        self.log_viewer.append_log(f"워크플로우 완료됨: {workflow_name}")
        self.statusBar.showMessage(f"워크플로우 완료됨: {workflow_name}")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str)
    def on_workflow_failed(self, workflow_id, workflow_name, error):
        """워크플로우 실패 이벤트 처리"""
        self.log_viewer.append_log(f"워크플로우 실행 실패: {workflow_name}", "ERROR")
        self.log_viewer.append_log(f"오류: {error}", "ERROR")
        self.statusBar.showMessage(f"워크플로우 실패: {workflow_name}")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str)
    def on_workflow_canceled(self, workflow_id, workflow_name, prev_status):
        """워크플로우 취소 이벤트 처리"""
        self.log_viewer.append_log(f"워크플로우 취소됨: {workflow_name}")
        self.statusBar.showMessage(f"워크플로우 취소됨: {workflow_name}")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str, str)
    def on_step_started(self, workflow_id, workflow_name, step_id, step_name):
        """워크플로우 단계 시작 이벤트 처리"""
        self.log_viewer.append_log(f"단계 시작: {step_name}")
        self.statusBar.showMessage(f"단계 실행 중: {step_name}")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str, str, dict)
    def on_step_completed(self, workflow_id, workflow_name, step_id, step_name, result):
        """워크플로우 단계 완료 이벤트 처리"""
        self.log_viewer.append_log(f"단계 완료: {step_name}")
        
        # 결과가 있는 경우 요약 정보 출력
        if result:
            try:
                # JSON 형식이면 요약 정보만 출력
                if isinstance(result, dict):
                    summary = {}
                    for key, value in result.items():
                        if key in ["status", "message", "count"]:
                            summary[key] = value
                        elif key == "file_path" and isinstance(value, str):
                            summary["file"] = os.path.basename(value)
                    
                    if summary:
                        self.log_viewer.append_log(f"결과: {json.dumps(summary, ensure_ascii=False)}")
                    else:
                        self.log_viewer.append_log(f"결과: {type(result).__name__} 객체")
                else:
                    self.log_viewer.append_log(f"결과: {type(result).__name__} 객체")
            except:
                self.log_viewer.append_log(f"결과: {type(result).__name__} 객체")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str, str, str)
    def on_step_failed(self, workflow_id, workflow_name, step_id, step_name, error):
        """워크플로우 단계 실패 이벤트 처리"""
        self.log_viewer.append_log(f"단계 실패: {step_name}", "ERROR")
        self.log_viewer.append_log(f"오류: {error}", "ERROR")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    @pyqtSlot(str, str, str, str)
    def on_step_skipped(self, workflow_id, workflow_name, step_id, step_name):
        """워크플로우 단계 건너뜀 이벤트 처리"""
        self.log_viewer.append_log(f"단계 건너뜀: {step_name}", "WARNING")
        
        # 상태 업데이트
        self.update_workflow_status()
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        # 실행 중인 워크플로우 확인
        active_workflows = False
        for workflow_id, workflow in self.workflow_manager.workflows.items():
            if workflow.status == WorkflowStatus.RUNNING:
                active_workflows = True
                break
        
        if active_workflows:
            reply = QMessageBox.question(
                self, '종료 확인',
                "실행 중인 워크플로우가 있습니다. 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        try:
            # 워크플로우 관리자 종료
            self.workflow_manager.shutdown()
            
            # 플러그인 종료
            self.plugin_manager.shutdown_all_plugins()
            
            # 설정 저장
            self.settings_manager.save_settings()
            
            logger.info("애플리케이션 종료됨")
            
        except Exception as e:
            logger.error(f"종료 중 오류: {str(e)}")
        
        event.accept()