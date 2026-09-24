# Telegram flow

## Назначение Telegram Bot

Telegram Bot нужен для:

- первичной точки входа клиента;
- идентификации клиента через Telegram User ID;
- открытия Telegram Mini App;
- отправки сервисных уведомлений.

Клиент не создает email/password аккаунт.

## /start

Сценарий:

1. Клиент открывает бота.
2. Клиент отправляет `/start`.
3. Bot получает Telegram user information:
   - `telegram_user_id`;
   - `username`;
   - `first_name`;
   - `last_name`;
   - `language_code`, если доступен.
4. Bot передает данные в backend.
5. Backend определяет организацию.
6. Backend создает или обновляет `customer`.
7. Bot отправляет сообщение с кнопкой открытия Mini App.

## Определение организации

Для MVP возможны два варианта:

- отдельный бот на организацию;
- один бот с deep link параметром организации.

Рекомендуемое решение для масштабирования: поддержать deep link:

```text
/start org_<organization_slug>
```

Backend должен проверить, что организация активна. Если организация не найдена или выключена, бот показывает нейтральное сообщение об ошибке.

## Открытие Mini App

Bot отправляет кнопку:

```text
Открыть запись
```

Кнопка открывает Telegram Mini App. Mini App получает `initData` от Telegram и отправляет его на:

```text
POST /api/v1/client/auth/telegram
```

Backend проверяет подпись Telegram init data и создает client session.

## Telegram authentication

Backend должен:

- валидировать подпись `initData`;
- проверять свежесть `auth_date`;
- извлекать Telegram user id;
- находить или создавать `customer`;
- связывать клиента с `organization_id`;
- выпускать session token для Client API.

Mini App не должен доверять данным Telegram без проверки backend.

## Уведомления

Типы уведомлений:

- подтверждение записи;
- напоминание перед записью;
- изменение записи;
- отмена записи;
- уведомление о готовности автомобиля;
- просьба оставить отзыв после завершения услуги.

Уведомления создаются как записи в `notifications`, а отправляются фоновой задачей.

## Примеры событий

### Создание записи

1. Booking Engine создает запись.
2. Создается notification `BOOKING_CREATED`.
3. Создается отложенная notification `BOOKING_REMINDER`.
4. Background worker отправляет сообщение в Telegram.

### Изменение статуса на READY

1. `ADMIN` меняет статус записи на `READY`.
2. Backend пишет `booking_status_history`.
3. Backend создает notification `CAR_READY`.
4. Background worker отправляет Telegram-сообщение клиенту.

### Отмена записи

1. Запись получает статус `CANCELLED`.
2. Будущие pending notifications по записи отменяются.
3. Создается notification `BOOKING_CANCELLED`.

## Ограничения

- Bot не должен выполнять административные операции.
- Bot не должен раскрывать данные другой организации.
- Bot не должен принимать произвольный `customer_id` от пользователя.
- Bot не должен заменять backend authorization.
