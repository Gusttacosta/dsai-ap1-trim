import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Booking.module.css';
import api from '../api';
import { MAX_DAYS_AHEAD, addDays, formatLongDate, shopToday, toStartDatetime } from '../utils/shopDate';

const Booking = () => {
  const navigate = useNavigate();
  const isAuthenticated = !!localStorage.getItem('token');
  const [step, setStep] = useState(isAuthenticated ? 1 : 0);
  const [guestName, setGuestName] = useState('');
  
  const [barbers, setBarbers] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);
  
  const [selectedBarber, setSelectedBarber] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedTime, setSelectedTime] = useState('');
  const [availableSlots, setAvailableSlots] = useState<string[]>([]);

  const today = shopToday();
  const lastDate = addDays(today, MAX_DAYS_AHEAD);
  const [selectedDate, setSelectedDate] = useState(today);

  useEffect(() => {
    api.get('/barbers').then(res => setBarbers(res.data)).catch(console.error);
    api.get('/services').then(res => setServices(res.data)).catch(console.error);
  }, []);

  useEffect(() => {
    if (step === 3 && selectedBarber && selectedService) {
      const service = services.find(s => s.id === selectedService);
      const duration = service ? service.duration_minutes : 30;
      
      api.get(`/appointments/availability?barber_id=${selectedBarber}&target_date=${selectedDate}&duration_minutes=${duration}`)
        .then(res => {
          const slots: string[] = res.data.available_slots || [];
          setAvailableSlots(slots);
          setSelectedTime(current => (slots.includes(current) ? current : ''));
        })
        .catch(console.error);
    }
  }, [step, selectedBarber, selectedService, services, selectedDate]);

  const handleNext = async () => {
    if (step < 4) setStep(step + 1);
    else {
      try {
        const payload = {
          barber_id: selectedBarber,
          service_ids: [selectedService],
          start_datetime: toStartDatetime(selectedDate, selectedTime),
          ...( !isAuthenticated && { guest_name: guestName } )
        };
        
        const endpoint = isAuthenticated ? '/appointments' : '/appointments/guest';
        await api.post(endpoint, payload);
        
        alert(`Agendamento confirmado para ${formatLongDate(selectedDate)} às ${selectedTime}! ✂️`);
        navigate('/');
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Erro desconhecido.';
        alert(`Falha no agendamento: ${errorMsg}`);
      }
    }
  };

  const handleBack = () => {
    if (step > (isAuthenticated ? 1 : 0)) setStep(step - 1);
    else navigate('/');
  };

  const isNextDisabled = () => {
    if (step === 0) return guestName.trim().length < 3;
    if (step === 1) return !selectedBarber;
    if (step === 2) return !selectedService;
    if (step === 3) return !selectedTime;
    return false;
  };

  return (
    <div className={styles.bookingContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>Agendar Horário</h2>
        <p className={styles.subtitle}>Sua aparência em boas mãos.</p>
      </div>

      <div className={styles.stepIndicator}>
        {(!isAuthenticated ? [0, 1, 2, 3, 4] : [1, 2, 3, 4]).map((s) => (
          <div
            key={s}
            className={`${styles.step} ${step === s ? styles.active : ''} ${
              step > s ? styles.completed : ''
            }`}
          >
            {step > s ? '✓' : (s === 0 ? '📝' : s)}
          </div>
        ))}
      </div>

      {/* STEP 0: Nome do Convidado */}
      {step === 0 && (
        <div style={{ textAlign: 'center', maxWidth: '400px', margin: '0 auto' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: '#fff' }}>Como podemos te chamar?</h3>
          <input 
            type="text" 
            placeholder="Seu nome" 
            value={guestName} 
            onChange={e => setGuestName(e.target.value)} 
            style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', border: '1px solid var(--color-border)', background: '#2c2c2e', color: '#fff', fontSize: '1.1rem', textAlign: 'center' }}
            autoFocus
          />
        </div>
      )}

      {/* STEP 1: Barbeiro */}
      {step === 1 && (
        <div className={styles.grid}>
          {barbers.map((barber) => (
            <div
              key={barber.id}
              className={`${styles.card} ${selectedBarber === barber.id ? styles.selected : ''}`}
              onClick={() => setSelectedBarber(barber.id)}
            >
              <div className={styles.cardTitle}>{barber.full_name}</div>
              <div className={styles.cardDesc}>{barber.bio || 'Profissional Trim'}</div>
            </div>
          ))}
        </div>
      )}

      {/* STEP 2: Serviço */}
      {step === 2 && (
        <div className={styles.grid}>
          {services.map((srv) => (
            <div
              key={srv.id}
              className={`${styles.card} ${selectedService === srv.id ? styles.selected : ''}`}
              onClick={() => setSelectedService(srv.id)}
            >
              <div className={styles.cardTitle}>{srv.name}</div>
              <div className={styles.cardDesc}>
                R$ {Number(srv.price).toFixed(2)} • {srv.duration_minutes} min
              </div>
            </div>
          ))}
        </div>
      )}

      {/* STEP 3: Data e horário */}
      {step === 3 && (
        <div>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <label htmlFor="booking-date" style={{ display: 'block', marginBottom: '0.5rem', color: '#fff' }}>
              Data
            </label>
            <input
              id="booking-date"
              type="date"
              value={selectedDate}
              min={today}
              max={lastDate}
              onChange={e => setSelectedDate(e.target.value || today)}
              style={{ padding: '0.6rem', borderRadius: '8px', border: '1px solid var(--color-border)', background: '#2c2c2e', color: '#fff', fontSize: '1rem' }}
            />
            <p style={{ marginTop: '0.5rem', color: 'var(--color-text-secondary)' }}>{formatLongDate(selectedDate)}</p>
          </div>
          {availableSlots.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              Nenhum horário livre nesta data. Escolha outro dia.
            </p>
          ) : (
            <div className={styles.gridTime}>
              {availableSlots.map((time) => (
                <div
                  key={time}
                  className={`${styles.card} ${selectedTime === time ? styles.selected : ''}`}
                  onClick={() => setSelectedTime(time)}
                >
                  <div className={styles.cardTitle}>{time}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* STEP 4: Confirmação */}
      {step === 4 && (
        <div style={{ textAlign: 'center' }}>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', color: '#fff' }}>Tudo Certo!</h3>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: '2rem' }}>
            Revise os dados abaixo antes de confirmar:
          </p>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '0.5rem', display: 'inline-block', textAlign: 'left' }}>
            <p><strong>Barbeiro:</strong> {barbers.find(b => b.id === selectedBarber)?.full_name}</p>
            <p><strong>Serviço:</strong> {services.find(s => s.id === selectedService)?.name}</p>
            <p><strong>Data/Hora:</strong> {formatLongDate(selectedDate)} às {selectedTime}</p>
            <p style={{ color: 'var(--color-primary)', marginTop: '1rem', fontSize: '1.2rem', fontWeight: 'bold' }}>
              Total: R$ {Number(services.find(s => s.id === selectedService)?.price || 0).toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className={styles.actions}>
        <button className={styles.btnBack} onClick={handleBack}>
          {step === 1 ? 'Cancelar' : 'Voltar'}
        </button>
        <button className={styles.btnNext} onClick={handleNext} disabled={isNextDisabled()}>
          {step === 4 ? 'Confirmar Agendamento' : 'Próximo'}
        </button>
      </div>
    </div>
  );
};

export default Booking;

