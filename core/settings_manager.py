 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 통합 자동화 시스템 - 설정 관리자
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import copy

logger = logging.getLogger(__name__)

class SettingsManager:
    """
    설정 관리자 - 시스템 및 플러그인 설정의 저장, 로드 및 관리를 담당
    """
    
    DEFAULT_SETTINGS = {
        "system": {
            "headless_mode": False,
            "log_level": "INFO",
            "checkpoint_dir": "",
            "max_retries": 3,
            "auto_recovery": True
        },
        "plugins": {},
        "automation": {
            "default_timeout": 60.0,
            "default_retry_delay": 2.0,
            "screenshot_on_error": True,
            "browser_type": "chromium"
        },
        "interruption": {
            "enabled": True,
            "popup_handling": True,
            "ad_blocking": True,
            "cookie_handling": True,
            "max_interruptions": 10,
            "whitelist": [],
            "blacklist": []
        },
        "ui": {
            "theme": "light",
            "language": "ko",
            "font_size": 12,
            "show_detailed_logs": True
        },
        "favorites": []
    }
    
    def __init__(self, settings_file: str = None):
        """설정 관리자 초기화"""
        # 기본 설정 파일 경로
        if settings_file is None:
            home_dir = Path.home()
            settings_dir = home_dir / "BlueAI" / "config"
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = settings_dir / "settings.json"
        
        self.settings_file = str(settings_file)
        self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)
        self.observers = []
        
        # 설정 로드 시도
        self.load_settings()
    
    def load_settings(self) -> bool:
        """설정 파일에서 설정 로드"""
        if not os.path.exists(self.settings_file):
            logger.info(f"설정 파일이 없습니다. 기본 설정을 사용합니다: {self.settings_file}")
            self.save_settings()  # 기본 설정 저장
            return True
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
            
            # 설정 병합 (깊은 병합)
            self._deep_merge(self.settings, loaded_settings)
            logger.info(f"설정 로드됨: {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"설정 로드 중 오류: {str(e)}")
            return False
    
    def _deep_merge(self, target: Dict, source: Dict):
        """두 딕셔너리를 깊은 병합 (재귀적으로 모든 수준의 키 병합)"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = copy.deepcopy(value)
    
    def save_settings(self) -> bool:
        """설정을 파일에 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            
            logger.info(f"설정 저장됨: {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"설정 저장 중 오류: {str(e)}")
            return False
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """설정 값 가져오기"""
        if section not in self.settings:
            return default
        
        if key is None:
            return copy.deepcopy(self.settings[section])
        
        return copy.deepcopy(self.settings[section].get(key, default))
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """설정 값 설정"""
        # 섹션이 없으면 생성
        if section not in self.settings:
            self.settings[section] = {}
        
        # 값이 변경되었는지 확인
        changed = section not in self.settings or key not in self.settings[section] or self.settings[section][key] != value
        
        # 값 설정
        self.settings[section][key] = copy.deepcopy(value)
        
        # 변경되었으면 옵저버 호출
        if changed:
            self._notify_observers(section, key, value)
        
        return changed
    
    def set_plugin_settings(self, plugin_type: str, plugin_name: str, settings: Dict[str, Any]) -> bool:
        """플러그인 설정 설정"""
        plugin_key = f"{plugin_type}.{plugin_name}"
        
        # plugins 섹션이 없으면 생성
        if "plugins" not in self.settings:
            self.settings["plugins"] = {}
        
        # 기존 설정 가져오기
        current_settings = self.settings["plugins"].get(plugin_key, {})
        
        # 변경 여부 확인
        changed = current_settings != settings
        
        # 설정 업데이트
        self.settings["plugins"][plugin_key] = copy.deepcopy(settings)
        
        # 변경되었으면 옵저버 호출
        if changed:
            self._notify_observers("plugins", plugin_key, settings)
        
        return changed
    
    def get_plugin_settings(self, plugin_type: str, plugin_name: str) -> Dict[str, Any]:
        """플러그인 설정 가져오기"""
        plugin_key = f"{plugin_type}.{plugin_name}"
        
        if "plugins" not in self.settings:
            return {}
        
        return copy.deepcopy(self.settings["plugins"].get(plugin_key, {}))
    
    def delete(self, section: str, key: str = None) -> bool:
        """설정 삭제"""
        if section not in self.settings:
            return False
        
        if key is None:
            # 섹션 전체 삭제
            del self.settings[section]
            self._notify_observers(section, None, None)
            return True
        
        if key not in self.settings[section]:
            return False
        
        # 키 삭제
        del self.settings[section][key]
        self._notify_observers(section, key, None)
        return True
    
    def reset_to_defaults(self, section: str = None) -> bool:
        """설정을 기본값으로 재설정"""
        if section is None:
            # 모든 설정 재설정
            self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)
            self._notify_observers(None, None, None)
            return True
        
        if section not in self.DEFAULT_SETTINGS:
            return False
        
        # 특정 섹션만 재설정
        self.settings[section] = copy.deepcopy(self.DEFAULT_SETTINGS[section])
        self._notify_observers(section, None, None)
        return True
    
    def get_sections(self) -> List[str]:
        """모든 설정 섹션 반환"""
        return list(self.settings.keys())
    
    def get_keys(self, section: str) -> List[str]:
        """특정 섹션의 모든 키 반환"""
        if section not in self.settings:
            return []
        
        return list(self.settings[section].keys())
    
    def register_observer(self, observer) -> None:
        """설정 변경 옵저버 등록"""
        if observer not in self.observers:
            self.observers.append(observer)
    
    def unregister_observer(self, observer) -> bool:
        """설정 변경 옵저버 제거"""
        if observer in self.observers:
            self.observers.remove(observer)
            return True
        return False
    
    def _notify_observers(self, section: str, key: str, value: Any) -> None:
        """옵저버에게 설정 변경 알림"""
        for observer in self.observers:
            try:
                if hasattr(observer, 'on_settings_changed'):
                    observer.on_settings_changed(section, key, value)
            except Exception as e:
                logger.error(f"옵저버 알림 중 오류: {str(e)}")
    
    def get_whitelist_domains(self) -> Set[str]:
        """인터럽션 화이트리스트 도메인 가져오기"""
        whitelist = self.get("interruption", "whitelist", [])
        return set(whitelist)
    
    def add_to_whitelist(self, domain: str) -> bool:
        """인터럽션 화이트리스트에 도메인 추가"""
        whitelist = set(self.get("interruption", "whitelist", []))
        if domain in whitelist:
            return False
        
        whitelist.add(domain)
        return self.set("interruption", "whitelist", list(whitelist))
    
    def remove_from_whitelist(self, domain: str) -> bool:
        """인터럽션 화이트리스트에서 도메인 제거"""
        whitelist = set(self.get("interruption", "whitelist", []))
        if domain not in whitelist:
            return False
        
        whitelist.remove(domain)
        return self.set("interruption", "whitelist", list(whitelist))
    
    def get_blacklist_domains(self) -> Set[str]:
        """인터럽션 블랙리스트 도메인 가져오기"""
        blacklist = self.get("interruption", "blacklist", [])
        return set(blacklist)
    
    def add_to_blacklist(self, domain: str) -> bool:
        """인터럽션 블랙리스트에 도메인 추가"""
        blacklist = set(self.get("interruption", "blacklist", []))
        if domain in blacklist:
            return False
        
        blacklist.add(domain)
        return self.set("interruption", "blacklist", list(blacklist))
    
    def remove_from_blacklist(self, domain: str) -> bool:
        """인터럽션 블랙리스트에서 도메인 제거"""
        blacklist = set(self.get("interruption", "blacklist", []))
        if domain not in blacklist:
            return False
        
        blacklist.remove(domain)
        return self.set("interruption", "blacklist", list(blacklist))
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """즐겨찾기 목록 가져오기"""
        return self.get("favorites", default=[])
    
    def add_favorite(self, name: str, command: str, description: str = "") -> bool:
        """즐겨찾기 추가"""
        favorites = self.get_favorites()
        
        # 이미 존재하는지 확인
        for favorite in favorites:
            if favorite.get("name") == name:
                return False
        
        favorites.append({
            "name": name,
            "command": command,
            "description": description
        })
        
        return self.set("favorites", None, favorites)
    
    def remove_favorite(self, name: str) -> bool:
        """즐겨찾기 제거"""
        favorites = self.get_favorites()
        original_count = len(favorites)
        
        favorites = [f for f in favorites if f.get("name") != name]
        
        if len(favorites) == original_count:
            return False
        
        return self.set("favorites", None, favorites)
    
    def update_favorite(self, name: str, command: str = None, description: str = None) -> bool:
        """즐겨찾기 업데이트"""
        favorites = self.get_favorites()
        
        for i, favorite in enumerate(favorites):
            if favorite.get("name") == name:
                if command is not None:
                    favorite["command"] = command
                if description is not None:
                    favorite["description"] = description
                
                favorites[i] = favorite
                return self.set("favorites", None, favorites)
        
        return False