"""
Менеджер дебатов между AI моделями
"""
import uuid
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from utils import config, log
from ai.models import AIResponse, DebateRound, DebateSession
from ai.openrouter_client import openrouter_client


class DebateManager:
    """Управление процессом дебатов между AI моделями"""
    
    def __init__(self):
        self.client = openrouter_client
        self.debates_dir = Path(__file__).parent.parent.parent / "data" / "debates"
        self.debates_dir.mkdir(parents=True, exist_ok=True)
    
    async def start_debate(
        self,
        user_id: int,
        question: str,
        mode: str = 'standard',
        model_keys: Optional[List[str]] = None
    ) -> DebateSession:
        """
        Запустить дебаты
        
        Args:
            user_id: ID пользователя Telegram
            question: Вопрос для дебатов
            mode: Режим дебатов (quick, standard, deep)
            model_keys: Список моделей (если None, используются все)
            
        Returns:
            DebateSession с результатами
        """
        # Создаем сессию
        session_id = str(uuid.uuid4())
        debate_mode = config.get_debate_mode(mode)
        
        session = DebateSession(
            session_id=session_id,
            user_id=user_id,
            question=question,
            mode=mode
        )
        
        # Определяем модели для дебатов
        if model_keys is None:
            model_keys = list(config.get_all_models().keys())
        
        log.info(
            f"Начало дебатов {session_id}: вопрос='{question}', "
            f"режим={mode}, раундов={debate_mode.rounds}, модели={model_keys}"
        )
        
        # Раунд 1: Независимые ответы
        round_1 = await self._run_initial_round(question, model_keys)
        session.add_round(round_1)
        
        # Раунды 2-N: Дебаты с учетом ответов других моделей
        for round_num in range(2, debate_mode.rounds + 1):
            debate_round = await self._run_debate_round(
                question=question,
                round_number=round_num,
                total_rounds=debate_mode.rounds,
                previous_responses=round_1.responses if round_num == 2 else session.rounds[-1].responses,
                model_keys=model_keys
            )
            session.add_round(debate_round)
        
        # Синтез финального ответа
        final_answer, final_confidence = await self._synthesize_final_answer(
            question=question,
            session=session
        )
        
        session.complete(final_answer, final_confidence)
        
        # Подсчет общего количества токенов
        total_tokens = sum(
            response.tokens_used or 0
            for round_data in session.rounds
            for response in round_data.responses
        )
        session.total_tokens = total_tokens
        
        # Сохраняем дебаты
        self._save_debate(session)
        
        log.info(
            f"Дебаты {session_id} завершены: "
            f"уверенность={final_confidence}%, токенов={total_tokens}"
        )
        
        return session
    
    async def _run_initial_round(
        self,
        question: str,
        model_keys: List[str]
    ) -> DebateRound:
        """
        Запустить первый раунд - независимые ответы
        
        Args:
            question: Вопрос
            model_keys: Список моделей
            
        Returns:
            DebateRound с ответами
        """
        log.info(f"Раунд 1: независимые ответы от {len(model_keys)} моделей")
        
        system_prompt = config.get_system_prompt('initial_round')
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        responses = await self.client.get_multiple_responses(
            model_keys=model_keys,
            messages=messages
        )
        
        round_data = DebateRound(
            round_number=1,
            responses=responses
        )
        
        log.info(f"Раунд 1 завершен: получено {len(responses)} ответов")
        
        return round_data
    
    async def _run_debate_round(
        self,
        question: str,
        round_number: int,
        total_rounds: int,
        previous_responses: List[AIResponse],
        model_keys: List[str]
    ) -> DebateRound:
        """
        Запустить раунд дебатов с учетом предыдущих ответов
        
        Args:
            question: Исходный вопрос
            round_number: Номер текущего раунда
            total_rounds: Общее количество раундов
            previous_responses: Ответы из предыдущего раунда
            model_keys: Список моделей
            
        Returns:
            DebateRound с ответами
        """
        log.info(f"Раунд {round_number}/{total_rounds}: дебаты")
        
        # Формируем контекст с ответами других моделей
        other_responses_text = self._format_responses_for_context(previous_responses)
        
        system_prompt = config.get_system_prompt(
            'debate_round',
            round_number=round_number,
            total_rounds=total_rounds,
            question=question,
            other_responses=other_responses_text
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Продолжи анализ вопроса: {question}"}
        ]
        
        responses = await self.client.get_multiple_responses(
            model_keys=model_keys,
            messages=messages
        )
        
        round_data = DebateRound(
            round_number=round_number,
            responses=responses
        )
        
        log.info(f"Раунд {round_number} завершен: получено {len(responses)} ответов")
        
        return round_data
    
    async def _synthesize_final_answer(
        self,
        question: str,
        session: DebateSession
    ) -> tuple[str, float]:
        """
        Синтезировать финальный ответ на основе всех раундов дебатов
        
        Args:
            question: Исходный вопрос
            session: Сессия дебатов
            
        Returns:
            Кортеж (финальный_ответ, уверенность)
        """
        log.info("Синтез финального ответа")
        
        # Собираем все ответы из всех раундов
        all_responses_text = ""
        for round_data in session.rounds:
            all_responses_text += f"\n\n=== РАУНД {round_data.round_number} ===\n"
            all_responses_text += self._format_responses_for_context(round_data.responses)
        
        system_prompt = config.get_system_prompt('synthesis')
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Вопрос: {question}\n\nВсе ответы из дебатов:{all_responses_text}"}
        ]
        
        # Используем самую мощную модель для синтеза (ChatGPT 5.1)
        synthesis_response = await self.client.get_response(
            model_key='chatgpt',
            messages=messages
        )
        
        if synthesis_response:
            final_answer = synthesis_response.content
            final_confidence = synthesis_response.confidence or 85.0
        else:
            # Fallback: берем последний ответ с наибольшей уверенностью
            last_round = session.rounds[-1]
            best_response = max(
                last_round.responses,
                key=lambda r: r.confidence or 0
            )
            final_answer = best_response.content
            final_confidence = best_response.confidence or 80.0
        
        log.info(f"Финальный ответ синтезирован, уверенность: {final_confidence}%")
        
        return final_answer, final_confidence
    
    def _format_responses_for_context(self, responses: List[AIResponse]) -> str:
        """
        Форматировать ответы для включения в контекст
        
        Args:
            responses: Список ответов
            
        Returns:
            Отформатированный текст
        """
        formatted = []
        for response in responses:
            model_config = config.get_model_config(response.model_key)
            color = model_config.color if model_config else "⚪"
            
            confidence_text = f" (Уверенность: {response.confidence}%)" if response.confidence else ""
            
            formatted.append(
                f"\n{color} **{response.model_name}**{confidence_text}:\n{response.content}"
            )
        
        return "\n".join(formatted)
    
    def _save_debate(self, session: DebateSession):
        """
        Сохранить дебаты в файл
        
        Args:
            session: Сессия дебатов
        """
        try:
            filename = f"debate_{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.debates_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            
            log.info(f"Дебаты сохранены в {filepath}")
        except Exception as e:
            log.error(f"Ошибка при сохранении дебатов: {e}")
    
    def format_debate_for_user(self, session: DebateSession) -> str:
        """
        Форматировать результаты дебатов для отображения пользователю
        
        Args:
            session: Сессия дебатов
            
        Returns:
            Отформатированный текст
        """
        output = f"🎯 **Вопрос:** {session.question}\n\n"
        output += f"📊 **Режим:** {session.mode} ({len(session.rounds)} раундов)\n"
        output += f"⏱ **Время:** {(session.completed_at - session.started_at).total_seconds():.1f} сек\n"
        output += f"🔢 **Токенов использовано:** {session.total_tokens}\n\n"
        
        output += "=" * 50 + "\n\n"
        output += f"✅ **ФИНАЛЬНЫЙ ОТВЕТ** (Уверенность: {session.final_confidence}%)\n\n"
        output += session.final_answer + "\n\n"
        output += "=" * 50 + "\n\n"
        
        output += "📝 **ДЕТАЛИ ДЕБАТОВ:**\n\n"
        
        for round_data in session.rounds:
            output += f"**Раунд {round_data.round_number}:**\n\n"
            for response in round_data.responses:
                model_config = config.get_model_config(response.model_key)
                color = model_config.color if model_config else "⚪"
                conf = f" ({response.confidence}%)" if response.confidence else ""
                
                output += f"{color} **{response.model_name}**{conf}:\n"
                output += f"{response.content[:300]}...\n\n"
        
        return output


# Глобальный экземпляр менеджера
debate_manager = DebateManager()
