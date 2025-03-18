#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 로그 뷰어 패치 - 스레드 안전 버전
"""

from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from datetime import datetime

class LogViewer(QTextBrowser):
    """로그 메시지 표시 위젯 (스레드 안전 버전)"""
    
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
        
        # 맨 아래로 스크롤
        self.moveCursor(QTextCursor.End)
        
        # 최대 라인 수 제한
        if self.document().lineCount() > self.max_lines:
            cursor = QTextCursor(self.document())
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                               self.document().lineCount() - self.max_lines)
            cursor.removeSelectedText()
