#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 메인 패치
모든 스레드 안전 패치를 적용합니다.
"""

import sys
import os
from PyQt5.QtCore import qRegisterMetaType

# QTextCursor 타입 등록 (스레드 간 시그널에서 사용 가능하도록)
qRegisterMetaType("QTextCursor")

# LogViewer 패치 적용
def apply_logviewer_patch():
    """LogViewer 클래스 패치"""
    try:
        from patches.logviewer_patch import LogViewer
        import ui.main_window
        # 원래 클래스 저장
        ui.main_window._original_LogViewer = ui.main_window.LogViewer
        # 패치된 클래스로 교체
        ui.main_window.LogViewer = LogViewer
        print("LogViewer 패치 적용됨")
        return True
    except Exception as e:
        print(f"LogViewer 패치 적용 실패: {str(e)}")
        return False

# WorkflowStatusWidget 패치 적용
def apply_workflow_status_patch():
    """WorkflowStatusWidget 패치 적용"""
    try:
        from patches.workflow_status_patch import WorkflowStatusWidget
        import ui.main_window
        # 패치 적용
        ui.main_window.WorkflowStatusWidget = WorkflowStatusWidget.patch_update_status(
            ui.main_window.WorkflowStatusWidget
        )
        print("WorkflowStatusWidget 패치 적용됨")
        return True
    except Exception as e:
        print(f"WorkflowStatusWidget 패치 적용 실패: {str(e)}")
        return False

# MainWindow 패치 적용
def apply_main_window_patch():
    """MainWindow 패치 적용"""
    try:
        from patches.main_window_patch import patch_update_workflow_status
        import ui.main_window
        # 패치 적용
        ui.main_window.MainWindow = patch_update_workflow_status(
            ui.main_window.MainWindow
        )
        print("MainWindow 패치 적용됨")
        return True
    except Exception as e:
        print(f"MainWindow 패치 적용 실패: {str(e)}")
        return False

# 모든 패치 적용
def apply_all_patches():
    """모든 패치 적용"""
    logviewer_patched = apply_logviewer_patch()
    workflow_patched = apply_workflow_status_patch()
    mainwindow_patched = apply_main_window_patch()
    
    if logviewer_patched and workflow_patched and mainwindow_patched:
        print("모든 패치가 성공적으로 적용되었습니다.")
    else:
        print("일부 패치가 적용되지 않았습니다.")

# 패치 자동 적용
apply_all_patches()
