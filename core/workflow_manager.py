 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 작업 흐름 관리자
복잡한 다단계 작업 실행, 상태 관리 및 오류 복구를 담당
"""

import os
import json
import logging
import time
from typing import Dict, List, Callable, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pathlib import Path
import threading
import uuid

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """작업 흐름 상태"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkflowStepStatus(Enum):
    """작업 흐름 단계 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep:
    """작업 흐름의 단일 단계"""
    
    def __init__(self, step_id: str, name: str, action: Dict[str, Any], retry_count: int = 3,
                retry_delay: float = 2.0, timeout: float = 60.0, dependencies: List[str] = None,
                condition: str = None, rollback_action: Dict[str, Any] = None):
        self.step_id = step_id
        self.name = name
        self.action = action  # {'plugin_type': str, 'plugin_name': str, 'action': str, 'params': dict}
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.dependencies = dependencies or []
        self.condition = condition  # 조건식 문자열 (파이썬 eval() 사용)
        self.rollback_action = rollback_action
        
        self.status = WorkflowStepStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.retry_attempts = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """단계 정보를 딕셔너리로 변환"""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "action": self.action,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "dependencies": self.dependencies,
            "condition": self.condition,
            "rollback_action": self.rollback_action,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "retry_attempts": self.retry_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """딕셔너리에서 단계 정보 생성"""
        step = cls(
            step_id=data["step_id"],
            name=data["name"],
            action=data["action"],
            retry_count=data.get("retry_count", 3),
            retry_delay=data.get("retry_delay", 2.0),
            timeout=data.get("timeout", 60.0),
            dependencies=data.get("dependencies", []),
            condition=data.get("condition"),
            rollback_action=data.get("rollback_action")
        )
        
        # 상태 복원
        step.status = WorkflowStepStatus(data.get("status", "pending"))
        step.result = data.get("result")
        step.error = data.get("error")
        step.start_time = datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
        step.end_time = datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        step.retry_attempts = data.get("retry_attempts", 0)
        
        return step


class Workflow:
    """작업 흐름 - 여러 단계로 구성된 자동화 작업"""
    
    def __init__(self, workflow_id: str = None, name: str = None, description: str = None,
                checkpoint_dir: str = None, auto_recovery: bool = True):
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.name = name or f"Workflow_{self.workflow_id[:8]}"
        self.description = description or ""
        self.steps: Dict[str, WorkflowStep] = {}
        self.step_order: List[str] = []
        self.status = WorkflowStatus.PENDING
        self.checkpoint_dir = checkpoint_dir
        self.auto_recovery = auto_recovery
        self.variables: Dict[str, Any] = {}
        self.start_time = None
        self.end_time = None
        self.current_step_id = None
        self.error = None
    
    def add_step(self, step: WorkflowStep) -> str:
        """작업 흐름에 단계 추가"""
        if step.step_id in self.steps:
            logger.warning(f"중복된 단계 ID: {step.step_id}, 덮어쓰기")
        
        self.steps[step.step_id] = step
        
        # 순서가 아직 없다면 추가
        if step.step_id not in self.step_order:
            self.step_order.append(step.step_id)
        
        return step.step_id
    
    def add_steps(self, steps: List[WorkflowStep]) -> List[str]:
        """여러 단계를 한꺼번에 추가"""
        step_ids = []
        for step in steps:
            step_id = self.add_step(step)
            step_ids.append(step_id)
        return step_ids
    
    def remove_step(self, step_id: str) -> bool:
        """단계 제거"""
        if step_id not in self.steps:
            logger.warning(f"제거할 단계를 찾을 수 없음: {step_id}")
            return False
        
        del self.steps[step_id]
        
        # 순서에서도 제거
        if step_id in self.step_order:
            self.step_order.remove(step_id)
        
        return True
    
    def set_step_order(self, step_order: List[str]) -> bool:
        """단계 실행 순서 설정"""
        # 모든 단계가 존재하는지 확인
        for step_id in step_order:
            if step_id not in self.steps:
                logger.error(f"단계를 찾을 수 없음: {step_id}")
                return False
        
        # 모든 단계가 포함되었는지 확인
        for step_id in self.steps:
            if step_id not in step_order:
                logger.warning(f"단계가 순서에 포함되지 않음: {step_id}")
        
        self.step_order = step_order
        return True
    
    def get_next_step(self) -> Optional[WorkflowStep]:
        """다음 실행할 단계 반환"""
        if self.status != WorkflowStatus.RUNNING:
            return None
        
        for step_id in self.step_order:
            step = self.steps[step_id]
            
            # 이미 완료된 단계는 건너뜀
            if step.status in [WorkflowStepStatus.COMPLETED, WorkflowStepStatus.SKIPPED]:
                continue
            
            # 종속성 확인
            dependencies_met = True
            for dep_id in step.dependencies:
                if dep_id not in self.steps:
                    logger.error(f"종속성을 찾을 수 없음: {dep_id}")
                    dependencies_met = False
                    break
                
                dep_step = self.steps[dep_id]
                if dep_step.status != WorkflowStepStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            if not dependencies_met:
                continue
            
            # 조건 확인
            if step.condition:
                try:
                    # 변수 컨텍스트에서 조건 평가
                    condition_context = {**self.variables}
                    
                    # 이전 단계 결과 포함
                    for prev_id in self.step_order:
                        prev_step = self.steps[prev_id]
                        if prev_step.status == WorkflowStepStatus.COMPLETED:
                            condition_context[f"step_{prev_id}"] = prev_step.result
                        if prev_id == step_id:
                            break
                    
                    condition_met = eval(step.condition, {"__builtins__": {}}, condition_context)
                    
                    if not condition_met:
                        logger.info(f"조건 불충족으로 단계 건너뜀: {step.step_id}")
                        step.status = WorkflowStepStatus.SKIPPED
                        continue
                except Exception as e:
                    logger.error(f"조건 평가 중 오류: {step.condition} - {str(e)}")
                    step.status = WorkflowStepStatus.FAILED
                    step.error = f"조건 평가 오류: {str(e)}"
                    return None
            
            # 다음 단계 반환
            return step
        
        # 모든 단계가 완료됨
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """작업 흐름 정보를 딕셔너리로 변환"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": {step_id: step.to_dict() for step_id, step in self.steps.items()},
            "step_order": self.step_order,
            "status": self.status.value,
            "checkpoint_dir": self.checkpoint_dir,
            "auto_recovery": self.auto_recovery,
            "variables": self.variables,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "current_step_id": self.current_step_id,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """딕셔너리에서 작업 흐름 정보 생성"""
        workflow = cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data["description"],
            checkpoint_dir=data.get("checkpoint_dir"),
            auto_recovery=data.get("auto_recovery", True)
        )
        
        # 단계 복원
        for step_id, step_data in data["steps"].items():
            workflow.steps[step_id] = WorkflowStep.from_dict(step_data)
        
        workflow.step_order = data["step_order"]
        workflow.status = WorkflowStatus(data["status"])
        workflow.variables = data.get("variables", {})
        workflow.start_time = datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
        workflow.end_time = datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        workflow.current_step_id = data.get("current_step_id")
        workflow.error = data.get("error")
        
        return workflow
    
    def save_checkpoint(self) -> str:
        """현재 상태를 체크포인트로 저장"""
        if not self.checkpoint_dir:
            logger.warning("체크포인트 디렉토리가 설정되지 않음")
            return ""
        
        checkpoint_dir = Path(self.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = checkpoint_dir / f"{self.workflow_id}_{timestamp}.json"
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"체크포인트 저장됨: {checkpoint_file}")
        return str(checkpoint_file)
    
    @classmethod
    def load_checkpoint(cls, checkpoint_file: str) -> 'Workflow':
        """체크포인트에서 작업 흐름 로드"""
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        workflow = cls.from_dict(data)
        logger.info(f"체크포인트에서 작업 흐름 로드됨: {checkpoint_file}")
        return workflow
    
    @classmethod
    def find_latest_checkpoint(cls, workflow_id: str, checkpoint_dir: str) -> Optional[str]:
        """지정된 작업 흐름의 최신 체크포인트 찾기"""
        checkpoint_dir = Path(checkpoint_dir)
        if not checkpoint_dir.exists():
            return None
        
        checkpoints = []
        for checkpoint_file in checkpoint_dir.glob(f"{workflow_id}_*.json"):
            checkpoints.append(str(checkpoint_file))
        
        if not checkpoints:
            return None
        
        # 파일 수정 시간 기준으로 최신 체크포인트 반환
        return max(checkpoints, key=lambda f: os.path.getmtime(f))


