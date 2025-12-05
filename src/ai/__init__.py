"""AI модули для дебатов"""
from .models import AIResponse, DebateRound, DebateSession
from .openrouter_client import openrouter_client, OpenRouterClient
from .debate_manager import debate_manager, DebateManager

__all__ = [
    'AIResponse',
    'DebateRound',
    'DebateSession',
    'openrouter_client',
    'OpenRouterClient',
    'debate_manager',
    'DebateManager'
]
