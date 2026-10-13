import { useCallback, useEffect, useState } from 'react';

import { authenticateWithTelegram } from '../api/auth';
import { getMyProfile } from '../api/profile';
import type { User } from '../types/api';
import { ApiError, clearStoredToken, getApiUrl, getStoredToken } from '../api/client';

type AuthStatus = 'loading' | 'authenticated' | 'unauthorized' | 'error';

interface AuthDebugInfo {
  apiUrl: string;
  hasStoredToken: boolean;
  initDataLength: number;
  isTelegram: boolean;
  lastStep: string;
  startParam: string;
}

export function useAuth(initData: string, startParam: string, isTelegram: boolean, telegramReady: boolean) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [error, setError] = useState<string>('');
  const [debugInfo, setDebugInfo] = useState<AuthDebugInfo>({
    apiUrl: getApiUrl(),
    hasStoredToken: false,
    initDataLength: 0,
    isTelegram: false,
    lastStep: 'init',
    startParam: '',
  });

  const authenticate = useCallback(async () => {
    setStatus('loading');
    setError('');
    setDebugInfo({
      apiUrl: getApiUrl(),
      hasStoredToken: Boolean(getStoredToken()),
      initDataLength: initData.length,
      isTelegram,
      lastStep: telegramReady ? 'started' : 'waiting-telegram-ready',
      startParam,
    });

    try {
      if (!telegramReady) {
        return;
      }

      const authenticateFromTelegram = async () => {
        if (!isTelegram || !initData) {
          setStatus('unauthorized');
          setError('Откройте приложение внутри Telegram.');
          setDebugInfo((current) => ({ ...current, lastStep: 'missing-telegram-init-data' }));
          return;
        }

        setDebugInfo((current) => ({ ...current, lastStep: 'telegram-auth-request' }));
        setUser(await authenticateWithTelegram(initData, startParam));
        setStatus('authenticated');
        setDebugInfo((current) => ({ ...current, hasStoredToken: true, lastStep: 'telegram-auth-ok' }));
      };

      const token = getStoredToken();
      if (token) {
        try {
          setDebugInfo((current) => ({ ...current, lastStep: 'stored-token-profile-request' }));
          setUser(await getMyProfile());
          setStatus('authenticated');
          setDebugInfo((current) => ({ ...current, lastStep: 'stored-token-profile-ok' }));
        } catch (caught) {
          clearStoredToken();
          setDebugInfo((current) => ({
            ...current,
            hasStoredToken: false,
            lastStep: caught instanceof ApiError ? `stored-token-failed-${caught.status}` : 'stored-token-failed',
          }));
          await authenticateFromTelegram();
          return;
        }
        return;
      }

      await authenticateFromTelegram();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setStatus('unauthorized');
        setError('Не удалось авторизоваться через Telegram.');
        setDebugInfo((current) => ({ ...current, lastStep: `${current.lastStep}-401-${caught.code}` }));
        return;
      }
      setStatus('error');
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить данные.');
      setDebugInfo((current) => ({
        ...current,
        lastStep: caught instanceof ApiError ? `${current.lastStep}-${caught.status}-${caught.code}` : `${current.lastStep}-error`,
      }));
    }
  }, [initData, isTelegram, startParam, telegramReady]);

  useEffect(() => {
    void authenticate();
  }, [authenticate]);

  return { user, status, error, retry: authenticate, debugInfo };
}
