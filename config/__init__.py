"""프로젝트 설정 관리 모듈"""

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "settings.json")


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """JSON 설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        설정 딕셔너리
        
    Raises:
        FileNotFoundError: 설정 파일이 없는 경우
        json.JSONDecodeError: 설정 파일 형식이 잘못된 경우
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """설정을 로드하거나 캐시된 설정을 반환합니다.
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        설정 딕셔너리
    """
    return load_config(config_path)
