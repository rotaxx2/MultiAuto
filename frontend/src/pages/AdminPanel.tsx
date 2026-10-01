import { useEffect, useMemo, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Boxes, Building2, CalendarClock, CalendarDays, Gauge, Search, Settings2, UsersRound } from 'lucide-react';

import { adminApi } from '../api/admin';
import type { AdminClient, AdminDashboard, Booking, Branch, BusinessHour, ScheduleException, Service, Workstation } from '../types/api';

export type AdminPage = 'dashboard' | 'bookings' | 'clients' | 'services' | 'branches' | 'boxes' | 'schedule';

interface AdminPanelProps {
  initialPage?: AdminPage;
}

type Notice = { type: 'success' | 'error'; text: string };

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
  PENDING: 'Ожидает подтверждения',
  CONFIRMED: 'Подтверждена',
  ARRIVED: 'Клиент прибыл',
  IN_PROGRESS: 'В процессе',
  READY: 'Готова',
  COMPLETED: 'Завершена',
  CANCELLED: 'Отменена',
  NO_SHOW: 'Неявка',
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

const weekdayLabels = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium' }).format(new Date(value));
}

function formatPrice(value: string) {
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(amount);
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

function toDateTimeLocalValue(value: string) {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function clientName(client: Pick<AdminClient, 'first_name' | 'last_name' | 'username' | 'telegram_id'>) {
  return `${client.first_name ?? ''} ${client.last_name ?? ''}`.trim() || client.username || (client.telegram_id ? `Telegram ${client.telegram_id}` : 'Без имени');
}

function bookingClientName(booking: Booking) {
  return booking.client_name || (booking.client_telegram_id ? `Telegram ${booking.client_telegram_id}` : 'Клиент не указан');
}

function normalizeText(value: string) {
  return value.toLowerCase().trim();
}

function readableError(caught: unknown, fallback: string) {
  const message = caught instanceof Error ? caught.message : fallback;
  const normalized = message.toLowerCase();
  if (normalized.includes('availability') || normalized.includes('available') || normalized.includes('занят') || normalized.includes('conflict')) {
    return 'Это время или бокс уже занят. Выберите другой слот.';
  }
  return message || fallback;
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
  const [scheduleExceptions, setScheduleExceptions] = useState<ScheduleException[]>([]);

  const branchById = useMemo(() => new Map(branches.map((branch) => [branch.id, branch])), [branches]);

  async function loadAdminData() {
    setLoading(true);
    setError('');
    try {
      const [dashboardData, bookingData, clientData, branchData, serviceData, boxData, hourData, exceptionData] = await Promise.all([
        adminApi.dashboard(),
        adminApi.bookings(),
        adminApi.clients(),
        adminApi.branches(),
        adminApi.services(),
        adminApi.boxes(),
        adminApi.businessHours(),
        adminApi.scheduleExceptions(),
      ]);
      setDashboard(dashboardData);
      setBookings(bookingData.results);
      setClients(clientData.results);
      setBranches(branchData.results);
      setServices(serviceData.results);
      setBoxes(boxData.results);
      setBusinessHours(hourData.results);
      setScheduleExceptions(exceptionData.results);
    } catch (caught) {
      setError(readableError(caught, 'Не удалось загрузить админку.'));
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
        {!loading && !error && page === 'dashboard' ? <DashboardView dashboard={dashboard} branchesCount={branches.length} boxesCount={boxes.length} /> : null}
        {!loading && !error && page === 'bookings' ? <BookingsAdminView bookings={bookings} boxes={boxes} branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'clients' ? <ClientsAdminView clients={clients} /> : null}
        {!loading && !error && page === 'services' ? <ServicesAdminView services={services} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'branches' ? <BranchesAdminView branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'boxes' ? <BoxesAdminView boxes={boxes} branches={branches} onReload={loadAdminData} /> : null}
        {!loading && !error && page === 'schedule' ? <ScheduleAdminView hours={businessHours} exceptions={scheduleExceptions} branchById={branchById} onReload={loadAdminData} /> : null}
      </main>
    </div>
  );
}

function DashboardView({ dashboard, branchesCount, boxesCount }: { dashboard: AdminDashboard; branchesCount: number; boxesCount: number }) {
  const completed = dashboard.bookings_by_status.COMPLETED ?? 0;
  const cancelled = (dashboard.bookings_by_status.CANCELLED ?? 0) + (dashboard.bookings_by_status.NO_SHOW ?? 0);
  const stats = [
    ['Сегодня', dashboard.today_bookings],
    ['Завтра', dashboard.tomorrow_bookings],
    ['Активные', dashboard.active_bookings],
    ['Клиенты', dashboard.clients],
    ['Филиалы', branchesCount],
    ['Боксы', boxesCount || dashboard.total_boxes],
    ['Свободно', dashboard.available_boxes],
    ['Занято', dashboard.occupied_boxes],
    ['Завершено', completed],
    ['Отмены/неявки', cancelled],
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
        <Panel title="Ближайшие записи" subtitle="Следующие визиты клиентов">
          <AdminTable rows={dashboard.upcoming_bookings} empty="Ближайших записей нет." columns={['Время', 'Клиент', 'Авто', 'Услуга', 'Филиал', 'Бокс', 'Статус']} render={(booking) => [
            formatDateTime(booking.start_at),
            bookingClientName(booking),
            booking.car_label,
            booking.service_name,
            booking.branch_name,
            booking.workstation_name ?? 'Не назначен',
            formatStatus(booking.status),
          ]} />
        </Panel>
        <Panel title="Статусы" subtitle="Срез по всем записям">
          <div className="admin-status-list">
            {bookingStatuses.some((status) => dashboard.bookings_by_status[status]) ? (
              bookingStatuses.map((status) => (
                <div key={status}>
                  <span className={statusBadgeClass(status)}>{formatStatus(status)}</span>
                  <strong>{dashboard.bookings_by_status[status] ?? 0}</strong>
                </div>
              ))
            ) : (
              <EmptyState text="Записей пока нет." />
            )}
          </div>
        </Panel>
      </div>
    </section>
  );
}

function BookingsAdminView({ bookings, boxes, branches, onReload }: { bookings: Booking[]; boxes: Workstation[]; branches: Branch[]; onReload: () => Promise<void> }) {
  const [dateFilter, setDateFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(bookings[0]?.id ?? '');
  const [notice, setNotice] = useState<Notice | null>(null);

  const filteredBookings = bookings.filter((booking) => {
    const searchable = normalizeText(`${bookingClientName(booking)} ${booking.client_telegram_id ?? ''} ${booking.car_label} ${booking.service_name} ${booking.branch_name} ${booking.workstation_name ?? ''}`);
    const matchesDate = !dateFilter || toDateInputValue(booking.start_at) === dateFilter;
    const matchesStatus = !statusFilter || booking.status === statusFilter;
    const matchesBranch = !branchFilter || booking.branch === branchFilter;
    const matchesSearch = !query || searchable.includes(normalizeText(query));
    return matchesDate && matchesStatus && matchesBranch && matchesSearch;
  });

  const selectedBooking = filteredBookings.find((booking) => booking.id === selectedId) ?? filteredBookings[0] ?? null;

  useEffect(() => {
    if (filteredBookings.length && !filteredBookings.some((booking) => booking.id === selectedId)) {
      setSelectedId(filteredBookings[0].id);
    }
  }, [filteredBookings, selectedId]);

  async function updateBooking(booking: Booking, payload: Partial<Pick<Booking, 'status' | 'admin_comment' | 'start_at' | 'workstation'>>) {
    try {
      setNotice(null);
      await adminApi.updateBooking(booking.id, payload);
      setNotice({ type: 'success', text: 'Запись обновлена.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось обновить запись.') });
    }
  }

  return (
    <section className="admin-stack">
      <div className="admin-section-header">
        <div>
          <h3 className="section-title">Управление записями</h3>
          <p className="muted">Фильтры, быстрые статусы и карточка деталей для выбранной записи.</p>
        </div>
        <strong>{filteredBookings.length} из {bookings.length}</strong>
      </div>
      <div className="admin-filter-bar">
        <label className="admin-search">
          <Search size={16} aria-hidden="true" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Клиент, авто, услуга, Telegram" />
        </label>
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
      {notice ? <p className={notice.type === 'success' ? 'admin-success' : 'inline-error'}>{notice.text}</p> : null}
      {selectedBooking ? <BookingDetailPanel booking={selectedBooking} boxes={boxes} onSave={updateBooking} /> : null}
      <div className="admin-table-wrap admin-desktop-only">
        <table className="admin-table">
          <thead><tr><th>Время</th><th>Клиент</th><th>Авто</th><th>Услуга</th><th>Филиал</th><th>Бокс</th><th>Цена</th><th>Статус</th><th>Действие</th></tr></thead>
          <tbody>
            {filteredBookings.map((booking) => (
              <tr className={selectedBooking?.id === booking.id ? 'selected' : ''} key={booking.id}>
                <td>{formatDateTime(booking.start_at)}</td>
                <td>{bookingClientName(booking)}</td>
                <td>{booking.car_label}</td>
                <td>{booking.service_name}</td>
                <td>{booking.branch_name}</td>
                <td>{booking.workstation_name ?? 'Не назначен'}</td>
                <td>{formatPrice(booking.price)}</td>
                <td><span className={statusBadgeClass(booking.status)}>{formatStatus(booking.status)}</span></td>
                <td><button className="secondary-button compact" type="button" onClick={() => setSelectedId(booking.id)}>Открыть</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="admin-mobile-list">
        {filteredBookings.map((booking) => (
          <button className={selectedBooking?.id === booking.id ? 'admin-booking-card selected' : 'admin-booking-card'} key={booking.id} type="button" onClick={() => setSelectedId(booking.id)}>
            <span className={statusBadgeClass(booking.status)}>{formatStatus(booking.status)}</span>
            <strong>{formatDateTime(booking.start_at)}</strong>
            <span>{bookingClientName(booking)} · {booking.car_label}</span>
            <span>{booking.service_name} · {booking.branch_name}</span>
          </button>
        ))}
      </div>
      {!filteredBookings.length ? <EmptyState text="Записи по выбранным фильтрам не найдены." /> : null}
    </section>
  );
}

function BookingDetailPanel({ booking, boxes, onSave }: { booking: Booking; boxes: Workstation[]; onSave: (booking: Booking, payload: Partial<Pick<Booking, 'status' | 'admin_comment' | 'start_at' | 'workstation'>>) => Promise<void> }) {
  const branchBoxes = boxes.filter((box) => box.branch === booking.branch);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const startAt = String(form.get('start_at') || '');
    await onSave(booking, {
      status: String(form.get('status') || booking.status),
      start_at: startAt ? new Date(startAt).toISOString() : booking.start_at,
      workstation: String(form.get('workstation') || booking.workstation || ''),
      admin_comment: String(form.get('admin_comment') || ''),
    });
  }

  return (
    <form className="admin-detail-panel" onSubmit={(event) => void save(event)}>
      <div className="admin-detail-head">
        <div>
          <p className="eyebrow">Детали записи</p>
          <h3>{bookingClientName(booking)}</h3>
        </div>
        <span className={statusBadgeClass(booking.status)}>{formatStatus(booking.status)}</span>
      </div>
      <div className="admin-detail-grid">
        <AdminField label="Клиент" value={bookingClientName(booking)} />
        <AdminField label="Telegram ID" value={booking.client_telegram_id ? String(booking.client_telegram_id) : 'Не указан'} />
        <AdminField label="Автомобиль" value={booking.car_label} />
        <AdminField label="Услуга" value={booking.service_name} />
        <AdminField label="Филиал" value={booking.branch_name} />
        <AdminField label="Цена" value={formatPrice(booking.price)} />
      </div>
      <div className="admin-edit-row admin-booking-edit">
        <select name="status" defaultValue={booking.status}>
          {bookingStatuses.map((status) => <option key={status} value={status}>{formatStatus(status)}</option>)}
        </select>
        <input name="start_at" type="datetime-local" defaultValue={toDateTimeLocalValue(booking.start_at)} />
        <select name="workstation" defaultValue={booking.workstation ?? ''}>
          <option value="">Без бокса</option>
          {branchBoxes.map((box) => <option key={box.id} value={box.id}>{box.name}</option>)}
        </select>
        <textarea name="admin_comment" defaultValue={booking.admin_comment ?? ''} placeholder="Комментарий администратора" rows={3} />
        <button className="primary-button compact" type="submit">Сохранить</button>
      </div>
      <div className="admin-comments">
        <AdminField label="Комментарий клиента" value={booking.client_comment || 'Нет комментария'} />
        <AdminField label="Комментарий администратора" value={booking.admin_comment || 'Нет комментария'} />
      </div>
    </form>
  );
}

function ClientsAdminView({ clients }: { clients: AdminClient[] }) {
  const [query, setQuery] = useState('');
  const filteredClients = clients.filter((client) => normalizeText(`${clientName(client)} ${client.username} ${client.telegram_id ?? ''}`).includes(normalizeText(query)));
  return (
    <section className="admin-stack">
      <div className="admin-section-header">
        <div>
          <h3 className="section-title">Клиенты</h3>
          <p className="muted">Поиск по имени, username или Telegram ID.</p>
        </div>
        <strong>{filteredClients.length} из {clients.length}</strong>
      </div>
      <div className="admin-filter-bar">
        <label className="admin-search">
          <Search size={16} aria-hidden="true" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Найти клиента" />
        </label>
      </div>
      <AdminTable rows={filteredClients} empty="Клиенты не найдены." columns={['Telegram', 'Имя', 'Username', 'Авто', 'Записи', 'Регистрация', 'Статус']} render={(client) => [
        String(client.telegram_id ?? ''),
        clientName(client),
        client.username || 'Не указан',
        String(client.cars_count),
        String(client.bookings_count),
        formatDateTime(client.created_at),
        client.is_active ? 'Активен' : 'Отключен',
      ]} />
    </section>
  );
}

function ServicesAdminView({ services, onReload }: { services: Service[]; onReload: () => Promise<void> }) {
  const [notice, setNotice] = useState<Notice | null>(null);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.createService({
        name: String(form.get('name')),
        description: String(form.get('description') || ''),
        duration_minutes: Number(form.get('duration_minutes')),
        price: String(form.get('price')),
        is_active: true,
      });
      event.currentTarget.reset();
      setNotice({ type: 'success', text: 'Услуга создана.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить услугу.') });
    }
  }
  async function update(event: FormEvent<HTMLFormElement>, service: Service) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.updateService(service.id, {
        name: String(form.get('name')),
        description: String(form.get('description') || ''),
        duration_minutes: Number(form.get('duration_minutes')),
        price: String(form.get('price')),
        is_active: form.get('is_active') === 'on',
      });
      setNotice({ type: 'success', text: 'Услуга обновлена.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить услугу.') });
    }
  }

  return (
    <CrudSection title="Услуги" subtitle="Название, длительность, цена и доступность услуги." notice={notice} onSubmit={create} fields={[['name', 'Название'], ['duration_minutes', 'Длительность, мин'], ['price', 'Цена'], ['description', 'Описание']]}>
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
      {!services.length ? <EmptyState text="Услуг пока нет." /> : null}
    </CrudSection>
  );
}

