"""
Клавиатуры для Telegram бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        ['🤖 Задать вопрос одной модели', '🎯 Запустить дебаты'],
        ['⚙️ Настройки', '📊 История'],
        ['ℹ️ Помощь']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_debate_mode_keyboard() -> InlineKeyboardMarkup:
    """Выбор режима дебатов"""
    keyboard = [
        [
            InlineKeyboardButton("⚡ Быстрый (2 раунда)", callback_data="debate_mode_quick"),
        ],
        [
            InlineKeyboardButton("📊 Стандартный (3 раунда)", callback_data="debate_mode_standard"),
        ],
        [
            InlineKeyboardButton("🔬 Глубокий (5 раундов)", callback_data="debate_mode_deep"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="debate_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_model_selection_keyboard() -> InlineKeyboardMarkup:
    """Выбор модели для одиночного запроса"""
    keyboard = [
        [
            InlineKeyboardButton("🔵 Gemini 3 Pro", callback_data="model_gemini"),
        ],
        [
            InlineKeyboardButton("🟣 Claude Opus 4.5", callback_data="model_claude"),
        ],
        [
            InlineKeyboardButton("🟢 Grok 4.1", callback_data="model_grok"),
        ],
        [
            InlineKeyboardButton("🟠 ChatGPT 5.1", callback_data="model_chatgpt"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="model_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 Режим дебатов по умолчанию", callback_data="settings_debate_mode"),
        ],
        [
            InlineKeyboardButton("🌡️ Температура генерации", callback_data="settings_temperature"),
        ],
        [
            InlineKeyboardButton("🤖 Выбор моделей для дебатов", callback_data="settings_models"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="settings_back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)
