# Booking logic

## Цель

Booking Engine должен показывать клиенту только реально доступные слоты и не допускать double booking при параллельных запросах.

На Stage 6 реализован базовый Booking Engine. Он использует:

- `Car` клиента;
- активные `Service` организации;
- `Branch`;
- `Workstation` филиала;
- `BusinessHour`;
- `ScheduleException`;
- utility `get_branch_schedule(branch, date)`;
- `Booking`;
- service layer `apps.bookings.services`.

## Входные параметры расчета слотов

- `organization_id` из server auth context.
- `branch_id`.
- `service_id`.
- `car_id` нужен при создании записи, но не нужен для расчета текущих слотов.
- `date`.
- timezone филиала.

## Данные для расчета

Booking Engine загружает:

- активный филиал;
- активную услугу;
- длительность услуги;
- активные боксы филиала;
- базовое расписание филиала на день недели;
- исключение расписания на конкретную дату;
- существующие записи филиала на выбранную дату в активных статусах.

Активные статусы, блокирующие слот:

```text
PENDING, CONFIRMED, ARRIVED, IN_PROGRESS, READY
```

`CANCELLED`, `COMPLETED`, `NO_SHOW` не блокируют слот.

## Расчет рабочего окна

1. Определить локальную дату филиала.
2. Проверить `schedule_exceptions` для даты.
3. Если исключение найдено и `is_closed = true`, вернуть пустой список.
4. Если исключение найдено и филиал открыт, использовать `opens_at` и `closes_at` из исключения.
5. Если исключения нет, использовать `branch_working_hours` по `weekday`.
6. Если рабочий день закрыт, вернуть пустой список.
7. Преобразовать локальные `opening_time` и `closing_time` филиала в timezone-aware datetime.
8. `Booking.start_at` и `Booking.end_at` хранить как timezone-aware значения.

## Учет перерывов

Перерывы как отдельная сущность пока не реализованы. Для MVP рабочее окно определяется через `BusinessHour` и `ScheduleException`. Когда появятся отдельные break windows, они должны вычитаться из рабочего окна тем же service layer, а не во frontend.

## Генерация слотов

На MVP используется фиксированный шаг сетки 30 минут.

Алгоритм:

1. Взять начало рабочего окна.
2. Округлить к ближайшему шагу сетки.
3. Для каждого потенциального `slot_start` рассчитать `slot_end = slot_start + service.duration_minutes`.
4. Проверить, что `slot_end <= closes_at`.
5. Проверить, что интервал не пересекает перерывы.
6. Проверить, что хотя бы один активный бокс свободен на весь интервал.
7. Добавить слот в результат.

## Проверка доступности боксов

Бокс свободен, если для него нет активной записи, пересекающей интервал:

```text
existing.starts_at < requested.ends_at
AND existing.ends_at > requested.starts_at
```

Клиент не выбирает `workstation_id`. Booking Engine на backend выбирает первый свободный активный бокс филиала внутри транзакции.

## Создание записи

Создание записи должно выполняться в транзакции:

1. Получить auth context.
2. Проверить, что клиент принадлежит `organization_id`.
3. Проверить, что автомобиль принадлежит клиенту и организации.
4. Проверить, что филиал принадлежит организации и активен.
5. Проверить, что услуга принадлежит организации и активна.
6. Рассчитать `ends_at`.
7. Повторно проверить расписание и доступность боксов.
8. Выбрать свободный `workstation_id`.
9. Заблокировать активные боксы филиала через `select_for_update()` на время транзакции.
10. Создать `booking` со статусом `PENDING`.
11. Сохранить snapshot цены в `Booking.price`.
12. Зафиксировать транзакцию.

## Защита от double booking

Минимальный уровень:

- транзакция;
- повторная проверка доступности внутри транзакции;
- блокировка активных `Workstation` филиала через `select_for_update()`;
- индекс по `workstation_id, starts_at, ends_at`.

Рекомендуемый уровень для PostgreSQL:

- хранить интервал записи как range или вычисляемое выражение;
- добавить exclusion constraint для активных статусов по `workstation_id` и временному диапазону;
- при конфликте возвращать клиенту ошибку `SLOT_UNAVAILABLE`.

Если две записи одновременно пытаются занять один слот, успешной должна быть только одна транзакция.

На Stage 6 используется transaction + row locking active workstations. PostgreSQL serializes concurrent allocation attempts for the same branch workstations. `ExclusionConstraint` пока не добавлен, потому что тестовая конфигурация проекта использует SQLite, а текущий вариант уже совместим с PostgreSQL и покрыт тестами. Перед production-нагрузкой можно добавить PostgreSQL-specific exclusion constraint как дополнительную database-level защиту.

## Перенос записи

Перенос доступен, если:

- запись принадлежит клиенту или организации администратора;
- статус позволяет перенос;
- новое время проходит все проверки доступности.

Статусы, из которых клиент может запросить перенос:

- `PENDING`
- `CONFIRMED`

`ADMIN` и `OWNER` могут переносить записи из:

- `PENDING`
- `CONFIRMED`
- `ARRIVED`

Не переносить из:

- `IN_PROGRESS`
- `READY`
- `COMPLETED`
- `CANCELLED`
- `NO_SHOW`

Перенос выполняется в транзакции с повторной проверкой доступности и записью в audit/status history.

## Отмена записи

`CLIENT` может отменить только свою запись в статусе:

- `PENDING`

`ADMIN` и `OWNER` могут отменить запись организации в статусах:

- `PENDING`
- `CONFIRMED`

При отмене:

- статус меняется на `CANCELLED`;
- запись перестает блокировать слот;
- уведомления и status history будут добавлены отдельным этапом.

## Переходы статусов

Разрешенные переходы:

| From | To | Кто |
|---|---|---|
| `PENDING` | `CONFIRMED` | ADMIN, OWNER, SYSTEM |
| `PENDING` | `CANCELLED` | CLIENT, ADMIN, OWNER |
| `PENDING` | `NO_SHOW` | ADMIN, OWNER |
| `CONFIRMED` | `ARRIVED` | ADMIN, OWNER |
| `CONFIRMED` | `CANCELLED` | ADMIN, OWNER |
| `CONFIRMED` | `NO_SHOW` | ADMIN, OWNER |
| `ARRIVED` | `IN_PROGRESS` | ADMIN, OWNER |
| `IN_PROGRESS` | `READY` | ADMIN, OWNER |
| `READY` | `COMPLETED` | ADMIN, OWNER |

Финальные статусы:

- `COMPLETED`
- `CANCELLED`
- `NO_SHOW`

Из финальных статусов переходы запрещены.

## История статусов

`booking_status_history` остается запланированной сущностью. На Stage 6 переходы статусов валидируются в service layer, но отдельная audit history не реализована.

- прежний статус;
- новый статус;
- кто изменил;
- причина;
- дата изменения.

История не редактируется и не удаляется обычными операциями.
