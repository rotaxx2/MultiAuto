import { useEffect, useMemo, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Boxes, Building2, CalendarClock, CalendarDays, Gauge, Settings2, UsersRound } from 'lucide-react';

import { adminApi } from '../api/admin';
import type { AdminClient, AdminDashboard, Booking, Branch, BusinessHour, Service, Workstation } from '../types/api';

export type AdminPage = 'dashboard' | 'bookings' | 'clients' | 'services' | 'branches' | 'boxes' | 'schedule';

interface AdminPanelProps {
  initialPage?: AdminPage;
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Gauge },
  { id: 'bookings', label: 'Записи', icon: CalendarDays },
  { id: 'clients', label: 'Клиенты', icon: UsersRound },
  { id: 'services', label: 'Услуги', icon: Settings2 },
  { id: 'branches', label: 'Филиалы', icon: Building2 },
  { id: 'boxes', label: 'Боксы', icon: Boxes },
  { id: 'schedule', label: 'Расписание', icon: CalendarClock },
] satisfies Array<{ id: AdminPage; label: string; icon: typeof Gauge }>;

const emptyDashboard: AdminDashboard = {
  today_bookings: 0,
  tomorrow_bookings: 0,
  active_bookings: 0,
  clients: 0,
  available_boxes: 0,
  occupied_boxes: 0,
  total_boxes: 0,
  bookings_by_status: {},
  upcoming_bookings: [],
};

const bookingStatuses = ['PENDING', 'CONFIRMED', 'ARRIVED', 'IN_PROGRESS', 'READY', 'COMPLETED', 'CANCELLED', 'NO_SHOW'];

const statusLabels: Record<string, string> = {
  PENDING: 'Ожидает',
  CONFIRMED: 'Подтверждена',
  ARRIVED: 'Клиент на месте',
  IN_PROGRESS: 'В работе',
  READY: 'Готово',
  COMPLETED: 'Завершена',
  CANCELLED: 'Отменена',
  NO_SHOW: 'Не пришел',
};

const statusTone: Record<string, string> = {
  PENDING: 'warning',
  CONFIRMED: 'info',
  ARRIVED: 'info',
  IN_PROGRESS: 'progress',
  READY: 'success',
  COMPLETED: 'neutral',
  CANCELLED: 'danger',
  NO_SHOW: 'danger',
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}

function formatStatus(status: string) {
  return statusLabels[status] ?? status;
}

function statusBadgeClass(status: string) {
  return `admin-status-badge ${statusTone[status] ?? 'neutral'}`;
}

function toDateInputValue(value: string) {
  return new Date(value).toISOString().slice(0, 10);
}

