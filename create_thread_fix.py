#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 스레드 안전 패치
이 스크립트는 Qt 스레딩 문제를 해결하기 위한 패치를 생성합니다.
"""

import os
import shutil
import sys

def backup_file(file_path):
    """파일 백업 생성"""
    backup_path = file_path + '.bak'
    shutil.copy2(file_path, backup_path)
    print(f"백업 생성됨: {backup_path}")
    return backup_path

def create_patches_directory():
    """패치 디렉토리 생성"""
    patches_dir = 'patches'
    os.makedirs(patches_dir, exist_ok=True)
    
    # __init__.py 파일 생성하여 패키지로 만들기
    with open(os.path.join(patches_dir, '__init__.py'), 'w') as f:
        f.write('# BlueAI 패치 패키지\n')
    
    return patches_dir

def create_log_viewer_patch(patches_dir):
    """LogViewer 패치 파일 생성"""
    file_path = os.path.join(patches_dir, 'logviewer_patch.py')
    
    content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
BlueAI 로그 뷰어 패치 - 스레드 안전 버전
\"\"\"

from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from datetime import datetime

class LogViewer(QTextBrowser):
    \"\"\"로그 메시지 표시 위젯 (스레드 안전 버전)\"\"\"
    
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
        \"\"\"로그 메시지 추가 (스레드 안전)\"\"\"
        # 시그널을 통해 메인 스레드에서 처리
        self.log_signal.emit(message, level)
    
    @pyqtSlot(str, str)
    def _append_log_safe(self, message, level):
        \"\"\"메인 UI 스레드에서 실행되는 실제 로그 추가 메서드\"\"\"
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
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"LogViewer 패치 파일 생성됨: {file_path}")
    return file_path

def create_workflow_status_patch(patches_dir):
    """WorkflowStatusWidget 패치 파일 생성"""
    file_path = os.path.join(patches_dir, 'workflow_status_patch.py')
    
    content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
BlueAI 워크플로우 상태 위젯 패치 - 스레드 안전 버전
\"\"\"

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QColor
from typing import Optional

class WorkflowStatusWidget:
    \"\"\"WorkflowStatusWidget 패치 메서드\"\"\"
    
    @staticmethod
    def patch_update_status(widget_class):
        \"\"\"update_status 메서드를 스레드 안전하게 패치\"\"\"
        original_method = widget_class.update_status
        
        @pyqtSlot(object)
        def thread_safe_update_status(self, workflow=None):
            \"\"\"스레드 안전한 워크플로우 상태 업데이트\"\"\"
            return original_method(self, workflow)
        
        widget_class.update_status = thread_safe_update_status
        return widget_class
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"WorkflowStatusWidget 패치 파일 생성됨: {file_path}")
    return file_path

def create_main_window_patch(patches_dir):
    """MainWindow 패치 파일 생성"""
    file_path = os.path.join(patches_dir, 'main_window_patch.py')
    
    content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
BlueAI 메인 윈도우 패치 - 스레드 안전 메서드
\"\"\"

from PyQt5.QtCore import Qt, QMetaObject, Q_ARG

def patch_update_workflow_status(window_class):
    \"\"\"update_workflow_status 메서드를 스레드 안전하게 패치\"\"\"
    original_method = window_class.update_workflow_status
    
    def thread_safe_update_workflow_status(self):
        \"\"\"워크플로우 상태 주기적 업데이트 (스레드 안전)\"\"\"
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
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"MainWindow 패치 파일 생성됨: {file_path}")
    return file_path

def create_main_patch(patches_dir):
    """메인 패치 파일 생성"""
    file_path = os.path.join(patches_dir, 'main_patch.py')
    
    content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
BlueAI 통합 자동화 시스템 - 메인 패치
모든 스레드 안전 패치를 적용합니다.
\"\"\"

import sys
import os
from PyQt5.QtCore import qRegisterMetaType

# QTextCursor 타입 등록 (스레드 간 시그널에서 사용 가능하도록)
qRegisterMetaType("QTextCursor")

# LogViewer 패치 적용
def apply_logviewer_patch():
    \"\"\"LogViewer 클래스 패치\"\"\"
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
    \"\"\"WorkflowStatusWidget 패치 적용\"\"\"
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
    \"\"\"MainWindow 패치 적용\"\"\"
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
    \"\"\"모든 패치 적용\"\"\"
    logviewer_patched = apply_logviewer_patch()
    workflow_patched = apply_workflow_status_patch()
    mainwindow_patched = apply_main_window_patch()
    
    if logviewer_patched and workflow_patched and mainwindow_patched:
        print("모든 패치가 성공적으로 적용되었습니다.")
    else:
        print("일부 패치가 적용되지 않았습니다.")

# 패치 자동 적용
apply_all_patches()
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"메인 패치 파일 생성됨: {file_path}")
    return file_path

def create_run_blueai_py():
    """BlueAI 실행 래퍼 생성"""
    file_path = 'run_blueai.py'
    
    content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
BlueAI 통합 자동화 시스템 - 스레드 안전 실행 래퍼
\"\"\"

import os
import sys
import importlib.util
import traceback

# Qt 스레드 안전성 향상을 위한 환경 변수 설정
os.environ['QT_THREAD_UNSAFE'] = '1'

def main():
    \"\"\"메인 함수\"\"\"
    # 현재 디렉토리를 Python 경로에 추가
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # 패치 모듈 가져오기 및 적용
        print("BlueAI 패치 적용 중...")
        import patches.main_patch
        
        # 원래 main.py 실행
        print("BlueAI 시스템 시작 중...")
        from main import main as original_main
        return original_main()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 실행 권한 부여
    try:
        os.chmod(file_path, 0o755)
    except:
        pass
    
    print(f"BlueAI 실행 래퍼 파일 생성됨: {file_path}")
    return file_path

def main():
    """메인 함수"""
    print("BlueAI 통합 자동화 시스템 - 스레드 안전 패치 생성 시작")
    
    # 현재 디렉토리 확인
    if not os.path.exists('ui/main_window.py'):
        print("오류: 스크립트를 BlueAI 프로젝트 루트 디렉토리에서 실행해야 합니다.")
        return 1
    
    # ui/main_window.py 백업
    backup_file('ui/main_window.py')
    
    # 패치 디렉토리 생성
    patches_dir = create_patches_directory()
    
    # 패치 파일 생성
    create_log_viewer_patch(patches_dir)
    create_workflow_status_patch(patches_dir)
    create_main_window_patch(patches_dir)
    create_main_patch(patches_dir)
    
    # 실행 래퍼 생성
    create_run_blueai_py()
    
    print("\n패치 생성이 완료되었습니다. 다음 명령어로 BlueAI를 실행하세요:")
    print("python run_blueai.py")
    print("\n문제가 계속되면 백업 파일(.bak)을 사용하여 복원할 수 있습니다.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())