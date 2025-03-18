#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 메인 윈도우 패치 - 스레드 안전 메서드
"""

from PyQt5.QtCore import Qt, QMetaObject, Q_ARG

def patch_update_workflow_status(window_class):
    """update_workflow_status 메서드를 스레드 안전하게 패치"""
    original_method = window_class.update_workflow_status
    
    def thread_safe_update_workflow_status(self):
        """워크플로우 상태 주기적 업데이트 (스레드 안전)"""
        if not self.current_workflow_id:
            return

        workflow = self.workflow_manager.get_workflow(self.current_workflow_id)
        if workflow:
            # QMetaObject.invokeMethod를 사용하여 메인 스레드에서 업데이트
            QMetaObject.invokeMethod(self.workflow_status, "update_status",
                                    Qt.QueuedConnection,
                                    Q_ARG(object, workflow))
    
    window_class.update_workflow_status = thread_safe_update_workflow_status
    return window_class
