#!/usr/bin/env python3
"""
Тест для проверки правильности форматирования времени выполнения тестов.
"""

def format_time_taken(minutes):
    """
    Безопасно форматирует время выполнения теста для отображения.
    
    Args:
        minutes: Время в минутах (может быть None, 0 или отрицательным)
    
    Returns:
        str: Отформатированная строка времени
    """
    if minutes is None or minutes < 0:
        return "0 мин"
    
    if minutes == 0:
        return "<1 мин"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours == 0:
        return f"{remaining_minutes} мин"
    elif remaining_minutes == 0:
        return f"{hours} ч"
    else:
        return f"{hours} ч {remaining_minutes} мин"

def test_time_formatting():
    """Тестирует различные случаи форматирования времени."""
    test_cases = [
        (None, "0 мин"),
        (-5, "0 мин"),
        (0, "<1 мин"),
        (1, "1 мин"),
        (5, "5 мин"),
        (59, "59 мин"),
        (60, "1 ч"),
        (61, "1 ч 1 мин"),
        (65, "1 ч 5 мин"),
        (120, "2 ч"),
        (125, "2 ч 5 мин"),
        (180, "3 ч"),
        (185, "3 ч 5 мин")
    ]
    
    print("Тестирование функции format_time_taken:")
    print("=" * 50)
    
    all_passed = True
    for input_minutes, expected in test_cases:
        result = format_time_taken(input_minutes)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} {input_minutes} мин -> '{result}' (ожидалось: '{expected}')")
    
    print("=" * 50)
    if all_passed:
        print("✓ Все тесты прошли успешно!")
    else:
        print("✗ Некоторые тесты не прошли!")
    
    return all_passed

if __name__ == "__main__":
    test_time_formatting()