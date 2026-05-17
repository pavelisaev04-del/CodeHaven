import { useState, useEffect } from "react";
import { getTemplates, purchaseTemplate } from "../../services/api";

export default function TemplateCatalog() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [buyForm, setBuyForm] = useState({ email: "", name: "" });
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getTemplates()
      .then((r) => setTemplates(r.data))
      .catch(() => setError("Не удалось загрузить шаблоны"))
      .finally(() => setLoading(false));
  }, []);

  const handleBuy = async (e) => {
    e.preventDefault();
    if (!buyForm.email.includes("@")) return;
    setBuying(true);
    try {
      const { data } = await purchaseTemplate(selected.id, {
        buyer_email: buyForm.email,
        buyer_name: buyForm.name,
        payment_provider: "yookassa",
      });
      window.location.href = data.checkout_url;
    } catch {
      setError("Ошибка создания платежа. Попробуйте позже.");
    } finally {
      setBuying(false);
    }
  };

  if (loading) return <Spinner />;

  if (selected) {
    return (
      <div className="max-w-xl mx-auto space-y-6">
        <button onClick={() => setSelected(null)} className="text-blue-600 hover:underline text-sm">
          ← Назад к каталогу
        </button>

        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-start justify-between mb-3">
            <h2 className="text-xl font-bold text-gray-900">{selected.name}</h2>
            <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded-full">
              {selected.file_format.toUpperCase()}
            </span>
          </div>
          <p className="text-gray-600 mb-4">{selected.description}</p>

          {selected.preview_text && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4 font-mono text-sm text-gray-600 line-clamp-4">
              {selected.preview_text}
            </div>
          )}

          <div className="flex items-center gap-3 mb-6">
            {selected.original_price && (
              <span className="text-gray-400 line-through text-lg">
                {selected.original_price.toLocaleString("ru")} ₽
              </span>
            )}
            <span className="text-2xl font-bold text-gray-900">
              {selected.price.toLocaleString("ru")} ₽
            </span>
            {selected.sales_count > 0 && (
              <span className="text-xs text-gray-400">{selected.sales_count} продаж</span>
            )}
          </div>

          <form onSubmit={handleBuy} className="space-y-3">
            <input
              type="text"
              placeholder="Ваше имя"
              value={buyForm.name}
              onChange={(e) => setBuyForm({ ...buyForm, name: e.target.value })}
              className="w-full border border-gray-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="email"
              required
              placeholder="Email для получения шаблона *"
              value={buyForm.email}
              onChange={(e) => setBuyForm({ ...buyForm, email: e.target.value })}
              className="w-full border border-gray-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={buying}
              className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium transition-colors text-lg"
            >
              {buying ? "Создаю платёж…" : `Купить за ${selected.price.toLocaleString("ru")} ₽`}
            </button>
            <p className="text-xs text-gray-400 text-center">
              Шаблон будет отправлен на email сразу после оплаты
            </p>
          </form>
        </div>

        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-blue-800">
          💡 Нужна помощь с заполнением шаблона?{" "}
          <a href="/consultation" className="underline font-medium">Запишитесь на консультацию</a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((t) => (
          <TemplateCard key={t.id} template={t} onSelect={setSelected} />
        ))}
      </div>
      {templates.length === 0 && !loading && (
        <p className="text-center text-gray-500 py-12">Шаблоны пока не добавлены</p>
      )}
    </div>
  );
}

function TemplateCard({ template, onSelect }) {
  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
      onClick={() => onSelect(template)}
    >
      {template.is_featured && (
        <span className="inline-block bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full mb-2">
          ⭐ Популярное
        </span>
      )}
      <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors mb-2 line-clamp-2">
        {template.name}
      </h3>
      <p className="text-sm text-gray-500 line-clamp-2 mb-4">{template.description}</p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {template.original_price && (
            <span className="text-gray-400 line-through text-sm">
              {template.original_price.toLocaleString("ru")} ₽
            </span>
          )}
          <span className="font-bold text-gray-900 text-lg">
            {template.price.toLocaleString("ru")} ₽
          </span>
        </div>
        <span className="text-xs text-gray-400 uppercase bg-gray-100 px-2 py-0.5 rounded">
          {template.file_format}
        </span>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
