# ASEAN Trade Monitor

Платформа для сбора, тегирования и анализа экономических новостей стран АСЕАН (Индонезия, Вьетнам, Малайзия). Разработана в рамках исследования перспектив торгового сотрудничества России и стран АСЕАН.

Сбор новостей осуществляется по **JSON-картам обхода** (sitemap), совместимым с форматом Chrome-расширения [Web Scraper](https://webscraper.io/). Карты можно импортировать напрямую из расширения, создавать и редактировать через веб-интерфейс.

## Требования

- Python 3.11+
- Node.js 18+
- Ключ Anthropic API (опционально — для тегирования и суммаризации)

## Установка

### 1. Backend

```bash
cd backend

# Создать виртуальное окружение
python -m venv .venv

# Активировать
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Frontend

```bash
cd frontend
npm install
```

### 3. Переменные окружения (опционально)

Создать файл `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-ваш-ключ-здесь
```

Ключ можно получить на https://console.anthropic.com/

## Запуск

### Backend (из папки `backend/`)

```bash
uvicorn app.main:app --reload
```

Сервер запустится на http://localhost:8000

При первом запуске:
- Автоматически создаётся база данных SQLite (`asean_news.db`) в режиме WAL
- Загружаются 9 предустановленных карт обхода (seed maps) для новостных сайтов АСЕАН

API-документация: http://localhost:8000/docs

### Frontend (из папки `frontend/`)

```bash
npm run dev
```

Интерфейс откроется на http://localhost:5173

## Первый запуск

1. Открыть http://localhost:5173
2. Перейти в **Settings**
3. Увидите таблицу с 9 предустановленными картами обхода
4. Нажать **Run All** для запуска сбора по всем активным картам
5. Наблюдать за прогрессом в панели **Live Scraping** (логи обновляются каждые 1.5 сек)
6. После завершения перейти в **News Registry** — появятся собранные статьи

По умолчанию сбор запускается автоматически каждые 6 часов.

## Карты обхода (Scrape Maps)

Система использует JSON-карты обхода вместо hardcoded скраперов. Каждая карта описывает:

- **startUrls** — страницы-разделы для поиска ссылок на статьи
- **selectors** — дерево CSS-селекторов для извлечения данных (ссылки, заголовок, текст, дата)
- **_meta** — метаданные: страна, имя источника, фильтр URL, форматы дат, маппинг категорий

### Формат карты

Полностью совместим с [Web Scraper Chrome Extension](https://webscraper.io/) + дополнительный блок `_meta`:

```json
{
  "_id": "my_source",
  "startUrls": ["https://example.com/news"],
  "sitemapSpecificationVersion": 1,
  "rootSelector": {"id": "_root", "uuid": "0"},
  "selectors": [
    {
      "id": "article_links",
      "type": "SelectorLink",
      "uuid": "1",
      "multiple": true,
      "selector": "a[href]",
      "parentSelectors": ["0"],
      "extractAttribute": "href"
    },
    {
      "id": "title",
      "type": "SelectorText",
      "uuid": "2",
      "selector": "h1",
      "parentSelectors": ["1"]
    },
    {
      "id": "body",
      "type": "SelectorText",
      "uuid": "3",
      "multiple": true,
      "selector": "div.article-body, article",
      "parentSelectors": ["1"]
    },
    {
      "id": "published_date",
      "type": "SelectorText",
      "uuid": "4",
      "selector": "time[datetime]",
      "parentSelectors": ["1"]
    }
  ],
  "_meta": {
    "country": "ID",
    "source_display": "My Source",
    "url_filter_pattern": "/news/\\d+/",
    "date_source": "selector",
    "date_selector_formats": ["%Y-%m-%dT%H:%M:%S", "%B %d, %Y"],
    "category_mapping": {"https://example.com/news": "General"},
    "min_body_length": 200,
    "author_selectors": ["meta[name='author']"]
  }
}
```

### Дерево селекторов

- `parentSelectors: ["0"]` — применяется на страницах startUrl (корневой уровень)
- `parentSelectors: ["1"]` — применяется на страницах статей (найденных через SelectorLink)

### Поля `_meta`

| Поле | Описание |
|------|----------|
| `country` | ISO-код страны (ID, VN, MY) |
| `source_display` | Человекочитаемое название источника |
| `url_filter_pattern` | Regex для фильтрации URL статей (только совпавшие будут обработаны) |
| `date_source` | `"url"` — дата из URL, `"selector"` — дата из HTML-элемента |
| `date_url_pattern` | Regex с группами (год, месяц, день) для извлечения даты из URL |
| `date_selector_formats` | Список форматов `strptime` для парсинга дат из текста |
| `category_mapping` | `{startUrl: "Категория"}` — маппинг разделов на категории |
| `min_body_length` | Минимальная длина текста статьи (в символах) |
| `author_selectors` | CSS-селекторы для извлечения автора |

### Управление картами

Через веб-интерфейс (Settings):
- **Create** — создать карту с JSON-шаблоном
- **Import JSON** — вставить JSON из Web Scraper Chrome Extension
- **Edit** — редактировать JSON карты с валидацией
- **Toggle** — включить/выключить карту для автосбора
- **Delete** — удалить карту
- **Scrape** — запустить сбор по одной карте

Через API:
- `GET /api/scrape-maps` — список карт
- `GET /api/scrape-maps/{map_id}` — полная карта с JSON
- `POST /api/scrape-maps` — создать карту
- `PUT /api/scrape-maps/{map_id}` — обновить карту
- `DELETE /api/scrape-maps/{map_id}` — удалить
- `POST /api/scrape-maps/{map_id}/toggle` — вкл/выкл

## Логирование

Логи сбора отображаются в реальном времени на странице Settings:

- **Live Scraping** — панель с консольным выводом (тёмная тема, auto-scroll), обновляется каждые 1.5 сек
- **Recent Scrape Runs** — таблица с историей запусков, статусами, кол-вом найденных/новых статей
- **Run Detail** — подробные логи конкретного запуска (timeline с цветовой индикацией уровней)

API для логов:
- `GET /api/scrape/live` — текущие запущенные сборщики с последними логами
- `GET /api/scrape/runs` — история запусков
- `GET /api/scrape/runs/{id}` — детали запуска с полными логами
- `GET /api/scrape/runs/{id}/logs?after_id=0` — инкрементальный polling логов
- `GET /api/scrape/stats` — статистика по источникам (всего статей, последний сбор)

## Настройка

Параметры задаются через переменные окружения в файле `backend/.env`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(пусто)_ | Ключ API Anthropic для Claude (опционально) |
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
│   │   ├── main.py                     # Точка входа FastAPI, lifespan, роутеры
│   │   ├── config.py                   # Настройки из .env
│   │   ├── database.py                 # SQLite + WAL mode + async engine
│   │   ├── models/
│   │   │   ├── article.py              # Модель Article
│   │   │   ├── tag.py                  # Модель ArticleTag
│   │   │   ├── scrape_log.py           # Модели ScrapeRun, ScrapeLogEntry
│   │   │   └── scrape_map.py           # Модель ScrapeMap (карты обхода)
│   │   ├── schemas/
│   │   │   ├── scrape.py               # Схемы запусков и логов
│   │   │   └── scrape_map.py           # Схемы CRUD карт обхода
│   │   ├── api/
│   │   │   ├── news.py                 # CRUD статей, фильтрация, пагинация
│   │   │   ├── scrape.py               # Управление pipeline, live-логи, статистика
│   │   │   ├── scrape_maps.py          # CRUD карт обхода
│   │   │   ├── analytics.py            # Аналитика и графики
│   │   │   └── summarize.py            # LLM-суммаризация
│   │   ├── services/
│   │   │   ├── llm_tagger.py           # Классификация статей через Claude
│   │   │   └── text_analysis.py        # Word clouds, NLP
│   │   ├── scrapers/
│   │   │   ├── base.py                 # RawArticle, ScrapeStats, USER_AGENTS
│   │   │   ├── sitemap_executor.py     # Универсальный движок карт обхода
│   │   │   ├── registry.py             # Загрузка карт из БД
│   │   │   └── seed_maps.py            # 9 предустановленных карт + seed_default_maps()
│   │   └── pipeline/
│   │       ├── orchestrator.py         # ETL: scrape → store → tag
│   │       └── scheduler.py            # APScheduler для автозапуска
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                     # Роутинг, layout
│   │   ├── pages/
│   │   │   ├── NewsArchive.tsx         # Реестр новостей с фильтрами
│   │   │   ├── ArticleDetail.tsx       # Детали статьи
│   │   │   ├── Dashboard.tsx           # Аналитика и графики
│   │   │   ├── Summarize.tsx           # LLM-суммаризация
│   │   │   ├── Settings.tsx            # Управление картами, запуски, live-логи
│   │   │   └── MapEditor.tsx           # Редактор JSON карт обхода
│   │   ├── components/
│   │   │   └── LiveLogPanel.tsx        # Панель live-логов (polling 1.5s)
│   │   ├── api/
│   │   │   ├── client.ts              # Axios instance
│   │   │   ├── scrape.ts              # API сбора, логов, статистики
│   │   │   └── scrapeMaps.ts          # API карт обхода
│   │   └── types/
│   │       └── index.ts               # TypeScript интерфейсы
│   └── package.json
├── website_maps_examples/              # Примеры карт обхода + Chrome-расширение
└── README.md
```

## Предустановленные источники

| Страна | Источник | Разделы |
|---|---|---|
| Индонезия | The Jakarta Post | News, Business, World, Southeast Asia, Academia |
| Индонезия | Kompas.com (English) | Money, National, Global, Tech, Lifestyle |
| Индонезия | Antara News | News, Economy, Politics, National, World |
| Вьетнам | VnExpress International | Business, Economy, Industries, News, Perspectives |
| Вьетнам | Vietnam News | Economy, Politics & Law, Society, Environment, ODA & FDI |
| Вьетнам | Tuoi Tre News | Business, Politics, Society, Education |
| Малайзия | The Star | Business, Nation, Regional, ASEAN+, Tech |
| Малайзия | Malay Mail | Malaysia, Money, World, Tech |
| Малайзия | Bernama | General, Business, World, Politics, Sports |

Все источники — это карты обхода в БД, которые можно редактировать, отключать или удалять через UI.

## Работа без ключа API

Приложение полностью работает без `ANTHROPIC_API_KEY`. Новости будут собираться и сохраняться, но автоматическое тегирование (темы, страны, тональность) и суммаризация будут недоступны.

## Добавление нового источника

1. Открыть Settings в веб-интерфейсе
2. Нажать **Create** (или **Import JSON** если есть карта из Chrome Web Scraper)
3. Заполнить JSON: `_id`, `startUrls`, `selectors`, `_meta`
4. Нажать **Validate** для проверки
5. Нажать **Save**
6. Новый источник появится в таблице — нажать **Scrape** для проверки