function BranchesAdminView({ branches, onReload }: { branches: Branch[]; onReload: () => Promise<void> }) {
  const [notice, setNotice] = useState<Notice | null>(null);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.createBranch({
        name: String(form.get('name')),
        address: String(form.get('address')),
        phone: String(form.get('phone') || ''),
        timezone: String(form.get('timezone') || 'UTC'),
        is_active: true,
      });
      event.currentTarget.reset();
      setNotice({ type: 'success', text: 'Филиал создан.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить филиал.') });
    }
  }
  async function update(event: FormEvent<HTMLFormElement>, branch: Branch) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.updateBranch(branch.id, {
        name: String(form.get('name')),
        address: String(form.get('address')),
        phone: String(form.get('phone') || ''),
        timezone: String(form.get('timezone') || 'UTC'),
        is_active: form.get('is_active') === 'on',
      });
      setNotice({ type: 'success', text: 'Филиал обновлен.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить филиал.') });
    }
  }

  return (
    <CrudSection title="Филиалы" subtitle="Адреса, телефоны и часовые пояса точек обслуживания." notice={notice} onSubmit={create} fields={[['name', 'Название'], ['address', 'Адрес'], ['phone', 'Телефон'], ['timezone', 'Timezone']]}>
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
      {!branches.length ? <EmptyState text="Филиалов пока нет." /> : null}
    </CrudSection>
  );
}

