import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';

import { createMyCar, deleteMyCar, getMyCars, updateMyCar } from '../api/profile';
import { StateView } from '../components/StateView';
import type { Car } from '../types/api';
import { carTitle, humanizeError } from '../utils/format';

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
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const loadCars = () => {
    setLoading(true);
    setError('');
    getMyCars()
      .then((response) => {
        setCars(response.results);
      })
      .catch((caught: unknown) => {
        setError(humanizeError(caught, 'Не удалось загрузить автомобили. Попробуйте еще раз.'));
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
      setError(humanizeError(caught, 'Не удалось сохранить автомобиль. Проверьте данные и попробуйте еще раз.'));
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
    const confirmed = window.confirm('Удалить автомобиль из списка?');
    if (!confirmed) {
      return;
    }
    setError('');
    setDeletingId(id);
    try {
      await deleteMyCar(id);
      setCars((items) => items.filter((car) => car.id !== id));
    } catch (caught) {
      setError(humanizeError(caught, 'Не удалось удалить автомобиль. Возможно, он связан с активной записью.'));
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return <StateView title="Загрузка..." description="Получаем ваши автомобили." />;
  }

  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Мои автомобили</p>
        <h1>Автомобили для записи</h1>
        <p>Добавьте авто один раз и выбирайте его при бронировании.</p>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
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
            {saving ? 'Сохраняем...' : editingId ? 'Сохранить' : 'Добавить автомобиль'}
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
        <div className="empty-note">У вас пока нет автомобилей. Заполните форму выше, чтобы добавить первый автомобиль.</div>
      ) : (
        <div className="list">
          {cars.map((car) => (
            <article className="car-card" key={car.id}>
              <strong>{carTitle(car)}</strong>
              <span className="plate">{car.license_plate}</span>
              <small>{car.color}{car.year ? ` · ${car.year}` : ''}</small>
              <div className="button-row">
                <button className="secondary-button" type="button" onClick={() => startEdit(car)}>
                  Редактировать
                </button>
                <button className="danger-button" disabled={deletingId === car.id} type="button" onClick={() => void removeCar(car.id)}>
                  {deletingId === car.id ? 'Удаляем...' : 'Удалить'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
