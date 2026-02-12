# ASEAN Trade Monitor

Платформа для сбора, тегирования и анализа экономических новостей стран АСЕАН (Индонезия, Вьетнам, Малайзия). Разработана в рамках исследования перспектив торгового сотрудничества России и стран АСЕАН.

## Требования

- Python 3.11+
- Node.js 18+
- Ключ Anthropic API (для тегирования и суммаризации)

## Установка

### 1. Клонирование и настройка окружения

```bash
git clone <repository-url>
cd ASEAN_EC_News
```

Создать файл `.env` в корне проекта:

```
ANTHROPIC_API_KEY=sk-ant-ваш-ключ-здесь
```

Ключ можно получить на https://console.anthropic.com/

### 2. Backend

```bash
cd backend

# Создать виртуальное окружение (рекомендуется)
python -m venv .venv

# Активировать
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Запуск

### Backend (из папки `backend/`)

```bash
uvicorn app.main:app --reload
```

Сервер запустится на http://localhost:8000

При первом запуске автоматически создаётся база данных SQLite (`asean_news.db`).

API-документация доступна по адресу http://localhost:8000/docs

### Frontend (из папки `frontend/`)

```bash
npm run dev
```

Интерфейс откроется на http://localhost:5173

## Первый запуск

1. Открыть http://localhost:5173
2. Перейти в **Settings**
3. Нажать **Run All Scrapers** для первого сбора новостей
4. Дождаться завершения (статус видно в таблице Scrape Runs)
5. Перейти в **News Registry** - появятся собранные статьи с тегами

По умолчанию скраперы запускаются автоматически каждые 6 часов.

## Настройка

Все параметры задаются через переменные окружения в файле `.env`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `ANTHROPIC_API_KEY` | (обязательно) | Ключ API Anthropic для Claude |
| `DATABASE_URL` | `sqlite+aiosqlite:///./asean_news.db` | Строка подключения к БД |
| `SCRAPE_INTERVAL_HOURS` | `6` | Интервал автоматического сбора (часы) |
| `SCRAPE_DELAY_SECONDS` | `2.0` | Задержка между запросами к одному сайту (секунды) |
| `LLM_MODEL_TAGGING` | `claude-sonnet-4-20250514` | Модель для тегирования статей |
| `LLM_MODEL_SUMMARIZE` | `claude-opus-4-20250514` | Модель для суммаризации |

## Структура проекта

```
ASEAN_EC_News/
├── backend/
│   ├── app/
│   │   ├── main.py              # Точка входа FastAPI
│   │   ├── config.py            # Настройки из .env
│   │   ├── database.py          # Подключение к SQLite
│   │   ├── models/              # SQLAlchemy-модели (Article, ArticleTag, ScrapeRun)
│   │   ├── schemas/             # Pydantic-схемы запросов/ответов
│   │   ├── api/                 # REST-эндпоинты
│   │   ├── services/            # LLM-тегирование, суммаризация, анализ текста
│   │   ├── scrapers/            # 9 парсеров новостных сайтов
│   │   └── pipeline/            # ETL-оркестратор и планировщик
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # 5 страниц: реестр, статья, аналитика, суммаризация, настройки
│   │   ├── components/          # WordCloud и др.
│   │   ├── api/                 # HTTP-клиент к backend
│   │   └── types/               # TypeScript-типы
│   └── package.json
├── .env                         # Секреты (не коммитится)
└── .env.example                 # Шаблон .env
```

## Источники новостей

| Страна | Источник | Разделы |
|---|---|---|
| Индонезия | The Jakarta Post | News, Business, World, Southeast Asia, Academia |
| Индонезия | Kompas.com (English) | Money, National, Global, Tech |
| Индонезия | Antara News | News, Economy, Politics, National, World |
| Вьетнам | VnExpress International | Business, Economy, Industries, News, Perspectives |
| Вьетнам | Vietnam News | Economy, Politics, Society, Environment, ODA & FDI |
| Вьетнам | Tuoi Tre News | Business, Politics, Society, Education |
| Малайзия | The Star | Business, Nation, Regional, ASEAN+, Tech |
| Малайзия | Malay Mail | Malaysia, Money, World, Tech |
| Малайзия | Bernama | General, Business, World, Politics |

## Логирование

Логи пишутся одновременно в консоль и в файл `asean_trade_monitor.log` в папке `backend/`. В логах видно:

- Какие секции каждого сайта были обработаны
- Сколько URL найдено и сколько успешно спарсено
- Заголовок, источник, категория и размер каждой новой статьи
- Результаты LLM-тегирования (страны, темы, отрасли, тональность)
- Ошибки при HTTP-запросах и парсинге

## Работа без ключа API

Приложение работает и без `ANTHROPIC_API_KEY`. Новости будут собираться и сохраняться, но автоматическое тегирование и суммаризация будут недоступны.
