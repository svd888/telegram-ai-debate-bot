"""
Обработчики команд и сообщений Telegram бота
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from utils import log, config
from ai import debate_manager, openrouter_client
from bot.keyboards import (
    get_main_menu_keyboard,
    get_debate_mode_keyboard,
    get_model_selection_keyboard,
    get_settings_keyboard
)

# Состояния для ConversationHandler
WAITING_QUESTION, WAITING_DEBATE_QUESTION, WAITING_MODEL_CHOICE = range(3)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я **AI Debate Bot** - бот, который использует несколько мощнейших AI моделей для поиска наиболее точных ответов на ваши вопросы.

🤖 **Доступные модели:**
🔵 Google Gemini 3 Pro
🟣 Claude Opus 4.5
🟢 Grok 4.1
🟠 ChatGPT 5.1 Reasoning High

🎯 **Режим дебатов:**
В этом режиме модели обсуждают ваш вопрос в несколько раундов, аргументируя свои позиции и находя наиболее обоснованный ответ.

📊 **Доступные режимы:**
⚡ Быстрый - 2 раунда
📊 Стандартный - 3 раунда
🔬 Глубокий - 5 раундов

Используйте кнопки меню или команды:
/ask - Задать вопрос одной модели
/debate - Запустить дебаты
/settings - Настройки
/history - История запросов
/help - Справка
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    log.info(f"Пользователь {user.id} ({user.username}) запустил бота")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 **Справка по использованию AI Debate Bot**

**Основные команды:**

/start - Начать работу с ботом
/ask - Задать вопрос одной AI модели
/debate - Запустить режим дебатов между моделями
/settings - Настроить параметры работы
/history - Посмотреть историю запросов
/help - Показать эту справку

**Как работает режим дебатов:**

1️⃣ **Раунд 1:** Все модели независимо отвечают на ваш вопрос

2️⃣ **Раунды 2-N:** Модели видят ответы друг друга и могут:
   • Согласиться с аргументами
   • Предложить контраргументы
   • Уточнить свою позицию

3️⃣ **Финал:** Система синтезирует наиболее обоснованный ответ

**Режимы дебатов:**

⚡ **Быстрый** - 2 раунда, ~30-60 сек
📊 **Стандартный** - 3 раунда, ~60-90 сек
🔬 **Глубокий** - 5 раундов, ~120-180 сек

**Советы:**

• Формулируйте вопросы четко и конкретно
• Для сложных вопросов используйте глубокий режим
• Для быстрых ответов - режим одной модели
• Проверяйте уровень уверенности в ответах

Возникли вопросы? Напишите разработчику: @your_username
"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /ask - запрос к одной модели"""
    await update.message.reply_text(
        "🤖 Выберите модель для ответа:",
        reply_markup=get_model_selection_keyboard()
    )
    return WAITING_MODEL_CHOICE


