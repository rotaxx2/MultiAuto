# Database design

## Общие правила

- Основной идентификатор: `id` UUID.
- Все tenant-сущности содержат `organization_id`.
- Временные поля хранятся в UTC: `created_at`, `updated_at`, `deleted_at`.
- Для soft delete используется `deleted_at`, если сущность не должна физически удаляться.
- Денежные значения хранятся в минимальных единицах валюты: `base_price_amount`.
- Все внешние ключи индексируются.

## organizations

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `name` | varchar(255) | not null |
| `slug` | varchar(100) | not null, unique |
| `timezone` | varchar(64) | not null |
| `currency` | char(3) | not null |
| `is_active` | boolean | not null, default true |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Индексы:

- unique `organizations_slug_uq(slug)`.

## branches

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `name` | varchar(255) | not null |
| `address` | text | not null |
| `phone` | varchar(32) | nullable |
| `timezone` | varchar(64) | not null |
| `is_active` | boolean | not null, default true |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, name)`.

Индексы:

- `branches_organization_id_idx`.
- `branches_organization_active_idx(organization_id, is_active)`.

## admin_users

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `role` | enum(`ADMIN`, `OWNER`) | not null |
| `email` | varchar(255) | not null |
| `password_hash` | text | not null |
| `full_name` | varchar(255) | not null |
| `is_active` | boolean | not null, default true |
| `last_login_at` | timestamp | nullable |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, email)`.
- check `role in ('ADMIN', 'OWNER')`.

Индексы:

- `admin_users_org_role_idx(organization_id, role)`.

## customers

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `telegram_user_id` | bigint | not null |
| `telegram_username` | varchar(255) | nullable |
| `first_name` | varchar(255) | nullable |
| `last_name` | varchar(255) | nullable |
| `phone` | varchar(32) | nullable |
| `is_active` | boolean | not null, default true |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, telegram_user_id)`.

Индексы:

- `customers_org_telegram_idx(organization_id, telegram_user_id)`.
- `customers_org_phone_idx(organization_id, phone)`.

## vehicle_types

Справочник типов автомобилей.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `code` | varchar(50) | not null, unique |
| `name` | varchar(100) | not null |
| `sort_order` | integer | not null, default 0 |
| `is_active` | boolean | not null, default true |

Начальные значения: `sedan`, `crossover`, `suv`, `minivan`, `other`.

## cars

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `owner_id` | UUID | FK -> accounts_user.id, not null |
| `brand` | varchar(100) | not null |
| `model` | varchar(100) | not null |
| `license_plate` | varchar(32) | not null |
| `color` | varchar(50) | not null |
| `year` | smallint | nullable |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(owner_id, license_plate)`.
- `license_plate` хранится в нормализованном виде: uppercase, без пробелов.

Индексы:

- `cars_owner_idx(owner_id)`.
- `cars_owner_plate_idx(owner_id, license_plate)`.

## services

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `name` | varchar(255) | not null |
| `description` | text | nullable |
| `duration_minutes` | integer | not null |
| `price` | decimal(10,2) | not null |
| `is_active` | boolean | not null, default true |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |
| `deleted_at` | timestamp | nullable |

Ограничения:

- check `duration_minutes > 0`.
- check `price >= 0`.
- unique `(organization_id, name)`.

Индексы:

- `services_org_active_idx(organization_id, is_active)`.

## service_vehicle_prices

Опциональная таблица для будущей цены по типу автомобиля.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `service_id` | UUID | FK -> services.id, not null |
| `vehicle_type_id` | UUID | FK -> vehicle_types.id, not null |
| `price_amount` | integer | not null |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, service_id, vehicle_type_id)`.
- check `price_amount >= 0`.

## workstations

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `branch_id` | UUID | FK -> branches.id, not null |
| `name` | varchar(100) | not null |
| `is_active` | boolean | not null, default true |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, branch_id, name)`.

В реализации `organization_id` получается через `branch.organization_id`; API всегда фильтрует по организации пользователя.

Индексы:

- `workstations_branch_active_idx(organization_id, branch_id, is_active)`.

