import { useEffect, useState } from 'react';

import { getServices } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Service } from '../types/api';

export function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getServices()
      .then((response) => setServices(response.results))
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : 'Не удалось загрузить услуги'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем услуги автомойки." />;
  }

  if (error) {
    return <StateView title="Не удалось загрузить данные" description={error} />;
  }

  return (
    <section className="page">
      <h1>Услуги</h1>
      {services.length === 0 ? (
        <StateView title="Нет услуг" description="Активные услуги пока не добавлены." />
      ) : (
        <div className="list">
          {services.map((service) => (
            <article className="list-item" key={service.id}>
              <strong>{service.name}</strong>
              {service.description ? <span>{service.description}</span> : null}
              <small>
                {service.duration_minutes} минут · {service.price} ₽
              </small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
