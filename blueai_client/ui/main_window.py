#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 메인 윈도우 UI
"""

import logging
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QTextEdit, 
                            QStatusBar, QComboBox, QAction, QMenu, QSystemTrayIcon,
                            QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, QSize, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QTextCursor

from ui.widgets.command_input import CommandInput
from ui.widgets.log_viewer import LogViewer
from ui.widgets.task_status import TaskStatusWidget
from ui.system_tray import SystemTrayIcon

logger = logging.getLogger(__name__)

class TaskExecutionThread(QThread):
    """작업 실행을 위한 스레드"""
    taskStarted = pyqtSignal(str)
    taskProgress = pyqtSignal(str, int)
    taskCompleted = pyqtSignal(str, dict)
    taskError = pyqtSignal(str, str)
    
    def __init__(self, task_parser, command):
        super().__init__()
        self.task_parser = task_parser
        self.command = command
    
    def run(self):
        try:
            task_id = f"task_{id(self)}"
            self.taskStarted.emit(task_id)
            
            # 작업 진행 상황을 시뮬레이션
            self.taskProgress.emit(task_id, 25)
            
            # 명령어 파싱 및 실행
            result = self.task_parser.parse_and_execute(self.command)
            
            self.taskProgress.emit(task_id, 100)
            self.taskCompleted.emit(task_id, result)
            
        except Exception as e:
            logger.error(f"작업 실행 중 오류 발생: {str(e)}")
            self.taskError.emit(task_id, str(e))

class MainWindow(QMainWindow):
    """BlueAI 클라이언트 메인 윈도우"""
    
    def __init__(self, browser_manager, task_parser, server_url=None):
        super().__init__()
        
        self.browser_manager = browser_manager
        self.task_parser = task_parser
        self.server_url = server_url
        self.setup_ui()
        
        # 시스템 트레이 아이콘 설정
        self.setupSystemTray()
        
        logger.debug("메인 윈도우 초기화 완료")
    
    def setup_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BlueAI 클라이언트")
        self.setMinimumSize(800, 600)
        
        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 상단 상태 표시 영역
        status_layout = QHBoxLayout()
        self.connection_status = QLabel("연결 상태: 독립 모드")
        self.connection_status.setStyleSheet("color: orange")
        status_layout.addWidget(self.connection_status)
        
        status_layout.addStretch()
        
        self.browser_status = QLabel("브라우저: 준비됨")
        self.browser_status.setStyleSheet("color: green")
        status_layout.addWidget(self.browser_status)
        
        main_layout.addLayout(status_layout)
        
        # 명령어 입력 영역
        command_layout = QHBoxLayout()
        
        self.command_input = CommandInput()
        self.command_input.setPlaceholderText("명령어 입력 (예: 나라장터에서 RPA 공고를 검색해줘)")
        command_layout.addWidget(self.command_input, 1)
        
        self.execute_button = QPushButton("실행")
        self.execute_button.clicked.connect(self.execute_command)
        command_layout.addWidget(self.execute_button)
        
        main_layout.addLayout(command_layout)
        
        # 작업 상태 및 결과 영역
        self.task_status = TaskStatusWidget()
        main_layout.addWidget(self.task_status)
        
        # 로그 뷰어
        self.log_viewer = LogViewer()
        main_layout.addWidget(self.log_viewer, 1)  # 1 = 늘어나는 비율
        
        # 상태바
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("준비")
        
        # 메뉴바 설정
        self.setup_menubar()
        
        self.setCentralWidget(main_widget)
    
    def setup_menubar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일')
        
        exit_action = QAction('종료', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 설정 메뉴
        settings_menu = menubar.addMenu('설정')
        
        headless_action = QAction('헤드리스 모드', self, checkable=True)
        headless_action.setChecked(self.browser_manager.headless)
        headless_action.triggered.connect(self.toggle_headless)
        settings_menu.addAction(headless_action)
        
        server_action = QAction('서버 설정', self)
        server_action.triggered.connect(self.show_server_settings)
        settings_menu.addAction(server_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말')
        
        about_action = QAction('정보', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setupSystemTray(self):
        """시스템 트레이 아이콘 설정"""
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        # 시스템 트레이로 최소화
        if self.tray_icon.isVisible():
            QMessageBox.information(self, "BlueAI 클라이언트",
                                   "애플리케이션이 시스템 트레이로 최소화됩니다.")
            self.hide()
            event.ignore()
        else:
            event.accept()
    
    @pyqtSlot()
    def execute_command(self):
        """명령어 실행"""
        command = self.command_input.text().strip()
        if not command:
            self.statusBar.showMessage("명령어를 입력하세요")
            return
        
        self.log_viewer.append_log(f"명령어 실행: {command}")
        self.statusBar.showMessage(f"명령어 실행 중: {command}")
        
        # 스레드에서 작업 실행
        self.task_thread = TaskExecutionThread(self.task_parser, command)
        self.task_thread.taskStarted.connect(self.on_task_started)
        self.task_thread.taskProgress.connect(self.on_task_progress)
        self.task_thread.taskCompleted.connect(self.on_task_completed)
        self.task_thread.taskError.connect(self.on_task_error)
        self.task_thread.start()
    
    @pyqtSlot(str)
    def on_task_started(self, task_id):
        """작업 시작 이벤트 처리"""
        self.task_status.add_task(task_id, "작업 시작됨")
        self.log_viewer.append_log(f"작업 시작: {task_id}")
    
    @pyqtSlot(str, int)
    def on_task_progress(self, task_id, progress):
        """작업 진행 상황 이벤트 처리"""
        self.task_status.update_task(task_id, f"진행 중: {progress}%", progress)
        
        # 25%, 50%, 75%에 로그 메시지 추가
        if progress in [25, 50, 75]:
            self.log_viewer.append_log(f"작업 진행 중: {progress}%")
    
    @pyqtSlot(str, dict)
    def on_task_completed(self, task_id, result):
        """작업 완료 이벤트 처리"""
        self.task_status.complete_task(task_id, "완료됨")
        self.log_viewer.append_log(f"작업 완료: {task_id}")
        self.log_viewer.append_log(f"결과: {result}")
        self.statusBar.showMessage("명령어 실행 완료")
        
        # 시스템 트레이에서도 알림
        if self.isHidden():
            self.tray_icon.showMessage("BlueAI 클라이언트", 
                                     "작업이 완료되었습니다.", 
                                     QSystemTrayIcon.Information, 
                                     2000)
    
    @pyqtSlot(str, str)
    def on_task_error(self, task_id, error):
        """작업 오류 이벤트 처리"""
        self.task_status.fail_task(task_id, f"오류: {error}")
        self.log_viewer.append_log(f"작업 오류: {error}", level=logging.ERROR)
        self.statusBar.showMessage("명령어 실행 실패")
    
    def toggle_headless(self, checked):
        """헤드리스 모드 전환"""
        self.browser_manager.headless = checked
        mode = "헤드리스" if checked else "일반"
        self.log_viewer.append_log(f"브라우저 모드 변경: {mode}")
    
    def show_server_settings(self):
        """서버 설정 다이얼로그 표시"""
        server_url, ok = QInputDialog.getText(self, "서버 설정", 
                                        "BlueAI 서버 URL:",
                                        QLineEdit.Normal,
                                        self.server_url or "")
        if ok and server_url:
            self.server_url = server_url
            self.connection_status.setText(f"연결 상태: {server_url}")
            self.connection_status.setStyleSheet("color: green")
            self.log_viewer.append_log(f"서버 URL 설정됨: {server_url}")
    
    def show_about(self):
        """정보 다이얼로그 표시"""
        QMessageBox.about(self, "BlueAI 클라이언트", 
                         "BlueAI 클라이언트 v0.1.0\n\n"
                         "© 2025 BlueAI. 모든 권리 보유.")