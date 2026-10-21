<div align="center">

# ⚔️ Legends of Runeterra Deck Tracker

**Профессиональный игровой оверлей (HUD) для Legends of Runeterra в стиле Hearthstone Deck Tracker.**

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D6.svg)](https://microsoft.com/windows)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-gold.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.0.0-purple.svg)](release/)

[Возможности](#-основные-возможности) •
[Установка](#-установка-и-запуск) •
[Сборка EXE](#-сборка-автономного-exe) •
[Структура проекта](#-структура-проекта) •
[Документация](#-документация)

</div>

---

## 🌟 Основные возможности

### 1. 🎴 Модульный игровой HUD (HDT Design)
- **Колода игрока (`PlayerPanel`)**: список оставшихся карт вашей колоды, кривая маны, счетчики механик («Освящение», ядовитые грибы, бомбы, прогресс чемпионов) и фильтрация «Только оставшиеся».
- **Трекер противника (`OpponentPanel`)**: подсчет карт в руке, история ходов удержания карт, список всех сыгранных и сброшенных карт врага.
- **Тактический советник угроз (`AdvisorBar` & Threat Matrix)**: автоматический расчет текущей маны оппонента (мана юнитов + банк маны заклинаний) и список летальных контр-заклинаний врага (Возмездие, Погибель, Отрицание, зачистки стола).
- **Всплывающий предпросмотр карт (Hover Tooltip)**: наведите курсор на любую плитку карты, чтобы увидеть ее оригинальный полноразмерный арт, характеристики и описание на русском языке.

### 2. 🇷🇺 Полная русская локализация DataDragon
- Встроенный офлайн-кэш на **2512 карт** всех наборов (Сеты 1–9 + глобалы Riot).
- Локализованные названия, типы («Заклинание», «Боец», «Место силы»), скорости заклинаний («Взрывное», «Быстрое», «Медленное») и ключевые слова.
- Официальные векторные значки всех 11 регионов Рунтерры (Демасия, Ноксус, Иония, Фрельйорд, Сумрачные острова, Билджвотер, Таргон, Шурима, Бандл Сити, Рунтерра).

### 3. 🖥️ Нативная интеграция с Windows
- **Безрамочный HUD**: прозрачные панели в стиле Arcane Hextech без стандартных белых рамок Windows.
- **Отображение в панели задач**: оверлей регистрируется в панели задач с фирменной иконкой кристалла маны.
- **Иконка в системном трее**: контекстное меню с текущим статусом матча, быстрым доступом к настройкам, режимом предпросмотра и сбросом позиций.
- **Защита от потери фокуса**: режим `WS_EX_NOACTIVATE` гарантирует, что клики по оверлею никогда не сворачивают игру. Поддержка сквозных кликов (click-through).
- **Анти-фликкеринг**: учет карт по постоянному `CardID` предотвращает мерцание и возврат разыгранных карт обратно в колоду.

---

## 🚀 Установка и запуск

### Вариант A. Для игроков (Готовый `.exe`)
1. Скачайте автономный файл из папки `release/`:
   ```
   release/LoRDeckTracker.exe
   ```
2. Запустите `LoRDeckTracker.exe` двойным кликом.
3. Программа появится в системном трее и панели задач. Как только вы начнете матч в Legends of Runeterra, оверлей автоматически развернется поверх игры.

> [!TIP]
> Чтобы настроить положение окон до начала игры, нажмите правой кнопкой мыши по иконке в трее и выберите **«Всегда показывать оверлеи (тест)»**, затем перетащите панели в нужные места. Позиции сохраняются автоматически!

### Вариант B. Для разработчиков (Запуск из исходников)
```bash
# Клонируйте репозиторий
git clone https://github.com/lor-deck-tracker/lor-deck-tracker-windows.git
cd lor-deck-tracker-windows

# Установите зависимости
python -m pip install -r requirements.txt

# Запустите трекер
python main.py
# или используйте run.bat
```

---

## 🔨 Сборка автономного `.exe`

Вся сборка автоматизирована. В проекте настроен пайплайн сборки с внедрением ресурсов, иконки и информации о версии Windows.

### Сборка в 1 клик (Windows):
Просто запустите командный файл:
```cmd
build.bat
```

### Сборка через Python:
```bash
python scripts/build_exe.py --clean --zip
```

Готовый файл будет скомпилирован и сохранен в:
- `release/LoRDeckTracker.exe` (автономный бинарник, не требующий Python).
- `release/LoRDeckTracker-v1.0.0-windows-x64.zip` (дистрибутивный архив).

---

## 📁 Структура проекта

```
c:\LoR-deck-tracker-windows\
├── .gitignore                  # Правила исключений Git
├── LICENSE                     # MIT License + Riot Games API Disclaimer
├── README.md                   # Документация проекта
├── CHANGELOG.md                # История изменений и версий
├── pyproject.toml              # Метаданные пакета Python (PEP 621)
├── requirements.txt            # Зависимости проекта
├── build.bat                   # 1-клик сборщик EXE для Windows
├── run.bat                     # 1-клик запуск для разработчиков
├── main.py                     # Главная точка входа приложения
│
├── lor/                        # Основной пакет приложения
│   ├── __init__.py             # Экспорт API и метаданные пакета
│   ├── card_db.py              # Локальная БД карт DataDragon
│   ├── tracker_engine.py       # Клиент опроса LoR с постоянными CardID
│   ├── advisor_engine.py       # Движок расчета угроз и маны оппонента
│   ├── manager.py              # Координатор оверлеев и системный трей
│   ├── panels.py               # Панели игрока и противника
│   ├── advisor.py              # Верхняя панель угроз оппонента
│   ├── preview.py              # Всплывающий предпросмотр карт (HDT)
│   ├── settings.py             # Окно настроек HUD
│   ├── theme.py                # Цветовая палитра и стили Runeterra
│   ├── widgets.py              # Графические компоненты и кривая маны
│   └── win32ext.py             # Win32 API (topmost, click-through, taskbar)
│
├── data/                       # Статические данные и ресурсы
│   ├── cards_cache_ru.json     # 2512 локализованных карт (UTF-8)
│   ├── globals_ru.json         # Глобальные параметры DataDragon
│   ├── settings.json           # Пользовательские настройки
│   └── icons/                  # Иконка приложения и регионы
│       ├── app_icon.ico        # Мульти-размерная иконка Windows
│       ├── app_icon.png        # Высокое разрешение
│       └── regions/            # Иконки всех 11 регионов LoR
│
├── release/                    # Папка для распространяемых релизов
│   └── LoRDeckTracker.exe      # Собранный автономный исполняемый файл
│
├── scripts/                    # Скрипты автоматизации
│   ├── build_exe.py            # Пайплайн сборки PyInstaller
│   └── fetch_cards.py          # Обновление базы карт из Riot CDN
│
├── tests/                      # Модульные и интеграционные тесты
│   ├── test_card_db.py
│   ├── test_live_lor.py
│   ├── test_simulation.py
│   └── test_overlay_render.py
│
├── tools/                      # Инструменты разработки
│   └── mock_lor_server.py      # Мок-сервер API клиента LoR
│
├── docs/                       # Дополнительная документация
│   ├── BUILD.md                # Полное руководство по сборке
│   ├── USER_GUIDE.md           # Руководство пользователя
│   └── ARCHITECTURE.md         # Описание архитектуры и пайплайнов
│
└── legacy/                     # Архив устаревших прототипов (Tkinter/Flask)
```

---

## 📖 Документация

- [Руководство по сборке](docs/BUILD.md)
- [Руководство пользователя и горячие клавиши](docs/USER_GUIDE.md)
- [Архитектура и внутреннее устройство](docs/ARCHITECTURE.md)
- [История изменений (Changelog)](CHANGELOG.md)

---

## ⚖️ Правовая оговорка (Legal Notice)

> Legends of Runeterra Deck Tracker isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
