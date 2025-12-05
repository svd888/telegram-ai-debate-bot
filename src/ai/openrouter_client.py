"""
Клиент для работы с OpenRouter API
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
from utils import config, log
from ai.models import OpenRouterRequest, OpenRouterResponse, AIResponse


class OpenRouterClient:
    """Клиент для взаимодействия с OpenRouter API"""
    
    def __init__(self):
        self.api_key = config.settings.openrouter_api_key
        self.base_url = config.openrouter['base_url']
        self.timeout = config.openrouter['timeout']
        self.retry_attempts = config.openrouter['retry_attempts']
        self.retry_delay = config.openrouter['retry_delay']
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/telegram-ai-debate-bot',
            'X-Title': 'Telegram AI Debate Bot'
        }
    
    async def _make_request(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        reasoning: str = "high",
        verbosity: str = "high"
    ) -> Optional[OpenRouterResponse]:
        """
        Выполнить запрос к OpenRouter API
        
        Args:
            model_id: ID модели в OpenRouter
            messages: Список сообщений для модели
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Ответ от API или None в случае ошибки
        """
        # Подготовка данных запроса с reasoning параметрами
        request_dict = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Добавляем reasoning параметры если модель поддерживает
        if reasoning:
            request_dict["reasoning_effort"] = reasoning
        if verbosity:
            request_dict["verbosity"] = verbosity
        
        request_data = OpenRouterRequest(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        url = f"{self.base_url}/chat/completions"
        
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=request_dict,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            log.info(f"Успешный запрос к модели {model_id}")
                            return OpenRouterResponse(**data)
                        else:
                            error_text = await response.text()
                            log.error(
                                f"Ошибка API (попытка {attempt + 1}/{self.retry_attempts}): "
                                f"статус {response.status}, текст: {error_text}"
                            )
                            
            except asyncio.TimeoutError:
                log.error(
                    f"Таймаут запроса к {model_id} "
                    f"(попытка {attempt + 1}/{self.retry_attempts})"
                )
            except Exception as e:
                log.error(
                    f"Ошибка при запросе к {model_id}: {str(e)} "
                    f"(попытка {attempt + 1}/{self.retry_attempts})"
                )
            
            # Ждем перед следующей попыткой
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay)
        
        return None
    
    async def get_response(
        self,
        model_key: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[AIResponse]:
        """
        Получить ответ от конкретной модели
        
        Args:
            model_key: Ключ модели из конфигурации (gemini, claude, grok, chatgpt)
            messages: Список сообщений
            temperature: Температура (если None, берется из конфигурации)
            max_tokens: Максимум токенов (если None, берется из конфигурации)
            
        Returns:
            AIResponse или None
        """
        model_config = config.get_model_config(model_key)
        if not model_config:
            log.error(f"Модель {model_key} не найдена в конфигурации")
            return None
        
        temp = temperature if temperature is not None else model_config.get('temperature', 0.2)
        tokens = max_tokens if max_tokens is not None else model_config.get('max_tokens', 8192)
        reasoning = model_config.get('reasoning', 'high')
        verbosity = model_config.get('verbosity', 'high')
        
        log.info(f"Запрос к модели {model_config['name']} ({model_config['id']}) с reasoning={reasoning}")
        
        response = await self._make_request(
            model_id=model_config['id'],
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            reasoning=reasoning,
            verbosity=verbosity
        )
        
        if response:
            content = response.get_content()
            tokens_used = response.get_tokens_used()
            
            # Попытка извлечь уверенность из ответа
            confidence = self._extract_confidence(content)
            
            return AIResponse(
                model_key=model_key,
                model_name=model_config['name'],
                content=content,
                confidence=confidence,
                tokens_used=tokens_used
            )
        
        return None
    
    async def get_multiple_responses(
        self,
        model_keys: List[str],
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> List[AIResponse]:
        """
        Получить ответы от нескольких моделей параллельно
        
        Args:
            model_keys: Список ключей моделей
            messages: Сообщения для всех моделей
            temperature: Температура
            max_tokens: Максимум токенов
            
        Returns:
            Список ответов от моделей
        """
        tasks = [
            self.get_response(model_key, messages, temperature, max_tokens)
            for model_key in model_keys
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Фильтруем None значения
        return [r for r in responses if r is not None]
    
    def _extract_confidence(self, content: str) -> Optional[float]:
        """
        Попытка извлечь уверенность из текста ответа
        
        Ищет паттерны типа "Уверенность: 85%" или "Confidence: 85%"
        """
        import re
        
        patterns = [
            r'[Уу]веренность[:\s]+(\d+)%',
            r'[Cc]onfidence[:\s]+(\d+)%',
            r'(\d+)%\s+[уУ]веренност',
            r'(\d+)%\s+[cC]onfiden'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None


# Глобальный экземпляр клиента
openrouter_client = OpenRouterClient()
