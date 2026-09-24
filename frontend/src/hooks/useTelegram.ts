import { useEffect, useMemo, useState } from 'react';

import {
  getTelegramStartParam,
  getTelegramUser,
  getTelegramWebApp,
  initializeTelegramWebApp,
  isTelegramEnvironment,
} from '../utils/telegram';

export function useTelegram() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    initializeTelegramWebApp();
    setReady(true);
  }, []);

  return useMemo(
    () => ({
      ready,
      webApp: getTelegramWebApp(),
      isTelegram: isTelegramEnvironment(),
      user: getTelegramUser(),
      initData: getTelegramWebApp()?.initData ?? '',
      startParam: getTelegramStartParam(),
    }),
    [ready],
  );
}
