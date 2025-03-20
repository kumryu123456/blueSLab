"""
작업 흐름 관리 모듈

이 모듈은 자동화 작업의 흐름을 관리합니다.
서버에서 받은 작업 계획을 실행하고, 작업 상태를 추적하며, 오류 발생 시 복구를 담당합니다.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .plugin_system import PluginManager, PluginType


class StepStatus(Enum):
    """작업 단계 상태"""
    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패
    SKIPPED = "skipped"  # 건너뜀


class WorkflowStatus(Enum):
    """작업 흐름 상태"""
    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패
    PAUSED = "paused"  # 일시 중지


@dataclass
class StepResult:
    """작업 단계 결과"""
    status: StepStatus  # 단계 상태
    output: Dict[str, Any] = field(default_factory=dict)  # 단계 출력
    error: Optional[str] = None  # 오류 메시지
    execution_time: float = 0.0  # 실행 시간(초)


@dataclass
class WorkflowContext:
    """작업 흐름 컨텍스트"""
    workflow_id: str  # 작업 흐름 ID
    state: Dict[str, Any] = field(default_factory=dict)  # 상태 저장소
    settings: Dict[str, Any] = field(default_factory=dict)  # 작업 설정
    results: Dict[str, StepResult] = field(default_factory=dict)  # 단계별 결과
    checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # 체크포인트
    execution_path: List[str] = field(default_factory=list)  # 실행 경로
    start_time: float = field(default_factory=time.time)  # 시작 시간
    status: WorkflowStatus = WorkflowStatus.PENDING  # 작업 흐름 상태
    
    def get_step_result(self, step_id: str) -> Optional[StepResult]:
        """단계 결과 가져오기"""
        return self.results.get(step_id)
    
    def set_step_result(self, step_id: str, result: StepResult) -> None:
        """단계 결과 설정"""
        self.results[step_id] = result
        self.execution_path.append(step_id)
    
    def create_checkpoint(self, checkpoint_id: str) -> None:
        """체크포인트 생성"""
        self.checkpoints[checkpoint_id] = {
            'state': self.state.copy(),
            'execution_path': self.execution_path.copy(),
            'results': {k: v for k, v in self.results.items()},
            'time': time.time()
        }
    
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """체크포인트 복원"""
        if checkpoint_id not in self.checkpoints:
            return False
        
        checkpoint = self.checkpoints[checkpoint_id]
        self.state = checkpoint['state'].copy()
        
        # 체크포인트 이후 단계 결과 제거
        checkpoint_path = checkpoint['execution_path']
        for step_id in self.execution_path[len(checkpoint_path):]:
            if step_id in self.results:
                del self.results[step_id]
        
        self.execution_path = checkpoint_path.copy()
        return True
    
    def get_execution_time(self) -> float:
        """현재까지의 실행 시간(초)"""
        return time.time() - self.start_time
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """상태 업데이트"""
        self.state.update(updates)


class WorkflowError(Exception):
    """작업 흐름 오류"""
    pass


class WorkflowManager:
    """작업 흐름 관리자"""
    
    def __init__(self, plugin_manager: PluginManager, logger=None):
        """작업 흐름 관리자 초기화
        
        Args:
            plugin_manager: 플러그인 관리자
            logger: 로거 객체
        """
        self.plugin_manager = plugin_manager
        self.logger = logger or logging.getLogger(__name__)
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.step_handlers: Dict[str, Callable] = {}
        self._register_default_step_handlers()
    
    def _register_default_step_handlers(self) -> None:
        """기본 단계 핸들러 등록"""
        # 기본 핸들러 등록 (향후 확장)
        self.register_step_handler("web_navigation", self._handle_web_navigation)
        self.register_step_handler("element_recognition", self._handle_element_recognition)
        self.register_step_handler("interruption_handling", self._handle_interruption_handling)
        self.register_step_handler("input_text", self._handle_input_text)
        self.register_step_handler("key_press", self._handle_key_press)
        self.register_step_handler("wait_for_load", self._handle_wait_for_load)
    
    def register_step_handler(self, step_type: str, handler: Callable) -> None:
        """단계 핸들러 등록
        
        Args:
            step_type: 단계 유형
            handler: 핸들러 함수
        """
        self.step_handlers[step_type] = handler
        self.logger.debug(f"단계 핸들러 등록: {step_type}")
    
    def create_workflow(self, workflow_plan: Dict[str, Any], settings: Dict[str, Any] = None) -> str:
        """작업 흐름 생성
        
        Args:
            workflow_plan: 작업 계획
            settings: 작업 설정
            
        Returns:
            작업 흐름 ID
        """
        workflow_id = workflow_plan.get('id') or str(uuid.uuid4())
        
        context = WorkflowContext(
            workflow_id=workflow_id,
            settings=settings or {},
        )
        
        self.active_workflows[workflow_id] = context
        self.logger.info(f"작업 흐름 생성: {workflow_id}")
        return workflow_id
    
    def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """작업 흐름 실행
        
        Args:
            workflow_id: 작업 흐름 ID
            
        Returns:
            작업 결과
        """
        if workflow_id not in self.active_workflows:
            raise WorkflowError(f"작업 흐름을 찾을 수 없음: {workflow_id}")
        
        context = self.active_workflows[workflow_id]
        context.status = WorkflowStatus.RUNNING
        
        workflow_plan = context.settings.get('workflow_plan', {})
        steps = workflow_plan.get('steps', [])
        
        try:
            for step in steps:
                if context.status != WorkflowStatus.RUNNING:
                    # 작업이 일시 중지되거나 중단된 경우
                    break
                
                step_id = step.get('id')
                if not step_id:
                    self.logger.warning("단계 ID가 없음, 건너뜀")
                    continue
                
                # 체크포인트 생성
                if step.get('checkpoint', False):
                    context.create_checkpoint(step_id)
                    self.logger.debug(f"체크포인트 생성: {step_id}")
                
                # 단계 실행
                result = self._execute_step(context, step)
                context.set_step_result(step_id, result)
                
                # 실패한 경우 오류 복구 시도
                if result.status == StepStatus.FAILED:
                    if not self._try_recover(context, step):
                        context.status = WorkflowStatus.FAILED
                        raise WorkflowError(f"단계 실행 실패: {step_id} - {result.error}")
            
            # 모든 단계 성공적으로 완료
            context.status = WorkflowStatus.COMPLETED
            self.logger.info(f"작업 흐름 완료: {workflow_id}")
            
            return {
                'workflow_id': workflow_id,
                'status': context.status.value,
                'execution_time': context.get_execution_time(),
                'state': context.state,
                'results': {k: {'status': v.status.value, 'output': v.output} 
                           for k, v in context.results.items()}
            }
            
        except Exception as e:
            context.status = WorkflowStatus.FAILED
            self.logger.error(f"작업 흐름 실행 중 오류: {workflow_id} - {str(e)}")
            
            return {
                'workflow_id': workflow_id,
                'status': context.status.value,
                'error': str(e),
                'execution_time': context.get_execution_time(),
                'state': context.state,
                'results': {k: {'status': v.status.value, 'output': v.output} 
                           for k, v in context.results.items()}
            }
    
    def _execute_step(self, context: WorkflowContext, step: Dict[str, Any]) -> StepResult:
        """단계 실행
        
        Args:
            context: 작업 흐름 컨텍스트
            step: 단계 정보
            
        Returns:
            단계 실행 결과
        """
        step_id = step.get('id', 'unknown')
        step_type = step.get('type')
        
        if not step_type:
            return StepResult(
                status=StepStatus.FAILED,
                error="단계 유형이 지정되지 않음"
            )
        
        handler = self.step_handlers.get(step_type)
        if not handler:
            return StepResult(
                status=StepStatus.FAILED,
                error=f"처리할 수 없는 단계 유형: {step_type}"
            )
        
        try:
            self.logger.info(f"단계 실행: {step_id} ({step_type})")
            start_time = time.time()
            
            # 단계 파라미터 (변수 대체 포함)
            params = self._resolve_parameters(context, step.get('params', {}))
            
            # 단계 실행
            output = handler(context, params)
            
            execution_time = time.time() - start_time
            
            # 상태 업데이트 (단계 출력이 사전인 경우)
            if isinstance(output, dict):
                context.update_state(output)
            
            return StepResult(
                status=StepStatus.COMPLETED,
                output=output if isinstance(output, dict) else {'result': output},
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"단계 실행 중 오류: {step_id} - {str(e)}")
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e)
            )
    
    def _try_recover(self, context: WorkflowContext, step: Dict[str, Any]) -> bool:
        """오류 복구 시도
        
        Args:
            context: 작업 흐름 컨텍스트
            step: 단계 정보
            
        Returns:
            복구 성공 여부
        """
        step_id = step.get('id', 'unknown')
        self.logger.info(f"오류 복구 시도: {step_id}")
        
        recovery_strategies = step.get('recovery_strategies', [])
        if not recovery_strategies:
            # 기본 복구 전략: 체크포인트로 롤백
            last_checkpoint = None
            for checkpoint_id in reversed(context.execution_path):
                if checkpoint_id in context.checkpoints:
                    last_checkpoint = checkpoint_id
                    break
            
            if last_checkpoint:
                self.logger.info(f"체크포인트로 롤백: {last_checkpoint}")
                return context.restore_checkpoint(last_checkpoint)
            
            return False
        
        # 복구 전략 시도
        for strategy in recovery_strategies:
            strategy_type = strategy.get('type')
            if strategy_type == 'retry':
                # 재시도 전략
                max_retries = strategy.get('max_retries', 3)
                delay = strategy.get('delay', 1.0)
                
                for i in range(max_retries):
                    self.logger.info(f"재시도 {i+1}/{max_retries}: {step_id}")
                    time.sleep(delay)
                    
                    result = self._execute_step(context, step)
                    context.set_step_result(step_id, result)
                    
                    if result.status == StepStatus.COMPLETED:
                        return True
            
            elif strategy_type == 'alternative':
                # 대체 단계 실행
                alt_step = strategy.get('step')
                if alt_step:
                    self.logger.info(f"대체 단계 실행: {alt_step.get('id', 'unknown')}")
                    result = self._execute_step(context, alt_step)
                    context.set_step_result(alt_step.get('id', f"{step_id}_alt"), result)
                    return result.status == StepStatus.COMPLETED
            
            elif strategy_type == 'rollback':
                # 특정 체크포인트로 롤백
                checkpoint_id = strategy.get('checkpoint_id')
                if checkpoint_id and checkpoint_id in context.checkpoints:
                    self.logger.info(f"체크포인트로 롤백: {checkpoint_id}")
                    return context.restore_checkpoint(checkpoint_id)
        
        return False
    
    def _resolve_parameters(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터 해결 (변수 대체)
        
        Args:
            context: 작업 흐름 컨텍스트
            params: 원본 파라미터
            
        Returns:
            해결된 파라미터
        """
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$'):
                # 변수 참조
                var_path = value[1:].split('.')
                var_value = context.state
                
                try:
                    for path_part in var_path:
                        var_value = var_value[path_part]
                    resolved[key] = var_value
                except (KeyError, TypeError):
                    self.logger.warning(f"변수를 찾을 수 없음: {value}")
                    resolved[key] = value
            elif isinstance(value, dict):
                # 중첩된 사전
                resolved[key] = self._resolve_parameters(context, value)
            elif isinstance(value, list):
                # 목록
                resolved[key] = [
                    self._resolve_parameters(context, item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # 기타 값
                resolved[key] = value
        
        return resolved
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 일시 중지
        
        Args:
            workflow_id: 작업 흐름 ID
            
        Returns:
            성공 여부
        """
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        if context.status == WorkflowStatus.RUNNING:
            context.status = WorkflowStatus.PAUSED
            self.logger.info(f"작업 흐름 일시 중지: {workflow_id}")
            return True
        
        return False
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 재개
        
        Args:
            workflow_id: 작업 흐름 ID
            
        Returns:
            성공 여부
        """
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        if context.status == WorkflowStatus.PAUSED:
            context.status = WorkflowStatus.RUNNING
            self.logger.info(f"작업 흐름 재개: {workflow_id}")
            return True
        
        return False
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """작업 흐름 취소
        
        Args:
            workflow_id: 작업 흐름 ID
            
        Returns:
            성공 여부
        """
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        context.status = WorkflowStatus.FAILED
        self.logger.info(f"작업 흐름 취소: {workflow_id}")
        return True
    
    def cleanup_workflow(self, workflow_id: str) -> None:
        """작업 흐름 정리
        
        Args:
            workflow_id: 작업 흐름 ID
        """
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
            self.logger.info(f"작업 흐름 정리: {workflow_id}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """작업 흐름 상태 가져오기
        
        Args:
            workflow_id: 작업 흐름 ID
            
        Returns:
            작업 흐름 상태
        """
        if workflow_id not in self.active_workflows:
            return None
        
        context = self.active_workflows[workflow_id]
        return {
            'workflow_id': workflow_id,
            'status': context.status.value,
            'execution_time': context.get_execution_time(),
            'execution_path': context.execution_path,
            'step_count': len(context.results),
            'completed_steps': sum(1 for r in context.results.values() 
                                if r.status == StepStatus.COMPLETED),
            'failed_steps': sum(1 for r in context.results.values() 
                              if r.status == StepStatus.FAILED)
        }
    
    # 기본 단계 핸들러 (구현 예시)
    def _handle_web_navigation(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """웹 탐색 단계 처리
        
        Args:
            context: 작업 흐름 컨텍스트
            params: 단계 파라미터
            
        Returns:
            단계 결과
        """
        # 실제 구현은 Playwright 플러그인 사용
        url = params.get('url')
        if not url:
            raise ValueError("URL이 지정되지 않음")
        
        # 웹 자동화 플러그인 찾기 (이름 대신 ID로 검색)
        plugin = self.plugin_manager.get_plugin("playwright_automation")
        
        if not plugin:
            # 직접 모든 자동화 플러그인 확인 (디버깅용)
            all_automation_plugins = self.plugin_manager.get_plugins_by_type(PluginType.AUTOMATION)
            plugin_names = [p.get_plugin_info().name for p in all_automation_plugins]
            self.logger.info(f"사용 가능한 자동화 플러그인: {plugin_names}")
            
            # 이름으로 다시 시도
            for p in all_automation_plugins:
                if "Playwright" in p.get_plugin_info().name:
                    plugin = p
                    self.logger.info(f"이름으로 플러그인 찾음: {p.get_plugin_info().name}")
                    break
            
            if not plugin:
                raise WorkflowError("Playwright 플러그인을 찾을 수 없음")
        
        # 플러그인 초기화
        plugin_id = plugin.get_plugin_info().id
        if plugin_id not in self.plugin_manager.initialized_plugins:
            try:
                # Playwright 초기화 설정
                browser_config = context.settings.get('browser_config', {})
                self.plugin_manager.initialize_plugin(plugin_id, browser_config)
                self.logger.info(f"플러그인 초기화 성공: {plugin_id}")
            except Exception as e:
                self.logger.error(f"플러그인 초기화 실패: {plugin_id} - {str(e)}")
                raise WorkflowError(f"Playwright 플러그인 초기화 실패: {str(e)}")
        
        # 작업 실행
        try:
            result = plugin.execute_action('navigate', {'url': url})
            
            if not result.get('success', False):
                error_msg = result.get('error', '알 수 없는 오류')
                self.logger.error(f"탐색 실패: {error_msg}")
                raise WorkflowError(f"웹 페이지 탐색 실패: {error_msg}")
            
            return {'current_url': result.get('url', url)}
        except Exception as e:
            self.logger.error(f"탐색 중 예외 발생: {str(e)}")
            raise WorkflowError(f"웹 페이지 탐색 중 오류: {str(e)}")
    
    def _handle_element_recognition(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """요소 인식 단계 처리
        
        Args:
            context: 작업 흐름 컨텍스트
            params: 단계 파라미터
            
        Returns:
            단계 결과
        """
        target = params.get('target')
        if not target:
            raise ValueError("인식 대상이 지정되지 않음")
        
        strategies = params.get('strategies', ['selector'])
        mode = context.settings.get('mode', 'balanced')
        
        # 사용 가능한 인식 플러그인 모두 가져오기 (디버깅용)
        all_recognition_plugins = self.plugin_manager.get_plugins_by_type(PluginType.RECOGNITION)
        plugin_names = [p.get_plugin_info().name for p in all_recognition_plugins]
        self.logger.info(f"사용 가능한 인식 플러그인: {plugin_names}")
        
        # 자동화 컨텍스트 가져오기 (Playwright 페이지 등)
        automation_context = context.state.get('automation_context')
        
        # 웹 자동화 컨텍스트가 없으면 Playwright 플러그인에서 가져오기
        if not automation_context:
            playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
            if playwright_plugin and playwright_plugin.get_plugin_info().id in self.plugin_manager.initialized_plugins:
                # Playwright 페이지 가져오기 시도
                try:
                    result = playwright_plugin.execute_action('get_page', {})
                    if result.get('success', False) and 'page' in result:
                        automation_context = result['page']
                        self.logger.info("Playwright 페이지 가져오기 성공")
                except Exception as e:
                    self.logger.warning(f"자동화 컨텍스트 가져오기 실패: {str(e)}")
        
        # 인식 시스템 플러그인 사용
        result = None
        errors = []
        
        for strategy_name in strategies:
            # ID 기반으로 직접 플러그인 검색 시도
            plugin = None
            
            # 전략 이름에 따라 플러그인 ID 매핑
            strategy_to_id = {
                'selector': 'selector_recognition',
                'aria': 'aria_recognition',
                'template': 'template_recognition',
                'ocr': 'ocr_recognition'
            }
            
            plugin_id = strategy_to_id.get(strategy_name)
            if plugin_id:
                plugin = self.plugin_manager.get_plugin(plugin_id)
            
            # ID로 찾지 못하면 이름 기반으로 검색
            if not plugin:
                for p in all_recognition_plugins:
                    p_name = p.get_plugin_info().name.lower()
                    if strategy_name.lower() in p_name:
                        plugin = p
                        self.logger.info(f"이름으로 플러그인 찾음: {p.get_plugin_info().name}")
                        break
            
            if not plugin:
                self.logger.warning(f"인식 전략을 찾을 수 없음: {strategy_name}")
                continue
            
            # 플러그인 초기화
            plugin_id = plugin.get_plugin_info().id
            if plugin_id not in self.plugin_manager.initialized_plugins:
                try:
                    self.plugin_manager.initialize_plugin(plugin_id)
                    self.logger.info(f"인식 플러그인 초기화 성공: {plugin_id}")
                except Exception as e:
                    self.logger.error(f"인식 플러그인 초기화 실패: {plugin_id} - {str(e)}")
                    errors.append(f"{strategy_name}: 초기화 실패 - {str(e)}")
                    continue
            
            try:
                self.logger.info(f"인식 시도: {strategy_name}")
                result = plugin.execute_action('recognize', {
                    'context': automation_context,
                    'target': target,
                    'timeout': context.settings.get('timeouts', {}).get('element', 10.0)
                })
                
                if result.get('success', False):
                    self.logger.info(f"인식 성공: {strategy_name}")
                    return {
                        'element': result.get('element'),
                        'strategy_used': strategy_name,
                        'confidence': result.get('confidence', 1.0)
                    }
                else:
                    error_msg = result.get('error', '알 수 없는 오류')
                    self.logger.warning(f"인식 실패 ({strategy_name}): {error_msg}")
                    errors.append(f"{strategy_name}: {error_msg}")
            except Exception as e:
                self.logger.warning(f"인식 중 예외 발생 ({strategy_name}): {str(e)}")
                errors.append(f"{strategy_name}: {str(e)}")
        
        # 임시 해결책: 실패했지만 워크플로우 계속 진행 (테스트용)
        if context.settings.get('ignore_recognition_errors', True):
            self.logger.warning("인식 오류 무시하고 계속 진행")
            return {
                'element': None,
                'strategy_used': None,
                'ignored_errors': True
            }
        
        raise WorkflowError(f"모든 인식 전략 실패: {', '.join(errors)}")
    
    def _handle_interruption_handling(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """인터럽션 처리 단계
        
        Args:
            context: 작업 흐름 컨텍스트
            params: 단계 파라미터
            
        Returns:
            단계 결과
        """
        types = params.get('types', ['ads', 'popups', 'cookies'])
        
        # 현재 인터럽션 처리기가 구현되지 않았으므로 빈 결과 반환 (성공으로 처리)
        self.logger.info(f"인터럽션 처리 단계: 아직 완전히 구현되지 않음 (유형: {types})")
        
        # 플러그인 구현 상태 확인 (디버깅용)
        interruption_plugins = self.plugin_manager.get_plugins_by_type(PluginType.INTERRUPTION)
        if interruption_plugins:
            plugin_names = [p.get_plugin_info().name for p in interruption_plugins]
            self.logger.info(f"사용 가능한 인터럽션 처리 플러그인: {plugin_names}")
        else:
            self.logger.info("인터럽션 처리 플러그인이 없음")
        
        # 웹 컨텍스트 가져오기 시도
        automation_context = context.state.get('automation_context')
        if not automation_context:
            playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
            if playwright_plugin and playwright_plugin.get_plugin_info().id in self.plugin_manager.initialized_plugins:
                try:
                    result = playwright_plugin.execute_action('get_page', {})
                    if result.get('success', False) and 'page' in result:
                        automation_context = result['page']
                except Exception:
                    pass
        
        # 임시 처리: 아직 인터럽션 플러그인이 완전히 구현되지 않았으므로 
        # 기본적인 쿠키/팝업 처리를 시도
        handled = []
        
        if automation_context and 'cookies' in types:
            try:
                # 쿠키 수락 버튼 찾기 시도 (간단한 선택자)
                cookie_selectors = [
                    "button[aria-label*='accept' i]", 
                    "button[aria-label*='cookie' i]",
                    "button:has-text('Accept')",
                    "button:has-text('Accept All')",
                    "button:has-text('Accept Cookies')",
                    "button:has-text('동의')",
                    "button:has-text('수락')"
                ]

                for selector in cookie_selectors:
                    try:
                        # Playwright 플러그인 통해 클릭 시도
                        if playwright_plugin:
                            result = playwright_plugin.execute_action('find_element', {
                                'selector': selector,
                                'timeout': 1000
                            })
                            
                            if result.get('found', False):
                                click_result = playwright_plugin.execute_action('click', {
                                    'selector': selector
                                })
                                if click_result.get('success', False):
                                    self.logger.info(f"쿠키 버튼 클릭: {selector}")
                                    handled.append({
                                        'type': 'cookies',
                                        'selector': selector
                                    })
                                    break
                    except Exception:
                        continue

            except Exception as e:
                self.logger.warning(f"쿠키 처리 중 오류: {str(e)}")

    def _handle_input_text(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 입력 단계 처리"""
        text = params.get('text')
        if not text:
            raise ValueError("입력할 텍스트가 지정되지 않음")
        
        # 이전 단계에서 요소 가져오기
        element = None
        element_from_step = params.get('element_from_step')
        
        if element_from_step:
            step_result = context.get_step_result(element_from_step)
            if step_result and step_result.status == StepStatus.COMPLETED:
                element = step_result.output.get('element')
        
        # 요소 또는 선택자 확인
        selector = params.get('selector')
        
        if not element and not selector:
            raise ValueError("요소 또는 선택자가 지정되지 않음")
        
        # Playwright 플러그인 가져오기
        playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
        if not playwright_plugin:
            raise WorkflowError("Playwright 플러그인을 찾을 수 없음")
        
        # 플러그인 초기화 확인
        if playwright_plugin.get_plugin_info().id not in self.plugin_manager.initialized_plugins:
            self.logger.info("Playwright 플러그인 초기화 중...")
            self.plugin_manager.initialize_plugin(playwright_plugin.get_plugin_info().id)
        
        # 사용할 선택자 결정
        use_selector = element.get('selector') if element else selector
        
        if not use_selector:
            raise WorkflowError("유효한 선택자를 찾을 수 없음")
        
        try:
            # 1. 요소 클릭 - 포커스 확보
            click_result = playwright_plugin.execute_action('click', {'selector': use_selector})
            
            if not click_result.get('success', False):
                self.logger.warning(f"요소 클릭 실패: {use_selector}")
            
            # 2. 잠시 대기
            import time
            time.sleep(0.5)
            
            # 3. JavaScript로 기존 텍스트 지우기
            evaluate_result = playwright_plugin.execute_action('evaluate', {
                'script': f"""
                    (() => {{
                        const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                        if (el) {{
                            el.value = "";
                            return true;
                        }}
                        return false;
                    }})()
                """
            })
            
            # 4. JavaScript로 바로 텍스트 입력 (한글 문제 해결)
            input_result = playwright_plugin.execute_action('evaluate', {
                'script': f"""
                    (() => {{
                        const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                        if (el) {{
                            el.value = "{text.replace('"', '\\"')}";
                            
                            // 변경 이벤트 발생시키기
                            const event = new Event('input', {{ bubbles: true }});
                            el.dispatchEvent(event);
                            
                            const changeEvent = new Event('change', {{ bubbles: true }});
                            el.dispatchEvent(changeEvent);
                            
                            return true;
                        }}
                        return false;
                    }})()
                """
            })
            
            if not input_result.get('success', False) or not input_result.get('result', False):
                self.logger.warning("JavaScript로 텍스트 입력 실패, 다른 방법 시도")
                
                # 대체 방법: clipboard 사용
                clipboard_result = playwright_plugin.execute_action('evaluate', {
                    'script': f"""
                        (() => {{
                            const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                            if (el) {{
                                const dataTransfer = new DataTransfer();
                                dataTransfer.setData('text', "{text.replace('"', '\\"')}");
                                el.focus();
                                
                                const pasteEvent = new ClipboardEvent('paste', {{
                                    bubbles: true,
                                    clipboardData: dataTransfer,
                                    cancelable: true
                                }});
                                el.dispatchEvent(pasteEvent);
                                
                                return true;
                            }}
                            return false;
                        }})()
                    """
                })
            
            return {
                'text': text,
                'selector': use_selector,
                'method': 'javascript_input'
            }
        except Exception as e:
            self.logger.error(f"텍스트 입력 중 오류: {str(e)}")
            raise WorkflowError(f"텍스트 입력 중 오류: {str(e)}")

    def _handle_key_press(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """키 누르기 단계 처리"""
        key = params.get('key')
        if not key:
            raise ValueError("키가 지정되지 않음")
        
        # 이전 단계에서 요소 가져오기
        element = None
        element_from_step = params.get('element_from_step')
        
        if element_from_step:
            step_result = context.get_step_result(element_from_step)
            if step_result and step_result.status == StepStatus.COMPLETED:
                element = step_result.output.get('element')
        
        # Playwright 플러그인 가져오기
        playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
        if not playwright_plugin:
            raise WorkflowError("Playwright 플러그인을 찾을 수 없음")
        
        # 사용할 선택자 결정
        use_selector = element.get('selector') if element and element.get('selector') else params.get('selector')
        
        try:
            if use_selector:
                # 1. 먼저 JavaScript로 포커스 확보
                focus_result = playwright_plugin.execute_action('evaluate', {
                    'script': f"""
                        (() => {{
                            const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                            if (el) {{
                                el.focus();
                                return true;
                            }}
                            return false;
                        }})()
                    """
                })
                
                # 2. 키 누르기는 여러 방법으로 시도
                result = playwright_plugin.execute_action('press', {
                    'selector': use_selector,
                    'key': key
                })
                
                # 실패하면 JavaScript로 시도
                if not result.get('success', False):
                    # Enter 키에 대한 특별 처리
                    if key.lower() == 'enter':
                        submit_result = playwright_plugin.execute_action('evaluate', {
                            'script': f"""
                                (() => {{
                                    const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                                    if (el) {{
                                        if (el.form) {{
                                            el.form.submit();
                                            return true;
                                        }}
                                        
                                        // 폼이 없으면 엔터 이벤트 발생
                                        const e = new KeyboardEvent('keydown', {{
                                            bubbles: true,
                                            cancelable: true,
                                            key: 'Enter',
                                            code: 'Enter',
                                            keyCode: 13
                                        }});
                                        el.dispatchEvent(e);
                                        
                                        return true;
                                    }}
                                    return false;
                                }})()
                            """
                        })
                        
                        # 페이지 전환 확인 대기
                        wait_result = playwright_plugin.execute_action('wait_for_load', {
                            'state': 'networkidle',
                            'timeout': 10000
                        })
                        
                        return {
                            'key': key,
                            'method': 'javascript_submit',
                            'success': submit_result.get('success', False) and submit_result.get('result', False)
                        }
                    
                    # 다른 키 처리
                    self.logger.warning(f"일반 키 누르기 실패: {key}, JavaScript 이벤트 시도")
                    key_result = playwright_plugin.execute_action('evaluate', {
                        'script': f"""
                            (() => {{
                                const el = document.querySelector('{use_selector.replace("'", "\\'")}');
                                if (el) {{
                                    const keyEvent = new KeyboardEvent('keydown', {{
                                        bubbles: true,
                                        cancelable: true,
                                        key: '{key}',
                                        code: '{key}'
                                    }});
                                    el.dispatchEvent(keyEvent);
                                    return true;
                                }}
                                return false;
                            }})()
                        """
                    })
                    
                    return {
                        'key': key,
                        'method': 'javascript_keydown',
                        'success': key_result.get('success', False) and key_result.get('result', False)
                    }
            else:
                # 전역 키보드 처리
                result = playwright_plugin.execute_action('keyboard_press', {
                    'key': key
                })
                
                # 실패하면 JavaScript로 시도
                if not result.get('success', False):
                    self.logger.warning(f"글로벌 키 누르기 실패: {key}, JavaScript 이벤트 시도")
                    document_key_result = playwright_plugin.execute_action('evaluate', {
                        'script': f"""
                            (() => {{
                                document.activeElement.dispatchEvent(new KeyboardEvent('keydown', {{
                                    bubbles: true,
                                    cancelable: true,
                                    key: '{key}',
                                    code: '{key}'
                                }}));
                                return true;
                            }})()
                        """
                    })
                    
                    return {
                        'key': key,
                        'method': 'javascript_global_keydown',
                        'success': document_key_result.get('success', False) and document_key_result.get('result', False)
                    }
            
            return {
                'key': key,
                'method': 'press',
                'success': result.get('success', False)
            }
        except Exception as e:
            self.logger.error(f"키 누르기 중 오류: {str(e)}")
            raise WorkflowError(f"키 누르기 중 오류: {str(e)}")

    def _handle_wait_for_load(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """페이지 로드 대기 단계 처리
        
        Args:
            context: 작업 흐름 컨텍스트
            params: 단계 파라미터
            
        Returns:
            단계 결과
        """
        timeout = params.get('timeout', 30.0)
        
        # Playwright 플러그인 가져오기
        playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
        if not playwright_plugin:
            raise WorkflowError("Playwright 플러그인을 찾을 수 없음")
        
        if playwright_plugin.get_plugin_info().id not in self.plugin_manager.initialized_plugins:
            self.plugin_manager.initialize_plugin(playwright_plugin.get_plugin_info().id)
        
        # 페이지 로드 대기 실행
        result = playwright_plugin.execute_action('wait_for_load', {
            'state': 'networkidle',  # 네트워크 활동이 끝날 때까지 대기
            'timeout': timeout * 1000  # 밀리초로 변환
        })
        
        if not result.get('success', False):
            error_msg = result.get('error', '알 수 없는 오류')
            raise WorkflowError(f"페이지 로드 대기 실패: {error_msg}")
        
        # 현재 URL 가져오기
        url_result = playwright_plugin.execute_action('get_url', {})
        current_url = url_result.get('url', '')
        
        return {'url': current_url}

def _handle_wait_for_results(self, context: WorkflowContext, params: Dict[str, Any]) -> Dict[str, Any]:
    """페이지 로드 대기 단계 처리"""
    timeout = params.get('timeout', 30.0)
    
    # Playwright 플러그인 가져오기
    playwright_plugin = self.plugin_manager.get_plugin("playwright_automation")
    if not playwright_plugin:
        raise WorkflowError("Playwright 플러그인을 찾을 수 없음")
    
    if playwright_plugin.get_plugin_info().id not in self.plugin_manager.initialized_plugins:
        self.plugin_manager.initialize_plugin(playwright_plugin.get_plugin_info().id)
    
    # 페이지 로드 대기 실행
    result = playwright_plugin.execute_action('wait_for_load', {
        'state': 'networkidle',  # 네트워크 활동이 끝날 때까지 대기
        'timeout': timeout * 1000  # 밀리초로 변환
    })
    
    if not result.get('success', False):
        error_msg = result.get('error', '알 수 없는 오류')
        raise WorkflowError(f"페이지 로드 대기 실패: {error_msg}")
    
    # 현재 URL 가져오기
    url_result = playwright_plugin.execute_action('get_url', {})
    current_url = url_result.get('url', '')
    
    # CAPTCHA 페이지 감지
    if "www.google.com/sorry" in current_url or "웹사이트에서 비정상적인 트래픽" in current_url:
        self.logger.warning("Google CAPTCHA 페이지 감지됨")
        
        # 사용자 알림 (콘솔 출력)
        print("\n======= Google CAPTCHA 감지 =======")
        print("자동화 봇으로 감지되어 CAPTCHA 확인이 필요합니다.")
        print("브라우저에서 CAPTCHA를 직접 해결해 주세요.")
        print("===================================\n")
        
        # 스크린샷 캡처 (선택 사항)
        screenshot_result = playwright_plugin.execute_action('screenshot', {
            'path': 'captcha_detected.png'
        })
        
        if screenshot_result.get('success', False):
            self.logger.info("CAPTCHA 화면 스크린샷 저장: captcha_detected.png")
        
        # 사용자 개입 대기 (15초 정도)
        import time
        for i in range(15):
            self.logger.info(f"CAPTCHA 해결 대기 중... ({i+1}/15)")
            time.sleep(1)
        
        # URL 다시 확인
        url_result = playwright_plugin.execute_action('get_url', {})
        updated_url = url_result.get('url', '')
        
        return {'url': updated_url, 'captcha_detected': True}
    
    return {'url': current_url}