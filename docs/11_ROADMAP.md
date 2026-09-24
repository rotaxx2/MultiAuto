# Roadmap

## Этап 0: архитектурная основа

Результат:

- продуктовые требования;
- системная архитектура;
- роли и permissions;
- database design;
- booking logic;
- API plan;
- Telegram flow;
- Mini App flow;
- Admin flow;
- security plan.

## Этап 1: backend foundation

Задачи:

- выбрать backend stack;
- настроить проект backend;
- подключить database;
- описать миграции основных сущностей;
- реализовать auth context;
- реализовать tenant-aware repositories или query layer;
- добавить базовые тесты tenant isolation.

## Этап 2: Telegram client auth

Задачи:

- создать Telegram Bot;
- реализовать `/start`;
- реализовать проверку Telegram Mini App init data;
- создавать или находить customer;
- выпускать client session token;
- добавить client endpoint `/me`.

## Этап 3: client domain

Задачи:

- реализовать vehicle types;
- реализовать CRUD автомобилей клиента;
- реализовать просмотр филиалов и услуг;
- реализовать историю записей клиента;
- покрыть IDOR tests для client API.

## Этап 4: booking engine

Задачи:

- реализовать расписание филиала;
- реализовать перерывы и исключения;
- реализовать расчет слотов;
- реализовать создание записи;
- реализовать перенос и отмену;
- реализовать защиту от double booking;
- покрыть race-condition tests.

## Этап 5: admin MVP

Задачи:

- admin auth;
- dashboard;
- bookings list;
- calendar;
- customers;
- cars;
- services;
- workstations;
- schedule;
- reviews;
- status transitions;
- audit log.

## Этап 6: owner features

Задачи:

- administrators management;
- branches management;
- organization settings;
- owner analytics;
- ограничения, чтобы в организации оставался минимум один owner.

## Этап 7: notifications

Задачи:

- notifications table;
- background worker;
- Telegram sender;
- booking confirmation;
- reminders;
- booking changed;
- booking cancelled;
- car ready;
- review request.

## Этап 8: Mini App frontend

Задачи:

- Telegram Mini App shell;
- Telegram auth integration;
- главная страница;
- автомобили;
- выбор услуги;
- выбор даты и слота;
- создание записи;
- текущая запись;
- перенос и отмена;
- история;
- отзывы.

## Этап 9: production readiness

Задачи:

- observability;
- structured logging;
- error tracking;
- backups;
- rate limiting;
- security headers;
- production secrets;
- load testing booking engine;
- deployment plan.

## Возможные будущие модули

Архитектура должна позволять добавить:

- онлайн-оплату;
- промокоды;
- маркетинговые рассылки;
- расширенную аналитику;
- несколько филиалов;
- подписки для автомоек.

Эти модули не входят в текущий MVP и не должны блокировать запуск базовой записи.