class WorkflowManager:
    """작업 흐름 관리자 - 여러 작업 흐름의 생성, 실행 및 관리를 담당"""
    
    def __init__(self, checkpoint_dir: str = None, plugin_manager: Any = None):
        self.checkpoint_dir = checkpoint_dir or os.path.join(os.path.expanduser("~"), "BlueAI", "checkpoints")
        self.plugin_manager = plugin_manager
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflows: Dict[str, threading.Thread] = {}
        self.callbacks: Dict[str, List[Callable]] = {
            "workflow_started": [],
            "workflow_completed": [],
            "workflow_failed": [],
            "workflow_canceled": [],
            "step_started": [],
            "step_completed": [],
            "step_failed": [],
            "step_skipped": []
        }
        
        # 체크포인트 디렉토리 생성
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def create_workflow(self, name: str, description: str = None,
                       auto_recovery: bool = True) -> Workflow:
        """새 작업 흐름 생성"""
        workflow = Workflow(
            name=name,
            description=description,
            checkpoint_dir=self.checkpoint_dir,
            auto_recovery=auto_recovery
        )
        
        self.workflows[workflow.workflow_id] = workflow
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """지정된 ID의 작업 흐름 반환"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """모든 작업 흐름 목록 반환"""
        return [
            {
                "workflow_id": wf.workflow_id,
                "name": wf.name,
                "description": wf.description,
                "status": wf.status.value,
                "step_count": len(wf.steps),
                "start_time": wf.start_time.isoformat() if wf.start_time else None,
                "end_time": wf.end_time.isoformat() if wf.end_time else None
            }
            for wf in self.workflows.values()
        ]
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 삭제"""
        if workflow_id not in self.workflows:
            logger.warning(f"삭제할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        # 실행 중인 작업 흐름은 삭제 불가
        if self.is_workflow_running(workflow_id):
            logger.error(f"실행 중인 작업 흐름은 삭제할 수 없음: {workflow_id}")
            return False
        
        del self.workflows[workflow_id]
        return True
    
    def is_workflow_running(self, workflow_id: str) -> bool:
        """작업 흐름이 현재 실행 중인지 확인"""
        if workflow_id not in self.workflows:
            return False
        
        return self.workflows[workflow_id].status == WorkflowStatus.RUNNING
    
    def _trigger_event(self, event_type: str, **kwargs):
        """이벤트 트리거하여 콜백 실행 (예외 처리 강화)"""
        if event_type not in self.callbacks:
            return
        
        # 콜백 목록 복사 (콜백 내에서 콜백 목록이 변경될 수 있음)
        callbacks = list(self.callbacks[event_type])
        
        for callback in callbacks:
            try:
                # 콜백이 여전히 유효한지 확인
                if callable(callback):
                    callback(**kwargs)
                else:
                    logger.warning(f"유효하지 않은 콜백: {callback}")
            except Exception as e:
                logger.error(f"콜백 실행 중 오류: {event_type} - {str(e)}")
    
    def register_callback(self, event_type: str, callback: Callable) -> bool:
        """이벤트 콜백 등록"""
        if event_type not in self.callbacks:
            logger.error(f"유효하지 않은 이벤트 타입: {event_type}")
            return False
        
        self.callbacks[event_type].append(callback)
        return True
    
    def unregister_callback(self, event_type: str, callback: Callable) -> bool:
        """이벤트 콜백 제거"""
        if event_type not in self.callbacks:
            return False
        
        if callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            return True
        return False
    
    def execute_step(self, workflow: Workflow, step: WorkflowStep) -> bool:
        """단일 단계 실행"""
        if not self.plugin_manager:
            logger.error("플러그인 관리자가 설정되지 않음")
            return False
        
        workflow.current_step_id = step.step_id
        step.status = WorkflowStepStatus.RUNNING
        step.start_time = datetime.now()
        step.retry_attempts = 0
        
        # 단계 시작 이벤트 트리거
        self._trigger_event(
            "step_started",
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            step_id=step.step_id,
            step_name=step.name
        )
        
        success = False
        
        for attempt in range(step.retry_count + 1):
            if attempt > 0:
                logger.info(f"단계 재시도 중: {step.name} (시도 {attempt}/{step.retry_count})")
                step.retry_attempts = attempt
                time.sleep(step.retry_delay)
            
            try:
                # 플러그인 실행
                plugin_type = step.action.get("plugin_type")
                plugin_name = step.action.get("plugin_name")
                action = step.action.get("action")
                params = step.action.get("params", {})
                
                # 변수 통합 (변수에 이전 단계 결과 포함)
                context_params = {**params}
                for var_name, var_value in workflow.variables.items():
                    context_params[var_name] = var_value
                
                # 타임아웃 설정
                start_time = time.time()
                max_end_time = start_time + step.timeout
                
                # 액션 실행
                result = self.plugin_manager.execute_plugin(
                    plugin_type, plugin_name, action, context_params
                )
                
                if time.time() > max_end_time:
                    raise TimeoutError(f"단계 실행 시간 초과: {step.timeout}초")
                
                if result is not None:
                    step.result = result
                    step.status = WorkflowStepStatus.COMPLETED
                    step.end_time = datetime.now()
                    success = True
                    
                    # 단계 완료 이벤트 트리거
                    self._trigger_event(
                        "step_completed",
                        workflow_id=workflow.workflow_id,
                        workflow_name=workflow.name,
                        step_id=step.step_id,
                        step_name=step.name,
                        result=step.result
                    )
                    
                    # 변수에 결과 저장
                    workflow.variables[f"step_{step.step_id}_result"] = result
                    break
                
            except Exception as e:
                step.error = str(e)
                logger.error(f"단계 실행 중 오류: {step.name} - {str(e)}")
                
                # 마지막 시도였는지 확인
                if attempt >= step.retry_count:
                    step.status = WorkflowStepStatus.FAILED
                    step.end_time = datetime.now()
                    
                    # 단계 실패 이벤트 트리거
                    self._trigger_event(
                        "step_failed",
                        workflow_id=workflow.workflow_id,
                        workflow_name=workflow.name,
                        step_id=step.step_id,
                        step_name=step.name,
                        error=step.error
                    )
                    
                    # 롤백 액션이 있으면 실행
                    if step.rollback_action:
                        logger.info(f"롤백 액션 실행 중: {step.name}")
                        try:
                            rollback_type = step.rollback_action.get("plugin_type")
                            rollback_name = step.rollback_action.get("plugin_name")
                            rollback_action = step.rollback_action.get("action")
                            rollback_params = step.rollback_action.get("params", {})
                            
                            self.plugin_manager.execute_plugin(
                                rollback_type, rollback_name, rollback_action, rollback_params
                            )
                        except Exception as rb_err:
                            logger.error(f"롤백 액션 실행 중 오류: {str(rb_err)}")
        
        return success
    
    def _execute_workflow_thread(self, workflow_id: str):
        """작업 흐름 실행 스레드"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.error(f"실행할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = datetime.now()
        workflow.current_step_id = None
        
        # 작업 흐름 시작 이벤트 트리거
        self._trigger_event(
            "workflow_started",
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name
        )
        
        try:
            # 체크포인트 저장
            if workflow.checkpoint_dir:
                workflow.save_checkpoint()
            
            # 단계 순차 실행
            while True:
                step = workflow.get_next_step()
                if not step:
                    break
                
                # 단계 실행
                success = self.execute_step(workflow, step)
                
                # 실패 시 작업 흐름 중단 (auto_recovery가 꺼져 있는 경우)
                if not success and not workflow.auto_recovery:
                    workflow.status = WorkflowStatus.FAILED
                    workflow.error = f"단계 실패: {step.name} - {step.error}"
                    workflow.end_time = datetime.now()
                    
                    # 작업 흐름 실패 이벤트 트리거
                    self._trigger_event(
                        "workflow_failed",
                        workflow_id=workflow.workflow_id,
                        workflow_name=workflow.name,
                        error=workflow.error
                    )
                    
                    # 체크포인트 저장
                    if workflow.checkpoint_dir:
                        workflow.save_checkpoint()
                    
                    return
                
                # 체크포인트 저장
                if workflow.checkpoint_dir:
                    workflow.save_checkpoint()
            
            # 모든 단계 완료
            workflow.status = WorkflowStatus.COMPLETED
            workflow.end_time = datetime.now()
            
            # 작업 흐름 완료 이벤트 트리거
            self._trigger_event(
                "workflow_completed",
                workflow_id=workflow.workflow_id,
                workflow_name=workflow.name,
                results={
                    step_id: step.result
                    for step_id, step in workflow.steps.items()
                    if step.status == WorkflowStepStatus.COMPLETED
                }
            )
            
            # 최종 체크포인트 저장
            if workflow.checkpoint_dir:
                workflow.save_checkpoint()
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            workflow.end_time = datetime.now()
            
            # 작업 흐름 실패 이벤트 트리거
            self._trigger_event(
                "workflow_failed",
                workflow_id=workflow.workflow_id,
                workflow_name=workflow.name,
                error=workflow.error
            )
            
            # 체크포인트 저장
            if workflow.checkpoint_dir:
                workflow.save_checkpoint()
            
            logger.error(f"작업 흐름 실행 중 오류: {workflow.name} - {str(e)}")
        
        finally:
            # 활성 작업 흐름 목록에서 제거
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def start_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 실행 시작"""
        if workflow_id not in self.workflows:
            logger.error(f"실행할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        # 이미 실행 중인 작업 흐름인지 확인
        if self.is_workflow_running(workflow_id):
            logger.warning(f"작업 흐름이 이미 실행 중: {workflow_id}")
            return False
        
        # 워크플로우 초기화
        workflow = self.workflows[workflow_id]
        for step in workflow.steps.values():
            if step.status != WorkflowStepStatus.COMPLETED:
                step.status = WorkflowStepStatus.PENDING
                step.result = None
                step.error = None
                step.start_time = None
                step.end_time = None
                step.retry_attempts = 0
        
        # 실행 스레드 시작
        thread = threading.Thread(
            target=self._execute_workflow_thread,
            args=(workflow_id,),
            daemon=True
        )
        thread.start()
        
        self.active_workflows[workflow_id] = thread
        return True
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 일시 중지 (현재 실행 중인 단계 완료 후)"""
        if workflow_id not in self.workflows:
            logger.error(f"일시 중지할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        
        # 실행 중인 작업 흐름만 일시 중지 가능
        if workflow.status != WorkflowStatus.RUNNING:
            logger.warning(f"실행 중이 아닌 작업 흐름은 일시 중지할 수 없음: {workflow_id}")
            return False
        
        workflow.status = WorkflowStatus.PAUSED
        
        # 체크포인트 저장
        if workflow.checkpoint_dir:
            workflow.save_checkpoint()
        
        return True
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """일시 중지된 작업 흐름 재개"""
        if workflow_id not in self.workflows:
            logger.error(f"재개할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        
        # 일시 중지된 작업 흐름만 재개 가능
        if workflow.status != WorkflowStatus.PAUSED:
            logger.warning(f"일시 중지된 작업 흐름만 재개 가능: {workflow_id}")
            return False
        
        # 상태 업데이트 및 재실행
        workflow.status = WorkflowStatus.RUNNING
        
        # 실행 스레드 시작
        thread = threading.Thread(
            target=self._execute_workflow_thread,
            args=(workflow_id,),
            daemon=True
        )
        thread.start()
        
        self.active_workflows[workflow_id] = thread
        return True
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 취소"""
        if workflow_id not in self.workflows:
            logger.error(f"취소할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        prev_status = workflow.status
        
        # 이미 완료된 작업 흐름은 취소 불가
        if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELED]:
            logger.warning(f"이미 완료된 작업 흐름은 취소할 수 없음: {workflow_id}")
            return False
        
        workflow.status = WorkflowStatus.CANCELED
        workflow.end_time = datetime.now()
        
        # 작업 흐름 취소 이벤트 트리거
        self._trigger_event(
            "workflow_canceled",
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            prev_status=prev_status
        )
        
        # 체크포인트 저장
        if workflow.checkpoint_dir:
            workflow.save_checkpoint()
        
        return True
    
    def retry_workflow(self, workflow_id: str, from_beginning: bool = False) -> bool:
        """실패한 작업 흐름 재시도"""
        if workflow_id not in self.workflows:
            logger.error(f"재시도할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        
        # 실패하거나 취소된 작업 흐름만 재시도 가능
        if workflow.status not in [WorkflowStatus.FAILED, WorkflowStatus.CANCELED]:
            logger.warning(f"실패하거나 취소된 작업 흐름만 재시도 가능: {workflow_id}")
            return False
        
        # 처음부터 재시작하는 경우
        if from_beginning:
            for step in workflow.steps.values():
                step.status = WorkflowStepStatus.PENDING
                step.result = None
                step.error = None
                step.start_time = None
                step.end_time = None
                step.retry_attempts = 0
        
        # 실패한 단계부터 재시작하는 경우 (기본값)
        else:
            for step in workflow.steps.values():
                if step.status in [WorkflowStepStatus.FAILED, WorkflowStepStatus.PENDING]:
                    step.status = WorkflowStepStatus.PENDING
                    step.result = None
                    step.error = None
                    step.start_time = None
                    step.end_time = None
                    step.retry_attempts = 0
        
        # 상태 초기화
        workflow.status = WorkflowStatus.PENDING
        workflow.error = None
        workflow.current_step_id = None
        
        # 작업 흐름 재시작
        return self.start_workflow(workflow_id)
    
    def load_workflow_from_file(self, file_path: str) -> str:
        """파일에서 작업 흐름 정의 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            workflow = Workflow.from_dict(data)
            workflow.checkpoint_dir = self.checkpoint_dir
            
            self.workflows[workflow.workflow_id] = workflow
            logger.info(f"작업 흐름 로드됨: {workflow.name} (ID: {workflow.workflow_id})")
            
            return workflow.workflow_id
            
        except Exception as e:
            logger.error(f"작업 흐름 로드 중 오류: {file_path} - {str(e)}")
            return ""
    
    def save_workflow_to_file(self, workflow_id: str, file_path: str) -> bool:
        """작업 흐름 정의를 파일로 저장"""
        if workflow_id not in self.workflows:
            logger.error(f"저장할 작업 흐름을 찾을 수 없음: {workflow_id}")
            return False
        
        try:
            workflow = self.workflows[workflow_id]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"작업 흐름 저장됨: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"작업 흐름 저장 중 오류: {file_path} - {str(e)}")
            return False
    
    def recover_from_checkpoint(self, workflow_id: str = None, checkpoint_file: str = None) -> Optional[str]:
        """체크포인트에서 작업 흐름 복구"""
        # 체크포인트 파일이 지정된 경우
        if checkpoint_file:
            try:
                workflow = Workflow.load_checkpoint(checkpoint_file)
                self.workflows[workflow.workflow_id] = workflow
                logger.info(f"체크포인트에서 작업 흐름 복구됨: {workflow.name} (ID: {workflow.workflow_id})")
                return workflow.workflow_id
            except Exception as e:
                logger.error(f"체크포인트 로드 중 오류: {checkpoint_file} - {str(e)}")
                return None
        
        # 작업 흐름 ID가 지정된 경우, 최신 체크포인트 찾기
        elif workflow_id:
            latest_checkpoint = Workflow.find_latest_checkpoint(workflow_id, self.checkpoint_dir)
            if latest_checkpoint:
                return self.recover_from_checkpoint(checkpoint_file=latest_checkpoint)
            else:
                logger.warning(f"복구할 체크포인트를 찾을 수 없음: {workflow_id}")
                return None
        
        # 둘 다 지정되지 않은 경우
        else:
            logger.error("복구할 workflow_id 또는 checkpoint_file이 필요함")
            return None
    
    def shutdown(self):
        """관리자 종료 및 리소스 정리"""
        # 실행 중인 모든 작업 흐름 취소
        for workflow_id in list(self.active_workflows.keys()):
            self.cancel_workflow(workflow_id)
        
        # 체크포인트 저장
        for workflow in self.workflows.values():
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.CANCELED
                if workflow.checkpoint_dir:
                    workflow.save_checkpoint()
        
        logger.info("워크플로우 관리자 종료됨")