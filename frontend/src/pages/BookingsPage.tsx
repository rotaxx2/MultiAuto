import { useCallback, useEffect, useState } from 'react';

import { cancelBooking, getMyBookings } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Booking } from '../types/api';
import { formatBookingStatus, formatDateTime, formatPrice, humanizeError, statusBadgeClass } from '../utils/format';

export function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const loadBookings = useCallback((showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    return getMyBookings()
      .then((response) => {
        setError('');
        setBookings(response.results);
      })
      .catch((caught: unknown) => {
        setError(humanizeError(caught, 'Не удалось загрузить записи. Попробуйте еще раз.'));
      })
      .finally(() => {
        if (showLoading) {
          setLoading(false);
        }
      });
  }, []);

  useEffect(() => {
    void loadBookings(true);
  }, [loadBookings]);

  useEffect(() => {
    const refreshVisibleBookings = () => {
      if (document.visibilityState === 'visible') {
        void loadBookings();
      }
    };

    document.addEventListener('visibilitychange', refreshVisibleBookings);
    window.addEventListener('focus', refreshVisibleBookings);
    return () => {
      document.removeEventListener('visibilitychange', refreshVisibleBookings);
      window.removeEventListener('focus', refreshVisibleBookings);
    };
  }, [loadBookings]);

  const cancel = async (id: string) => {
    const confirmed = window.confirm('Вы уверены, что хотите отменить запись?');
    if (!confirmed) {
      return;
    }
    setError('');
    setCancellingId(id);
    try {
      const updated = await cancelBooking(id);
      setBookings((items) => items.map((booking) => (booking.id === id ? updated : booking)));
    } catch (caught) {
      setError(humanizeError(caught, 'Не удалось отменить запись. Попробуйте еще раз.'));
    } finally {
      setCancellingId(null);
    }
  };

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем ваши записи." />;
  }

  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Мои записи</p>
        <h1>Текущие и будущие визиты</h1>
        <p>Здесь отображаются ваши записи и их статусы.</p>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      {bookings.length === 0 ? (
        <StateView title="Нет записей" description="Создайте первую запись через раздел записи." />
      ) : (
        <div className="list">
          {bookings.map((booking) => (
            <article className="booking-card" key={booking.id}>
              <div className="booking-card-header">
                <strong>{booking.service_name}</strong>
                <span className={statusBadgeClass(booking.status)}>{formatBookingStatus(booking.status)}</span>
              </div>
              <div className="booking-meta">
                <span>{formatDateTime(booking.start_at)}</span>
                <span>{booking.branch_name}</span>
                <span>{booking.car_label}</span>
                <span>{formatPrice(booking.price)}</span>
              </div>
              {booking.status === 'PENDING' ? (
                <button className="danger-button" disabled={cancellingId === booking.id} type="button" onClick={() => void cancel(booking.id)}>
                  {cancellingId === booking.id ? 'Отменяем...' : 'Отменить запись'}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
