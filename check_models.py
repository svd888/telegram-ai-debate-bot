#!/usr/bin/env python3
"""
Скрипт для проверки доступных моделей в OpenRouter
и поиска корректных ID для моделей в config.yaml
"""
import os
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not OPENROUTER_API_KEY:
    print("❌ Ошибка: OPENROUTER_API_KEY не найден в .env файле")
    exit(1)

print("🔍 Проверка доступных моделей в OpenRouter...\n")

headers = {
    'Authorization': f'Bearer {OPENROUTER_API_KEY}'
}

try:
    response = requests.get('https://openrouter.ai/api/v1/models', headers=headers)
    response.raise_for_status()
    
    data = response.json()
    models = data.get('data', [])
    
    print(f"✅ Найдено {len(models)} моделей\n")
    print("=" * 80)
    
    # Ищем нужные модели
    search_terms = {
        'Gemini 3 Pro': ['gemini', '3', 'pro'],
        'Claude Opus 4.5': ['claude', 'opus', '4.5'],
        'Grok 4.1': ['grok', '4.1', '4'],
        'ChatGPT 5.1': ['gpt', '5.1', '5', 'reasoning']
    }
    
    print("\n🎯 ПОИСК НУЖНЫХ МОДЕЛЕЙ:\n")
    
    for model_name, terms in search_terms.items():
        print(f"\n{model_name}:")
        print("-" * 80)
        
        found = False
        for model in models:
            model_id = model.get('id', '').lower()
            model_display_name = model.get('name', '').lower()
            
            # Проверяем, содержит ли модель все ключевые слова
            if any(term.lower() in model_id or term.lower() in model_display_name for term in terms):
                print(f"  ID: {model.get('id')}")
                print(f"  Название: {model.get('name')}")
                print(f"  Описание: {model.get('description', 'Нет описания')[:100]}...")
                print()
                found = True
        
        if not found:
            print(f"  ⚠️ Модели не найдены. Попробуйте поискать вручную.")
    
    print("\n" + "=" * 80)
    print("\n📋 ВСЕ ДОСТУПНЫЕ МОДЕЛИ (первые 50):\n")
    
    for i, model in enumerate(models[:50], 1):
        print(f"{i}. {model.get('id')} - {model.get('name')}")
    
    if len(models) > 50:
        print(f"\n... и еще {len(models) - 50} моделей")
    
    print("\n" + "=" * 80)
    print("\n💡 РЕКОМЕНДАЦИИ:\n")
    print("1. Найдите корректные ID моделей выше")
    print("2. Обновите config.yaml с правильными ID")
    print("3. Проверьте, что у вас есть доступ к этим моделям на OpenRouter")
    print("4. Убедитесь, что на балансе достаточно средств")
    print("\n" + "=" * 80)

except requests.exceptions.RequestException as e:
    print(f"❌ Ошибка при запросе к OpenRouter API: {e}")
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
