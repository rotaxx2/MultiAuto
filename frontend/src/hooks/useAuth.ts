import { useCallback, useEffect, useState } from 'react';

import { authenticateWithTelegram } from '../api/auth';
import { getMyProfile } from '../api/profile';
import type { User } from '../types/api';
import { ApiError, getStoredToken } from '../api/client';

type AuthStatus = 'loading' | 'authenticated' | 'unauthorized' | 'error';

export function useAuth(initData: string, startParam: string, isTelegram: boolean) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [error, setError] = useState<string>('');

  const authenticate = useCallback(async () => {
    setStatus('loading');
    setError('');

    try {
      const token = getStoredToken();
      if (token) {
        setUser(await getMyProfile());
        setStatus('authenticated');
        return;
      }

      if (!isTelegram || !initData) {
        setStatus('unauthorized');
        setError('Откройте приложение внутри Telegram.');
        return;
      }

      setUser(await authenticateWithTelegram(initData, startParam));
      setStatus('authenticated');
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setStatus('unauthorized');
        setError('Не удалось авторизоваться через Telegram.');
        return;
      }
      setStatus('error');
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить данные.');
    }
  }, [initData, isTelegram, startParam]);

  useEffect(() => {
    void authenticate();
  }, [authenticate]);

  return { user, status, error, retry: authenticate };
}
