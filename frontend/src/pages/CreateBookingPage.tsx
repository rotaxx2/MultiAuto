import { useEffect, useMemo, useState } from 'react';

import { createBooking, getAvailability, getAvailableDates, getBranches, getMyCars, getServices } from '../api/profile';
import { StateView } from '../components/StateView';
import type { AvailabilitySlot, AvailableDate, Booking, Branch, Car, Service } from '../types/api';
import type { PageId } from '../types/navigation';
import { carTitle, formatDate, formatPrice, formatTime, formatVisitDate, humanizeError } from '../utils/format';

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
  const [submitting, setSubmitting] = useState(false);
  const [createdBooking, setCreatedBooking] = useState<Booking | null>(null);
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
      .catch((caught) => setError(humanizeError(caught, 'Не удалось загрузить данные для записи. Попробуйте еще раз.')))
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
      .catch((caught) => setError(humanizeError(caught, 'Не удалось загрузить даты записи. Попробуйте еще раз.')));
  }, [branchId]);

  useEffect(() => {
    if (!branchId || !serviceId || !date) {
      return;
    }
    setSlot(null);
    setSlotLoading(true);
    getAvailability(branchId, serviceId, date)
      .then((response) => setSlots(response.slots))
      .catch((caught) => setError(humanizeError(caught, 'Не удалось загрузить свободное время. Попробуйте обновить список.')))
      .finally(() => setSlotLoading(false));
  }, [branchId, date, serviceId]);

  const selectedBranch = useMemo(() => branches.find((item) => item.id === branchId), [branchId, branches]);
  const selectedService = useMemo(() => services.find((item) => item.id === serviceId), [serviceId, services]);
  const selectedCar = useMemo(() => cars.find((item) => item.id === carId), [carId, cars]);

  const submit = async () => {
    if (!slot || !selectedBranch || !selectedService || !selectedCar || submitting) {
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      const booking = await createBooking({
        branch_id: selectedBranch.id,
        service_id: selectedService.id,
        car_id: selectedCar.id,
        start_at: slot.start_at,
      });
      setCreatedBooking(booking);
    } catch (caught) {
      setError(humanizeError(caught, 'Не удалось создать запись. Проверьте выбранное время и попробуйте еще раз.'));
    } finally {
      setSubmitting(false);
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

  if (createdBooking) {
    return (
      <section className="page">
        <div className="success-panel">
          <p className="eyebrow">Готово</p>
          <h1>Запись создана</h1>
          <p>Мы сохранили вашу запись. Напоминание придет в Telegram ближе к визиту.</p>
        </div>
        <div className="summary-card">
          <div><span>Филиал</span><strong>{createdBooking.branch_name}</strong></div>
          <div><span>Услуга</span><strong>{createdBooking.service_name}</strong></div>
          <div><span>Автомобиль</span><strong>{createdBooking.car_label}</strong></div>
          <div><span>Дата и время</span><strong>{formatVisitDate(createdBooking.start_at)}, {formatTime(createdBooking.start_at)}</strong></div>
          <div><span>Стоимость</span><strong>{formatPrice(createdBooking.price)}</strong></div>
        </div>
        <div className="button-row">
          <button className="primary-button compact" type="button" onClick={() => onNavigate('bookings')}>Мои записи</button>
          <button className="secondary-button" type="button" onClick={() => onNavigate('home')}>На главную</button>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Новая запись</p>
        <h1>Выберите удобное время</h1>
        <p>Филиал, услуга, автомобиль, дата и свободный слот.</p>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}

      <div className="step-card">
        <div className="step-title"><span>1</span><h2>Филиал</h2></div>
        <div className="choice-list">
          {branches.map((branch) => (
            <button className={branchId === branch.id ? 'choice-card active' : 'choice-card'} key={branch.id} type="button" onClick={() => setBranchId(branch.id)}>
              <strong>{branch.name}</strong>
              <span>{branch.address}</span>
              <small>{branch.is_active ? 'Открыт для записи' : 'Недоступен'}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="step-card">
        <div className="step-title"><span>2</span><h2>Услуга</h2></div>
        <div className="choice-list">
          {services.map((service) => (
            <button className={serviceId === service.id ? 'choice-card active' : 'choice-card'} key={service.id} type="button" onClick={() => setServiceId(service.id)}>
              <strong>{service.name}</strong>
              <span>{service.description || `${service.duration_minutes} минут`}</span>
              <small className="price-chip">{formatPrice(service.price)}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="step-card">
        <div className="step-title"><span>3</span><h2>Автомобиль</h2></div>
        <div className="choice-list">
          {cars.map((car) => (
            <button className={carId === car.id ? 'choice-card active' : 'choice-card'} key={car.id} type="button" onClick={() => setCarId(car.id)}>
              <strong>{carTitle(car)}</strong>
              <span>{car.license_plate}</span>
              <small>{car.color}{car.year ? ` · ${car.year}` : ''}</small>
            </button>
          ))}
        </div>
        <button className="secondary-button" type="button" onClick={() => onNavigate('cars')}>Добавить автомобиль</button>
      </div>

      <div className="step-card">
        <div className="step-title"><span>4</span><h2>Дата</h2></div>
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
              <small>{formatDate(item.date)}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="step-card">
        <div className="step-title"><span>5</span><h2>Время</h2></div>
        {slotLoading ? <div className="skeleton-list"><span /><span /><span /></div> : null}
        {!slotLoading && slots.length === 0 ? <p className="empty-note">На эту дату свободных мест нет. Выберите другой день.</p> : null}
        <div className="slot-grid">
          {slots.filter((item) => item.is_available).map((item) => (
            <button className={slot?.start_at === item.start_at ? 'slot-button active' : 'slot-button'} key={item.start_at} type="button" onClick={() => setSlot(item)}>
              <span>{formatTime(item.start_at)}</span>
              <small>{item.free_workstations} {item.free_workstations === 1 ? 'бокс свободен' : 'бокса свободно'}</small>
            </button>
          ))}
        </div>
      </div>

      {slot && selectedBranch && selectedService && selectedCar ? (
        <div className="summary-card">
          <h2 className="section-title">Ваша запись</h2>
          <div><span>Филиал</span><strong>{selectedBranch.name}</strong></div>
          <div><span>Услуга</span><strong>{selectedService.name} · {formatPrice(selectedService.price)}</strong></div>
          <div><span>Автомобиль</span><strong>{carTitle(selectedCar)} · {selectedCar.license_plate}</strong></div>
          <div><span>Дата</span><strong>{formatVisitDate(slot.start_at)}</strong></div>
          <div><span>Время</span><strong>{formatTime(slot.start_at)}</strong></div>
          <div><span>Свободные боксы</span><strong>{slot.free_workstations} из {slot.total_workstations}</strong></div>
          <button className="primary-button compact" disabled={submitting} type="button" onClick={() => void submit()}>
            {submitting ? 'Создаем запись...' : 'Подтвердить запись'}
          </button>
        </div>
      ) : null}
    </section>
  );
}
