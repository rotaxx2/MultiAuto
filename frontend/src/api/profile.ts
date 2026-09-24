import { apiRequest } from './client';
import type { Booking, Car, ListResponse, Profile } from '../types/api';

export function getMyProfile(): Promise<Profile> {
  return apiRequest<Profile>('/api/my-profile/');
}

export function getMyCars(): Promise<ListResponse<Car>> {
  return apiRequest<ListResponse<Car>>('/api/my-cars/');
}

export function getMyBookings(): Promise<ListResponse<Booking>> {
  return apiRequest<ListResponse<Booking>>('/api/my-bookings/');
}
