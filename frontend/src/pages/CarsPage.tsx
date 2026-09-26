import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';

import { createMyCar, deleteMyCar, getMyCars, updateMyCar } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Car } from '../types/api';

type CarForm = Omit<Car, 'id' | 'created_at' | 'updated_at'>;

const emptyForm: CarForm = {
  brand: '',
  model: '',
  license_plate: '',
  color: '',
  year: null,
};

export function CarsPage() {
  const [cars, setCars] = useState<Car[]>([]);
  const [form, setForm] = useState<CarForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadCars = () => {
    setLoading(true);
    setError('');
    getMyCars()
      .then((response) => {
        setCars(response.results);
      })
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : 'Не удалось загрузить автомобили');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadCars();
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');

    try {
      if (editingId) {
        await updateMyCar(editingId, form);
      } else {
        await createMyCar(form);
      }
      setForm(emptyForm);
      setEditingId(null);
      loadCars();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось сохранить автомобиль');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (car: Car) => {
    setEditingId(car.id);
    setForm({
      brand: car.brand,
      model: car.model,
      license_plate: car.license_plate,
      color: car.color,
      year: car.year,
    });
  };

  const removeCar = async (id: string) => {
    setError('');
    try {
      await deleteMyCar(id);
      setCars((items) => items.filter((car) => car.id !== id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось удалить автомобиль');
    }
  };

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем ваши автомобили." />;
  }

  if (error) {
    return <StateView title="Не удалось загрузить данные" description={error} />;
  }

  return (
    <section className="page">
      <h1>Автомобили</h1>
      <form className="form" onSubmit={handleSubmit}>
        <input
          required
          placeholder="Марка"
          value={form.brand}
          onChange={(event) => setForm({ ...form, brand: event.target.value })}
        />
        <input
          required
          placeholder="Модель"
          value={form.model}
          onChange={(event) => setForm({ ...form, model: event.target.value })}
        />
        <input
          required
          placeholder="Госномер"
          value={form.license_plate}
          onChange={(event) => setForm({ ...form, license_plate: event.target.value })}
        />
        <input
          required
          placeholder="Цвет"
          value={form.color}
          onChange={(event) => setForm({ ...form, color: event.target.value })}
        />
        <input
          min="1900"
          max="2100"
          placeholder="Год, необязательно"
          type="number"
          value={form.year ?? ''}
          onChange={(event) => setForm({ ...form, year: event.target.value ? Number(event.target.value) : null })}
        />
        <div className="button-row">
          <button className="primary-button compact" disabled={saving} type="submit">
            {editingId ? 'Сохранить' : 'Добавить автомобиль'}
          </button>
          {editingId ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setEditingId(null);
                setForm(emptyForm);
              }}
            >
              Отмена
            </button>
          ) : null}
        </div>
      </form>
      {cars.length === 0 ? (
        <StateView title="Нет автомобилей" description="Добавьте автомобиль, чтобы он появился в списке." />
      ) : (
        <div className="list">
          {cars.map((car) => (
            <article className="list-item" key={car.id}>
              <strong>
                {car.brand} {car.model}
              </strong>
              <span>{car.license_plate}</span>
              <small>
                {car.color}
                {car.year ? ` · ${car.year}` : ''}
              </small>
              <div className="button-row">
                <button className="secondary-button" type="button" onClick={() => startEdit(car)}>
                  Редактировать
                </button>
                <button className="danger-button" type="button" onClick={() => void removeCar(car.id)}>
                  Удалить
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
