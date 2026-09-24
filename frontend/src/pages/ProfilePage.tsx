import type { User } from '../types/api';

interface ProfilePageProps {
  user: User;
}

export function ProfilePage({ user }: ProfilePageProps) {
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Не указано';

  return (
    <section className="page">
      <h1>Профиль</h1>
      <dl className="info-list">
        <div>
          <dt>Имя</dt>
          <dd>{fullName}</dd>
        </div>
        <div>
          <dt>Username</dt>
          <dd>{user.username ? `@${user.username}` : 'Не указан'}</dd>
        </div>
        <div>
          <dt>Телефон</dt>
          <dd>{user.phone_number || 'Не указан'}</dd>
        </div>
        <div>
          <dt>Организация</dt>
          <dd>{user.organization?.name ?? 'Не выбрана'}</dd>
        </div>
      </dl>
    </section>
  );
}
