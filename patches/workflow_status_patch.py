#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 워크플로우 상태 위젯 패치 - 스레드 안전 버전
"""

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QColor
from typing import Optional

class WorkflowStatusWidget:
    """WorkflowStatusWidget 패치 메서드"""
    
    @staticmethod
    def patch_update_status(widget_class):
        """update_status 메서드를 스레드 안전하게 패치"""
        original_method = widget_class.update_status
        
        @pyqtSlot(object)
        def thread_safe_update_status(self, workflow=None):
            """스레드 안전한 워크플로우 상태 업데이트"""
            return original_method(self, workflow)
        
        widget_class.update_status = thread_safe_update_status
        return widget_class