function BoxesAdminView({ boxes, branches, onReload }: { boxes: Workstation[]; branches: Branch[]; onReload: () => Promise<void> }) {
  const [notice, setNotice] = useState<Notice | null>(null);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.createBox({ branch: String(form.get('branch')), name: String(form.get('name')), is_active: true });
      event.currentTarget.reset();
      setNotice({ type: 'success', text: 'Бокс создан.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить бокс.') });
    }
  }
  async function update(event: FormEvent<HTMLFormElement>, box: Workstation) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.updateBox(box.id, {
        branch: String(form.get('branch')),
        name: String(form.get('name')),
        is_active: form.get('is_active') === 'on',
      });
      setNotice({ type: 'success', text: 'Бокс обновлен.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить бокс.') });
    }
  }

  return (
    <section className="admin-stack">
      <div className="admin-section-header">
        <div>
          <h3 className="section-title">Боксы</h3>
          <p className="muted">Рабочие места по филиалам.</p>
        </div>
        <strong>{boxes.length}</strong>
      </div>
      {notice ? <p className={notice.type === 'success' ? 'admin-success' : 'inline-error'}>{notice.text}</p> : null}
      <form className="admin-form" onSubmit={(event) => void create(event)}>
        <select name="branch" required>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>
        <input name="name" placeholder="Название бокса" required />
        <button className="primary-button compact" type="submit">Создать</button>
      </form>
      <div className="admin-list">
        {boxes.map((box) => (
          <form className="admin-edit-row compact-edit" key={box.id} onSubmit={(event) => void update(event, box)}>
            <select name="branch" defaultValue={box.branch} required>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>
            <input name="name" defaultValue={box.name} aria-label="Название бокса" />
            <label className="admin-check"><input name="is_active" type="checkbox" defaultChecked={box.is_active} /> Активен</label>
            <button className="secondary-button" type="submit">Сохранить</button>
          </form>
        ))}
        {!boxes.length ? <EmptyState text="Боксов пока нет." /> : null}
      </div>
    </section>
  );
}

