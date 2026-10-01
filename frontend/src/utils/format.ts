import { ApiError } from '../api/client';

export const bookingStatusLabels: Record<string, string> = {
  PENDING: 'Ожидает подтверждения',
  CONFIRMED: 'Подтверждена',
  ARRIVED: 'Клиент прибыл',
  IN_PROGRESS: 'В процессе',
  READY: 'Готово',
  COMPLETED: 'Завершена',
  CANCELLED: 'Отменена',
  NO_SHOW: 'Неявка',
};

export const bookingStatusTone: Record<string, string> = {
  PENDING: 'warning',
  CONFIRMED: 'info',
  ARRIVED: 'info',
  IN_PROGRESS: 'progress',
  READY: 'success',
  COMPLETED: 'neutral',
  CANCELLED: 'danger',
  NO_SHOW: 'danger',
};

export function formatBookingStatus(status: string) {
  return bookingStatusLabels[status] ?? status;
}

export function statusBadgeClass(status: string) {
  return `status-badge ${bookingStatusTone[status] ?? 'neutral'}`;
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
  }).format(new Date(`${value}T12:00:00`));
}

export function formatVisitDate(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
  }).format(new Date(value));
}

export function formatPrice(value: string | number) {
  return `${Number(value).toLocaleString('ru-RU')} ₽`;
}

export function humanizeError(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return 'Это время уже недоступно. Обновите список и выберите другой слот.';
    }
    if (error.status === 401) {
      return 'Сессия истекла. Откройте Mini App из Telegram еще раз.';
    }
    if (error.status === 403) {
      return 'Недостаточно прав для этого действия.';
    }
    if (error.status === 404) {
      return 'Данные не найдены. Обновите экран и попробуйте еще раз.';
    }
    if (error.status >= 500) {
      return 'Сервис временно недоступен. Попробуйте немного позже.';
    }
    return error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

export function carTitle(car: { brand: string; model: string }) {
  return `${car.brand} ${car.model}`.trim();
}

