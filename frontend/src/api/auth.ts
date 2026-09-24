import { apiRequest, setStoredToken } from './client';
import type { AuthResponse, User } from '../types/api';

export async function authenticateWithTelegram(initData: string, startParam: string): Promise<User> {
  const response = await apiRequest<AuthResponse>('/api/v1/client/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({
      init_data: initData,
      start_param: startParam,
    }),
  });

  setStoredToken(response.token);
  return response.user;
}
