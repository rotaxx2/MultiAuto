# API plan

## Общие принципы

- Все endpoint'ы версионируются: `/api/v1`.
- Client API и Admin API разделены по namespace.
- Backend проверяет auth, role и tenant isolation на каждом защищенном endpoint.
- `organization_id` берется из server auth context, а не из произвольного тела запроса.
- Все списки должны поддерживать pagination.

## Client API

### Telegram auth

| Method | Endpoint | Назначение |
|---|---|---|
| `POST` | `/api/v1/client/auth/telegram` | Проверить Telegram Mini App init data и выдать client session token. |
| `POST` | `/api/v1/client/auth/logout` | Завершить client session. |

Реализовано на текущем этапе:

- `POST /api/v1/client/auth/telegram` принимает `init_data` и опциональный `start_param`;
- backend проверяет подпись Telegram `initData`;
- backend проверяет срок действия `auth_date`;
- backend находит или создает `User` с ролью `CLIENT`;
- backend возвращает DRF token для заголовка `Authorization: Token <token>`.

### Профиль клиента

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/v1/client/me` | Получить профиль клиента. |
| `PATCH` | `/api/v1/client/me` | Обновить доступные поля профиля. |

Дополнительно для текущей интеграции доступны короткие клиентские endpoint'ы:

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/me/` | Получить профиль текущего клиента. |
| `GET` | `/api/my-profile/` | Получить профиль текущего клиента. |
| `GET` | `/api/my-cars/` | Список автомобилей текущего клиента. |
| `GET` | `/api/my-bookings/` | Список записей текущего клиента. |

### Реализованные booking endpoints Stage 6

| Method | Endpoint | Role | Описание |
|---|---|---|---|
| `GET` | `/api/branches/{branch_id}/availability/?date=YYYY-MM-DD&service_id={id}` | CLIENT | Возвращает доступные слоты филиала для активной услуги. Не раскрывает workstation и чужие booking data. |
| `POST` | `/api/bookings/` | CLIENT | Создает запись. Клиент передает `branch_id`, `car_id`, `service_id`, `start_at`, `client_comment`. Backend сам определяет `organization`, `client`, `workstation`, `end_at`, `status`, `price`. |
| `GET` | `/api/my-bookings/` | CLIENT | Список записей текущего клиента. |
| `GET` | `/api/my-bookings/{id}/` | CLIENT | Детали только своей записи. Чужие записи не раскрываются. |
| `POST` | `/api/my-bookings/{id}/cancel/` | CLIENT | Отмена своей записи в статусе `PENDING`. |
| `GET` | `/api/admin/bookings/` | ADMIN, OWNER | Список записей своей организации. |
| `GET` | `/api/admin/bookings/{id}/` | ADMIN, OWNER | Детали записи своей организации. |
| `PATCH` | `/api/admin/bookings/{id}/` | ADMIN, OWNER | Изменение `status` и `admin_comment` с проверкой допустимых переходов. |

`POST /api/bookings/` не принимает `organization_id`, `client_id`, `workstation_id`, `end_at`, `status`, `price`. Эти поля определяются backend.

Эти endpoint'ы не принимают `user_id` из URL или query params для выбора владельца данных.

Frontend Mini App использует:

- `POST /api/v1/client/auth/telegram` для обмена Telegram `initData` на DRF token;
- `GET /api/my-profile/` для загрузки профиля;
- `GET /api/my-cars/` для текущего списка автомобилей;
- `GET /api/my-bookings/` для текущего списка записей.

Все запросы после авторизации отправляются с:

```text
Authorization: Token <token>
```

`GET /api/my-cars/` теперь реализован как полноценный CRUD:

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/my-cars/` | Список автомобилей текущего клиента. |
| `POST` | `/api/my-cars/` | Добавить автомобиль текущему клиенту. |
| `GET` | `/api/my-cars/{id}/` | Получить свой автомобиль. |
| `PATCH` | `/api/my-cars/{id}/` | Обновить свой автомобиль. |
| `DELETE` | `/api/my-cars/{id}/` | Удалить свой автомобиль. |

### Автомобили клиента

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/v1/client/cars` | Список своих автомобилей. |
| `POST` | `/api/v1/client/cars` | Добавить автомобиль. |
| `GET` | `/api/v1/client/cars/{car_id}` | Получить свой автомобиль. |
| `PATCH` | `/api/v1/client/cars/{car_id}` | Обновить свой автомобиль. |
| `DELETE` | `/api/v1/client/cars/{car_id}` | Удалить свой автомобиль. |

