import { useEffect, useState } from 'react';

import { getMyCars } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Car } from '../types/api';

export function CarsPage() {
  const [cars, setCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    getMyCars()
      .then((response) => {
        if (mounted) {
          setCars(response.results);
        }
      })
      .catch((caught: unknown) => {
        if (mounted) {
          setError(caught instanceof Error ? caught.message : 'Не удалось загрузить автомобили');
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
    return <StateView title="Загрузка..." description="Получаем ваши автомобили." />;
  }

  if (error) {
    return <StateView title="Не удалось загрузить данные" description={error} />;
  }

  return (
    <section className="page">
      <h1>Автомобили</h1>
      {cars.length === 0 ? (
        <StateView title="Нет автомобилей" description="Добавление автомобиля появится на следующем этапе." />
      ) : (
        <div className="list">
          {cars.map((car) => (
            <article className="list-item" key={car.id}>
              <strong>
                {car.brand} {car.model}
              </strong>
              <span>{car.license_plate}</span>
              <small>
                {car.color} · {car.vehicle_type}
              </small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
