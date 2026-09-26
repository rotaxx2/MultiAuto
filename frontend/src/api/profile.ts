import { apiRequest } from './client';
import type { AvailabilityResponse, AvailableDatesResponse, Booking, Branch, Car, ListResponse, Profile, Service } from '../types/api';

export function getMyProfile(): Promise<Profile> {
  return apiRequest<Profile>('/api/my-profile/');
}

export function getMyCars(): Promise<ListResponse<Car>> {
  return apiRequest<ListResponse<Car>>('/api/my-cars/');
}

export function createMyCar(payload: Omit<Car, 'id' | 'created_at' | 'updated_at'>): Promise<Car> {
  return apiRequest<Car>('/api/my-cars/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateMyCar(id: string, payload: Partial<Omit<Car, 'id' | 'created_at' | 'updated_at'>>): Promise<Car> {
  return apiRequest<Car>(`/api/my-cars/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteMyCar(id: string): Promise<void> {
  return apiRequest<void>(`/api/my-cars/${id}/`, {
    method: 'DELETE',
  });
}

export function getMyBookings(): Promise<ListResponse<Booking>> {
  return apiRequest<ListResponse<Booking>>('/api/my-bookings/');
}

export function createBooking(payload: {
  branch_id: string;
  car_id: string;
  service_id: string;
  start_at: string;
  client_comment?: string;
}): Promise<Booking> {
  return apiRequest<Booking>('/api/bookings/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function cancelBooking(id: string): Promise<Booking> {
  return apiRequest<Booking>(`/api/my-bookings/${id}/cancel/`, {
    method: 'POST',
  });
}

export function getAvailability(branchId: string, serviceId: string, date: string): Promise<AvailabilityResponse> {
  const params = new URLSearchParams({ service_id: serviceId, date });
  return apiRequest<AvailabilityResponse>(`/api/branches/${branchId}/availability/?${params.toString()}`);
}

export function getAvailableDates(branchId: string): Promise<AvailableDatesResponse> {
  return apiRequest<AvailableDatesResponse>(`/api/branches/${branchId}/available-dates/`);
}

export function getServices(): Promise<ListResponse<Service>> {
  return apiRequest<ListResponse<Service>>('/api/services/');
}

export function getBranches(): Promise<ListResponse<Branch>> {
  return apiRequest<ListResponse<Branch>>('/api/branches/');
}
