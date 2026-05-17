import { useState } from "react";
import { createApplication, answerQuestion } from "../../services/api";

const CATEGORY_LABELS = {
  consumer_rights: "⚖️ Права потребителя",
  labor_dispute: "👷 Трудовой спор",
  tax: "💰 Налоговый вопрос",
  family_law: "👨‍👩‍👧 Семейное право",
  property: "🏠 Имущество / недвижимость",
  criminal: "🔒 Уголовное дело",
  administrative: "📜 Административное",
  business: "💼 Бизнес / договоры",
  housing: "🏢 ЖКХ / жилищные",
  other: "❓ Другое",
};

const TOTAL_QUESTIONS = 5;

// Поток: form → loading → ai_response → questioning → completed
export default function ApplicationForm({ onComplete }) {
  const [step, setStep] = useState("form");
  const [form, setForm] = useState({ name: "", email: "", phone: "", problem: "" });
  const [errors, setErrors] = useState({});
  const [appData, setAppData] = useState(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = "Укажите имя";
    if (!form.email.includes("@")) e.email = "Некорректный email";
    if (form.problem.trim().length < 20) e.problem = "Опишите ситуацию подробнее (минимум 20 символов)";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setStep("loading");

    try {
      const { data } = await createApplication({
        contact_name: form.name,
        contact_email: form.email,
        contact_phone: form.phone || undefined,
        problem_description: form.problem,
      });
      setAppData(data);
      setStep("ai_response");
    } catch {
      setStep("form");
      setErrors({ submit: "Ошибка сервера. Попробуйте позже." });
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = async (e) => {
    e.preventDefault();
    if (!answer.trim()) return;

    setLoading(true);
    try {
      const { data } = await answerQuestion(appData.id, {
        question_id: appData.qualification_step + 1,
        answer: answer.trim(),
      });
      setAppData(data);
      setAnswer("");
      if (data.completed) {
        setStep("completed");
        onComplete?.(data);
      } else {
        setStep("questioning");
      }
    } catch {
      setErrors({ submit: "Ошибка. Попробуйте снова." });
    } finally {
      setLoading(false);
    }
  };

  if (step === "loading") {
    return (
      <div className="text-center py-16">
        <div className="inline-block w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-gray-600 text-lg">AI анализирует вашу ситуацию…</p>
        <p className="text-gray-400 text-sm mt-1">Обычно занимает 5–10 секунд</p>
      </div>
    );
  }

  if (step === "ai_response") {
    return (
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <p className="text-sm font-medium text-blue-700 mb-1">
            Категория: {CATEGORY_LABELS[appData?.legal_category] || "Определяется"}
          </p>
          <p className="text-gray-800">{appData?.ai_preliminary_answer}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold text-gray-900 mb-2">
            Вопрос 1 из {TOTAL_QUESTIONS}
          </h3>
          <p className="text-gray-700 mb-1">{appData?.current_question?.text}</p>
          {appData?.current_question?.hint && (
            <p className="text-sm text-gray-400">💡 {appData.current_question.hint}</p>
          )}
        </div>
        <form onSubmit={(e) => { setStep("questioning"); handleAnswer(e); }}>
          <QuestionInput value={answer} onChange={setAnswer} loading={loading} />
        </form>
      </div>
    );
  }

  if (step === "questioning") {
    const currentQ = appData?.current_question;
    const stepNum = (appData?.qualification_step || 0) + 1;
    const progress = ((appData?.qualification_step || 0) / TOTAL_QUESTIONS) * 100;

    return (
      <div className="space-y-5">
        {/* Прогресс-бар */}
        <div>
          <div className="flex justify-between text-sm text-gray-500 mb-1">
            <span>Уточняющие вопросы</span>
            <span>{appData?.qualification_step} / {TOTAL_QUESTIONS}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold text-gray-900 mb-2">Вопрос {stepNum}</h3>
          <p className="text-gray-700 mb-1">{currentQ?.text}</p>
          {currentQ?.hint && (
            <p className="text-sm text-gray-400">💡 {currentQ.hint}</p>
          )}
        </div>

        <form onSubmit={handleAnswer}>
          <QuestionInput value={answer} onChange={setAnswer} loading={loading} />
        </form>

        {errors.submit && <p className="text-red-500 text-sm">{errors.submit}</p>}
      </div>
    );
  }

  if (step === "completed") {
    return (
      <div className="space-y-5">
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-800 text-lg mb-2">✅ Анализ завершён</h3>
          <p className="text-gray-700 mb-3">{appData?.ai_summary}</p>
          <p className="text-gray-600 text-sm">{appData?.ai_preliminary_answer}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a
            href="/consultation"
            className="flex items-center justify-center gap-2 bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            🗓 Записаться на консультацию
          </a>
          <a
            href="/templates"
            className="flex items-center justify-center gap-2 bg-white border-2 border-blue-600 text-blue-600 py-3 px-4 rounded-lg hover:bg-blue-50 transition-colors font-medium"
          >
            📄 Подобрать шаблон
          </a>
        </div>
      </div>
    );
  }

  // Форма заявки
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
      </div>
      <Field label="Телефон">
        <input
          type="tel"
          className={inputCls()}
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
          placeholder="+7 (999) 000-00-00"
        />
      </Field>
      <Field label="Опишите вашу ситуацию *" error={errors.problem}>
        <textarea
          className={`${inputCls(errors.problem)} min-h-[120px] resize-none`}
          value={form.problem}
          onChange={(e) => setForm({ ...form, problem: e.target.value })}
          placeholder="Например: купил телефон в магазине, он сломался через 2 недели. Продавец отказывает в ремонте по гарантии..."
        />
        <p className="text-xs text-gray-400 mt-1">{form.problem.length} символов (мин. 20)</p>
      </Field>
      {errors.submit && <p className="text-red-500 text-sm">{errors.submit}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium text-lg"
      >
        {loading ? "Отправляю…" : "Получить бесплатную оценку →"}
      </button>
      <p className="text-xs text-gray-400 text-center">
        AI проанализирует ситуацию за 10 секунд. Данные защищены.
      </p>
    </form>
  );
}

function QuestionInput({ value, onChange, loading }) {
  return (
    <div className="space-y-3">
      <textarea
        className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none min-h-[80px]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ваш ответ..."
        autoFocus
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
      >
        {loading ? "Сохраняю…" : "Ответить →"}
      </button>
    </div>
  );
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
  `w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition ${
    error ? "border-red-400 bg-red-50" : "border-gray-300"
  }`;
