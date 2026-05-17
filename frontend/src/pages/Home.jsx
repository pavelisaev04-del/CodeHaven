import ApplicationForm from "../components/ApplicationForm/ApplicationForm";

export default function HomePage() {
  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Юридическая помощь онлайн
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
          AI-анализ вашей ситуации за 30 секунд. Шаблоны документов от 500 ₽.
          Консультация юриста с автоматической Zoom-ссылкой.
        </p>
        <div className="flex flex-wrap justify-center gap-4 text-sm">
          {["⚖️ Права потребителя", "👷 Трудовые споры", "🏠 Недвижимость",
            "💼 Бизнес", "👨‍👩‍👧 Семейное право", "📜 Административное"].map((tag) => (
            <span key={tag} className="bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      </section>

      {/* Форма заявки */}
      <section className="max-w-xl mx-auto">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Бесплатная первичная оценка
          </h2>
          <p className="text-gray-500 mb-6">
            Опишите ситуацию — AI задаст 5 уточняющих вопросов и даст предварительную оценку
          </p>
          <ApplicationForm />
        </div>
      </section>

      {/* Как это работает */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Как это работает</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              step: "1",
              icon: "📝",
              title: "Опишите ситуацию",
              text: "Заполните форму. AI проанализирует проблему и задаст уточняющие вопросы",
            },
            {
              step: "2",
              icon: "🤖",
              title: "Получите оценку",
              text: "Автоматический анализ с категорией проблемы и предварительной рекомендацией",
            },
            {
              step: "3",
              icon: "🗓",
              title: "Консультация или шаблон",
              text: "Купите готовый шаблон документа или запишитесь к юристу с Zoom-ссылкой",
            },
          ].map((item) => (
            <div key={item.step} className="bg-white rounded-xl border border-gray-200 p-5 text-center">
              <div className="text-3xl mb-3">{item.icon}</div>
              <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-500">{item.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