### Услуги и филиалы

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/v1/client/branches` | Список активных филиалов организации. |
| `GET` | `/api/v1/client/services` | Список активных услуг. |
| `GET` | `/api/v1/client/vehicle-types` | Список типов автомобилей. |

Дополнительно реализованы:

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/services/` | Активные услуги организации клиента. |
| `GET` | `/api/branches/` | Активные филиалы организации клиента. |
| `GET` | `/api/branches/{id}/services/` | Активные услуги организации для выбранного филиала. |
| `GET` | `/api/branches/{id}/schedule/?date=YYYY-MM-DD` | Рабочее время филиала на дату с учетом исключений. |

### Записи

| Method | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/v1/client/booking-slots` | Получить доступные слоты по филиалу, услуге, автомобилю и дате. |
| `GET` | `/api/v1/client/bookings` | Список своих записей. |
| `POST` | `/api/v1/client/bookings` | Создать запись. |
| `GET` | `/api/v1/client/bookings/{booking_id}` | Получить свою запись. |
| `POST` | `/api/v1/client/bookings/{booking_id}/reschedule` | Перенести свою запись. |
| `POST` | `/api/v1/client/bookings/{booking_id}/cancel` | Отменить свою запись. |
| `GET` | `/api/v1/client/bookings/history` | История своих записей. |

### Отзывы

| Method | Endpoint | Назначение |
|---|---|---|
| `POST` | `/api/v1/client/bookings/{booking_id}/review` | Оставить отзыв по завершенной записи. |
| `GET` | `/api/v1/client/reviews` | Список своих отзывов. |

## Admin API

### Admin auth

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `POST` | `/api/v1/admin/auth/login` | ADMIN, OWNER | Войти в административную часть. |
| `POST` | `/api/v1/admin/auth/logout` | ADMIN, OWNER | Выйти. |
| `GET` | `/api/v1/admin/auth/me` | ADMIN, OWNER | Получить текущего администратора. |

### Dashboard и аналитика

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/dashboard` | ADMIN, OWNER | Операционные метрики организации. |
| `GET` | `/api/v1/admin/analytics` | OWNER | Общая аналитика организации. |

### Bookings

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/bookings` | ADMIN, OWNER | Список записей организации. |
| `POST` | `/api/v1/admin/bookings` | ADMIN, OWNER | Создать запись от имени клиента. |
| `GET` | `/api/v1/admin/bookings/{booking_id}` | ADMIN, OWNER | Детали записи. |
| `PATCH` | `/api/v1/admin/bookings/{booking_id}` | ADMIN, OWNER | Обновить административные поля. |
| `POST` | `/api/v1/admin/bookings/{booking_id}/status` | ADMIN, OWNER | Изменить статус. |
| `POST` | `/api/v1/admin/bookings/{booking_id}/reschedule` | ADMIN, OWNER | Перенести запись. |
| `POST` | `/api/v1/admin/bookings/{booking_id}/cancel` | ADMIN, OWNER | Отменить запись. |

### Calendar

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/calendar` | ADMIN, OWNER | Календарное представление записей по филиалу и датам. |

### Customers и cars

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/customers` | ADMIN, OWNER | Список клиентов организации. |
| `POST` | `/api/v1/admin/customers` | ADMIN, OWNER | Создать клиента вручную. |
| `GET` | `/api/v1/admin/customers/{customer_id}` | ADMIN, OWNER | Детали клиента. |
| `PATCH` | `/api/v1/admin/customers/{customer_id}` | ADMIN, OWNER | Обновить клиента. |
| `GET` | `/api/v1/admin/customers/{customer_id}/cars` | ADMIN, OWNER | Автомобили клиента. |
| `POST` | `/api/v1/admin/customers/{customer_id}/cars` | ADMIN, OWNER | Добавить автомобиль клиенту. |
| `PATCH` | `/api/v1/admin/cars/{car_id}` | ADMIN, OWNER | Обновить автомобиль. |
| `DELETE` | `/api/v1/admin/cars/{car_id}` | ADMIN, OWNER | Удалить автомобиль. |

### Services

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/services` | ADMIN, OWNER | Список услуг. |
| `POST` | `/api/v1/admin/services` | ADMIN, OWNER | Создать услугу. |
| `PATCH` | `/api/v1/admin/services/{service_id}` | ADMIN, OWNER | Обновить услугу. |
| `DELETE` | `/api/v1/admin/services/{service_id}` | ADMIN, OWNER | Деактивировать услугу. |

