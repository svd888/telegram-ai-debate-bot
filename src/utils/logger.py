"""
Модуль логирования для Telegram AI Debate Bot
"""
import sys
from loguru import logger
from pathlib import Path


def setup_logger(log_level: str = "INFO"):
    """
    Настройка логгера
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Создаем директорию для логов
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Формат логов
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Консольный вывод
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Файл с общими логами
    logger.add(
        log_dir / "bot.log",
        format=log_format,
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    # Файл только с ошибками
    logger.add(
        log_dir / "errors.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    return logger


# Глобальный логгер
log = setup_logger()
