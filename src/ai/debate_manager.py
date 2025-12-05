"""
Менеджер дебатов между AI моделями v2.0
С интеграцией Гарвардской методики и MIT Multi-Agent Debate
"""
import uuid
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from utils import config, log
from ai.models import AIResponse, DebateRound, DebateSession
from ai.openrouter_client import openrouter_client


class DebateManagerV2:
    """Управление процессом дебатов между AI моделями с разделением ролей"""
    
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
        Запустить дебаты с разделением ролей
        
        Args:
            user_id: ID пользователя Telegram
            question: Вопрос для дебатов
            mode: Режим дебатов (quick, standard, deep)
            model_keys: Список моделей (если None, используются все)
            
        Returns:
            DebateSession с результатами
        """
        start_time = time.time()
        
        # Создаем сессию
        session_id = str(uuid.uuid4())
        debate_mode = config.debate_modes.get(mode, config.debate_modes['standard'])
        
        session = DebateSession(
            session_id=session_id,
            user_id=user_id,
            question=question,
            mode=mode
        )
        
        # Определяем модели для дебатов
        if model_keys is None:
            model_keys = list(config.models.keys())
        
        log.info(
            f"Начало дебатов {session_id}: вопрос='{question[:50]}...', "
            f"режим={mode}, раундов={debate_mode['rounds']}, модели={model_keys}"
        )
        
        # Выполняем раунды согласно структуре режима
        for round_info in debate_mode['structure']:
            round_num = round_info['round']
            round_type = round_info['type']
            
            log.info(f"Раунд {round_num}: {round_info['name']} ({round_type})")
            
            if round_type == 'independent_generation':
                debate_round = await self._run_independent_generation(
                    question, model_keys, round_num
                )
            elif round_type == 'mutual_critique':
                debate_round = await self._run_mutual_critique(
                    question, model_keys, round_num, session.rounds[-1].responses
                )
            elif round_type == 'critique_and_synthesis':
                debate_round = await self._run_critique_and_synthesis(
                    question, model_keys, round_num, session.rounds[-1].responses
                )
            elif round_type == 'improvement':
                debate_round = await self._run_improvement(
                    question, model_keys, round_num, session.rounds
                )
            elif round_type == 'improvement_and_synthesis':
                debate_round = await self._run_improvement_and_synthesis(
                    question, model_keys, round_num, session.rounds
                )
            elif round_type == 'consensus_building':
                debate_round = await self._run_consensus_building(
                    question, model_keys, round_num, session.rounds
                )
            elif round_type == 'final_synthesis':
                debate_round = await self._run_final_synthesis(
                    question, round_num, session
                )
            else:
                log.warning(f"Неизвестный тип раунда: {round_type}")
                continue
            
            session.add_round(debate_round)
        
        # Финальный синтез (если еще не был выполнен)
        if debate_mode['structure'][-1]['type'] != 'final_synthesis':
            final_answer, final_confidence = await self._synthesize_final_answer(
                question, session
            )
        else:
            # Берем результат последнего раунда
            last_response = session.rounds[-1].responses[0]  # ChatGPT синтез
            final_answer = last_response.content
            final_confidence = last_response.confidence or 85.0
        
        # Завершаем сессию
        elapsed_time = int(time.time() - start_time)
        session.complete(final_answer, final_confidence)
        
        # Подсчет токенов
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
            f"уверенность={final_confidence}%, токенов={total_tokens}, время={elapsed_time}с"
        )
        
        return session
    
    async def _run_independent_generation(
        self,
        question: str,
        model_keys: List[str],
        round_num: int
    ) -> DebateRound:
        """
        Раунд 1: Независимая генерация ответов
        Каждая модель анализирует вопрос независимо согласно своей роли
        """
        log.info(f"Раунд {round_num}: Независимая генерация от {len(model_keys)} моделей")
        
        responses = []
        
        for model_key in model_keys:
            model_config = config.models[model_key]
            role = model_config.get('role', 'Analyst')
            specialization = ', '.join(model_config.get('specialization', []))
            
            # Формируем промпт с учетом роли
            system_prompt = config.prompts['system_base']
            round_prompt = config.prompts['round_1_independent'].format(
                role=role,
                specialization=specialization,
                question=question
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": round_prompt}
            ]
            
            response = await self.client.get_response(
                model_key=model_key,
                messages=messages
            )
            
            if response:
                responses.append(response)
                log.info(f"  {model_config['name']}: уверенность {response.confidence}%")
        
        return DebateRound(round_number=round_num, responses=responses)
    
    async def _run_mutual_critique(
        self,
        question: str,
        model_keys: List[str],
        round_num: int,
        previous_responses: List[AIResponse]
    ) -> DebateRound:
        """
        Раунд 2: Взаимная критика
        Каждая модель критикует ответы других моделей
        """
        log.info(f"Раунд {round_num}: Взаимная критика")
        
        # Форматируем предыдущие ответы
        other_responses_text = self._format_responses_for_context(previous_responses)
        
        responses = []
        
        for model_key in model_keys:
            model_config = config.models[model_key]
            role = model_config.get('role', 'Analyst')
            specialization = ', '.join(model_config.get('specialization', []))
            
            system_prompt = config.prompts['system_base']
            round_prompt = config.prompts['round_2_critique'].format(
                role=role,
                specialization=specialization,
                other_responses=other_responses_text
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": round_prompt}
            ]
            
            response = await self.client.get_response(
                model_key=model_key,
                messages=messages
            )
            
            if response:
                responses.append(response)
                log.info(f"  {model_config['name']}: критика предоставлена")
        
        return DebateRound(round_number=round_num, responses=responses)
    
    async def _run_critique_and_synthesis(
        self,
        question: str,
        model_keys: List[str],
        round_num: int,
        previous_responses: List[AIResponse]
    ) -> DebateRound:
        """
        Раунд 2 (быстрый режим): Критика и синтез в одном раунде
        """
        log.info(f"Раунд {round_num}: Критика и синтез")
        
        # Сначала критика
        critique_round = await self._run_mutual_critique(
            question, model_keys, round_num, previous_responses
        )
        
        # Затем синтез (только ChatGPT)
        all_data = self._format_all_responses([
            previous_responses,
            critique_round.responses
        ])
        
        system_prompt = config.prompts['system_base']
        synthesis_prompt = f"""
        Проанализируй все ответы и критику. Синтезируй финальный ответ.
        
        ДАННЫЕ ДЕБАТОВ:
        {all_data}
        
        Вопрос: {question}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        synthesis_response = await self.client.get_response(
            model_key='chatgpt',
            messages=messages
        )
        
        if synthesis_response:
            critique_round.responses.append(synthesis_response)
        
        return critique_round
    
    async def _run_improvement(
        self,
        question: str,
        model_keys: List[str],
        round_num: int,
        previous_rounds: List[DebateRound]
    ) -> DebateRound:
        """
        Раунд 3: Улучшение на основе критики
        """
        log.info(f"Раунд {round_num}: Улучшение ответов")
        
        # Получаем начальные ответы и критику
        initial_responses = previous_rounds[0].responses
        critique_responses = previous_rounds[1].responses
        
        responses = []
        
        for model_key in model_keys:
            model_config = config.models[model_key]
            role = model_config.get('role', 'Analyst')
            specialization = ', '.join(model_config.get('specialization', []))
            
            # Находим свой предыдущий ответ
            your_previous = next(
                (r for r in initial_responses if r.model_key == model_key),
                None
            )
            
            # Собираем критику от других
            critique_received = self._format_responses_for_context([
                r for r in critique_responses if r.model_key != model_key
            ])
            
            system_prompt = config.prompts['system_base']
            round_prompt = config.prompts['round_3_improvement'].format(
                role=role,
                specialization=specialization,
                your_previous_response=your_previous.content if your_previous else "Нет предыдущего ответа",
                critique_received=critique_received
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": round_prompt}
            ]
            
            response = await self.client.get_response(
                model_key=model_key,
                messages=messages
            )
            
            if response:
                responses.append(response)
                log.info(f"  {model_config['name']}: ответ улучшен")
        
        return DebateRound(round_number=round_num, responses=responses)
    
    async def _run_improvement_and_synthesis(
        self,
        question: str,
        model_keys: List[str],
        round_num: int,
        previous_rounds: List[DebateRound]
    ) -> DebateRound:
        """
        Раунд 3 (стандартный режим): Улучшение и финальный синтез
        """
        log.info(f"Раунд {round_num}: Улучшение и синтез")
        
        # Сначала улучшение
        improvement_round = await self._run_improvement(
            question, model_keys, round_num, previous_rounds
        )
        
        # Затем синтез всех данных
        all_rounds_data = self._format_all_rounds(previous_rounds + [improvement_round])
        
        system_prompt = config.prompts['system_base']
        synthesis_prompt = f"""
        Синтезируй финальный ответ на основе всех раундов дебатов.
        
        ДАННЫЕ ВСЕХ РАУНДОВ:
        {all_rounds_data}
        
        Вопрос: {question}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        synthesis_response = await self.client.get_response(
            model_key='chatgpt',
            messages=messages
        )
        
        if synthesis_response:
            improvement_round.responses.append(synthesis_response)
        
        return improvement_round
    
    async def _run_consensus_building(
        self,
        question: str,
        model_keys: List[str],
        round_num: int,
        previous_rounds: List[DebateRound]
    ) -> DebateRound:
        """
        Раунд 4: Поиск консенсуса
        """
        log.info(f"Раунд {round_num}: Поиск консенсуса")
        
        # Получаем улучшенные ответы
        improved_responses = previous_rounds[-1].responses
        all_improved_text = self._format_responses_for_context(improved_responses)
        
        responses = []
        
        for model_key in model_keys:
            model_config = config.models[model_key]
            role = model_config.get('role', 'Analyst')
            specialization = ', '.join(model_config.get('specialization', []))
            
            system_prompt = config.prompts['system_base']
            round_prompt = config.prompts['round_4_consensus'].format(
                role=role,
                specialization=specialization,
                all_improved_responses=all_improved_text
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": round_prompt}
            ]
            
            response = await self.client.get_response(
                model_key=model_key,
                messages=messages
            )
            
            if response:
                responses.append(response)
                log.info(f"  {model_config['name']}: консенсус предложен")
        
        return DebateRound(round_number=round_num, responses=responses)
    
    async def _run_final_synthesis(
        self,
        question: str,
        round_num: int,
        session: DebateSession
    ) -> DebateRound:
        """
        Раунд 5: Финальный синтез (только ChatGPT 5.1)
        """
        log.info(f"Раунд {round_num}: Финальный синтез (ChatGPT 5.1)")
        
        # Собираем все данные дебатов
        all_debate_data = self._format_all_rounds(session.rounds)
        
        total_tokens = sum(
            r.tokens_used or 0
            for round_data in session.rounds
            for r in round_data.responses
        )
        
        elapsed_time = int(time.time() - session.started_at.timestamp())
        
        system_prompt = config.prompts['system_base']
        synthesis_prompt = config.prompts['round_5_synthesis'].format(
            all_debate_data=all_debate_data,
            rounds=len(session.rounds),
            time=elapsed_time,
            tokens=total_tokens
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        synthesis_response = await self.client.get_response(
            model_key='chatgpt',
            messages=messages
        )
        
        if synthesis_response:
            log.info(f"  Финальный синтез: уверенность {synthesis_response.confidence}%")
            return DebateRound(round_number=round_num, responses=[synthesis_response])
        else:
            log.error("Не удалось получить финальный синтез")
            # Fallback
            return session.rounds[-1]
    
    async def _synthesize_final_answer(
        self,
        question: str,
        session: DebateSession
    ) -> tuple[str, float]:
        """
        Синтезировать финальный ответ (fallback метод)
        """
        log.info("Синтез финального ответа (fallback)")
        
        all_responses_text = self._format_all_rounds(session.rounds)
        
        system_prompt = config.prompts['system_base']
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Вопрос: {question}\n\nВсе ответы из дебатов:\n{all_responses_text}\n\nСинтезируй финальный ответ."}
        ]
        
        synthesis_response = await self.client.get_response(
            model_key='chatgpt',
            messages=messages
        )
        
        if synthesis_response:
            return synthesis_response.content, synthesis_response.confidence or 85.0
        else:
            # Берем лучший ответ из последнего раунда
            last_round = session.rounds[-1]
            best_response = max(
                last_round.responses,
                key=lambda r: r.confidence or 0
            )
            return best_response.content, best_response.confidence or 80.0
    
    def _format_responses_for_context(self, responses: List[AIResponse]) -> str:
        """Форматировать ответы для контекста"""
        formatted = []
        for response in responses:
            model_config = config.models.get(response.model_key, {})
            role = model_config.get('role', 'Unknown')
            color = model_config.get('color', '⚪')
            
            formatted.append(
                f"{color} **{response.model_name}** ({role}):\n"
                f"{response.content}\n"
                f"Уверенность: {response.confidence}%\n"
            )
        return "\n".join(formatted)
    
    def _format_all_responses(self, response_lists: List[List[AIResponse]]) -> str:
        """Форматировать несколько списков ответов"""
        result = []
        for i, responses in enumerate(response_lists, 1):
            result.append(f"=== ЭТАП {i} ===")
            result.append(self._format_responses_for_context(responses))
        return "\n\n".join(result)
    
    def _format_all_rounds(self, rounds: List[DebateRound]) -> str:
        """Форматировать все раунды"""
        result = []
        for round_data in rounds:
            result.append(f"=== РАУНД {round_data.round_number} ===")
            result.append(self._format_responses_for_context(round_data.responses))
        return "\n\n".join(result)
    
    def _save_debate(self, session: DebateSession):
        """Сохранить дебаты в JSON"""
        try:
            filename = f"{session.session_id}_{session.user_id}.json"
            filepath = self.debates_dir / filename
            
            # Преобразуем в словарь
            debate_data = {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'question': session.question,
                'mode': session.mode,
                'started_at': session.started_at.isoformat(),
                'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                'final_answer': session.final_answer,
                'final_confidence': session.final_confidence,
                'total_tokens': session.total_tokens,
                'rounds': [
                    {
                        'round_number': r.round_number,
                        'responses': [
                            {
                                'model_key': resp.model_key,
                                'model_name': resp.model_name,
                                'content': resp.content,
                                'confidence': resp.confidence,
                                'tokens_used': resp.tokens_used
                            }
                            for resp in r.responses
                        ]
                    }
                    for r in session.rounds
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debate_data, f, ensure_ascii=False, indent=2)
            
            log.info(f"Дебаты сохранены: {filepath}")
        except Exception as e:
            log.error(f"Ошибка сохранения дебатов: {e}")


# Глобальный экземпляр менеджера
debate_manager_v2 = DebateManagerV2()

# Алиас для обратной совместимости
debate_manager = debate_manager_v2
DebateManager = DebateManagerV2
