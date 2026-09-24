# Security

## Authentication

В системе два независимых auth flow:

- клиентский Telegram auth для Mini App;
- административный auth для Admin App.

Клиент не использует email/password. Администраторы и владельцы используют отдельные административные учетные записи.

## Telegram authentication

Backend должен:

- принимать Telegram Mini App `initData`;
- проверять подпись по Telegram Bot Token;
- проверять `auth_date`;
- отклонять устаревшие auth payload;
- извлекать `telegram_user_id`;
- создавать или находить `customer`;
- выпускать собственный session token для Client API.

Нельзя доверять Telegram user data, если подпись не проверена backend.

Реализация текущего этапа:

- проверка `initData` находится на backend;
- подпись проверяется по Telegram Bot Token через HMAC SHA-256 по алгоритму Telegram Mini Apps;
- `auth_date` ограничен настройкой `TELEGRAM_AUTH_MAX_AGE_SECONDS`;
- после успешной проверки backend выдает DRF token;
- клиентские API принимают только `Authorization: Token <token>`;
- `telegram_id` из обычного request body, query params или URL не используется как источник истины.

## Admin authentication

Для `ADMIN` и `OWNER`:

- email и пароль;
- пароль хранится только как hash;
- inactive admin не может войти;
- желательно добавить refresh token rotation;
- желательно добавить MFA после MVP.

Admin session token должен содержать минимум:

- `admin_user_id`;
- `role`;
- `organization_id`;
- срок действия.

## Authorization

Backend проверяет права на каждом защищенном endpoint.

Проверки:

- пользователь аутентифицирован;
- роль имеет право на действие;
- объект принадлежит `organization_id`;
- клиент обращается только к своим объектам;
- admin не выходит за границы организации.

Для клиентских endpoint'ов текущего этапа добавлен permission class `IsClient`. Он требует:

- authenticated user;
- `is_active = true`;
- `role = CLIENT`.

## RBAC

RBAC основан на трех ролях:

- `CLIENT`;
- `ADMIN`;
- `OWNER`.

Роль `CLIENT` не должна иметь доступ к `/api/v1/admin/*`.

Роль `ADMIN` не должна иметь доступ к owner-only endpoint'ам:

- administrators;
- branches management;
- organization settings;
- full analytics.

## Tenant isolation

Правила:

- все tenant-запросы фильтруются по `organization_id`;
- `organization_id` берется из auth context;
- ID объектов из path params всегда проверяются на принадлежность организации;
- нельзя возвращать `404` и данные другой организации;
- при попытке доступа к чужому объекту возвращать `404` или `FORBIDDEN` по выбранной политике, но без раскрытия деталей.

## Protection against IDOR

Для каждого endpoint с `{id}`:

1. Получить объект по `id` и `organization_id`.
2. Для Client API дополнительно проверить `customer_id`.
3. Если объект не найден в доступной области, вернуть `NOT_FOUND`.
4. Не выполнять update/delete без tenant filter.

Пример:

```text
Client can update car only where:
cars.id = car_id
AND cars.organization_id = auth.organization_id
AND cars.customer_id = auth.customer_id
```

Текущие endpoint'ы `/api/me/`, `/api/my-profile/`, `/api/my-cars/`, `/api/my-bookings/` не принимают `user_id` для выбора владельца данных. Пользователь определяется только из token auth.

## CORS и CSRF для Mini App

Backend разрешает frontend origins через environment variables:

```text
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
```

Для local development обычно используется:

```text
http://localhost:5173
```

Постоянное `CORS_ALLOW_ALL_ORIGINS = True` не используется. Production origins должны быть перечислены явно.

## Frontend secrets

Во frontend `.env` допускаются только публичные значения, например:

```text
VITE_API_URL
```

`TELEGRAM_BOT_TOKEN`, database credentials, Django `SECRET_KEY` и другие секреты никогда не передаются в React/Vite приложение.

## API security

Требования:

- HTTPS в production;
- CORS только для разрешенных frontend origin;
- строгая validation schema для каждого request body;
- ограничение размеров payload;
- единый формат ошибок;
- безопасные заголовки;
- запрет verbose stack traces в production;
- логирование security events.

## Rate limiting

Нужно ограничивать:

- admin login attempts по IP и email;
- Telegram auth attempts по Telegram user id и IP;
- создание booking;
- запросы доступных слотов;
- отправку отзывов;
- любые endpoint'ы, которые могут вызвать дорогие вычисления.

## Validation

Проверять:

- формат `license_plate`;
- допустимость `vehicle_type`;
- положительную длительность услуги;
- неотрицательную цену;
- корректность рабочего времени;
- отсутствие пересечения перерывов с некорректными интервалами;
- допустимость переходов статусов;
- принадлежность связанных сущностей одной организации.

## Booking security

Нельзя доверять слоту, выбранному на frontend.

При создании и переносе записи backend всегда:

- повторно рассчитывает доступность;
- проверяет активность услуги;
- проверяет активность филиала;
- проверяет активность бокса;
- проверяет пересечения;
- выполняет операцию в транзакции.

## Administrative endpoint protection

Для всех `/api/v1/admin/*`:

- требуется admin session;
- требуется роль `ADMIN` или `OWNER`;
- owner-only endpoint'ы требуют `OWNER`;
- все запросы scoped by `organization_id`;
- действия пишутся в audit log.

## Notification security

Фоновый worker отправляет уведомления только по записям из своей организации и только тем клиентам, которые связаны с booking.

Notification payload не должен хранить секреты. Ошибки отправки не должны раскрывать bot token.

## Secrets

В secrets входят:

- Telegram Bot Token;
- JWT signing secret;
- database credentials;
- credentials email/SMS providers, если появятся позже.

Secrets не хранятся в git и передаются через environment или secret manager.
