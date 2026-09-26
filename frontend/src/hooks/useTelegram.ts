import { useEffect, useState } from 'react';

import {
  getTelegramStartParam,
  getTelegramUser,
  getTelegramWebApp,
  initializeTelegramWebApp,
} from '../utils/telegram';
import type { TelegramWebApp, TelegramWebAppUser } from '../types/telegram';

interface TelegramState {
  ready: boolean;
  webApp: TelegramWebApp | null;
  isTelegram: boolean;
  user: TelegramWebAppUser | null;
  initData: string;
  startParam: string;
}

function readTelegramState(ready: boolean): TelegramState {
  const webApp = getTelegramWebApp();
  const initData = webApp?.initData ?? '';

  return {
    ready,
    webApp,
    isTelegram: Boolean(webApp && initData),
    user: getTelegramUser(),
    initData,
    startParam: getTelegramStartParam(),
  };
}

export function useTelegram() {
  const [state, setState] = useState<TelegramState>(() => readTelegramState(false));

  useEffect(() => {
    initializeTelegramWebApp();

    let attempt = 0;
    const maxAttempts = 20;
    const intervalId = window.setInterval(() => {
      attempt += 1;
      const nextState = readTelegramState(true);
      setState(nextState);

      if (nextState.initData || attempt >= maxAttempts) {
        window.clearInterval(intervalId);
      }
    }, 100);

    setState(readTelegramState(true));

    return () => window.clearInterval(intervalId);
  }, []);

  return state;
}