## business_hours

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `branch_id` | UUID | FK -> branches.id, not null |
| `weekday` | integer | not null, 0-6 |
| `opening_time` | time | nullable |
| `closing_time` | time | nullable |
| `is_closed` | boolean | not null, default false |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(branch_id, weekday)`.
- weekday: `0 = Monday`, `6 = Sunday`.
- if `is_closed = false`, `opening_time` and `closing_time` are not null and `opening_time < closing_time`.

## branch_breaks

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `branch_id` | UUID | FK -> branches.id, not null |
| `weekday` | integer | nullable |
| `date` | date | nullable |
| `starts_at` | time | not null |
| `ends_at` | time | not null |
| `is_active` | boolean | not null, default true |

Ограничения:

- check `starts_at < ends_at`.
- check either `weekday` or `date` is set.

## schedule_exceptions

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `branch_id` | UUID | FK -> branches.id, not null |
| `date` | date | not null |
| `opening_time` | time | nullable |
| `closing_time` | time | nullable |
| `is_closed` | boolean | not null, default false |
| `reason` | varchar(255) | nullable |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Ограничения:

- unique `(branch_id, date)`.
- if `is_closed = false`, `opening_time` and `closing_time` are not null and `opening_time < closing_time`.

`ScheduleException` имеет приоритет над `BusinessHour`.

## bookings

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `branch_id` | UUID | FK -> branches.id, not null |
| `client_id` | UUID | FK -> accounts_customuser.id, not null |
| `car_id` | UUID | FK -> cars.id, not null |
| `service_id` | UUID | FK -> services.id, not null |
| `workstation_id` | UUID | FK -> workstations.id, not null |
| `status` | enum | not null |
| `start_at` | timestamptz | not null |
| `end_at` | timestamptz | not null |
| `price` | decimal(10,2) | not null |
| `client_comment` | text | nullable |
| `admin_comment` | text | nullable |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Статусы:

- `PENDING`
- `CONFIRMED`
- `ARRIVED`
- `IN_PROGRESS`
- `READY`
- `COMPLETED`
- `CANCELLED`
- `NO_SHOW`

Ограничения:

- business validation `start_at < end_at`.
- business validation `price >= 0`.
- `car_id`, `client_id`, `service_id`, `branch_id`, `workstation_id` должны принадлежать тому же `organization_id`.
- `price` хранит snapshot цены услуги на момент создания записи.

Индексы:

- `book_org_branch_start_idx(organization_id, branch_id, start_at)`.
- `book_client_start_idx(client_id, start_at)`.
- `book_org_status_idx(organization_id, status)`.
- `book_ws_time_idx(workstation_id, start_at, end_at)`.

Защита от double booking:

- на уровне транзакции блокировать активные боксы филиала через `select_for_update()`;
- повторно проверять пересечения по `workstation_id`;
- перед production-нагрузкой можно усилить защиту PostgreSQL-specific `ExclusionConstraint` для активных статусов.

Активные статусы для блокировки слота:

```text
PENDING, CONFIRMED, ARRIVED, IN_PROGRESS, READY
```

## booking_status_history

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `booking_id` | UUID | FK -> bookings.id, not null |
| `from_status` | enum | nullable |
| `to_status` | enum | not null |
| `changed_by_type` | enum(`CLIENT`, `ADMIN`, `OWNER`, `SYSTEM`) | not null |
| `changed_by_id` | UUID | nullable |
| `reason` | text | nullable |
| `created_at` | timestamp | not null |

Индексы:

- `booking_status_history_booking_idx(booking_id, created_at)`.
- `booking_status_history_org_idx(organization_id, created_at)`.

## reviews

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `booking_id` | UUID | FK -> bookings.id, not null |
| `customer_id` | UUID | FK -> customers.id, not null |
| `rating` | integer | not null |
| `comment` | text | nullable |
| `created_at` | timestamp | not null |

Ограничения:

- unique `(organization_id, booking_id)`.
- check `rating between 1 and 5`.
- booking must be `COMPLETED`.

## notifications

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK -> organizations.id, not null |
| `customer_id` | UUID | FK -> customers.id, nullable |
| `booking_id` | UUID | FK -> bookings.id, nullable |
| `channel` | enum(`TELEGRAM`) | not null |
| `type` | varchar(100) | not null |
| `status` | enum(`PENDING`, `SENT`, `FAILED`, `CANCELLED`) | not null |
| `payload` | jsonb | not null |
| `scheduled_at` | timestamp | nullable |
| `sent_at` | timestamp | nullable |
| `failed_at` | timestamp | nullable |
| `retry_count` | integer | not null, default 0 |
| `error_message` | text | nullable |
| `created_at` | timestamp | not null |
| `updated_at` | timestamp | not null |

Индексы:

- `notifications_status_scheduled_idx(status, scheduled_at)`.
- `notifications_org_customer_idx(organization_id, customer_id)`.

## audit_log

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | nullable |
| `actor_type` | varchar(50) | not null |
| `actor_id` | UUID | nullable |
| `action` | varchar(100) | not null |
| `entity_type` | varchar(100) | not null |
| `entity_id` | UUID | nullable |
| `metadata` | jsonb | nullable |
| `created_at` | timestamp | not null |

Индексы:

- `audit_log_org_created_idx(organization_id, created_at desc)`.
- `audit_log_entity_idx(entity_type, entity_id)`.
