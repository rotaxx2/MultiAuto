import { useState } from 'react';

import { StateView } from './components/StateView';
import { useAuth } from './hooks/useAuth';
import { useTelegram } from './hooks/useTelegram';
import { AppLayout } from './layouts/AppLayout';
import { BranchesPage } from './pages/BranchesPage';
import { BookingsPage } from './pages/BookingsPage';
import { CarsPage } from './pages/CarsPage';
import { CreateBookingPage } from './pages/CreateBookingPage';
import { AdminPanel } from './pages/AdminPanel';
import type { AdminPage } from './pages/AdminPanel';
import { HomePage } from './pages/HomePage';
import { ProfilePage } from './pages/ProfilePage';
import { ServicesPage } from './pages/ServicesPage';
import type { PageId } from './types/navigation';

export default function App() {
  const telegram = useTelegram();
  const auth = useAuth(telegram.initData, telegram.startParam, telegram.isTelegram, telegram.ready);
  const [page, setPage] = useState<PageId>('home');
  const isAdminRoute = window.location.pathname.startsWith('/admin');
  const adminPage = getAdminPage(window.location.pathname);

  if (auth.status === 'loading') {
    return <StateView title="Загрузка..." description="Подключаем Mini App к MultiAuto." />;
  }

  if (auth.status === 'unauthorized') {
    return (
      <StateView
        title="Нужен Telegram"
        description={auth.error || 'Откройте приложение из Telegram-бота.'}
        actionLabel="Повторить"
        onAction={auth.retry}
      />
    );
  }

  if (auth.status === 'error' || !auth.user) {
    return (
      <StateView
        title="Не удалось загрузить данные"
        description={auth.error || 'Попробуйте открыть Mini App еще раз.'}
        actionLabel="Повторить"
        onAction={auth.retry}
      />
    );
  }

  if (isAdminRoute) {
    if (auth.user.role === 'CLIENT') {
      return <StateView title="Доступ закрыт" description="Административная панель доступна только ADMIN и OWNER." />;
    }
    return <AdminPanel initialPage={adminPage} />;
  }

  return (
    <AppLayout activePage={page} onNavigate={setPage}>
      {page === 'home' ? <HomePage user={auth.user} onNavigate={setPage} /> : null}
      {page === 'cars' ? <CarsPage /> : null}
      {page === 'services' ? <ServicesPage /> : null}
      {page === 'branches' ? <BranchesPage /> : null}
      {page === 'booking-create' ? <CreateBookingPage onNavigate={setPage} /> : null}
      {page === 'bookings' ? <BookingsPage /> : null}
      {page === 'profile' ? <ProfilePage user={auth.user} /> : null}
    </AppLayout>
  );
}

function getAdminPage(pathname: string): AdminPage {
  const segment = pathname.split('/').filter(Boolean)[1];
  if (segment === 'bookings' || segment === 'clients' || segment === 'services' || segment === 'branches' || segment === 'boxes' || segment === 'schedule' || segment === 'notifications') {
    return segment;
  }
  return 'dashboard';
}