function ScheduleAdminView({ hours, exceptions, branchById, onReload }: { hours: BusinessHour[]; exceptions: ScheduleException[]; branchById: Map<string, Branch>; onReload: () => Promise<void> }) {
  const [notice, setNotice] = useState<Notice | null>(null);

  async function update(event: FormEvent<HTMLFormElement>, hour: BusinessHour) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setNotice(null);
      await adminApi.updateBusinessHour(hour.id, {
        is_closed: form.get('is_closed') === 'on',
        opening_time: String(form.get('opening_time') || ''),
        closing_time: String(form.get('closing_time') || ''),
      });
      setNotice({ type: 'success', text: 'Расписание обновлено.' });
      await onReload();
    } catch (caught) {
      setNotice({ type: 'error', text: readableError(caught, 'Не удалось сохранить расписание.') });
    }
  }
  return (
    <section className="admin-stack">
      <div className="admin-section-header">
        <div>
          <h3 className="section-title">Рабочие часы</h3>
          <p className="muted">Базовое недельное расписание по филиалам.</p>
        </div>
        <strong>{hours.length}</strong>
      </div>
      {notice ? <p className={notice.type === 'success' ? 'admin-success' : 'inline-error'}>{notice.text}</p> : null}
      <div className="admin-schedule-grid">
        {hours.map((hour) => (
          <form className="admin-schedule-card" key={hour.id} onSubmit={(event) => void update(event, hour)}>
            <div>
              <strong>{branchById.get(hour.branch)?.name ?? 'Филиал'}</strong>
              <span>{weekdayLabels[hour.weekday] ?? `День ${hour.weekday + 1}`}</span>
            </div>
            <input name="opening_time" type="time" defaultValue={hour.opening_time ?? ''} />
            <input name="closing_time" type="time" defaultValue={hour.closing_time ?? ''} />
            <label className="admin-check"><input name="is_closed" type="checkbox" defaultChecked={hour.is_closed} /> Закрыто</label>
            <button className="secondary-button" type="submit">Сохранить</button>
          </form>
        ))}
      </div>
      <Panel title="Исключения" subtitle="Праздники и разовые изменения графика">
        <AdminTable rows={exceptions} empty="Исключений в расписании нет." columns={['Дата', 'Филиал', 'График', 'Причина']} render={(item) => [
          formatDate(item.date),
          branchById.get(item.branch)?.name ?? 'Филиал',
          item.is_closed ? 'Закрыто' : `${item.opening_time ?? ''} - ${item.closing_time ?? ''}`,
          item.reason || 'Без причины',
        ]} />
      </Panel>
    </section>
  );
}

