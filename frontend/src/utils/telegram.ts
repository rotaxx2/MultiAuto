import type { TelegramWebApp, TelegramWebAppUser } from '../types/telegram';

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function isTelegramEnvironment(): boolean {
  return Boolean(getTelegramWebApp()?.initData);
}

export function getTelegramUser(): TelegramWebAppUser | null {
  return getTelegramWebApp()?.initDataUnsafe?.user ?? null;
}

export function getTelegramStartParam(): string {
  return getTelegramWebApp()?.initDataUnsafe?.start_param ?? '';
}

export function initializeTelegramWebApp(): void {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return;
  }

  webApp.ready();
  webApp.expand();
}