export function AdminPanel({ initialPage = 'dashboard' }: AdminPanelProps) {
  const [page, setPage] = useState<AdminPage>(initialPage);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState<AdminDashboard>(emptyDashboard);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [clients, setClients] = useState<AdminClient[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [boxes, setBoxes] = useState<Workstation[]>([]);
  const [businessHours, setBusinessHours] = useState<BusinessHour[]>([]);

  const branchById = useMemo(() => new Map(branches.map((branch) => [branch.id, branch])), [branches]);

  async function loadAdminData() {
    setLoading(true);
    setError('');
    try {
      const [dashboardData, bookingData, clientData, branchData, serviceData, boxData, hourData] = await Promise.all([
        adminApi.dashboard(),
        adminApi.bookings(),
        adminApi.clients(),
        adminApi.branches(),
        adminApi.services(),
        adminApi.boxes(),
        adminApi.businessHours(),
      ]);
      setDashboard(dashboardData);
      setBookings(bookingData.results);
      setClients(clientData.results);
      setBranches(branchData.results);
      setServices(serviceData.results);
      setBoxes(boxData.results);
      setBusinessHours(hourData.results);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить админку.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAdminData();
  }, []);

  const activeItem = navItems.find((item) => item.id === page);

  function navigate(nextPage: AdminPage) {
    setPage(nextPage);
    const nextPath = nextPage === 'dashboard' ? '/admin' : `/admin/${nextPage}`;
    window.history.replaceState(null, '', nextPath);
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div>
          <p className="eyebrow">MultiAuto</p>
          <h1>Admin Panel</h1>
        </div>
        <nav className="admin-nav" aria-label="Админ-навигация">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={page === item.id ? 'admin-nav-item active' : 'admin-nav-item'} key={item.id} type="button" onClick={() => navigate(item.id)}>
                <Icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="admin-main">
        <header className="admin-header">
          <div>
            <p className="eyebrow">{activeItem?.label}</p>
            <h2>{activeItem?.label ?? 'Dashboard'}</h2>
          </div>
          <button className="secondary-button" type="button" onClick={loadAdminData}>Обновить</button>
        </header>

        {loading ? <div className="admin-loading">Загружаем административные данные...</div> : null}
        {error ? <p className="inline-error">{error}</p> : null}
        {!loading && !error && page === 'dashboard' ? <DashboardView dashboard={dashboard} /> : null}
        {!loading && !error && page === 'bookings' ? <BookingsAdminView bookings={bookings} boxes={boxes} branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'clients' ? <ClientsAdminView clients={clients} /> : null}
        {!loading && !error && page === 'services' ? <ServicesAdminView services={services} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'branches' ? <BranchesAdminView branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'boxes' ? <BoxesAdminView boxes={boxes} branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'schedule' ? <ScheduleAdminView hours={businessHours} branchById={branchById} onReload={loadAdminData} /> : null}
      </main>
    </div>
  );
}

function DashboardView({ dashboard }: { dashboard: AdminDashboard }) {
  const stats = [
    ['Сегодня', dashboard.today_bookings],
    ['Завтра', dashboard.tomorrow_bookings],
    ['Активные записи', dashboard.active_bookings],
    ['Клиенты', dashboard.clients],
    ['Свободные боксы', dashboard.available_boxes],
    ['Занятые боксы', dashboard.occupied_boxes],
  ];
  return (
    <section className="admin-stack">
      <div className="admin-metrics">
        {stats.map(([label, value]) => (
          <div className="admin-metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="admin-grid-two">
        <div>
          <h3 className="section-title">Ближайшие записи</h3>
          <AdminTable rows={dashboard.upcoming_bookings} empty="Ближайших записей нет." columns={['Время', 'Клиент', 'Услуга', 'Бокс']} render={(booking) => [
            formatDateTime(booking.start_at),
            booking.client_name ?? '',
            booking.service_name,
            booking.workstation_name ?? '',
          ]} />
        </div>
        <div>
          <h3 className="section-title">Статусы</h3>
          <div className="admin-status-list">
            {Object.entries(dashboard.bookings_by_status).length ? (
              Object.entries(dashboard.bookings_by_status).map(([status, count]) => (
                <div key={status}><span>{formatStatus(status)}</span><strong>{count}</strong></div>
              ))
            ) : (
              <p className="muted">Записей пока нет.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function BookingsAdminView({ bookings, boxes, branches, onReload }: { bookings: Booking[]; boxes: Workstation[]; branches: Branch[]; onReload: () => Promise<void> }) {
  const [dateFilter, setDateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [actionError, setActionError] = useState('');

  const filteredBookings = bookings.filter((booking) => {
    const matchesDate = !dateFilter || toDateInputValue(booking.start_at) === dateFilter;
    const matchesStatus = !statusFilter || booking.status === statusFilter;
    const matchesBranch = !branchFilter || booking.branch === branchFilter;
    return matchesDate && matchesStatus && matchesBranch;
  });

  async function updateStatus(id: string, status: string) {
    try {
      setActionError('');
      await adminApi.updateBooking(id, { status });
      await onReload();
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Не удалось изменить статус.');
    }
  }

  async function moveBooking(event: FormEvent<HTMLFormElement>, booking: Booking) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const start_at = String(form.get('start_at') || '');
    const workstation = String(form.get('workstation') || '');
    if (!start_at || !workstation) return;
    try {
      setActionError('');
      await adminApi.updateBooking(booking.id, { start_at: new Date(start_at).toISOString(), workstation });
      await onReload();
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Не удалось перенести запись.');
    }
  }

  return (
    <section className="admin-stack">
      <div className="admin-filter-bar">
        <input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">Все статусы</option>
          {bookingStatuses.map((status) => <option key={status} value={status}>{formatStatus(status)}</option>)}
        </select>
        <select value={branchFilter} onChange={(event) => setBranchFilter(event.target.value)}>
          <option value="">Все филиалы</option>
          {branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
        </select>
      </div>
      {actionError ? <p className="inline-error">{actionError}</p> : null}
      <div className="admin-list">
      {filteredBookings.map((booking) => (
        <article className="admin-row" key={booking.id}>
          <div>
            <strong>{formatDateTime(booking.start_at)}</strong>
            <span className={statusBadgeClass(booking.status)}>{formatStatus(booking.status)}</span>
            <span>{booking.client_name} · {booking.car_label}</span>
            <span>{booking.service_name} · {booking.branch_name} · {booking.workstation_name}</span>
          </div>
          <select value={booking.status} onChange={(event) => void updateStatus(booking.id, event.target.value)}>
            {bookingStatuses.map((status) => <option key={status} value={status}>{formatStatus(status)}</option>)}
          </select>
          <form className="admin-inline-form" onSubmit={(event) => void moveBooking(event, booking)}>
            <input name="start_at" type="datetime-local" />
            <select name="workstation" defaultValue={booking.workstation}>
              {boxes.map((box) => <option key={box.id} value={box.id}>{box.name}</option>)}
            </select>
            <button className="secondary-button" type="submit">Перенести</button>
          </form>
        </article>
      ))}
      {!filteredBookings.length ? <p className="muted">Записи по выбранным фильтрам не найдены.</p> : null}
      </div>
    </section>
  );
}

function ClientsAdminView({ clients }: { clients: AdminClient[] }) {
  return <AdminTable rows={clients} empty="Клиенты не найдены." columns={['Telegram', 'Имя', 'Username', 'Авто', 'Записи', 'Регистрация', 'Статус']} render={(client) => [
    String(client.telegram_id ?? ''),
    `${client.first_name} ${client.last_name}`.trim(),
    client.username,
    String(client.cars_count),
    String(client.bookings_count),
    formatDateTime(client.created_at),
    client.is_active ? 'Активен' : 'Отключен',
  ]} />;
}

function ServicesAdminView({ services, onReload }: { services: Service[]; onReload: () => Promise<void> }) {
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.createService({
      name: String(form.get('name')),
      description: String(form.get('description') || ''),
      duration_minutes: Number(form.get('duration_minutes')),
      price: String(form.get('price')),
      is_active: true,
    });
    event.currentTarget.reset();
    await onReload();
  }
  async function update(event: FormEvent<HTMLFormElement>, service: Service) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.updateService(service.id, {
      name: String(form.get('name')),
      description: String(form.get('description') || ''),
      duration_minutes: Number(form.get('duration_minutes')),
      price: String(form.get('price')),
      is_active: form.get('is_active') === 'on',
    });
    await onReload();
  }

  return (
    <CrudSection onSubmit={create} fields={[['name', 'Название'], ['duration_minutes', 'Длительность, мин'], ['price', 'Цена'], ['description', 'Описание']]}>
      {services.map((service) => (
        <form className="admin-edit-row" key={service.id} onSubmit={(event) => void update(event, service)}>
          <input name="name" defaultValue={service.name} aria-label="Название услуги" />
          <input name="duration_minutes" type="number" min="1" defaultValue={service.duration_minutes} aria-label="Длительность" />
          <input name="price" type="number" min="0" step="0.01" defaultValue={service.price} aria-label="Цена" />
          <input name="description" defaultValue={service.description} aria-label="Описание" />
          <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked={service.is_active} /> Активна</label>
          <button className="secondary-button" type="submit">Сохранить</button>
        </form>
      ))}
    </CrudSection>
  );
}

function BranchesAdminView({ branches, onReload }: { branches: Branch[]; onReload: () => Promise<void> }) {
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.createBranch({
      name: String(form.get('name')),
      address: String(form.get('address')),
      phone: String(form.get('phone') || ''),
      timezone: String(form.get('timezone') || 'UTC'),
      is_active: true,
    });
    event.currentTarget.reset();
    await onReload();
  }
  async function update(event: FormEvent<HTMLFormElement>, branch: Branch) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.updateBranch(branch.id, {
      name: String(form.get('name')),
      address: String(form.get('address')),
      phone: String(form.get('phone') || ''),
      timezone: String(form.get('timezone') || 'UTC'),
      is_active: form.get('is_active') === 'on',
    });
    await onReload();
  }

  return (
    <CrudSection onSubmit={create} fields={[['name', 'Название'], ['address', 'Адрес'], ['phone', 'Телефон'], ['timezone', 'Timezone']]}>
      {branches.map((branch) => (
        <form className="admin-edit-row" key={branch.id} onSubmit={(event) => void update(event, branch)}>
          <input name="name" defaultValue={branch.name} aria-label="Название филиала" />
          <input name="address" defaultValue={branch.address} aria-label="Адрес" />
          <input name="phone" defaultValue={branch.phone} aria-label="Телефон" />
          <input name="timezone" defaultValue={branch.timezone} aria-label="Timezone" />
          <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked={branch.is_active} /> Активен</label>
          <button className="secondary-button" type="submit">Сохранить</button>
        </form>
      ))}
    </CrudSection>
  );
}

function BoxesAdminView({ boxes, branches, onReload }: { boxes: Workstation[]; branches: Branch[]; onReload: () => Promise<void> }) {
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.createBox({ branch: String(form.get('branch')), name: String(form.get('name')), is_active: true });
    event.currentTarget.reset();
    await onReload();
  }
  async function update(event: FormEvent<HTMLFormElement>, box: Workstation) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.updateBox(box.id, {
      branch: String(form.get('branch')),
      name: String(form.get('name')),
      is_active: form.get('is_active') === 'on',
    });
    await onReload();
  }

  return (
    <section className="admin-stack">
      <form className="admin-form" onSubmit={(event) => void create(event)}>
        <select name="branch" required>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>
        <input name="name" placeholder="Название бокса" required />
        <button className="primary-button compact" type="submit">Создать</button>
      </form>
      {boxes.map((box) => (
        <form className="admin-edit-row compact-edit" key={box.id} onSubmit={(event) => void update(event, box)}>
          <select name="branch" defaultValue={box.branch} required>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>
          <input name="name" defaultValue={box.name} aria-label="Название бокса" />
          <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked={box.is_active} /> Активен</label>
          <button className="secondary-button" type="submit">Сохранить</button>
        </form>
      ))}
    </section>
  );
}

function ScheduleAdminView({ hours, branchById, onReload }: { hours: BusinessHour[]; branchById: Map<string, Branch>; onReload: () => Promise<void> }) {
  async function update(event: FormEvent<HTMLFormElement>, hour: BusinessHour) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await adminApi.updateBusinessHour(hour.id, {
      is_closed: form.get('is_closed') === 'on',
      opening_time: String(form.get('opening_time') || ''),
      closing_time: String(form.get('closing_time') || ''),
    });
    await onReload();
  }
  return (
    <div className="admin-list">
      {hours.map((hour) => (
        <form className="admin-row" key={hour.id} onSubmit={(event) => void update(event, hour)}>
          <div><strong>{branchById.get(hour.branch)?.name} · день {hour.weekday + 1}</strong><span>{hour.is_closed ? 'Закрыто' : `${hour.opening_time} - ${hour.closing_time}`}</span></div>
          <input name="opening_time" type="time" defaultValue={hour.opening_time ?? ''} />
          <input name="closing_time" type="time" defaultValue={hour.closing_time ?? ''} />
          <label className="admin-check"><input name="is_closed" type="checkbox" defaultChecked={hour.is_closed} /> Закрыто</label>
          <button className="secondary-button" type="submit">Сохранить</button>
        </form>
      ))}
    </div>
  );
}

function CrudSection({ children, fields, onSubmit }: { children: ReactNode; fields: Array<[string, string]>; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <section className="admin-stack">
      <form className="admin-form" onSubmit={onSubmit}>
        {fields.map(([name, label]) => <input key={name} name={name} placeholder={label} required={name !== 'description' && name !== 'phone'} />)}
        <button className="primary-button compact" type="submit">Создать</button>
      </form>
      <div className="admin-list">{children}</div>
    </section>
  );
}

function AdminTable<T>({ rows, columns, empty, render }: { rows: T[]; columns: string[]; empty: string; render: (row: T) => string[] }) {
  if (!rows.length) {
    return <p className="muted">{empty}</p>;
  }
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => <tr key={index}>{render(row).map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
  );
}