function CrudSection({ children, fields, notice, onSubmit, subtitle, title }: { children: ReactNode; fields: Array<[string, string]>; notice: Notice | null; onSubmit: (event: FormEvent<HTMLFormElement>) => void; subtitle: string; title: string }) {
  return (
    <section className="admin-stack">
      <div className="admin-section-header">
        <div>
          <h3 className="section-title">{title}</h3>
          <p className="muted">{subtitle}</p>
        </div>
      </div>
      {notice ? <p className={notice.type === 'success' ? 'admin-success' : 'inline-error'}>{notice.text}</p> : null}
      <form className="admin-form" onSubmit={onSubmit}>
        {fields.map(([name, label]) => <input key={name} name={name} placeholder={label} required={name !== 'description' && name !== 'phone'} />)}
        <button className="primary-button compact" type="submit">Создать</button>
      </form>
      <div className="admin-list">{children}</div>
    </section>
  );
}

function Panel({ children, subtitle, title }: { children: ReactNode; subtitle?: string; title: string }) {
  return (
    <div className="admin-panel">
      <div className="admin-panel-head">
        <h3 className="section-title">{title}</h3>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {children}
    </div>
  );
}

function AdminField({ label, value }: { label: string; value: string }) {
  return (
    <div className="admin-field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="admin-empty">{text}</div>;
}

function AdminTable<T>({ rows, columns, empty, render }: { rows: T[]; columns: string[]; empty: string; render: (row: T) => string[] }) {
  if (!rows.length) {
    return <EmptyState text={empty} />;
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
