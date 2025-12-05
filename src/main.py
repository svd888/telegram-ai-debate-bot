"""
Главный файл Telegram AI Debate Bot
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в sys.path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from utils import config, log
from bot.handlers import (
    start_command,
    help_command,
    ask_command,
    debate_command,
    settings_command,
    history_command,
    handle_text_message,
    cancel_command,
    error_handler,
    model_selected,
    process_single_question,
    debate_mode_selected,
    process_debate_question,
    WAITING_QUESTION,
    WAITING_DEBATE_QUESTION,
    WAITING_MODEL_CHOICE
)


def main():
    """Главная функция запуска бота"""
    
    # Настройка логирования
    log.info("=" * 50)
    log.info("Запуск Telegram AI Debate Bot")
    log.info("=" * 50)
    
    # Создание приложения
    app = Application.builder().token(config.settings.telegram_bot_token).build()
    
    # ConversationHandler для режима одной модели
    ask_conversation = ConversationHandler(
        entry_points=[
            CommandHandler('ask', ask_command),
            MessageHandler(filters.Regex('^🤖 Задать вопрос одной модели$'), ask_command)
        ],
        states={
            WAITING_MODEL_CHOICE: [
                CallbackQueryHandler(model_selected, pattern='^model_')
            ],
            WAITING_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_single_question)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # ConversationHandler для режима дебатов
    debate_conversation = ConversationHandler(
        entry_points=[
            CommandHandler('debate', debate_command),
            MessageHandler(filters.Regex('^🎯 Запустить дебаты$'), debate_command)
        ],
        states={
            WAITING_DEBATE_QUESTION: [
                CallbackQueryHandler(debate_mode_selected, pattern='^debate_mode_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_debate_question)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('settings', settings_command))
    app.add_handler(CommandHandler('history', history_command))
    
    # Добавляем conversation handlers
    app.add_handler(ask_conversation)
    app.add_handler(debate_conversation)
    
    # Обработчик текстовых сообщений (кнопки меню)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запуск бота
    log.info("Бот запущен и готов к работе!")
    log.info(f"Режимы дебатов: {', '.join(config.debate_modes.keys())}")
    log.info(f"Доступные модели: {', '.join(config.get_all_models().keys())}")
    log.info("🎯 Reasoning: HIGH для всех моделей")
    log.info("🏛️ Гарвардская методика дебатов активирована")
    log.info("🧪 MIT Multi-Agent Debate фреймворк включен")
    
    # Polling
    app.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log.info("Бот остановлен пользователем")
    except Exception as e:
        log.error(f"Критическая ошибка: {e}", exc_info=True)
