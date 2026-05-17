import ConsultationBooking from "../components/ConsultationBooking/ConsultationBooking";

export default function ConsultationPage() {
  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Запись на консультацию</h1>
        <p className="text-gray-500 mt-1">
          Выберите время — Zoom-ссылка придёт автоматически после оплаты
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <ConsultationBooking />
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-sm">
        <p className="font-medium text-amber-800 mb-1">💡 Совет</p>
        <p className="text-amber-700">
          Если вы уже заполняли форму заявки — у нас есть анализ вашей ситуации.
          Укажите тот же email при бронировании, и консультант подготовится заранее.
        </p>
      </div>
    </div>
  );
}
