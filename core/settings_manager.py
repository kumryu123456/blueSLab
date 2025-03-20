"""
설정 관리 모듈

이 모듈은 자동화 시스템의 설정을 관리합니다.
사용자 설정, 작업 모드, 로컬 즐겨찾기 등을 저장하고 로드합니다.
"""
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class AutomationMode(Enum):
    """자동화 모드"""
    SPEED = "speed"  # 속도 우선
    BALANCED = "balanced"  # 균형
    ACCURACY = "accuracy"  # 정확도 우선


@dataclass
class FavoriteTask:
    """즐겨찾기 작업"""
    id: str  # 작업 ID
    name: str  # 작업 이름
    description: str  # 작업 설명
    command: str  # 자연어 명령
    created_at: float  # 생성 시간
    last_used_at: float  # 마지막 사용 시간
    usage_count: int = 0  # 사용 횟수
    tags: List[str] = field(default_factory=list)  # 태그


class SettingsManager:
    """설정 관리자"""
    
    def __init__(self, settings_dir: str = None, logger=None):
        """설정 관리자 초기화
        
        Args:
            settings_dir: 설정 디렉토리
            logger: 로거 객체
        """
        self.settings_dir = settings_dir or os.path.join(os.path.expanduser("~"), ".blueai")
        self.logger = logger or logging.getLogger(__name__)
        
        # 설정 디렉토리 생성
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # 설정 파일 경로
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        self.favorites_file = os.path.join(self.settings_dir, "favorites.json")
        
        # 설정 로드
        self.settings = self._load_settings()
        self.favorites = self._load_favorites()
    
    def _load_settings(self) -> Dict[str, Any]:
        """설정 로드"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'mode': AutomationMode.BALANCED.value,
            'interruptions': {
                'enabled': True,
                'ads': True,
                'popups': True,
                'cookies': True,
                'login_prompts': False,
                'surveys': False,
                'notifications': True
            },
            'recognition': {
                'selectors': True,
                'aria': True,
                'template_matching': True,
                'ocr': True
            },
            'timeouts': {
                'navigation': 30.0,
                'element': 10.0,
                'action': 5.0
            },
            'retries': {
                'action': 3,
                'step': 2
            },
            'logging': {
                'level': 'INFO',
                'file_enabled': True,
                'max_files': 5,
                'max_size_mb': 10
            },
            'ui': {
                'theme': 'system',
                'compact_mode': False,
                'show_notifications': True
            },
            'proxy': {
                'enabled': False,
                'url': '',
                'auth': {
                    'username': '',
                    'password': ''
                }
            },
            'plugins': {
                'enabled': [],
                'disabled': []
            }
        }
    
    def _load_favorites(self) -> Dict[str, FavoriteTask]:
        """즐겨찾기 로드"""
        favorites = {}
        
        try:
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for item in data:
                    try:
                        task = FavoriteTask(
                            id=item['id'],
                            name=item['name'],
                            description=item['description'],
                            command=item['command'],
                            created_at=item['created_at'],
                            last_used_at=item['last_used_at'],
                            usage_count=item.get('usage_count', 0),
                            tags=item.get('tags', [])
                        )
                        favorites[task.id] = task
                    except KeyError as e:
                        self.logger.warning(f"즐겨찾기 항목 로드 오류: {e}")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        return favorites
    
    def save_settings(self) -> None:
        """설정 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.debug("설정 저장 완료")
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {str(e)}")
    
    def save_favorites(self) -> None:
        """즐겨찾기 저장"""
        try:
            data = [asdict(task) for task in self.favorites.values()]
            
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("즐겨찾기 저장 완료")
        except Exception as e:
            self.logger.error(f"즐겨찾기 저장 실패: {str(e)}")
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """설정 값 가져오기
        
        Args:
            path: 설정 경로 (점으로 구분)
            default: 기본값
            
        Returns:
            설정 값
        """
        parts = path.split('.')
        value = self.settings
        
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, path: str, value: Any) -> None:
        """설정 값 설정
        
        Args:
            path: 설정 경로 (점으로 구분)
            value: 설정 값
        """
        parts = path.split('.')
        target = self.settings
        
        # 마지막 부분을 제외한 경로 탐색
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        # 마지막 부분에 값 설정
        target[parts[-1]] = value
        
        # 설정 저장
        self.save_settings()
    
    def get_mode(self) -> AutomationMode:
        """현재 자동화 모드 가져오기
        
        Returns:
            자동화 모드
        """
        mode_str = self.get_setting('mode', AutomationMode.BALANCED.value)
        try:
            return AutomationMode(mode_str)
        except ValueError:
            return AutomationMode.BALANCED
    
    def set_mode(self, mode: Union[str, AutomationMode]) -> None:
        """자동화 모드 설정
        
        Args:
            mode: 자동화 모드
        """
        if isinstance(mode, AutomationMode):
            mode = mode.value
        
        try:
            AutomationMode(mode)  # 유효성 검사
            self.set_setting('mode', mode)
        except ValueError:
            self.logger.warning(f"유효하지 않은 모드: {mode}")
    
    def add_favorite(self, task: FavoriteTask) -> bool:
        """즐겨찾기 추가
        
        Args:
            task: 즐겨찾기 작업
            
        Returns:
            성공 여부
        """
        if task.id in self.favorites:
            return False
        
        self.favorites[task.id] = task
        self.save_favorites()
        
        return True
    
    def remove_favorite(self, task_id: str) -> bool:
        """즐겨찾기 제거
        
        Args:
            task_id: 작업 ID
            
        Returns:
            성공 여부
        """
        if task_id not in self.favorites:
            return False
        
        del self.favorites[task_id]
        self.save_favorites()
        
        return True
    
    def update_favorite(self, task: FavoriteTask) -> bool:
        """즐겨찾기 업데이트
        
        Args:
            task: 즐겨찾기 작업
            
        Returns:
            성공 여부
        """
        if task.id not in self.favorites:
            return False
        
        self.favorites[task.id] = task
        self.save_favorites()
        
        return True
    
    def get_favorite(self, task_id: str) -> Optional[FavoriteTask]:
        """즐겨찾기 가져오기
        
        Args:
            task_id: 작업 ID
            
        Returns:
            즐겨찾기 작업
        """
        return self.favorites.get(task_id)
    
    def get_favorites(self, tag: str = None) -> List[FavoriteTask]:
        """모든 즐겨찾기 가져오기
        
        Args:
            tag: 태그 필터 (선택 사항)
            
        Returns:
            즐겨찾기 작업 목록
        """
        if tag:
            return [task for task in self.favorites.values() if tag in task.tags]
        else:
            return list(self.favorites.values())
    
    def search_favorites(self, query: str) -> List[FavoriteTask]:
        """즐겨찾기 검색
        
        Args:
            query: 검색어
            
        Returns:
            일치하는 즐겨찾기 작업 목록
        """
        query = query.lower()
        results = []
        
        for task in self.favorites.values():
            if (query in task.name.lower() or
                query in task.description.lower() or
                query in task.command.lower() or
                any(query in tag.lower() for tag in task.tags)):
                results.append(task)
        
        return results
    
    def increment_favorite_usage(self, task_id: str) -> bool:
        """즐겨찾기 사용 횟수 증가
        
        Args:
            task_id: 작업 ID
            
        Returns:
            성공 여부
        """
        task = self.get_favorite(task_id)
        if not task:
            return False
        
        import time
        task.usage_count += 1
        task.last_used_at = time.time()
        
        self.save_favorites()
        
        return True
    
    def get_timeout(self, timeout_type: str) -> float:
        """타임아웃 값 가져오기
        
        Args:
            timeout_type: 타임아웃 유형
            
        Returns:
            타임아웃 값(초)
        """
        timeouts = self.get_setting('timeouts', {})
        
        if timeout_type in timeouts:
            return float(timeouts[timeout_type])
        
        # 기본값
        defaults = {
            'navigation': 30.0,
            'element': 10.0,
            'action': 5.0
        }
        
        return defaults.get(timeout_type, 5.0)
    
    def get_retry_count(self, retry_type: str) -> int:
        """재시도 횟수 가져오기
        
        Args:
            retry_type: 재시도 유형
            
        Returns:
            재시도 횟수
        """
        retries = self.get_setting('retries', {})
        
        if retry_type in retries:
            return int(retries[retry_type])
        
        # 기본값
        defaults = {
            'action': 3,
            'step': 2
        }
        
        return defaults.get(retry_type, 1)
    
    def is_feature_enabled(self, feature_path: str) -> bool:
        """기능 활성화 여부 확인
        
        Args:
            feature_path: 기능 경로
            
        Returns:
            활성화 여부
        """
        return bool(self.get_setting(feature_path, False))
    
    def get_mode_timeout_multiplier(self) -> float:
        """현재 모드에 따른 타임아웃 승수 가져오기
        
        Returns:
            타임아웃 승수
        """
        mode = self.get_mode()
        
        if mode == AutomationMode.SPEED:
            return 0.5
        elif mode == AutomationMode.ACCURACY:
            return 2.0
        else:  # BALANCED
            return 1.0
    
    def get_effective_timeout(self, timeout_type: str) -> float:
        """모드에 따른 실효 타임아웃 가져오기
        
        Args:
            timeout_type: 타임아웃 유형
            
        Returns:
            실효 타임아웃 값(초)
        """
        base_timeout = self.get_timeout(timeout_type)
        multiplier = self.get_mode_timeout_multiplier()
        
        return base_timeout * multiplier
    
    def export_settings(self) -> Dict[str, Any]:
        """설정 내보내기
        
        Returns:
            설정 데이터
        """
        return {
            'settings': self.settings,
            'favorites': [asdict(task) for task in self.favorites.values()]
        }
    
    def import_settings(self, data: Dict[str, Any]) -> bool:
        """설정 가져오기
        
        Args:
            data: 설정 데이터
            
        Returns:
            성공 여부
        """
        try:
            if 'settings' in data:
                self.settings = data['settings']
                self.save_settings()
            
            if 'favorites' in data:
                self.favorites = {}
                for item in data['favorites']:
                    try:
                        task = FavoriteTask(
                            id=item['id'],
                            name=item['name'],
                            description=item['description'],
                            command=item['command'],
                            created_at=item['created_at'],
                            last_used_at=item['last_used_at'],
                            usage_count=item.get('usage_count', 0),
                            tags=item.get('tags', [])
                        )
                        self.favorites[task.id] = task
                    except KeyError:
                        continue
                
                self.save_favorites()
            
            return True
        except Exception as e:
            self.logger.error(f"설정 가져오기 실패: {str(e)}")
            return False
    
    def reset_to_defaults(self) -> None:
        """기본 설정으로 초기화"""
        self.settings = self._get_default_settings()
        self.save_settings()