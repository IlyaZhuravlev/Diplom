import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function StudentSelectPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const classId = localStorage.getItem('classId');
    if (!classId) {
      navigate('/');
      return;
    }

    const fetchStudents = async () => {
      try {
        const res = await api.get(`/students/?class_id=${classId}`);
        const data = res.data.results || res.data;
        data.sort((a, b) => a.last_name.localeCompare(b.last_name));
        setStudents(data);
      } catch (err) {
        console.error("Student fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStudents();
  }, [navigate]);

  const handleSelect = (studentId) => {
    localStorage.setItem('studentId', studentId);
    navigate('/gallery');
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center pt-24">
        <div className="w-12 h-12 border-4 border-[#8B5E3C] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center pt-6 w-full max-w-6xl mx-auto">
      <div className="w-full flex justify-center md:justify-end mb-6 pr-0 md:pr-4">
        <button
          onClick={() => navigate('/schedule')}
          className="bg-[#8B5E3C] hover:bg-[#734c30] text-white font-bold font-sans text-xs tracking-widest uppercase transition-all duration-300 px-6 py-3 rounded-xl shadow-[0_4px_14px_rgba(139,94,60,0.3)] min-h-[44px] hover:-translate-y-1 active:translate-y-0"
        >
          Расписание съемок
        </button>
      </div>
      
      <div className="text-center mb-14">
        <h2 className="text-4xl md:text-5xl font-bold font-serif text-[#2d2d2d] mb-4">Выберите выпускника</h2>
        <p className="text-[#8c8c8c] font-medium text-lg max-w-xl mx-auto leading-relaxed px-4 md:px-0">
          Укажите ваше имя, чтобы система сформировала вашу персонализированную галерею фотоснимков
        </p>
      </div>
        
      {students.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6 gap-y-10 w-full px-4 md:px-0 mt-6">
          <div className="relative group cursor-pointer" onClick={() => handleSelect('null')}>
            <div className="w-1/2 h-8 bg-[#8B5E3C] border border-b-0 border-[#8B5E3C] rounded-t-2xl transition-all duration-300 absolute -top-7 left-2 z-0 group-hover:bg-[#734c30]"></div>
            <div className="px-8 py-8 rounded-[2rem] rounded-tl-none bg-white border-2 border-[#8B5E3C] group-hover:shadow-[0_0_30px_rgba(139,94,60,0.2)] transition-all duration-300 text-[#2d2d2d] group-hover:-translate-y-2 flex flex-col justify-center items-center h-44 relative z-10 overflow-hidden shadow-sm">
                <div className="absolute inset-0 bg-[#8B5E3C]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <span className="font-bold text-2xl font-serif text-[#2d2d2d] mb-2 tracking-wide relative z-10 transition-colors group-hover:text-[#8B5E3C]">
                  ОБЩИЕ
                </span>
                <span className="text-base font-bold text-[#8B5E3C] transition-colors relative z-10 tracking-widest uppercase">
                  ФОТО КЛАССА
                </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6 gap-y-10 w-full px-4 md:px-0 mt-6">
          
          {/* COMMON FOLDER */}
          <div className="relative group cursor-pointer" onClick={() => handleSelect('null')}>
            <div className="w-1/2 h-8 bg-[#8B5E3C] border border-b-0 border-[#8B5E3C] rounded-t-2xl transition-all duration-300 absolute -top-7 left-2 z-0 group-hover:bg-[#734c30]"></div>
            <div className="px-8 py-8 rounded-[2rem] rounded-tl-none bg-white border-2 border-[#8B5E3C] group-hover:shadow-[0_0_30px_rgba(139,94,60,0.2)] transition-all duration-300 text-[#2d2d2d] group-hover:-translate-y-2 flex flex-col justify-center items-center h-44 relative z-10 overflow-hidden shadow-md">
                <div className="absolute inset-0 bg-[#8B5E3C]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <span className="font-bold text-2xl font-serif text-[#2d2d2d] mb-2 tracking-wide relative z-10 transition-colors group-hover:text-[#8B5E3C]">
                  ОБЩИЕ
                </span>
                <span className="text-base font-bold text-[#8B5E3C] transition-colors relative z-10 tracking-widest uppercase">
                  ФОТО КЛАССА
                </span>
            </div>
          </div>

          {/* STUDENT FOLDERS */}
          {students.map((student) => (
            <div key={student.id} className="relative group cursor-pointer" onClick={() => handleSelect(student.id)}>
              <div className="w-1/2 h-8 bg-white border border-b-0 border-[#eae0d5] group-hover:border-[#D4AF37] rounded-t-2xl transition-all duration-300 absolute -top-7 left-2 z-0 group-hover:bg-[#FDFBF7]"></div>
              <div className="px-8 py-8 rounded-[2rem] rounded-tl-none bg-white border border-[#eae0d5] group-hover:border-[#D4AF37] group-hover:shadow-[0_0_30px_rgba(139,94,60,0.15)] transition-all duration-300 text-[#2d2d2d] group-hover:-translate-y-2 text-center flex flex-col justify-center items-center h-44 relative z-10 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#FDFBF7] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  <span className="font-bold text-2xl font-serif text-[#2d2d2d] mb-2 tracking-wide relative z-10 transition-colors group-hover:text-[#8B5E3C]">
                    {student.last_name}
                  </span>
                  <span className="text-base font-medium text-[#8c8c8c] group-hover:text-[#734c30] transition-colors relative z-10 tracking-widest">
                    {student.first_name}
                  </span>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <button 
        onClick={() => {
          localStorage.removeItem('classId');
          localStorage.removeItem('studentId');
          navigate('/');
        }}
        className="mt-20 text-[#8c8c8c] hover:text-[#2d2d2d] font-bold text-xs uppercase tracking-[0.2em] transition-colors border-b-2 border-transparent hover:border-[#2d2d2d] pb-1"
      >
        Вернуться ко входу
      </button>
    </div>
  );
}
