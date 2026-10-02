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
  client?: string;
  client_name?: string;
  client_telegram_id?: number | null;
  car: string;
  car_label: string;
  service: string;
  service_name: string;
  workstation?: string;
  workstation_name?: string;
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

export interface Workstation {
  id: string;
  branch: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusinessHour {
  id: string;
  branch: string;
  weekday: number;
  opening_time: string | null;
  closing_time: string | null;
  is_closed: boolean;
}

export interface ScheduleException {
  id: string;
  branch: string;
  date: string;
  is_closed: boolean;
  opening_time: string | null;
  closing_time: string | null;
  reason: string;
}

export interface AdminClient {
  id: string;
  telegram_id: number | null;
  username: string;
  first_name: string;
  last_name: string;
  cars_count: number;
  bookings_count: number;
  date_joined: string;
  created_at: string;
  is_active: boolean;
}

export interface AdminDashboard {
  today_bookings: number;
  tomorrow_bookings: number;
  active_bookings: number;
  clients: number;
  available_boxes: number;
  occupied_boxes: number;
  total_boxes: number;
  bookings_by_status: Record<string, number>;
  upcoming_bookings: Booking[];
  notifications: {
    pending: number;
    sent_today: number;
    failed_today: number;
  };
}

export interface AdminNotification {
  id: string;
  booking_id: string;
  booking_start_at: string;
  client_name: string;
  client_telegram_id: number | null;
  kind: string;
  scheduled_at: string;
  status: 'PENDING' | 'SENT' | 'FAILED' | 'CANCELLED';
  attempts: number;
  last_attempt_at: string | null;
  sent_at: string | null;
  error_message: string;
  service_name: string;
  branch_name: string;
  car_label: string;
  created_at: string;
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
