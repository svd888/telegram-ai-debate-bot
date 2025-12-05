#!/bin/bash

# Скрипт запуска Telegram AI Debate Bot

echo "🤖 Запуск Telegram AI Debate Bot..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "📦 Создаю виртуальное окружение..."
    python3.11 -m venv venv
    source venv/bin/activate
    echo "📥 Устанавливаю зависимости..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл на основе .env.example"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Создание директорий
mkdir -p logs
mkdir -p data/debates

# Запуск бота
echo "✅ Запускаю бота..."
cd src
python main.py
