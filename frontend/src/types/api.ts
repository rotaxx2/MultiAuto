export type UserRole = 'CLIENT' | 'ADMIN' | 'OWNER';

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
}

export interface User {
  id: string;
  telegram_id: number | null;
  username: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  role: UserRole;
  organization: OrganizationSummary | null;
}

export type Profile = User;

export interface Car {
  id: string;
  brand: string;
  model: string;
  license_plate: string;
  color: string;
  vehicle_type: string;
}

export interface Booking {
  id: string;
  status: string;
  starts_at: string;
  ends_at: string;
}

export interface ListResponse<T> {
  results: T[];
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  detail?: string;
}
