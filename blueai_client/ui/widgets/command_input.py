# ui/widgets/command_input.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 명령어 입력 위젯
"""

from PyQt5.QtWidgets import QLineEdit, QCompleter
from PyQt5.QtCore import Qt, pyqtSignal

class CommandInput(QLineEdit):
    """명령어 입력을 위한 커스텀 라인 에디트"""
    
    commandSubmitted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("명령어를 입력하세요...")
        self.returnPressed.connect(self.on_return_pressed)
        
        # 명령어 기록 및 자동완성
        self.command_history = []
        self.setup_completer()
    
    def setup_completer(self):
        """자동완성 설정"""
        self.completer = QCompleter(self.command_history)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer)
    
    def update_history(self, command):
        """명령어 기록 업데이트"""
        if command and command not in self.command_history:
            self.command_history.append(command)
            # 최대 20개만 유지
            if len(self.command_history) > 20:
                self.command_history.pop(0)
            
            # 자동완성 갱신
            self.completer.setModel(None)
            self.completer = QCompleter(self.command_history)
            self.completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.setCompleter(self.completer)
    
    def on_return_pressed(self):
        """엔터 키 이벤트 처리"""
        command = self.text().strip()
        if command:
            self.update_history(command)
            self.commandSubmitted.emit(command)

# ui/widgets/log_viewer.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 로그 뷰어 위젯
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt5.QtCore import Qt, pyqtSlot

class LogViewer(QTextEdit):
    """로그 메시지를 표시하는 텍스트 에디트 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        
        # 로그 레벨별 색상 설정
        self.level_colors = {
            logging.DEBUG: QColor(100, 100, 100),      # 회색
            logging.INFO: QColor(0, 0, 0),             # 검정
            logging.WARNING: QColor(255, 165, 0),      # 주황
            logging.ERROR: QColor(255, 0, 0),          # 빨강
            logging.CRITICAL: QColor(128, 0, 0)        # 어두운 빨강
        }
        
        # 최대 로그 개수
        self.max_logs = 1000
        self.log_count = 0
    
    @pyqtSlot(str, int)
    def append_log(self, message, level=logging.INFO):
        """로그 메시지 추가"""
        # 현재 시간
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 로그 레벨 문자열
        level_name = logging.getLevelName(level)
        
        # 포맷팅된 로그 메시지
        formatted_message = f"[{timestamp}] {level_name}: {message}"
        
        # 색상 설정
        format = QTextCharFormat()
        format.setForeground(self.level_colors.get(level, QColor(0, 0, 0)))
        
        # 커서 위치 저장
        cursor = self.textCursor()
        scrollbar_at_bottom = self.verticalScrollBar().value() == self.verticalScrollBar().maximum()
        
        # 메시지 추가
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(formatted_message + "\n", format)
        
        # 스크롤바가 맨 아래에 있었다면 계속 맨 아래로 유지
        if scrollbar_at_bottom:
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        # 로그 개수 제한
        self.log_count += 1
        if self.log_count > self.max_logs:
            self.trim_logs()
    
    def trim_logs(self):
        """오래된 로그 삭제"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, self.log_count - self.max_logs)
        cursor.removeSelectedText()
        self.log_count = self.max_logs

# ui/widgets/task_status.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 작업 상태 위젯
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QProgressBar, QPushButton, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSlot, QSize
from PyQt5.QtGui import QIcon

class TaskStatusItem(QFrame):
    """개별 작업 상태 아이템"""
    
    def __init__(self, task_id, status, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setup_ui(status)
    
    def setup_ui(self, status):
        """UI 초기화"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 작업 ID 및 상태
        info_layout = QHBoxLayout()
        
        self.id_label = QLabel(f"작업: {self.task_id}")
        self.id_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.id_label)
        
        info_layout.addStretch()
        
        self.status_label = QLabel(status)
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        
        # 진행 상태 표시줄
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
    
    def update_status(self, status, progress=None):
        """상태 업데이트"""
        self.status_label.setText(status)
        
        if progress is not None:
            self.progress_bar.setValue(progress)
    
    def complete(self, status):
        """작업 완료 처리"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.progress_bar.setValue(100)
    
    def fail(self, status):
        """작업 실패 처리"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

class TaskStatusWidget(QWidget):
    """작업 상태 및 진행 상황을 표시하는 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_items = {}
        self.setup_ui()
    
    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 제목
        title_layout = QHBoxLayout()
        title_label = QLabel("작업 상태")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        self.clear_button = QPushButton("모두 지우기")
        self.clear_button.clicked.connect(self.clear_tasks)
        title_layout.addWidget(self.clear_button)
        
        layout.addLayout(title_layout)
        
        # 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 작업 목록 위젯
        self.tasks_widget = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_widget)
        self.tasks_layout.setAlignment(Qt.AlignTop)
        self.tasks_layout.setSpacing(5)
        
        self.scroll_area.setWidget(self.tasks_widget)
        layout.addWidget(self.scroll_area)
    
    @pyqtSlot(str, str)
    def add_task(self, task_id, status):
        """작업 추가"""
        if task_id in self.task_items:
            return
        
        task_item = TaskStatusItem(task_id, status)
        self.tasks_layout.insertWidget(0, task_item)  # 최신 항목을 상단에 추가
        self.task_items[task_id] = task_item
    
    @pyqtSlot(str, str, int)
    def update_task(self, task_id, status, progress=None):
        """작업 상태 업데이트"""
        if task_id in self.task_items:
            self.task_items[task_id].update_status(status, progress)
    
    @pyqtSlot(str, str)
    def complete_task(self, task_id, status):
        """작업 완료 처리"""
        if task_id in self.task_items:
            self.task_items[task_id].complete(status)
    
    @pyqtSlot(str, str)
    def fail_task(self, task_id, status):
        """작업 실패 처리"""
        if task_id in self.task_items:
            self.task_items[task_id].fail(status)
    
    @pyqtSlot()
    def clear_tasks(self):
        """모든 작업 지우기"""
        for task_id, task_item in self.task_items.items():
            task_item.deleteLater()
        
        self.task_items.clear()

# ui/system_tray.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 시스템 트레이 아이콘
"""

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class SystemTrayIcon(QSystemTrayIcon):
    """시스템 트레이 아이콘"""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        
        # 아이콘 설정 (실제 아이콘 파일로 교체해야 함)
        self.setIcon(QIcon.fromTheme("system-run"))
        
        # 메뉴 설정
        self.setup_menu()
        
        # 아이콘 클릭 이벤트 연결
        self.activated.connect(self.on_tray_icon_activated)
    
    def setup_menu(self):
        """트레이 아이콘 메뉴 설정"""
        menu = QMenu()
        
        # 메인 윈도우 표시/숨기기
        self.toggle_window_action = QAction("창 표시")
        self.toggle_window_action.triggered.connect(self.toggle_main_window)
        menu.addAction(self.toggle_window_action)
        
        menu.addSeparator()
        
        # 종료
        exit_action = QAction("종료")
        exit_action.triggered.connect(self.main_window.close)
        menu.addAction(exit_action)
        
        self.setContextMenu(menu)
    
    def toggle_main_window(self):
        """메인 윈도우 표시/숨기기 토글"""
        if self.main_window.isVisible():
            self.main_window.hide()
            self.toggle_window_action.setText("창 표시")
        else:
            self.main_window.show()
            self.toggle_window_action.setText("창 숨기기")
    
    def on_tray_icon_activated(self, reason):
        """트레이 아이콘 활성화 이벤트 처리"""
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_main_window()