async def model_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора модели"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "model_cancel":
        await query.edit_message_text("❌ Отменено")
        return ConversationHandler.END
    
    model_key = query.data.replace("model_", "")
    context.user_data['selected_model'] = model_key
    
    model_config = config.get_model_config(model_key)
    
    await query.edit_message_text(
        f"✅ Выбрана модель: {model_config.color} **{model_config.name}**\n\n"
        f"Теперь отправьте ваш вопрос:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return WAITING_QUESTION


async def process_single_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопроса для одной модели"""
    question = update.message.text
    model_key = context.user_data.get('selected_model')
    
    if not model_key:
        await update.message.reply_text("❌ Ошибка: модель не выбрана")
        return ConversationHandler.END
    
    model_config = config.get_model_config(model_key)
    
    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text(
        f"⏳ Отправляю вопрос модели {model_config.color} **{model_config.name}**...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Получаем ответ от модели
        messages = [
            {"role": "system", "content": "Ты полезный AI ассистент. Отвечай точно, обоснованно и указывай степень уверенности в процентах."},
            {"role": "user", "content": question}
        ]
        
        response = await openrouter_client.get_response(
            model_key=model_key,
            messages=messages
        )
        
        if response:
            # Форматируем ответ
            answer_text = f"""
{model_config.color} **{model_config.name}**

**Вопрос:** {question}

**Ответ:**
{response.content}

---
📊 Уверенность: {response.confidence or 'не указана'}%
🔢 Токенов: {response.tokens_used or 'н/д'}
"""
            await processing_msg.edit_text(answer_text, parse_mode=ParseMode.MARKDOWN)
            log.info(f"Ответ от {model_key} для пользователя {update.effective_user.id}")
        else:
            await processing_msg.edit_text("❌ Ошибка при получении ответа от модели")
            log.error(f"Не удалось получить ответ от {model_key}")
    
    except Exception as e:
        await processing_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")
        log.error(f"Ошибка при обработке вопроса: {e}")
    
    return ConversationHandler.END


async def debate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /debate - запуск дебатов"""
    await update.message.reply_text(
        "🎯 Выберите режим дебатов:",
        reply_markup=get_debate_mode_keyboard()
    )
    return WAITING_DEBATE_QUESTION


async def debate_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора режима дебатов"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "debate_cancel":
        await query.edit_message_text("❌ Отменено")
        return ConversationHandler.END
    
    mode = query.data.replace("debate_mode_", "")
    context.user_data['debate_mode'] = mode
    
    mode_config = config.get_debate_mode(mode)
    
    await query.edit_message_text(
        f"✅ Выбран режим: **{mode_config.name}** ({mode_config.rounds} раундов)\n\n"
        f"Теперь отправьте ваш вопрос для дебатов:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return WAITING_DEBATE_QUESTION


async def process_debate_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопроса для дебатов"""
    question = update.message.text
    mode = context.user_data.get('debate_mode', 'standard')
    user_id = update.effective_user.id
    
    mode_config = config.get_debate_mode(mode)
    
    # Отправляем сообщение о начале дебатов
    processing_msg = await update.message.reply_text(
        f"🎯 Запускаю дебаты в режиме **{mode_config.name}** ({mode_config.rounds} раундов)...\n\n"
        f"Это может занять некоторое время ⏳",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Запускаем дебаты
        session = await debate_manager.start_debate(
            user_id=user_id,
            question=question,
            mode=mode
        )
        
        # Форматируем результаты
        result_text = debate_manager.format_debate_for_user(session)
        
        # Отправляем результат (разбиваем на части, если слишком длинный)
        max_length = 4000
        if len(result_text) <= max_length:
            await processing_msg.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)
        else:
            # Отправляем по частям
            await processing_msg.delete()
            
            parts = [result_text[i:i+max_length] for i in range(0, len(result_text), max_length)]
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(f"(продолжение {i+1})\n\n{part}", parse_mode=ParseMode.MARKDOWN)
        
        log.info(f"Дебаты завершены для пользователя {user_id}, сессия {session.session_id}")
    
    except Exception as e:
        await processing_msg.edit_text(f"❌ Произошла ошибка при проведении дебатов: {str(e)}")
        log.error(f"Ошибка при проведении дебатов: {e}", exc_info=True)
    
    return ConversationHandler.END


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /settings"""
    await update.message.reply_text(
        "⚙️ **Настройки**\n\nВыберите параметр для изменения:",
        reply_markup=get_settings_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history"""
    # TODO: Реализовать просмотр истории из базы данных
    await update.message.reply_text(
        "📊 **История запросов**\n\n"
        "Функция в разработке. Скоро здесь будет отображаться история ваших запросов и дебатов.",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (кнопки меню)"""
    text = update.message.text
    
    if text == '🤖 Задать вопрос одной модели':
        return await ask_command(update, context)
    elif text == '🎯 Запустить дебаты':
        return await debate_command(update, context)
    elif text == '⚙️ Настройки':
        return await settings_command(update, context)
    elif text == '📊 История':
        return await history_command(update, context)
    elif text == 'ℹ️ Помощь':
        return await help_command(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню или команды для работы с ботом.\n"
            "Введите /help для справки."
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены операции"""
    await update.message.reply_text(
        "❌ Операция отменена",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    log.error(f"Ошибка при обработке обновления: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        )
