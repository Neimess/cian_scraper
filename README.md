# 🏡 Cian Scraper

## 🔍 Описание

Cian Scraper — это инструмент для сбора данных с сайта **Cian** с помощью веб-скрейпинга. Проект включает **Telegram-бота**, базу данных для хранения результатов, систему логирования и поддержку работы через прокси.

---

## 📌 Основные компоненты

### 🔹 Веб-скрейпер (`src/web_scraper/`)

- 📡 `requester.py` — выполняет HTTP-запросы с поддержкой прокси.
- 🏗️ `parser.py` — извлекает данные из HTML-страниц.
- 🔍 `scraper.py` — основной класс для работы с Cian.

### 🤖 Telegram-бот (`src/bot/`)

- 🎮 `bot.py` — основной файл для управления ботом.
- 📝 `handlers/` — обработчики команд и событий.
- 🎛️ `keyboards/` — интерфейсные элементы для пользователя.

### ⚙️ Конфигурация (`configs/config.py`)

Загружается из файла `.env`

### 🗄️ База данных (`db/`)

- 🛠️ `database.py` — управление соединением с БД (PostgreSQL).
- 📋 `models.py` — структуры данных.
- 🔄 `crud/` — запросы к БД.

### 📜 Логирование (`src/utils/loggers.py`)

Логирует работу приложения.

---

## 🚀 Установка и настройка

### 🔽 1. Клонирование репозитория

```bash
git clone https://github.com/your-repo/cian-scraper.git
cd cian-scraper
```

### 📦 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### ⚙️ 3. Настройка `.env`

Создайте `` и добавьте:

```ini
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cian
LOGGER_MODE=console
TELEGRAM_API_KEY=your_telegram_api_key
TELEGRAM_ADMIN_ID=your_admin_id
PROXIES=http://proxy1:port,http://proxy2:port
```

---

## 🏃 Запуск проекта
```bash
export PYTHONPATH="$PWD"
python main.py
```
---

## ✅ Тестирование

```bash
pytest tests/
```

---

## 🐳 Docker

### 📥 Загрузка образа из Docker Hub
```bash
docker pull neimes/cian_scraper:latest
```
### 📌 Сборка и запуск контейнера

```bash
docker-compose up --build -d
```

### ⏹️ Остановка контейнера

```bash
docker-compose down
```

---


