import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api';

const API_BASE = 'http://127.0.0.1:8000';

const ZONE_COLORS = {
  hero:    { fill: 'rgba(239, 68, 68, 0.25)',   stroke: '#ef4444', label: 'Портрет' },
  teacher: { fill: 'rgba(59, 130, 246, 0.25)',   stroke: '#3b82f6', label: 'Учитель' },
  student: { fill: 'rgba(34, 197, 94, 0.25)',    stroke: '#22c55e', label: 'Ученик' },
  group:   { fill: 'rgba(168, 85, 247, 0.25)',   stroke: '#a855f7', label: 'Групповое' },
};

const ZONE_TYPE_OPTIONS = [
  { value: 'hero', label: 'Портрет героя (обложка)' },
  { value: 'teacher', label: 'Учитель' },
  { value: 'student', label: 'Ученик (виньетка)' },
  { value: 'group', label: 'Групповое фото' },
];

const HANDLE_SIZE = 8;
const MIN_ZONE_SIZE = 20;

export default function AlbumEditorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const templateId = searchParams.get('template_id');
  const orderId = searchParams.get('order_id');

  // Data state
  const [template, setTemplate] = useState(null);
  const [spreads, setSpreads] = useState([]);
  const [activeSpreadIdx, setActiveSpreadIdx] = useState(0);
  const [zones, setZones] = useState([]);
  const [selectedZoneIdx, setSelectedZoneIdx] = useState(-1);

  // Order mode state
  const [order, setOrder] = useState(null);
  const [groupPhotos, setGroupPhotos] = useState([]);

  // Upload state
  const [uploadSpreadType, setUploadSpreadType] = useState('cover');
  const [uploading, setUploading] = useState(false);

  // Canvas state
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const bgImageRef = useRef(null);
  const [canvasSize, setCanvasSize] = useState({ w: 1200, h: 850 });
  const [scale, setScale] = useState(1);
  const [bgLoaded, setBgLoaded] = useState(false);

  // Drag/resize state
  const [dragState, setDragState] = useState(null);
  // dragState: { type: 'move'|'resize', zoneIdx, handle?, startMouse, startZone }

  // Messages
  const [message, setMessage] = useState({ text: '', type: '' });
  const [saving, setSaving] = useState(false);
  const [detecting, setDetecting] = useState(false);

  // ── Load template ──
  useEffect(() => {
    if (!templateId) return;
    const load = async () => {
      try {
        const res = await api.get(`/album-templates/${templateId}/`);
        setTemplate(res.data);
        const spreadList = res.data.spreads || [];
        setSpreads(spreadList);
        if (spreadList.length > 0) {
          setActiveSpreadIdx(0);
          setZones(spreadList[0].zones || []);
        }
      } catch (e) {
        console.error('Ошибка загрузки шаблона:', e);
        setMessage({ text: 'Ошибка загрузки шаблона', type: 'error' });
      }
    };
    load();
  }, [templateId]);

  // ── Load order data (if in order mode) ──
  useEffect(() => {
    if (!orderId) return;
    const loadOrderData = async () => {
      try {
        const orderRes = await api.get(`/album-orders/${orderId}/`);
        setOrder(orderRes.data);
        const classId = typeof orderRes.data.school_class === 'object' 
                          ? orderRes.data.school_class.id 
                          : orderRes.data.school_class;
        if (classId) {
          const photosRes = await api.get(`/photos/?class_id=${classId}&photo_type=group`);
          setGroupPhotos(photosRes.data.results || photosRes.data);
        }
      } catch (e) {
        console.error('Ошибка загрузки данных заказа:', e);
      }
    };
    loadOrderData();
  }, [orderId]);

  // ── Switch active spread ──
  useEffect(() => {
    if (spreads.length > 0 && activeSpreadIdx < spreads.length) {
      const spread = spreads[activeSpreadIdx];
      setZones(spread.zones || []);
      setSelectedZoneIdx(-1);
      setBgLoaded(false);

      // Load background image
      if (spread.background_url) {
        const img = new window.Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
          bgImageRef.current = img;
          // Calculate scale to fit container (subtract padding 32px)
          const rawWidth = containerRef.current?.clientWidth || 950;
          const containerWidth = Math.min(rawWidth - 32, 950); // max 950px canvas
          const sc = containerWidth / img.width;
          setScale(sc);
          setCanvasSize({
            w: Math.round(img.width * sc),
            h: Math.round(img.height * sc),
          });
          setBgLoaded(true);
        };
        img.src = spread.background_url;
      }
    }
  }, [activeSpreadIdx, spreads]);

  // ── Canvas rendering ──
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background
    if (bgImageRef.current && bgLoaded) {
      ctx.drawImage(bgImageRef.current, 0, 0, canvas.width, canvas.height);
    } else {
      ctx.fillStyle = '#f5f5f5';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#aaa';
      ctx.font = '16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('Загрузите фоновое изображение', canvas.width / 2, canvas.height / 2);
    }

    // Draw zones
    zones.forEach((zone, idx) => {
      const colors = ZONE_COLORS[zone.zone_type] || ZONE_COLORS.group;
      const sx = zone.x * scale;
      const sy = zone.y * scale;
      const sw = zone.w * scale;
      const sh = zone.h * scale;

      // Fill
      ctx.fillStyle = colors.fill;
      ctx.fillRect(sx, sy, sw, sh);

      // Border
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = idx === selectedZoneIdx ? 3 : 1.5;
      if (idx === selectedZoneIdx) {
        ctx.setLineDash([6, 3]);
      } else {
        ctx.setLineDash([]);
      }
      ctx.strokeRect(sx, sy, sw, sh);
      ctx.setLineDash([]);

      // Label
      ctx.fillStyle = colors.stroke;
      ctx.font = 'bold 12px Arial';
      ctx.textAlign = 'left';
      const labelText = `${colors.label} #${zone.sort_order}`;
      ctx.fillText(labelText, sx + 4, sy + 14);

      // Resize handles (only for selected zone)
      if (idx === selectedZoneIdx) {
        const handles = getHandles(sx, sy, sw, sh);
        ctx.fillStyle = '#fff';
        ctx.strokeStyle = colors.stroke;
        ctx.lineWidth = 2;
        handles.forEach(h => {
          ctx.fillRect(h.x - HANDLE_SIZE / 2, h.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
          ctx.strokeRect(h.x - HANDLE_SIZE / 2, h.y - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE);
        });
      }
    });
  }, [zones, scale, selectedZoneIdx, bgLoaded]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  // ── Handle positions for resize ──
  function getHandles(sx, sy, sw, sh) {
    return [
      { x: sx,          y: sy,          cursor: 'nw-resize', pos: 'tl' },
      { x: sx + sw / 2, y: sy,          cursor: 'n-resize',  pos: 'tc' },
      { x: sx + sw,     y: sy,          cursor: 'ne-resize', pos: 'tr' },
      { x: sx + sw,     y: sy + sh / 2, cursor: 'e-resize',  pos: 'mr' },
      { x: sx + sw,     y: sy + sh,     cursor: 'se-resize', pos: 'br' },
      { x: sx + sw / 2, y: sy + sh,     cursor: 's-resize',  pos: 'bc' },
      { x: sx,          y: sy + sh,     cursor: 'sw-resize', pos: 'bl' },
      { x: sx,          y: sy + sh / 2, cursor: 'w-resize',  pos: 'ml' },
    ];
  }

  // ── Mouse events ──
  const getMousePos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const handleMouseDown = (e) => {
    const pos = getMousePos(e);

    // Check resize handles first (only on selected zone)
    if (selectedZoneIdx >= 0) {
      const zone = zones[selectedZoneIdx];
      const sx = zone.x * scale;
      const sy = zone.y * scale;
      const sw = zone.w * scale;
      const sh = zone.h * scale;
      const handles = getHandles(sx, sy, sw, sh);

      for (const h of handles) {
        if (Math.abs(pos.x - h.x) < HANDLE_SIZE && Math.abs(pos.y - h.y) < HANDLE_SIZE) {
          setDragState({
            type: 'resize',
            zoneIdx: selectedZoneIdx,
            handle: h.pos,
            startMouse: pos,
            startZone: { ...zone },
          });
          return;
        }
      }
    }

    // Check zone click (reverse order for top-most first)
    for (let i = zones.length - 1; i >= 0; i--) {
      const zone = zones[i];
      const sx = zone.x * scale;
      const sy = zone.y * scale;
      const sw = zone.w * scale;
      const sh = zone.h * scale;

      if (pos.x >= sx && pos.x <= sx + sw && pos.y >= sy && pos.y <= sy + sh) {
        setSelectedZoneIdx(i);
        setDragState({
          type: 'move',
          zoneIdx: i,
          handle: null,
          startMouse: pos,
          startZone: { ...zone },
        });
        return;
      }
    }

    // Clicked on empty space — deselect
    setSelectedZoneIdx(-1);
  };

  const handleMouseMove = (e) => {
    if (!dragState) return;
    const pos = getMousePos(e);
    const dx = (pos.x - dragState.startMouse.x) / scale;
    const dy = (pos.y - dragState.startMouse.y) / scale;
    const sz = dragState.startZone;

    const newZones = [...zones];
    const zone = { ...newZones[dragState.zoneIdx] };

    if (dragState.type === 'move') {
      zone.x = Math.max(0, Math.round(sz.x + dx));
      zone.y = Math.max(0, Math.round(sz.y + dy));
    } else if (dragState.type === 'resize') {
      const h = dragState.handle;
      // Resize from handle
      if (h.includes('l')) {
        const newX = Math.max(0, Math.round(sz.x + dx));
        zone.w = Math.max(MIN_ZONE_SIZE, sz.w - (newX - sz.x));
        zone.x = newX;
      }
      if (h.includes('r')) {
        zone.w = Math.max(MIN_ZONE_SIZE, Math.round(sz.w + dx));
      }
      if (h.includes('t')) {
        const newY = Math.max(0, Math.round(sz.y + dy));
        zone.h = Math.max(MIN_ZONE_SIZE, sz.h - (newY - sz.y));
        zone.y = newY;
      }
      if (h.includes('b')) {
        zone.h = Math.max(MIN_ZONE_SIZE, Math.round(sz.h + dy));
      }
    }

    newZones[dragState.zoneIdx] = zone;
    setZones(newZones);
  };

  const handleMouseUp = () => {
    setDragState(null);
  };

  // ── Double-click: create new zone ──
  const handleDoubleClick = (e) => {
    const pos = getMousePos(e);
    const origX = Math.round(pos.x / scale);
    const origY = Math.round(pos.y / scale);

    // Check if double-clicked on existing zone
    for (let i = zones.length - 1; i >= 0; i--) {
      const z = zones[i];
      if (origX >= z.x && origX <= z.x + z.w && origY >= z.y && origY <= z.y + z.h) {
        return; // Don't create new on top of existing
      }
    }

    const spread = spreads[activeSpreadIdx];
    const defaultType = spread?.spread_type === 'cover' ? 'hero' :
                        spread?.spread_type === 'vignette' ? 'student' : 'group';

    const newZone = {
      id: null,
      spread: spread?.id,
      zone_type: defaultType,
      sort_order: zones.length,
      x: origX - 150,
      y: origY - 100,
      w: 300,
      h: 400,
    };
    const newZones = [...zones, newZone];
    setZones(newZones);
    setSelectedZoneIdx(newZones.length - 1);
  };

  // ── Delete zone ──
  const handleDeleteZone = () => {
    if (selectedZoneIdx < 0) return;
    const newZones = zones.filter((_, i) => i !== selectedZoneIdx);
    setZones(newZones);
    setSelectedZoneIdx(-1);
  };

  // ── Key events ──
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        // Don't delete if user is typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        handleDeleteZone();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedZoneIdx, zones]);

  // ── Zone property updates ──
  const updateZoneProperty = (key, value) => {
    if (selectedZoneIdx < 0) return;
    const newZones = [...zones];
    newZones[selectedZoneIdx] = { ...newZones[selectedZoneIdx], [key]: value };
    setZones(newZones);
  };

  // ── Assign group photo to zone ──
  const handleAssignGroupPhoto = async (photoId) => {
    if (!selectedZone || !selectedZone.id || !order) return;
    
    const newAssignments = {
      ...(order.zone_assignments || {}),
      [selectedZone.id]: photoId
    };
    
    try {
      const res = await api.patch(`/album-orders/${order.id}/`, {
        zone_assignments: newAssignments
      });
      setOrder(res.data);
      setMessage({ text: 'Фотография привязана к зоне', type: 'success' });
    } catch (e) {
      console.error('Ошибка привязки фото:', e);
      setMessage({ text: 'Ошибка привязки фотографии', type: 'error' });
    }
  };

  // ── Save zones to backend ──
  const handleSaveZones = async () => {
    const spread = spreads[activeSpreadIdx];
    if (!spread) return;
    setSaving(true);
    try {
      const res = await api.post('/zones/bulk_update/', {
        spread_id: spread.id,
        zones: zones.map(z => ({
          id: z.id,
          x: z.x,
          y: z.y,
          w: z.w,
          h: z.h,
          zone_type: z.zone_type,
          sort_order: z.sort_order,
        })),
      });
      // Update zones with server-assigned IDs
      setZones(res.data.zones);
      // Update spreads cache
      const newSpreads = [...spreads];
      newSpreads[activeSpreadIdx] = {
        ...newSpreads[activeSpreadIdx],
        zones: res.data.zones,
      };
      setSpreads(newSpreads);
      setMessage({ text: `Зоны сохранены (${res.data.zones.length} шт.)`, type: 'success' });
    } catch (e) {
      console.error('Ошибка сохранения:', e);
      setMessage({ text: 'Ошибка сохранения зон', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  // ── Redetect zones ──
  const handleRedetect = async () => {
    const spread = spreads[activeSpreadIdx];
    if (!spread) return;
    setDetecting(true);
    try {
      const res = await api.post(`/spreads/${spread.id}/redetect/`);
      const updatedSpread = res.data.spread;
      setZones(updatedSpread.zones || []);
      const newSpreads = [...spreads];
      newSpreads[activeSpreadIdx] = updatedSpread;
      setSpreads(newSpreads);
      setSelectedZoneIdx(-1);
      setMessage({
        text: `Автодетект: найдено ${res.data.zones_detected} зон`,
        type: 'success',
      });
    } catch (e) {
      console.error('Ошибка автодетекта:', e);
      setMessage({ text: 'Ошибка автодетекта зон', type: 'error' });
    } finally {
      setDetecting(false);
    }
  };

  // ── Upload new spread background ──
  const handleUploadBackground = async (e) => {
    const file = e.target.files[0];
    if (!file || !templateId) return;
    setUploading(true);

    const nextOrder = spreads.length + 1;
    const formData = new FormData();
    formData.append('template', templateId);
    formData.append('spread_order', nextOrder);
    formData.append('spread_type', uploadSpreadType);
    formData.append('background', file);

    try {
      const res = await api.post('/spreads/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      // Reload template
      const templateRes = await api.get(`/album-templates/${templateId}/`);
      const newSpreads = templateRes.data.spreads || [];
      setSpreads(newSpreads);
      setActiveSpreadIdx(newSpreads.length - 1);
      setMessage({
        text: `Разворот ${nextOrder} загружен! Зоны обнаружены автоматически.`,
        type: 'success',
      });
    } catch (e) {
      console.error('Ошибка загрузки:', e);
      setMessage({ text: 'Ошибка загрузки фона', type: 'error' });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // ── Replace spread background ──
  const handleReplaceBackground = async (e) => {
    const file = e.target.files[0];
    const spread = spreads[activeSpreadIdx];
    if (!file || !spread) return;
    setUploading(true);

    const formData = new FormData();
    formData.append('background', file);

    try {
      await api.patch(`/spreads/${spread.id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      // Reload template
      const templateRes = await api.get(`/album-templates/${templateId}/`);
      const newSpreads = templateRes.data.spreads || [];
      setSpreads(newSpreads);
      setMessage({ text: 'Фон заменён, зоны обновлены', type: 'success' });
    } catch (e) {
      console.error('Ошибка замены фона:', e);
      setMessage({ text: 'Ошибка замены фона', type: 'error' });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // ── Delete spread ──
  const handleDeleteSpread = async () => {
    const spread = spreads[activeSpreadIdx];
    if (!spread) return;
    if (!window.confirm(`Удалить разворот ${spread.spread_order}?`)) return;
    try {
      await api.delete(`/spreads/${spread.id}/`);
      const templateRes = await api.get(`/album-templates/${templateId}/`);
      const newSpreads = templateRes.data.spreads || [];
      setSpreads(newSpreads);
      setActiveSpreadIdx(Math.max(0, activeSpreadIdx - 1));
      setMessage({ text: 'Разворот удалён', type: 'success' });
    } catch (e) {
      console.error('Ошибка удаления:', e);
      setMessage({ text: 'Ошибка удаления разворота', type: 'error' });
    }
  };

  const selectedZone = selectedZoneIdx >= 0 ? zones[selectedZoneIdx] : null;
  const activeSpread = spreads[activeSpreadIdx] || null;

  // ─── RENDER ───

  if (!templateId) {
    return (
      <div className="max-w-6xl mx-auto text-center py-20">
        <h2 className="font-serif text-3xl font-bold text-[#2d2d2d] mb-4">Редактор альбома</h2>
        <p className="text-[#8c8c8c]">Укажите template_id в URL: /album-editor?template_id=1</p>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto relative pt-4">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="flex justify-between items-center mb-2 px-4">
          <button 
            onClick={() => navigate('/photographer')}
            className="flex items-center gap-2 text-[#8B5E3C] hover:text-[#734c30] text-sm font-bold bg-[#FDFBF7] px-4 py-2 rounded-xl border border-[#eae0d5] hover:bg-[#f5f0ea] transition-all"
          >
            ← Назад к панели фотографа
          </button>
          {order && (
            <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-xs font-bold border border-blue-200">
              Сборка заказа #{order.id}
            </span>
          )}
        </div>
        <h2 className="font-serif text-3xl md:text-4xl font-bold text-[#2d2d2d] mb-2 mt-4">
          Редактор альбома
        </h2>
        <p className="text-[#8c8c8c] text-sm tracking-wide">
          {template ? template.name : 'Загрузка...'} · {order ? 'Привязка фотографий' : 'Визуальная разметка зон'}
        </p>
      </div>

      {/* Messages */}
      {message.text && (
        <div
          className={`mb-4 p-3 rounded-xl text-center text-sm font-medium border transition-all ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-red-50 text-red-700 border-red-200'
          }`}
        >
          {message.text}
          <button onClick={() => setMessage({ text: '', type: '' })} className="ml-3 opacity-50 hover:opacity-100">✕</button>
        </div>
      )}

      {/* ── Layout: Sidebar + Canvas + Properties ── */}
      <div className="flex gap-4">

        {/* LEFT: Spread navigation */}
        <div className="w-48 flex-shrink-0">
          <div className="bg-white rounded-2xl shadow-lg border border-[#eae0d5] p-4">
            <h3 className="text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-3">Развороты</h3>

            {spreads.map((sp, idx) => {
              const typeLabels = { cover: 'Обложка', vignette: 'Виньетка', group: 'Групповые' };
              const isActive = idx === activeSpreadIdx;
              return (
                <button
                  key={sp.id}
                  onClick={() => setActiveSpreadIdx(idx)}
                  className={`w-full text-left p-2 mb-2 rounded-lg text-xs transition-all ${
                    isActive
                      ? 'bg-[#8B5E3C] text-white shadow-md'
                      : 'bg-[#FDFBF7] text-[#2d2d2d] hover:bg-[#f0ebe4] border border-[#eae0d5]'
                  }`}
                >
                  <div className="font-bold">Разворот {sp.spread_order}</div>
                  <div className={`text-[10px] ${isActive ? 'text-white/70' : 'text-[#8c8c8c]'}`}>
                    {typeLabels[sp.spread_type] || sp.spread_type} · {sp.zone_count || sp.zones?.length || 0} зон
                  </div>
                </button>
              );
            })}

            {/* Add spread */}
            <div className="mt-4 pt-4 border-t border-[#eae0d5]">
              <label className="block text-[10px] uppercase tracking-widest font-bold text-[#8c8c8c] mb-1">Тип</label>
              <select
                value={uploadSpreadType}
                onChange={e => setUploadSpreadType(e.target.value)}
                className="w-full text-xs px-2 py-1.5 rounded-lg border border-[#eae0d5] bg-[#FDFBF7] mb-2"
              >
                <option value="cover">Обложка</option>
                <option value="vignette">Виньетка</option>
                <option value="group">Групповые</option>
              </select>
              <label className="block w-full text-center bg-[#8B5E3C] hover:bg-[#734c30] text-white py-2 px-3 rounded-lg font-bold text-xs cursor-pointer transition-all">
                {uploading ? '⏳ Загрузка...' : '+ Добавить'}
                <input type="file" accept="image/*" className="hidden" onChange={handleUploadBackground} disabled={uploading} />
              </label>
            </div>
          </div>
        </div>

        {/* CENTER: Canvas */}
        <div className="flex-1 min-w-0" ref={containerRef}>
          <div className="bg-white rounded-2xl shadow-lg border border-[#eae0d5] p-4">
            {/* Canvas toolbar */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRedetect}
                  disabled={!activeSpread || detecting}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-xs font-medium hover:bg-blue-100 transition-all disabled:opacity-40"
                >
                  {detecting ? '⏳ Детект...' : '🔍 Автодетект зон'}
                </button>
                <button
                  onClick={handleSaveZones}
                  disabled={!activeSpread || saving}
                  className="px-3 py-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-medium hover:bg-emerald-100 transition-all disabled:opacity-40"
                >
                  {saving ? '⏳ Сохранение...' : '💾 Сохранить зоны'}
                </button>
                <button
                  onClick={handleDeleteZone}
                  disabled={selectedZoneIdx < 0}
                  className="px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs font-medium hover:bg-red-100 transition-all disabled:opacity-40"
                >
                  🗑 Удалить зону
                </button>
              </div>
              <div className="flex items-center gap-2">
                {activeSpread && (
                  <>
                    <label className="px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg text-xs font-medium hover:bg-amber-100 cursor-pointer transition-all">
                      📁 Заменить фон
                      <input type="file" accept="image/*" className="hidden" onChange={handleReplaceBackground} />
                    </label>
                    <button
                      onClick={handleDeleteSpread}
                      className="px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs font-medium hover:bg-red-100 transition-all"
                    >
                      ✕
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Info bar */}
            {activeSpread && (
              <div className="flex items-center gap-4 mb-3 text-[10px] uppercase tracking-widest text-[#8c8c8c] font-bold">
                <span>Оригинал: {activeSpread.bg_width}×{activeSpread.bg_height} px</span>
                <span>Масштаб: {(scale * 100).toFixed(0)}%</span>
                <span>Зон: {zones.length}</span>
              </div>
            )}

            {/* Canvas */}
            <div className="border border-[#eae0d5] rounded-lg overflow-hidden bg-[#e8e8e8]">
              <canvas
                ref={canvasRef}
                width={canvasSize.w}
                height={canvasSize.h}
                style={{ width: canvasSize.w, height: canvasSize.h, cursor: dragState ? 'grabbing' : 'crosshair' }}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onDoubleClick={handleDoubleClick}
              />
            </div>

            {/* Tip */}
            <p className="mt-2 text-[10px] text-[#aaa] text-center">
              Клик — выделить зону · Перетаскивание — двигать · Углы — resize · Двойной клик — новая зона · Delete — удалить
            </p>
          </div>
        </div>

        {/* RIGHT: Zone properties */}
        <div className="w-56 flex-shrink-0">
          <div className="bg-white rounded-2xl shadow-lg border border-[#eae0d5] p-4">
            <h3 className="text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-3">Свойства зоны</h3>

            {selectedZone ? (
              <div className="space-y-3">
                {/* Zone type */}
                <div>
                  <label className="block text-[10px] uppercase tracking-widest font-bold text-[#8c8c8c] mb-1">Тип</label>
                  <select
                    value={selectedZone.zone_type}
                    onChange={e => updateZoneProperty('zone_type', e.target.value)}
                    className="w-full text-xs px-2 py-1.5 rounded-lg border border-[#eae0d5] bg-[#FDFBF7]"
                  >
                    {ZONE_TYPE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Sort order */}
                <div>
                  <label className="block text-[10px] uppercase tracking-widest font-bold text-[#8c8c8c] mb-1">Порядок</label>
                  <input
                    type="number"
                    min="0"
                    value={selectedZone.sort_order}
                    onChange={e => updateZoneProperty('sort_order', parseInt(e.target.value) || 0)}
                    className="w-full text-xs px-2 py-1.5 rounded-lg border border-[#eae0d5] bg-[#FDFBF7]"
                  />
                </div>

                {/* Coordinates */}
                <div className="grid grid-cols-2 gap-2">
                  {['x', 'y', 'w', 'h'].map(key => (
                    <div key={key}>
                      <label className="block text-[10px] uppercase tracking-widest font-bold text-[#8c8c8c] mb-0.5">{key}</label>
                      <input
                        type="number"
                        min="0"
                        value={selectedZone[key]}
                        onChange={e => updateZoneProperty(key, parseInt(e.target.value) || 0)}
                        className="w-full text-xs px-2 py-1.5 rounded-lg border border-[#eae0d5] bg-[#FDFBF7]"
                      />
                    </div>
                  ))}
                </div>

                {/* Zone color indicator */}
                <div className="flex items-center gap-2 mt-2">
                  <div
                    className="w-4 h-4 rounded-full border-2"
                    style={{
                      backgroundColor: (ZONE_COLORS[selectedZone.zone_type] || ZONE_COLORS.group).fill,
                      borderColor: (ZONE_COLORS[selectedZone.zone_type] || ZONE_COLORS.group).stroke,
                    }}
                  />
                  <span className="text-xs text-[#8c8c8c]">
                    {(ZONE_COLORS[selectedZone.zone_type] || ZONE_COLORS.group).label}
                  </span>
                </div>

                {/* ID info */}
                {selectedZone.id && (
                  <div className="text-[10px] text-[#ccc] mt-1">
                    ID: {selectedZone.id}
                  </div>
                )}
                
                {/* Group Photo Selection (Order Mode) */}
                {order && selectedZone.zone_type === 'group' && (
                  <div className="mt-4 pt-4 border-t border-[#eae0d5]">
                    <h4 className="text-[10px] uppercase tracking-widest font-bold text-[#8B5E3C] mb-2">
                      Привязка группового фото
                    </h4>
                    {groupPhotos.length === 0 ? (
                      <p className="text-xs text-[#8c8c8c]">Нет групповых фото в классе</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                        {groupPhotos.map(photo => {
                          const isAssigned = (order.zone_assignments || {})[selectedZone.id] === photo.id;
                          return (
                            <div 
                              key={photo.id}
                              onClick={() => handleAssignGroupPhoto(photo.id)}
                              className={`relative rounded-lg overflow-hidden cursor-pointer border-2 transition-all group ${
                                isAssigned ? 'border-[#8B5E3C]' : 'border-transparent hover:border-[#8B5E3C]/50'
                              }`}
                            >
                              <img 
                                src={photo.image.startsWith('http') ? photo.image : `${API_BASE}${photo.image}`} 
                                className="w-full h-16 object-cover" 
                                alt=""
                              />
                              {isAssigned && (
                                <div className="absolute inset-0 bg-[#8B5E3C]/20 flex items-center justify-center">
                                  <span className="bg-[#8B5E3C] text-white text-[10px] px-1.5 py-0.5 rounded-sm font-bold">
                                    Выбрано
                                  </span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-[#aaa] text-center py-8">
                Выберите зону на холсте
              </p>
            )}
          </div>

          {/* Zone list */}
          <div className="bg-white rounded-2xl shadow-lg border border-[#eae0d5] p-4 mt-4">
            <h3 className="text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-3">
              Все зоны ({zones.length})
            </h3>
            <div className="max-h-64 overflow-y-auto space-y-1">
              {zones.map((z, idx) => {
                const colors = ZONE_COLORS[z.zone_type] || ZONE_COLORS.group;
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedZoneIdx(idx)}
                    className={`w-full text-left px-2 py-1.5 rounded-lg text-xs transition-all flex items-center gap-2 ${
                      idx === selectedZoneIdx
                        ? 'bg-[#8B5E3C]/10 border border-[#8B5E3C]/30'
                        : 'hover:bg-[#f5f0ea]'
                    }`}
                  >
                    <div
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: colors.stroke }}
                    />
                    <span className="truncate">
                      {colors.label} #{z.sort_order}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
