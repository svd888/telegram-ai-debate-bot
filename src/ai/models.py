"""
Модели данных для AI дебатов
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    """Ответ от AI модели"""
    model_key: str
    model_name: str
    content: str
    confidence: Optional[float] = None  # 0-100%
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_used: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DebateRound(BaseModel):
    """Раунд дебатов"""
    round_number: int
    responses: List[AIResponse] = []
    summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DebateSession(BaseModel):
    """Сессия дебатов"""
    session_id: str
    user_id: int
    question: str
    mode: str  # quick, standard, deep
    rounds: List[DebateRound] = []
    final_answer: Optional[str] = None
    final_confidence: Optional[float] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_tokens: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_round(self, round_data: DebateRound):
        """Добавить раунд дебатов"""
        self.rounds.append(round_data)
    
    def complete(self, final_answer: str, confidence: float):
        """Завершить сессию дебатов"""
        self.final_answer = final_answer
        self.final_confidence = confidence
        self.completed_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return self.model_dump()


class OpenRouterRequest(BaseModel):
    """Запрос к OpenRouter API"""
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.2
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


class OpenRouterResponse(BaseModel):
    """Ответ от OpenRouter API"""
    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    
    def get_content(self) -> str:
        """Получить текст ответа"""
        if self.choices and len(self.choices) > 0:
            return self.choices[0].get('message', {}).get('content', '')
        return ''
    
    def get_tokens_used(self) -> int:
        """Получить количество использованных токенов"""
        if self.usage:
            return self.usage.get('total_tokens', 0)
        return 0
