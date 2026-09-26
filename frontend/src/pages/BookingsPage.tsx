import { useEffect, useState } from 'react';

import { cancelBooking, getMyBookings } from '../api/profile';
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

  const cancel = async (id: string) => {
    setError('');
    try {
      const updated = await cancelBooking(id);
      setBookings((items) => items.map((booking) => (booking.id === id ? updated : booking)));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось отменить запись');
    }
  };

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
        <StateView title="Нет записей" description="Создайте первую запись через раздел записи." />
      ) : (
        <div className="list">
          {bookings.map((booking) => (
            <article className="list-item" key={booking.id}>
              <strong>{booking.service_name}</strong>
              <span>{booking.branch_name}</span>
              <small>
                {new Date(booking.start_at).toLocaleString()} · {booking.status} · {booking.price} ₽
              </small>
              {booking.status === 'PENDING' ? (
                <button className="danger-button" type="button" onClick={() => void cancel(booking.id)}>
                  Отменить
                </button>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
