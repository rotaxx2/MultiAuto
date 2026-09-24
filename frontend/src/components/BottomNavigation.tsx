import { CalendarDays, Car, Home, UserRound } from 'lucide-react';

import type { PageId } from '../types/navigation';

interface BottomNavigationProps {
  activePage: PageId;
  onChange: (page: PageId) => void;
}

const items = [
  { id: 'home', label: 'Главная', icon: Home },
  { id: 'cars', label: 'Авто', icon: Car },
  { id: 'bookings', label: 'Записи', icon: CalendarDays },
  { id: 'profile', label: 'Профиль', icon: UserRound },
] satisfies Array<{ id: PageId; label: string; icon: typeof Home }>;

export function BottomNavigation({ activePage, onChange }: BottomNavigationProps) {
  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            className={activePage === item.id ? 'nav-item active' : 'nav-item'}
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
          >
            <Icon size={20} aria-hidden="true" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
