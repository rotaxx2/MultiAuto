import { useEffect, useMemo, useState } from 'react';

import { createBooking, getAvailability, getAvailableDates, getBranches, getMyCars, getServices } from '../api/profile';
import { StateView } from '../components/StateView';
import type { AvailabilitySlot, AvailableDate, Branch, Car, Service } from '../types/api';
import type { PageId } from '../types/navigation';

interface CreateBookingPageProps {
  onNavigate: (page: PageId) => void;
}

export function CreateBookingPage({ onNavigate }: CreateBookingPageProps) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [dates, setDates] = useState<AvailableDate[]>([]);
  const [date, setDate] = useState('');
  const [branchId, setBranchId] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [carId, setCarId] = useState('');
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [slot, setSlot] = useState<AvailabilitySlot | null>(null);
  const [loading, setLoading] = useState(true);
  const [slotLoading, setSlotLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getBranches(), getServices(), getMyCars()])
      .then(([branchResponse, serviceResponse, carResponse]) => {
        setBranches(branchResponse.results);
        setServices(serviceResponse.results);
        setCars(carResponse.results);
        setBranchId(branchResponse.results[0]?.id ?? '');
        setServiceId(serviceResponse.results[0]?.id ?? '');
        setCarId(carResponse.results[0]?.id ?? '');
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Не удалось загрузить данные для записи'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!branchId) {
      return;
    }
    setDate('');
    setDates([]);
    setSlot(null);
    getAvailableDates(branchId)
      .then((response) => {
        setDates(response.dates);
        setDate(response.dates.find((item) => item.is_available)?.date ?? response.dates[0]?.date ?? '');
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Не удалось загрузить даты записи'));
  }, [branchId]);

  useEffect(() => {
    if (!branchId || !serviceId || !date) {
      return;
    }
    setSlot(null);
    setSlotLoading(true);
    getAvailability(branchId, serviceId, date)
      .then((response) => setSlots(response.slots))
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Не удалось загрузить свободное время'))
      .finally(() => setSlotLoading(false));
  }, [branchId, date, serviceId]);

  const selectedBranch = useMemo(() => branches.find((item) => item.id === branchId), [branchId, branches]);
  const selectedService = useMemo(() => services.find((item) => item.id === serviceId), [serviceId, services]);
  const selectedCar = useMemo(() => cars.find((item) => item.id === carId), [carId, cars]);

  const submit = async () => {
    if (!slot || !selectedBranch || !selectedService || !selectedCar) {
      return;
    }
    setError('');
    try {
      await createBooking({
        branch_id: selectedBranch.id,
        service_id: selectedService.id,
        car_id: selectedCar.id,
        start_at: slot.start_at,
      });
      onNavigate('bookings');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось создать запись');
    }
  };

  if (loading) {
    return <StateView title="Загрузка..." description="Готовим форму записи." />;
  }

  if (!cars.length) {
    return (
      <StateView
        title="Нужен автомобиль"
        description="Добавьте автомобиль перед созданием записи."
        actionLabel="К автомобилям"
        onAction={() => onNavigate('cars')}
      />
    );
  }

  return (
    <section className="page">
      <h1>Новая запись</h1>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="form">
        <label>
          Филиал
          <select value={branchId} onChange={(event) => setBranchId(event.target.value)}>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Услуга
          <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
            {services.map((service) => (
              <option key={service.id} value={service.id}>
                {service.name} · {service.price} ₽
              </option>
            ))}
          </select>
        </label>
        <label>
          Автомобиль
          <select value={carId} onChange={(event) => setCarId(event.target.value)}>
            {cars.map((car) => (
              <option key={car.id} value={car.id}>
                {car.brand} {car.model} · {car.license_plate}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="list">
        <h2 className="section-title">Дата</h2>
        <div className="date-grid">
          {dates.map((item) => (
            <button
              className={date === item.date ? 'date-button active' : 'date-button'}
              disabled={!item.is_available}
              key={item.date}
              type="button"
              onClick={() => setDate(item.date)}
            >
              <span>{item.label}</span>
              <small>{new Date(`${item.date}T12:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}</small>
            </button>
          ))}
        </div>

        <h2 className="section-title">Свободное время</h2>
        {slotLoading ? <span className="muted">Загрузка...</span> : null}
        {!slotLoading && slots.length === 0 ? <span className="muted">Нет доступных интервалов</span> : null}
        <div className="slot-grid">
          {slots.map((item) => (
            <button
              className={slot?.start_at === item.start_at ? 'slot-button active' : 'slot-button'}
              key={item.start_at}
              type="button"
              onClick={() => setSlot(item)}
            >
              <span>{new Date(item.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <small>Свободно {item.free_workstations} из {item.total_workstations}</small>
            </button>
          ))}
        </div>
      </div>

      {slot && selectedBranch && selectedService && selectedCar ? (
        <div className="form">
          <h2 className="section-title">Подтверждение</h2>
          <p>{selectedBranch.name}</p>
          <p>
            {selectedService.name} · {selectedService.duration_minutes} минут · {selectedService.price} ₽
          </p>
          <p>
            {selectedCar.brand} {selectedCar.model} · {selectedCar.license_plate}
          </p>
          <p>
            {new Date(slot.start_at).toLocaleString()} · свободно {slot.free_workstations} из {slot.total_workstations}
          </p>
          <button className="primary-button compact" type="button" onClick={() => void submit()}>
            Подтвердить запись
          </button>
        </div>
      ) : null}
    </section>
  );
}