### Workstations и schedule

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/workstations` | ADMIN, OWNER | Список боксов. |
| `POST` | `/api/v1/admin/workstations` | ADMIN, OWNER | Создать бокс. |
| `PATCH` | `/api/v1/admin/workstations/{workstation_id}` | ADMIN, OWNER | Обновить бокс. |
| `GET` | `/api/v1/admin/schedule` | ADMIN, OWNER | Получить расписание филиала. |
| `PUT` | `/api/v1/admin/schedule/working-hours` | ADMIN, OWNER | Обновить рабочие часы. |
| `PUT` | `/api/v1/admin/schedule/breaks` | ADMIN, OWNER | Обновить перерывы. |
| `PUT` | `/api/v1/admin/schedule/exceptions` | ADMIN, OWNER | Обновить исключения. |

Текущие реализованные admin endpoints:

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET/POST` | `/api/admin/services/` | ADMIN, OWNER | Список и создание услуг своей организации. |
| `GET/PATCH/DELETE` | `/api/admin/services/{id}/` | ADMIN, OWNER | Управление услугой своей организации. |
| `GET/POST` | `/api/admin/workstations/` | ADMIN, OWNER | Список и создание боксов филиалов своей организации. |
| `GET/PATCH/DELETE` | `/api/admin/workstations/{id}/` | ADMIN, OWNER | Управление боксом своей организации. |
| `GET/POST` | `/api/admin/business-hours/` | ADMIN, OWNER | Рабочие часы филиалов своей организации. |
| `GET/PATCH/DELETE` | `/api/admin/business-hours/{id}/` | ADMIN, OWNER | Управление рабочими часами. |
| `GET/POST` | `/api/admin/schedule-exceptions/` | ADMIN, OWNER | Исключения расписания филиалов своей организации. |
| `GET/PATCH/DELETE` | `/api/admin/schedule-exceptions/{id}/` | ADMIN, OWNER | Управление исключением расписания. |

### Reviews

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/reviews` | ADMIN, OWNER | Список отзывов организации. |

### Owner-only

| Method | Endpoint | Роли | Назначение |
|---|---|---|---|
| `GET` | `/api/v1/admin/administrators` | OWNER | Список администраторов. |
| `POST` | `/api/v1/admin/administrators` | OWNER | Создать администратора. |
| `PATCH` | `/api/v1/admin/administrators/{admin_id}` | OWNER | Обновить администратора. |
| `POST` | `/api/v1/admin/administrators/{admin_id}/deactivate` | OWNER | Деактивировать администратора. |
| `GET` | `/api/v1/admin/branches` | OWNER | Список филиалов. |
| `POST` | `/api/v1/admin/branches` | OWNER | Создать филиал. |
| `PATCH` | `/api/v1/admin/branches/{branch_id}` | OWNER | Обновить филиал. |
| `GET` | `/api/v1/admin/organization/settings` | OWNER | Настройки организации. |
| `PATCH` | `/api/v1/admin/organization/settings` | OWNER | Обновить настройки организации. |

## Internal API / jobs

Внутренние операции не должны быть публичными endpoint'ами без защиты.

Планируемые операции:

- обработка pending notifications;
- отправка Telegram-сообщений;
- повторные попытки failed notifications;
- отмена будущих уведомлений при отмене записи;
- агрегация статистики.

## Ошибки API

Единый формат ошибки:

```json
{
  "error": {
    "code": "SLOT_UNAVAILABLE",
    "message": "Selected time slot is unavailable",
    "details": {}
  }
}
```

Ключевые коды:

- `UNAUTHORIZED`
- `FORBIDDEN`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `SLOT_UNAVAILABLE`
- `BOOKING_STATUS_INVALID`
- `TENANT_ACCESS_DENIED`
- `RATE_LIMITED`
