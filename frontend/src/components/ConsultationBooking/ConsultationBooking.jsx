import { useState, useEffect } from "react";
import { format, parseISO } from "date-fns";
import { ru } from "date-fns/locale";
import { getConsultationSlots, bookConsultation } from "../../services/api";

const DURATIONS = [
  { minutes: 30, label: "30 минут", price: 2500, desc: "Экспресс: 1–2 коротких вопроса" },
  { minutes: 60, label: "1 час", price: 4500, desc: "Стандарт: разбор ситуации + рекомендации" },
  { minutes: 90, label: "1.5 часа", price: 6500, desc: "Расширенная: сложные дела, стратегия" },
];

export default function ConsultationBooking() {
  const [step, setStep] = useState("duration");   // duration → slot → details → payment
  const [duration, setDuration] = useState(null);
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [errors, setErrors] = useState({});
  const [booking, setBooking] = useState(false);

  const loadSlots = async (dur) => {
    setSlotsLoading(true);
    try {
      const { data } = await getConsultationSlots(14);
      setSlots(data.slots || []);
    } catch {
      setSlots([]);
    } finally {
      setSlotsLoading(false);
    }
  };

  const handleDurationSelect = (d) => {
    setDuration(d);
    loadSlots(d.minutes);
    setStep("slot");
  };

  const handleSlotSelect = (slot) => {
    setSelectedSlot(slot);
    setStep("details");
  };

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = "Укажите имя";
    if (!form.email.includes("@")) e.email = "Некорректный email";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleBook = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setBooking(true);
    try {
      const { data } = await bookConsultation({
        client_name: form.name,
        client_email: form.email,
        client_phone: form.phone || undefined,
        duration_minutes: duration.minutes,
        scheduled_at: selectedSlot.start_time,
        timezone: "Europe/Moscow",
        payment_provider: "yookassa",
      });
      window.location.href = data.checkout_url;
    } catch {
      setErrors({ submit: "Ошибка бронирования. Попробуйте позже." });
    } finally {
      setBooking(false);
    }
  };

  // ─── Шаг 1: выбор длительности ─────────────────────────────────────────
  if (step === "duration") {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Выберите формат консультации</h2>
        {DURATIONS.map((d) => (
          <button
            key={d.minutes}
            onClick={() => handleDurationSelect(d)}
            className="w-full text-left bg-white border-2 border-gray-200 hover:border-blue-500 rounded-xl p-4 transition-colors group"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-semibold text-gray-900 group-hover:text-blue-700">
                  {d.label}
                </span>
                <p className="text-sm text-gray-500 mt-0.5">{d.desc}</p>
              </div>
              <span className="text-lg font-bold text-gray-900">
                {d.price.toLocaleString("ru")} ₽
              </span>
            </div>
          </button>
        ))}
        <p className="text-xs text-gray-400 text-center pt-2">
          После оплаты вы автоматически получите ссылку на Zoom-встречу
        </p>
      </div>
    );
  }

  // ─── Шаг 2: выбор слота ────────────────────────────────────────────────
  if (step === "slot") {
    const grouped = groupSlotsByDay(slots);

    return (
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <button onClick={() => setStep("duration")} className="text-blue-600 hover:underline text-sm">
            ← Назад
          </button>
          <h2 className="text-xl font-bold text-gray-900">Выберите время</h2>
        </div>

        {slotsLoading ? (
          <div className="flex justify-center py-10">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : slots.length === 0 ? (
          <p className="text-center text-gray-500 py-8">
            Нет доступных слотов. Напишите нам напрямую для согласования времени.
          </p>
        ) : (
          Object.entries(grouped).map(([day, daySlots]) => (
            <div key={day}>
              <p className="text-sm font-medium text-gray-500 mb-2">{day}</p>
              <div className="flex flex-wrap gap-2">
                {daySlots.map((slot) => {
                  const time = format(parseISO(slot.start_time), "HH:mm");
                  return (
                    <button
                      key={slot.start_time}
                      onClick={() => handleSlotSelect(slot)}
                      className="px-4 py-2 bg-white border-2 border-gray-200 hover:border-blue-500 hover:bg-blue-50 rounded-lg text-sm font-medium transition-colors"
                    >
                      {time}
                    </button>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  // ─── Шаг 3: контактные данные ──────────────────────────────────────────
  if (step === "details") {
    const slotDt = parseISO(selectedSlot.start_time);
    const slotLabel = format(slotDt, "d MMMM, EEEE, HH:mm", { locale: ru });

    return (
      <div className="space-y-5">
        <button onClick={() => setStep("slot")} className="text-blue-600 hover:underline text-sm">
          ← Изменить время
        </button>

        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
          <p className="text-sm text-blue-700">
            📅 {slotLabel} МСК · {duration.label} · {duration.price.toLocaleString("ru")} ₽
          </p>
        </div>

        <form onSubmit={handleBook} className="space-y-4">
          <Field label="Ваше имя *" error={errors.name}>
            <input
              className={inputCls(errors.name)}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Иван Иванов"
            />
          </Field>
          <Field label="Email *" error={errors.email}>
            <input
              type="email"
              className={inputCls(errors.email)}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="ivan@example.com"
            />
          </Field>
          <Field label="Телефон">
            <input
              type="tel"
              className={inputCls()}
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="+7 (999) 000-00-00"
            />
          </Field>
          {errors.submit && <p className="text-red-500 text-sm">{errors.submit}</p>}
          <button
            type="submit"
            disabled={booking}
            className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium text-lg transition-colors"
          >
            {booking ? "Бронирую…" : `Оплатить ${duration.price.toLocaleString("ru")} ₽ →`}
          </button>
          <p className="text-xs text-gray-400 text-center">
            После оплаты на email придёт ссылка на Zoom-встречу
          </p>
        </form>
      </div>
    );
  }

  return null;
}

function groupSlotsByDay(slots) {
  return slots.reduce((acc, slot) => {
    const dt = parseISO(slot.start_time);
    const day = format(dt, "d MMMM, EEEE", { locale: ru });
    if (!acc[day]) acc[day] = [];
    acc[day].push(slot);
    return acc;
  }, {});
}

function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}

const inputCls = (error) =>
  `w-full border rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition ${
    error ? "border-red-400 bg-red-50" : "border-gray-300"
  }`;
