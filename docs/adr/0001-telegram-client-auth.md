# ADR 0001: Telegram client auth через DRF TokenAuthentication

## Статус

Принято.

## Контекст

Клиенты MultiAuto не используют email/password. Основной внешний идентификатор клиента - Telegram User ID. Telegram Mini App передает backend строку `initData`, которую нельзя считать доверенной без server-side проверки подписи.

На текущем этапе нужно дать Mini App простой защищенный способ вызывать клиентские API, не реализуя еще полноценный JWT/refresh-token слой и административную auth-систему.

## Решение

Backend проверяет Telegram Mini App `initData` по Telegram Bot Token:

- валидирует HMAC подпись;
- проверяет `auth_date`;
- извлекает Telegram user payload;
- находит или создает `User` с ролью `CLIENT`;
- возвращает DRF token.

Клиентские API используют `Authorization: Token <token>` и permission class `IsClient`.

## Последствия

- Frontend не передает произвольный `user_id` как источник истины.
- Backend определяет клиента только из проверенного Telegram payload и server-side token.
- Текущий подход прост для MVP и совместим с будущей заменой на JWT/refresh token rotation.
- При переходе на JWT нужно сохранить прежний принцип: Telegram подпись проверяется только на backend, а `organization_id` и пользователь берутся из server auth context.
