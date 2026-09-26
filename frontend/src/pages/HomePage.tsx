import { CalendarPlus, CarFront, ClipboardList } from 'lucide-react';

import type { User } from '../types/api';
import type { PageId } from '../types/navigation';

interface HomePageProps {
  user: User;
  onNavigate: (page: PageId) => void;
}

export function HomePage({ user, onNavigate }: HomePageProps) {
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'клиент';

  return (
    <section className="page">
      <div className="hero">
        <p className="eyebrow">MultiAuto</p>
        <h1>Здравствуйте, {displayName}</h1>
        <p>{user.organization?.name ?? 'Выберите автомойку через Telegram-бота, чтобы продолжить запись.'}</p>
      </div>

      <div className="action-grid">
        <button className="action-card primary" type="button" onClick={() => onNavigate('booking-create')}>
          <CalendarPlus size={24} aria-hidden="true" />
          <span>Записаться на мойку</span>
          <small>Скоро подключим выбор услуги и времени</small>
        </button>
        <button className="action-card" type="button" onClick={() => onNavigate('cars')}>
          <CarFront size={24} aria-hidden="true" />
          <span>Мои автомобили</span>
          <small>Посмотреть сохраненные авто</small>
        </button>
        <button className="action-card" type="button" onClick={() => onNavigate('bookings')}>
          <ClipboardList size={24} aria-hidden="true" />
          <span>Мои записи</span>
          <small>Текущие и будущие визиты</small>
        </button>
      </div>
    </section>
  );
}
