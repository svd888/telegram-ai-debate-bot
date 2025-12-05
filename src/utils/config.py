"""
Модуль конфигурации для Telegram AI Debate Bot v2.0
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    telegram_bot_token: str = Field(..., env='TELEGRAM_BOT_TOKEN')
    openrouter_api_key: str = Field(..., env='OPENROUTER_API_KEY')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = 'utf-8'


class ConfigV2:
    """Главный класс конфигурации v2.0"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_path = self.base_dir / config_path
        
        # Загрузка настроек из .env
        self.settings = Settings()
        
        # Загрузка конфигурации из YAML
        self._load_yaml_config()
    
    def _load_yaml_config(self):
        """Загрузка конфигурации из YAML файла"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Сохраняем все данные как есть
        self.models = config_data['models']
        self.debate_modes = config_data['debate_modes']
        self.prompts = config_data['prompts']
        self.openrouter = config_data['openrouter']
        self.logging = config_data.get('logging', {})
        self.paths = config_data.get('paths', {})
    
    def get_model_config(self, model_key: str) -> Dict[str, Any]:
        """Получить конфигурацию модели по ключу"""
        return self.models.get(model_key)
    
    def get_all_models(self) -> Dict[str, Dict[str, Any]]:
        """Получить все модели"""
        return self.models
    
    def get_debate_mode(self, mode: str) -> Dict[str, Any]:
        """Получить конфигурацию режима дебатов"""
        return self.debate_modes.get(mode, self.debate_modes['standard'])
    
    def get_prompt(self, prompt_type: str) -> str:
        """Получить промпт по типу"""
        return self.prompts.get(prompt_type, '')


# Глобальный экземпляр конфигурации
config = ConfigV2()
