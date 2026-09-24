import type { ReactNode } from 'react';

import { BottomNavigation } from '../components/BottomNavigation';
import type { PageId } from '../types/navigation';

interface AppLayoutProps {
  activePage: PageId;
  children: ReactNode;
  onNavigate: (page: PageId) => void;
}

export function AppLayout({ activePage, children, onNavigate }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <main className="content">{children}</main>
      <BottomNavigation activePage={activePage} onChange={onNavigate} />
    </div>
  );
}
