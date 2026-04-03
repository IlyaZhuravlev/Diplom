import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const STATUS_MAP = {
  draft: { label: 'Черновик', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' },
  generating: { label: 'Генерация...', color: 'bg-amber-50 text-amber-700', dot: 'bg-amber-400 animate-pulse' },
  ready: { label: 'Готов', color: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500' },
  error: { label: 'Ошибка', color: 'bg-red-50 text-red-700', dot: 'bg-red-500' },
};

export default function PhotographerPage() {
  const navigate = useNavigate();

  // ── Состояние ──
  const [classes, setClasses] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [orders, setOrders] = useState([]);
  const [currentOrder, setCurrentOrder] = useState(null);
  const [classStatus, setClassStatus] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // ── Загрузка классов и шаблонов ──
  useEffect(() => {
    const load = async () => {
      try {
        const [classRes, templateRes] = await Promise.all([
          api.get('/classes/'),
          api.get('/album-templates/'),
        ]);
        setClasses(classRes.data.results || classRes.data);
        setTemplates(templateRes.data.results || templateRes.data);
      } catch (e) {
        console.error('Ошибка загрузки:', e);
      }
    };
    load();
  }, []);

  // ── При выборе класса — подгружаем заказы ──
  useEffect(() => {
    if (!selectedClassId) {
      setOrders([]);
      setCurrentOrder(null);
      setClassStatus(null);
      return;
    }
    const load = async () => {
      try {
        const ordersRes = await api.get('/album-orders/', { params: { class_id: selectedClassId } });
        const orderList = ordersRes.data.results || ordersRes.data;
        setOrders(orderList);
        if (orderList.length > 0) {
          setCurrentOrder(orderList[0]);
          loadClassStatus(orderList[0].id);
        } else {
          setCurrentOrder(null);
          setClassStatus(null);
        }
      } catch (e) {
        console.error('Ошибка загрузки:', e);
      }
    };
    load();
  }, [selectedClassId]);

  const loadClassStatus = async (orderId) => {
    try {
      const res = await api.get(`/album-orders/${orderId}/class_status/`);
      setClassStatus(res.data);
    } catch (e) {
      console.error('Ошибка загрузки статуса:', e);
    }
  };

  // ── Создание нового заказа ──
  const handleCreateOrder = async () => {
    if (!selectedClassId || !selectedTemplateId) {
      setMessage({ text: 'Выберите класс и шаблон', type: 'error' });
      return;
    }
    try {
      const res = await api.post('/album-orders/', {
        school_class: selectedClassId,
        template: selectedTemplateId,
      });
      const newOrder = res.data;
      setOrders((prev) => [newOrder, ...prev]);
      setCurrentOrder(newOrder);
      loadClassStatus(newOrder.id);
      setMessage({ text: 'Заказ создан!', type: 'success' });
    } catch (e) {
      console.error('Ошибка создания заказа:', e);
      setMessage({ text: 'Ошибка при создании заказа', type: 'error' });
    }
  };

  // ── Генерация ZIP ──
  const handleGenerate = async () => {
    if (!currentOrder) return;
    setIsGenerating(true);
    setMessage({ text: '', type: '' });
    try {
      const res = await api.post(`/album-orders/${currentOrder.id}/generate/`);
      setMessage({ text: res.data.message || 'Альбомы сгенерированы!', type: 'success' });
      // Обновить заказ
      const orderRes = await api.get(`/album-orders/${currentOrder.id}/`);
      setCurrentOrder(orderRes.data);
      loadClassStatus(currentOrder.id);
    } catch (e) {
      const errMsg = e.response?.data?.error || 'Ошибка при генерации';
      setMessage({ text: errMsg, type: 'error' });
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Скачивание ZIP ──
  const handleDownload = () => {
    if (!currentOrder?.zip_file) return;
    const url = currentOrder.zip_file.startsWith('http')
      ? currentOrder.zip_file
      : `http://127.0.0.1:8000${currentOrder.zip_file}`;
    window.location.href = url;
  };

  // ── Открыть редактор альбома ──
  const handleOpenEditor = () => {
    if (!currentOrder?.template) return;
    const tid = typeof currentOrder.template === 'object' ? currentOrder.template.id : currentOrder.template;
    navigate(`/album-editor?template_id=${tid}`);
  };

  const statusInfo = currentOrder ? STATUS_MAP[currentOrder.status] || STATUS_MAP.draft : null;

  return (
    <div className="max-w-6xl mx-auto">
      {/* ── Заголовок ── */}
      <div className="text-center mb-10">
        <h2 className="font-serif text-3xl md:text-4xl font-bold text-[#2d2d2d] mb-2">
          Панель фотографа
        </h2>
        <p className="text-[#8c8c8c] text-sm tracking-wide">
          Управление альбомами · Генерация · Экспорт
        </p>
      </div>

      {/* ── Уведомления ── */}
      {message.text && (
        <div
          className={`mb-6 p-4 rounded-2xl text-center text-sm font-medium border transition-all ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-red-50 text-red-700 border-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* ── Выбор класса и шаблона ── */}
      <div className="bg-white rounded-[2rem] shadow-2xl shadow-[#8B5E3C]/5 border border-[#8B5E3C]/10 p-8 mb-8">
        <h3 className="font-serif text-xl font-bold text-[#2d2d2d] mb-6 flex items-center gap-2">
          <span className="w-8 h-8 bg-[#8B5E3C] text-white rounded-full flex items-center justify-center text-sm font-bold">1</span>
          Выбор класса и шаблона
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-2">Класс</label>
            <select
              value={selectedClassId}
              onChange={(e) => setSelectedClassId(e.target.value)}
              className="w-full px-4 py-3 bg-[#FDFBF7] border border-[#eae0d5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B5E3C]/30 text-[#2d2d2d] font-medium"
            >
              <option value="">— Выберите класс —</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.graduation_year}) — {c.student_count || '?'} уч.
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-2">Шаблон альбома</label>
            <select
              value={selectedTemplateId}
              onChange={(e) => setSelectedTemplateId(e.target.value)}
              className="w-full px-4 py-3 bg-[#FDFBF7] border border-[#eae0d5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B5E3C]/30 text-[#2d2d2d] font-medium"
            >
              <option value="">— Выберите шаблон —</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.spread_count || 0} развор.)
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={handleCreateOrder}
              disabled={!selectedClassId || !selectedTemplateId}
              className="flex-1 bg-[#8B5E3C] hover:bg-[#734c30] text-white py-3 px-4 rounded-xl font-bold text-sm transition-all hover:shadow-lg hover:shadow-[#8B5E3C]/30 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-40 disabled:hover:translate-y-0 disabled:shadow-none"
            >
              + Создать заказ
            </button>
          </div>
        </div>

        {/* Шаблон: кнопка редактора */}
        {selectedTemplateId && (
          <div className="mt-4 pt-4 border-t border-[#eae0d5]">
            <button
              onClick={() => navigate(`/album-editor?template_id=${selectedTemplateId}`)}
              className="bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 py-2.5 px-5 rounded-xl font-bold text-sm transition-all"
            >
              🎨 Открыть редактор шаблона
            </button>
          </div>
        )}

        {/* Список существующих заказов */}
        {orders.length > 0 && (
          <div className="mt-6 pt-6 border-t border-[#eae0d5]">
            <p className="text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-3">Существующие заказы</p>
            <div className="flex flex-wrap gap-2">
              {orders.map((o) => {
                const si = STATUS_MAP[o.status] || STATUS_MAP.draft;
                const isActive = currentOrder?.id === o.id;
                return (
                  <button
                    key={o.id}
                    onClick={() => { setCurrentOrder(o); loadClassStatus(o.id); }}
                    className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${
                      isActive
                        ? 'bg-[#8B5E3C] text-white border-[#8B5E3C] shadow-lg'
                        : 'bg-white text-[#2d2d2d] border-[#eae0d5] hover:border-[#8B5E3C]/40'
                    }`}
                  >
                    #{o.id} · {si.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── Статус учеников ── */}
      {classStatus && (
        <div className="bg-white rounded-[2rem] shadow-2xl shadow-[#8B5E3C]/5 border border-[#8B5E3C]/10 p-8 mb-8">
          <h3 className="font-serif text-xl font-bold text-[#2d2d2d] mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-[#8B5E3C] text-white rounded-full flex items-center justify-center text-sm font-bold">2</span>
            Статус учеников
          </h3>

          {/* Прогресс-бар */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-[#8c8c8c] mb-2">
              <span>Подтверждено: {classStatus.confirmed_count} из {classStatus.total_students}</span>
              <span>{classStatus.total_students > 0 ? Math.round((classStatus.confirmed_count / classStatus.total_students) * 100) : 0}%</span>
            </div>
            <div className="h-3 bg-[#f0ebe4] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#8B5E3C] to-[#D4AF37] rounded-full transition-all duration-700"
                style={{ width: `${classStatus.total_students > 0 ? (classStatus.confirmed_count / classStatus.total_students) * 100 : 0}%` }}
              />
            </div>
          </div>

          {/* Список учеников */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {classStatus.students.map((s) => (
              <div
                key={s.id}
                className={`p-3 rounded-xl border text-center text-sm transition-all ${
                  s.is_confirmed
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : s.has_portrait
                    ? 'bg-amber-50 border-amber-200 text-amber-800'
                    : 'bg-red-50 border-red-200 text-red-700'
                }`}
              >
                <div className="font-bold">{s.last_name}</div>
                <div className="text-xs opacity-75">{s.first_name}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wide font-bold opacity-60">
                  {s.is_confirmed ? '✓ Подтв.' : s.has_portrait ? '⏳ Ожидание' : '✗ Нет фото'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Редактор шаблона + Генерация ── */}
      {currentOrder && (
        <div className="bg-white rounded-[2rem] shadow-2xl shadow-[#8B5E3C]/5 border border-[#8B5E3C]/10 p-8 mb-8">
          <h3 className="font-serif text-xl font-bold text-[#2d2d2d] mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-[#8B5E3C] text-white rounded-full flex items-center justify-center text-sm font-bold">3</span>
            Настройка и генерация
          </h3>

          {/* Статус */}
          {statusInfo && (
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium mb-6 ${statusInfo.color}`}>
              <span className={`w-2.5 h-2.5 rounded-full ${statusInfo.dot}`} />
              {statusInfo.label}
            </div>
          )}

          {/* Кнопка редактора */}
          <div className="mb-6 p-4 bg-[#FDFBF7] rounded-xl border border-[#eae0d5]">
            <p className="text-sm text-[#8c8c8c] mb-3">
              Откройте визуальный редактор для настройки зон на развороте: расставьте, где будут портреты учеников, учителя и групповые фото.
            </p>
            <button
              onClick={handleOpenEditor}
              className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-6 rounded-xl font-bold text-sm transition-all hover:shadow-lg hover:shadow-blue-500/30 hover:-translate-y-0.5 active:translate-y-0"
            >
              🎨 Открыть редактор альбома
            </button>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex-1 bg-gradient-to-r from-[#8B5E3C] to-[#A0724D] hover:from-[#734c30] hover:to-[#8B5E3C] text-white py-4 px-8 rounded-xl font-bold text-lg transition-all hover:shadow-xl hover:shadow-[#8B5E3C]/30 hover:-translate-y-1 active:translate-y-0 disabled:opacity-60 disabled:hover:translate-y-0 disabled:shadow-none"
            >
              {isGenerating ? (
                <span className="flex items-center justify-center gap-3">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Генерация альбомов...
                </span>
              ) : (
                '🎨 Сгенерировать альбомы'
              )}
            </button>

            {currentOrder.zip_file && (
              <button
                onClick={handleDownload}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-4 px-8 rounded-xl font-bold text-lg transition-all hover:shadow-xl hover:shadow-emerald-500/30 hover:-translate-y-1 active:translate-y-0"
              >
                📦 Скачать ZIP
              </button>
            )}
          </div>

          {currentOrder.zip_file && (
            <p className="mt-4 text-sm text-[#8c8c8c] text-center">
              Архив содержит персональный PDF-альбом для каждого ученика класса.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
