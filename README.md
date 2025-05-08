# vanlaack_stats

Проект: Телеграм-бот на aiogram для сбора выручки магазинов.

## Настройка окружения

1. Склонируйте репозиторий и перейдите в папку проекта.
2. Скопируйте файл `.env` и заполните переменные:
   ```
   BOT_TOKEN=ваш_токен
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost/dbname
   ADMIN_CHAT_IDS=<id_администратора1>,<id_администратора2>
   ```
   > Примечание: Вместо `ADMIN_CHAT_ID` теперь используется `ADMIN_CHAT_IDS`, который позволяет 
   > указать несколько ID администраторов через запятую. Для обратной совместимости поддерживается 
   > и старый вариант с одним ID.

## Настройка PostgreSQL

1. Создайте роль в Postgres, совпадающую с вашим системным пользователем или используйте свой логин:
   ```bash
   # Замените <user> на ваше имя пользователя, например edaltshuler
   createuser -s <user>
   createdb -O <user> dbname
   ```
2. Если вы хотите использовать другого пользователя, создайте его и задайте пароль:
   ```bash
   psql -U postgres -c "CREATE ROLE myuser WITH LOGIN PASSWORD 'mypassword';"
   psql -U postgres -c "CREATE DATABASE dbname OWNER myuser;"
   ```
3. Убедитесь, что `DATABASE_URL` в `.env` указывает на существующую базу.

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск бота

```bash
python app/main.py
```

## Команды бота

- `/start` — авторизация.
- `/revenue` — ввод выручки (менеджеры).
- `/setplan` — установка плана (администратор).
- `/report` — экспорт отчёта (администратор).

## Тестирование

```bash
pytest
```