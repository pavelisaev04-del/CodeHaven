import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 30000,
});

// ─── Заявки ──────────────────────────────────────────────────────────────────

export const createApplication = (data) => api.post("/applications/", data);
export const answerQuestion = (id, data) => api.post(`/applications/${id}/answer`, data);
export const getApplication = (id) => api.get(`/applications/${id}`);

// ─── Шаблоны ─────────────────────────────────────────────────────────────────

export const getTemplates = (categorySlug) =>
  api.get("/templates/", { params: categorySlug ? { category_slug: categorySlug } : {} });
export const getTemplate = (id) => api.get(`/templates/${id}`);
export const purchaseTemplate = (id, data) => api.post(`/templates/${id}/purchase`, data);

// ─── Консультации ─────────────────────────────────────────────────────────────

export const getConsultationSlots = (daysAhead = 14) =>
  api.get("/consultations/slots", { params: { days_ahead: daysAhead } });
export const bookConsultation = (data) => api.post("/consultations/", data);
export const getConsultation = (id) => api.get(`/consultations/${id}`);

export default api;
