# Star Burger

Сайт доставки еды «Star Burger». Сеть ресторанов с единым меню: пользователь выбирает блюда, оформляет заказ, а система автоматически подсказывает ближайшие рестораны для его приготовления.

[Рабочий сайт](https://tstdplmnt.site/)

## Технологический стек

- **Бэкенд:** Python 3.14, Django 6.1, Django REST Framework
- **БД:** PostgreSQL (для прода), SQLite (для локальной разработки)
- **Фронтенд:** JavaScript, React 17, Parcel 2
- **Деплой:** Gunicorn, Nginx, Systemd
- **Мониторинг ошибок:** Rollbar
- **Геокодинг:** Yandex Geocoder API (расчёт расстояний от ресторана до клиента)
- **Хранение сессий:** Django sessions в БД

## Интерфейсы сайта

- **Публичная часть (`/`)** — выбор блюд из меню и оформление заказа без регистрации.
- **Кабинет менеджера (`/manager/`)** — обработка заказов: подтверждение, выбор ресторана-исполнителя, просмотр доступных ресторанов и расстояния до них.
- **Админка (`/admin/`)** — управление товарами, ресторанами, заказами и остальным контентом.

## Переменные окружения

Создай файл `.env` в корне проекта на основе `.env.example`:

```bash
cp .env.example .env
```

### Обязательные переменные

| Переменная | Описание |
|------------|----------|
| `SECRET_KEY` | Секретный ключ Django. Сгенерировать: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | URL подключения к БД. Пример для PostgreSQL: `postgres://user:password@127.0.0.1:5432/starburger` |

### Необязательные переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DEBUG` | `False` | Режим отладки. **Никогда не включай в проде**. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Список доменов/IP, с которых разрешён доступ к сайту. |
| `YANDEX_GEOCODER_API_KEY` | `None` | Ключ [Яндекс.Геокодера](https://yandex.ru/dev/geocode/). Нужен для расчёта расстояний на странице менеджера. Без ключа заказы отображаются, но рестораны с расстояниями не будут предложены. |
| `GEOCODER_PLACE_TTL` | `86400` | Время кэширования координат в БД (секунды). |
| `ROLLBAR_ACCESS_TOKEN` | `None` | Токен для [Rollbar](https://rollbar.com/). |
| `ROLLBAR_ENVIRONMENT` | `development` | Окружение для логов в Rollbar (`production`, `staging` и др.) |

## Локальный запуск (разработка)

Нужны одновременно два терминала: бэкенд и фронтенд.

### 1. Бэкенд

```bash
# Клонировать репозиторий
git clone https://github.com/0rcb0n3-lab/star-burger.git
cd star-burger

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS
# .\venv\Scripts\activate  # Windows

# Зависимости
pip install -r requirements.txt

# Переменные окружения
cp .env.example .env
# Заполни SECRET_KEY и при необходимости остальные переменные

# Миграции и запуск
python manage.py migrate
python manage.py runserver
```

Сайт будет доступен по адресу [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 2. Фронтенд

```bash
# Установка зависимостей
npm ci

# Сборка в watch-режиме
./node_modules/.bin/parcel watch bundles-src/index.js --dist-dir bundles --public-url="./"
```

После первой сборки страница в браузере начнёт отображаться корректно.

## Продакшн-деплой

### Первичная настройка сервера

Требования: Ubuntu, Nginx, PostgreSQL, Python 3.12+, Node.js 16+.

1. Клонировать проект в `/opt/star-burger`
2. Создать и активировать venv, установить зависимости из `requirements.txt`
3. Настроить `.env` с `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`
4. Настроить Systemd-юнит `star-burger.service` (gunicorn на `127.0.0.1:8000`)
5. Настроить Nginx в качестве reverse-proxy с раздачей `/static/` и `/media/`
6. Собрать фронт и статику: `npm ci && ./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./" && python manage.py collectstatic --noinput`
7. Применить миграции: `python manage.py migrate`
8. Настроить HTTPS через Certbot

### Автоматический деплой

На сервере есть скрипт `/root/deploy-star-burger.sh`, который автоматически выполняет полный деплой:

1. `git fetch --all --prune && git reset --hard origin/main` — обновление кода
2. Установка Python-зависимостей (`pip install -r requirements.txt`)
3. Установка Node.js-зависимостей (`npm ci`)
4. Сборка фронтенда (`parcel build`)
5. Сбор статика Django (`collectstatic --noinput`)
6. Применение миграций (`migrate --noinput`)
7. Перезапуск `star-burger.service` с проверкой статуса
8. Отправка уведомления о деплое в Rollbar
9. Завершение с логированием в `/var/log/star-burger-deploy.log`

Запуск:

```bash
/root/deploy-star-burger.sh
```

Скрипт защищён от параллельных запусков через `flock`, падает при любой ошибке благодаря `set -euo pipefail`.

## Обслуживание

### Очистка просроченных сессий

Настроен автоматический запуск встроенной Django-команды `clearsessions`.

- **Сервис:** `starburger-clearsessions.service` (одноразовый запуск)
- **Таймер:** `starburger-clearsessions.timer` (запуск раз в месяц, `OnCalendar=monthly`)
- **Особенности:** `Persistent=true` — при пропущенном запуске (например, после выключения сервера) сессии будут очищены при старте, таймер включается автоматически после перезагрузки (`systemctl enable`)

Проверка таймера:

```bash
systemctl list-timers | grep starburger-clearsessions
systemctl status starburger-clearsessions.timer
```

Ручной запуск:

```bash
systemctl start starburger-clearsessions.service
journalctl -u starburger-clearsessions.service -n 20 --no-pager
```

### Автообновление SSL-сертификата

Используется Certbot с systemd-таймером `certbot.timer` (запуск дважды в сутки). Обновление происходит автоматически, если до истечения сертификата осталось менее 30 дней. Nginx перезагружается при успешном обновлении.

Проверка:

```bash
systemctl list-timers | grep certbot
certbot renew --dry-run
certbot certificates
```

## Полезные команды

```bash
# Статус основного сервиса
systemctl status star-burger.service

# Логи приложения
journalctl -u star-burger.service -n 100 --no-pager

# Логи деплоя
tail -f /var/log/star-burger-deploy.log

# Проверка конфига nginx
nginx -t
```

## Цель проекта

Код написан в учебных целях на курсе [dvmn.org](https://dvmn.org/).
