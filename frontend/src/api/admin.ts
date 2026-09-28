import { apiRequest } from './client';
import type { AdminClient, AdminDashboard, Booking, Branch, BusinessHour, ListResponse, ScheduleException, Service, Workstation } from '../types/api';

export const adminApi = {
  dashboard: () => apiRequest<AdminDashboard>('/api/admin/dashboard/'),
  bookings: () => apiRequest<ListResponse<Booking>>('/api/admin/bookings/'),
  updateBooking: (id: string, payload: Partial<Pick<Booking, 'status' | 'admin_comment' | 'start_at' | 'workstation'>>) =>
    apiRequest<Booking>(`/api/admin/bookings/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  clients: () => apiRequest<ListResponse<AdminClient>>('/api/admin/clients/'),
  branches: () => apiRequest<ListResponse<Branch>>('/api/admin/branches/'),
  createBranch: (payload: Omit<Branch, 'id'>) => apiRequest<Branch>('/api/admin/branches/', { method: 'POST', body: JSON.stringify(payload) }),
  updateBranch: (id: string, payload: Partial<Omit<Branch, 'id'>>) =>
    apiRequest<Branch>(`/api/admin/branches/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  services: () => apiRequest<ListResponse<Service>>('/api/admin/services/'),
  createService: (payload: Omit<Service, 'id'>) => apiRequest<Service>('/api/admin/services/', { method: 'POST', body: JSON.stringify(payload) }),
  updateService: (id: string, payload: Partial<Omit<Service, 'id'>>) =>
    apiRequest<Service>(`/api/admin/services/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  boxes: () => apiRequest<ListResponse<Workstation>>('/api/admin/workstations/'),
  createBox: (payload: Omit<Workstation, 'id' | 'created_at' | 'updated_at'>) =>
    apiRequest<Workstation>('/api/admin/workstations/', { method: 'POST', body: JSON.stringify(payload) }),
  updateBox: (id: string, payload: Partial<Omit<Workstation, 'id' | 'created_at' | 'updated_at'>>) =>
    apiRequest<Workstation>(`/api/admin/workstations/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  businessHours: () => apiRequest<ListResponse<BusinessHour>>('/api/admin/business-hours/'),
  updateBusinessHour: (id: string, payload: Partial<Omit<BusinessHour, 'id'>>) =>
    apiRequest<BusinessHour>(`/api/admin/business-hours/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) }),
  scheduleExceptions: () => apiRequest<ListResponse<ScheduleException>>('/api/admin/schedule-exceptions/'),
};
