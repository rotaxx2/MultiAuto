import { useEffect, useState } from 'react';

import { getMyBookings } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Booking } from '../types/api';

export function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    getMyBookings()
      .then((response) => {
        if (mounted) {
          setBookings(response.results);
        }
      })
      .catch((caught: unknown) => {
        if (mounted) {
          setError(caught instanceof Error ? caught.message : 'Не удалось загрузить записи');
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем ваши записи." />;
  }

  if (error) {
    return <StateView title="Не удалось загрузить данные" description={error} />;
  }

  return (
    <section className="page">
      <h1>Записи</h1>
      {bookings.length === 0 ? (
        <StateView title="Нет записей" description="Создание записи будет подключено вместе с booking engine." />
      ) : (
        <div className="list">
          {bookings.map((booking) => (
            <article className="list-item" key={booking.id}>
              <strong>{booking.status}</strong>
              <span>{booking.starts_at}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
