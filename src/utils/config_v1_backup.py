"""
Модуль конфигурации для Telegram AI Debate Bot
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Конфигурация AI модели"""
    name: str
    id: str
    description: str
    color: str
    temperature: float = 0.2
    max_tokens: int = 4096


class DebateModeConfig(BaseModel):
    """Конфигурация режима дебатов"""
    name: str
    rounds: int
    description: str


class OpenRouterConfig(BaseModel):
    """Конфигурация OpenRouter"""
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: int = 2


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    telegram_bot_token: str = Field(..., env='TELEGRAM_BOT_TOKEN')
    openrouter_api_key: str = Field(..., env='OPENROUTER_API_KEY')
    default_debate_rounds: int = Field(3, env='DEFAULT_DEBATE_ROUNDS')
    default_temperature: float = Field(0.2, env='DEFAULT_TEMPERATURE')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    database_url: str = Field('sqlite:///data/bot.db', env='DATABASE_URL')
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = 'utf-8'


class Config:
    """Главный класс конфигурации"""
    
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
        
        # Модели
        self.models: Dict[str, ModelConfig] = {
            key: ModelConfig(**value)
            for key, value in config_data['models'].items()
        }
        
        # Режимы дебатов
        self.debate_modes: Dict[str, DebateModeConfig] = {
            key: DebateModeConfig(**value)
            for key, value in config_data['debate_modes'].items()
        }
        
        # Системные промпты
        self.system_prompts: Dict[str, str] = config_data['system_prompts']
        
        # OpenRouter настройки
        self.openrouter = OpenRouterConfig(**config_data['openrouter'])
    
    def get_model_config(self, model_key: str) -> ModelConfig:
        """Получить конфигурацию модели по ключу"""
        return self.models.get(model_key)
    
    def get_all_models(self) -> Dict[str, ModelConfig]:
        """Получить все модели"""
        return self.models
    
    def get_debate_mode(self, mode: str) -> DebateModeConfig:
        """Получить конфигурацию режима дебатов"""
        return self.debate_modes.get(mode, self.debate_modes['standard'])
    
    def get_system_prompt(self, prompt_type: str, **kwargs) -> str:
        """Получить системный промпт с подстановкой параметров"""
        prompt = self.system_prompts.get(prompt_type, '')
        return prompt.format(**kwargs) if kwargs else prompt


# Глобальный экземпляр конфигурации
config = Config()
