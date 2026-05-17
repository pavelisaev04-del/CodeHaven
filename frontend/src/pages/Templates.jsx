import TemplateCatalog from "../components/TemplateCatalog/TemplateCatalog";

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Шаблоны документов</h1>
        <p className="text-gray-500 mt-1">
          Готовые юридические документы от 500 ₽. Скачайте сразу после оплаты.
        </p>
      </div>
      <TemplateCatalog />
    </div>
  );
}
