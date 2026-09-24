# Системная архитектура

## Компоненты

```text
Telegram Bot
  -> Backend API
  -> Database
  -> Background Jobs
  -> Telegram Notifications

Telegram Mini App
  -> Client API
  -> Backend API

Admin Web App
  -> Admin API
  -> Backend API
```

## Backend

Backend является единственным источником истины для:

- идентификации клиента по Telegram User ID;
- проверки ролей;
- tenant isolation;
- расчета доступных слотов;
- создания и изменения записей;
- изменения статусов записей;
- отправки уведомлений.

Frontend не определяет роль пользователя и не принимает решений о доступе к данным.

## Разделение API

API логически делится на три зоны:

- `Client API` - только клиентские операции Mini App.
- `Admin API` - операции администраторов и владельцев.
- `System/Internal API` - фоновые задачи, уведомления, интеграции.

Клиентские токены не должны давать доступ к `Admin API`. Административные endpoint'ы должны проверять роль и `organization_id` на каждом запросе.

## Модули backend

Рекомендуемая модульная структура:

```text
accounts
organizations
branches
customers
cars
services
workstations
schedules
bookings
reviews
notifications
analytics
auth
audit
```

## Tenant isolation

Правило по умолчанию: любой запрос к данным организации должен фильтроваться по `organization_id` из серверного auth context.

Запрещено:

- принимать `organization_id` от клиента как источник истины;
- возвращать записи другой организации;
- определять доступ только на frontend;
- строить admin-запросы без tenant filter.

Для `CLIENT` доступ ограничивается связкой `telegram_user_id -> customer -> organization_id` и личными объектами клиента.

Для `ADMIN` и `OWNER` доступ ограничивается организациями, к которым привязан административный аккаунт.

## Основные доменные связи

- `Organization` имеет много `Branch`.
- `Branch` имеет много `Workstation`.
- `Branch` имеет расписание и исключения расписания.
- `Organization` имеет много `Service`.
- `Customer` принадлежит `Organization`.
- `Car` принадлежит `Customer` и `Organization`.
- `Booking` принадлежит `Organization`, `Branch`, `Customer`, `Car`, `Service`.
- `Booking` может быть назначен на `Workstation`.
- `BookingStatusHistory` хранит историю изменения статусов.
- `Review` привязан к завершенной записи.
- `Notification` привязан к клиенту, записи и каналу отправки.

## Booking Engine

Booking Engine должен быть отдельным доменным сервисом, а не набором проверок внутри контроллеров. Он отвечает за:

- построение сетки слотов;
- учет расписания филиала;
- учет перерывов и исключений;
- учет длительности услуги;
- учет активных боксов;
- проверку пересечений;
- атомарное создание записи;
- перенос записи;
- отмену записи.

## Background Jobs

Фоновые задачи нужны для:

- отправки отложенных Telegram-уведомлений;
- напоминаний перед записью;
- повторных попыток отправки уведомлений;
- агрегации аналитики;
- технической очистки просроченных временных данных, если такие появятся позже.

Фоновая задача не должна обходить RBAC и tenant isolation. Если задача работает с данными организации, она должна явно получать `organization_id`.

## Рекомендуемая структура проекта

```text
MultiAuto/
  docs/
  backend/
    src/
      modules/
      common/
      database/
      jobs/
    tests/
  mini-app/
    src/
  admin-app/
    src/
  bot/
    src/
  README.md
```

На текущем этапе папки `backend`, `mini-app`, `admin-app` и `bot` не создаются как реализация. Они описывают целевую структуру.
