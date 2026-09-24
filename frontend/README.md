# MultiAuto Mini App

React + TypeScript Telegram Mini App для клиентской части MultiAuto.

## Запуск

```powershell
npm install
npm run dev
```

По умолчанию Vite запускается на:

```text
http://localhost:5173
```

## Environment

Создайте локальный `.env` рядом с `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

`VITE_API_URL` - адрес Django backend. Секреты Telegram Bot сюда не добавляются.

## Auth flow

Mini App получает `window.Telegram.WebApp.initData` и отправляет его на backend:

```text
POST /api/v1/client/auth/telegram
```

Backend проверяет подпись Telegram и возвращает DRF token. Frontend использует token для запросов:

```text
Authorization: Token <token>
```
