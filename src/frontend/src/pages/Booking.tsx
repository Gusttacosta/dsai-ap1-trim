import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Booking.module.css';

// Mocks temporários até integrarmos com a API do FastAPI
const MOCK_BARBERS = [
  { id: '1', name: 'João Silva', expert: 'Fade & Degradê' },
  { id: '2', name: 'Carlos Santos', expert: 'Navalha Clássica' },
  { id: '3', name: 'Qualquer Barbeiro', expert: 'O primeiro disponível' },
];

const MOCK_SERVICES = [
  { id: '1', name: 'Corte Máquina', price: 40, time: '30 min' },
  { id: '2', name: 'Corte + Barba', price: 75, time: '1h' },
  { id: '3', name: 'Platinado', price: 120, time: '2h' },
];

const MOCK_TIMES = ['09:00', '09:30', '10:00', '11:30', '14:00', '16:30'];

const Booking = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [selectedBarber, setSelectedBarber] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedTime, setSelectedTime] = useState('');

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
    else {
      // Mock Finalizar
      alert('Agendamento Confirmado! ✂️');
      navigate('/');
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
    else navigate('/');
  };

  const isNextDisabled = () => {
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
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`${styles.step} ${step === s ? styles.active : ''} ${
              step > s ? styles.completed : ''
            }`}
          >
            {step > s ? '✓' : s}
          </div>
        ))}
      </div>

      {/* STEP 1: Barbeiro */}
      {step === 1 && (
        <div className={styles.grid}>
          {MOCK_BARBERS.map((barber) => (
            <div
              key={barber.id}
              className={`${styles.card} ${selectedBarber === barber.id ? styles.selected : ''}`}
              onClick={() => setSelectedBarber(barber.id)}
            >
              <div className={styles.cardTitle}>{barber.name}</div>
              <div className={styles.cardDesc}>{barber.expert}</div>
            </div>
          ))}
        </div>
      )}

      {/* STEP 2: Serviço */}
      {step === 2 && (
        <div className={styles.grid}>
          {MOCK_SERVICES.map((srv) => (
            <div
              key={srv.id}
              className={`${styles.card} ${selectedService === srv.id ? styles.selected : ''}`}
              onClick={() => setSelectedService(srv.id)}
            >
              <div className={styles.cardTitle}>{srv.name}</div>
              <div className={styles.cardDesc}>
                R$ {srv.price} • {srv.time}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* STEP 3: Horário */}
      {step === 3 && (
        <div className={styles.grid}>
          {MOCK_TIMES.map((time) => (
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

      {/* STEP 4: Confirmação */}
      {step === 4 && (
        <div style={{ textAlign: 'center' }}>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', color: '#fff' }}>Tudo Certo!</h3>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: '2rem' }}>
            Revise os dados abaixo antes de confirmar:
          </p>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '0.5rem', display: 'inline-block', textAlign: 'left' }}>
            <p><strong>Barbeiro:</strong> {MOCK_BARBERS.find(b => b.id === selectedBarber)?.name}</p>
            <p><strong>Serviço:</strong> {MOCK_SERVICES.find(s => s.id === selectedService)?.name}</p>
            <p><strong>Data/Hora:</strong> Hoje às {selectedTime}</p>
            <p style={{ color: 'var(--color-primary)', marginTop: '1rem', fontSize: '1.2rem', fontWeight: 'bold' }}>
              Total: R$ {MOCK_SERVICES.find(s => s.id === selectedService)?.price}
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
