import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function SchedulePage() {
  const navigate = useNavigate();
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const classId = localStorage.getItem('classId');
    if (!classId) {
      navigate('/');
      return;
    }

    const fetchSchedule = async () => {
      try {
        const res = await api.get('/shoots/');
        const allShoots = res.data.results || res.data;
        const myShoots = allShoots.filter(s => s.school_class === parseInt(classId));
        
        myShoots.sort((a, b) => new Date(a.date) - new Date(b.date));
        setSchedules(myShoots);
      } catch (err) {
        console.error("Schedule fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSchedule();
  }, [navigate]);

  const getStatusVisuals = (statusValue) => {
    switch (statusValue) {
      case 'planned': return { statusText: 'Запланирована', color: 'bg-[#D4AF37] shadow-[#D4AF37]/50', bg: 'bg-[#FDFBF7] border-[#D4AF37]/30', text: 'text-[#8B5E3C]' };
      case 'completed': return { statusText: 'Завершена', color: 'bg-stone-400', bg: 'bg-stone-50 border-stone-200', text: 'text-stone-500' };
      case 'cancelled': return { statusText: 'Отменена', color: 'bg-red-400 shadow-red-400/50', bg: 'bg-red-50 border-red-100', text: 'text-red-700' };
      default: return { statusText: statusValue, color: 'bg-blue-400', bg: 'bg-blue-50 border-blue-200', text: 'text-blue-600' };
    }
  };

  const formatDate = (dateStr) => {
    try {
      return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center pt-32">
        <div className="w-16 h-16 border-4 border-[#8B5E3C] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto pt-6">
      <div className="flex flex-col md:flex-row justify-between items-center mb-12 gap-6 px-2 md:px-0">
        <h2 className="text-4xl md:text-5xl font-serif font-bold text-[#2d2d2d] text-center md:text-left">Расписание съемок</h2>
        
        <button
          onClick={() => navigate('/select-student')}
          className="bg-[#8B5E3C] hover:bg-[#734c30] text-white font-bold font-sans text-xs tracking-widest uppercase transition-all duration-300 px-6 py-3.5 rounded-xl shadow-lg shadow-[#8B5E3C]/30 hover:-translate-y-1 active:translate-y-0"
        >
          Вернуться к выбору
        </button>
      </div>

      <main className="w-full px-2 md:px-0">
        {schedules.length === 0 ? (
          <div className="text-center py-24 bg-white rounded-[3rem] border border-[#eae0d5] shadow-sm">
            <p className="text-2xl text-[#8c8c8c] font-serif italic">У вашего класса пока нет запланированных съемок.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {schedules.map((schedule) => {
              const visuals = getStatusVisuals(schedule.status);
              return (
                <div key={schedule.id} className="bg-white rounded-[2rem] shadow-[0_4px_20px_rgba(139,94,60,0.05)] border border-[#eae0d5] p-8 flex flex-col md:flex-row gap-6 justify-between items-start md:items-center hover:border-[#D4AF37] hover:shadow-[0_10px_30px_rgba(139,94,60,0.12)] transition-all duration-300 group">
                  <div className="space-y-4">
                    <h3 className="text-2xl font-bold font-serif text-[#2d2d2d] group-hover:text-[#8B5E3C] transition-colors">
                      {schedule.description || 'Фотосессия'}
                    </h3>
                    <div className="flex flex-wrap items-center gap-4 text-[#8c8c8c] font-medium font-sans text-sm tracking-wide">
                      <div className="flex items-center gap-2 bg-[#FDFBF7] px-4 py-2.5 rounded-xl border border-[#eae0d5]">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[#8B5E3C]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {formatDate(schedule.date)}
                      </div>
                      <div className="flex items-center gap-2 bg-[#FDFBF7] px-4 py-2.5 rounded-xl border border-[#eae0d5]">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[#8B5E3C]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {schedule.time.slice(0, 5)}
                      </div>
                    </div>
                  </div>
                  
                  <div className={`px-5 py-3 rounded-2xl text-xs uppercase tracking-[0.15em] font-bold flex items-center gap-3 ${visuals.bg} ${visuals.text} border w-full md:w-auto justify-center md:justify-start shadow-sm`}>
                    <span className={`w-2.5 h-2.5 rounded-full shadow-sm ${visuals.color}`}></span>
                    {visuals.statusText}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
