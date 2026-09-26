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
  year: number | null;
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  branch: string;
  branch_name: string;
  car: string;
  car_label: string;
  service: string;
  service_name: string;
  status: string;
  start_at: string;
  end_at: string;
  price: string;
  client_comment: string;
  admin_comment: string;
}

export interface AvailabilitySlot {
  start_at: string;
  end_at: string;
  total_workstations: number;
  occupied_workstations: number;
  free_workstations: number;
  is_available: boolean;
}

export interface AvailabilityResponse {
  date: string;
  timezone: string;
  service_id: string;
  duration_minutes: number;
  slots: AvailabilitySlot[];
}

export interface AvailableDate {
  date: string;
  label: string;
  is_available: boolean;
}

export interface AvailableDatesResponse {
  timezone: string;
  dates: AvailableDate[];
}

export interface Service {
  id: string;
  name: string;
  description: string;
  duration_minutes: number;
  price: string;
  is_active: boolean;
}

export interface Branch {
  id: string;
  name: string;
  address: string;
  phone: string;
  timezone: string;
  is_active: boolean;
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
