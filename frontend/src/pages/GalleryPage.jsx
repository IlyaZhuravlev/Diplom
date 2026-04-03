import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function GalleryPage() {
  const navigate = useNavigate();
  const [photos, setPhotos] = useState([]);
  const [classInfo, setClassInfo] = useState(null);
  const [selectedCards, setSelectedCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    const classId = localStorage.getItem('classId');
    const studentId = localStorage.getItem('studentId');

    if (!classId) {
      navigate('/');
      return;
    }
    
    if (!studentId) {
      navigate('/select-student');
      return;
    }

    const fetchData = async () => {
      try {
        const classRes = await api.get(`/classes/${classId}/`);
        setClassInfo(classRes.data);

        if (studentId === 'teacher') {
          // Показываем фото учителя из данных класса
          const teacherPhotoUrl = classRes.data.teacher_photo;
          if (teacherPhotoUrl) {
            setPhotos([{
              id: 'teacher',
              image: teacherPhotoUrl,
              photo_type: 'portrait',
              student: null,
            }]);
          } else {
            setPhotos([]);
          }
        } else {
          const queryParams = studentId === 'null' 
            ? `?class_id=${classId}&student_id=null` 
            : `?student_id=${studentId}&photo_type=portrait`;
          const photosRes = await api.get(`/photos/${queryParams}`);
          const allPhotos = photosRes.data.results || photosRes.data;
          
          if (studentId === 'null') {
             setPhotos(allPhotos);
          } else {
             // Строго только портреты текущего класса
             const myPhotos = allPhotos.filter(
               p => p.school_class === parseInt(classId) && p.photo_type === 'portrait'
             );
             setPhotos(myPhotos);
          }
        }
      } catch (err) {
        console.error("Fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [navigate]);

  const toggleSelect = (id) => {
    const studentId = localStorage.getItem('studentId');
    if (studentId === 'null' || studentId === 'teacher') return;
    
    if (selectedCards.includes(id)) {
      setSelectedCards([]);
    } else {
      setSelectedCards([id]);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('classId');
    localStorage.removeItem('studentId');
    navigate('/');
  };

  const handleConfirm = async () => {
    const studentId = localStorage.getItem('studentId');
    if (!studentId || selectedCards.length === 0) return;
    setIsConfirming(true);
    try {
      await api.post('/selections/confirm/', {
        student_id: studentId,
        photo_ids: selectedCards
      });
      alert('Ваш выбор успешно сохранен и подтвержден!');
    } catch (err) {
      console.error('Confirm error:', err);
      alert('Произошла ошибка при сохранении выбора. Попробуйте снова.');
    } finally {
      setIsConfirming(false);
    }
  };

  const getFullUrl = (path) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const baseUrl = 'http://127.0.0.1:8000';
    return `${baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center pt-32">
        <div className="w-16 h-16 border-4 border-[#8B5E3C] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-[85rem] mx-auto pt-6">
      <div className="flex flex-col md:flex-row justify-between items-center md:items-end mb-12 gap-8 px-2 md:px-0">
        <div className="text-center md:text-left flex flex-col md:flex-row items-center md:items-start gap-4">
          <button
            onClick={() => { localStorage.removeItem('studentId'); navigate('/select-student'); }}
            className="mt-1 md:mt-2 text-[#8B5E3C] hover:text-[#734c30] bg-[#f4ebe1] hover:bg-[#eae0d5] p-2.5 rounded-full transition-all hidden md:flex hover:-translate-x-1 shadow-sm"
            title="Назад к списку учеников"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <div>
            <div className="flex flex-wrap justify-center items-center gap-3 mb-3">
              <button
                onClick={() => { localStorage.removeItem('studentId'); navigate('/select-student'); }}
                className="text-[#8B5E3C] bg-[#f4ebe1] p-2 rounded-full md:hidden"
                title="Назад к списку"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <h2 className="text-4xl md:text-5xl font-serif font-bold text-[#2d2d2d]">Ваша Галерея</h2>
            </div>
            
            {classInfo && (
              <p className="text-[#8c8c8c] font-medium text-lg tracking-wide">
                Класс: <span className="text-[#8B5E3C] font-semibold">{classInfo.name}</span> <span className="text-[#d6cfc5] mx-2 font-sans font-light">/</span> Выпуск {classInfo.graduation_year}
              </p>
            )}
            {localStorage.getItem('studentId') === 'teacher' && (
              <p className="text-[#D4AF37] font-sans font-bold text-sm tracking-wide mt-2">
                Фото классного руководителя
              </p>
            )}
            {localStorage.getItem('studentId') !== 'null' && localStorage.getItem('studentId') !== 'teacher' && (
              <p className="text-[#D4AF37] font-sans font-bold text-sm tracking-wide mt-2">
                Выберите 1 лучшее фото для главного разворота альбома
              </p>
            )}
          </div>
        </div>
        
        {localStorage.getItem('studentId') !== 'null' && localStorage.getItem('studentId') !== 'teacher' && (
          <div className="flex flex-col sm:flex-row items-center gap-6 bg-white py-5 px-6 md:px-8 rounded-[2rem] shadow-xl shadow-[#8B5E3C]/5 border border-[#eae0d5]">
            <div className="text-center sm:text-right">
              <p className="text-[#8c8c8c] text-[0.65rem] uppercase tracking-[0.2em] font-bold mb-1">Выбранный Портрет</p>
              <p className="font-serif text-3xl font-bold text-[#2d2d2d]">
                <span className={selectedCards.length === 1 ? "text-[#8B5E3C]" : "text-stone-300"}>{selectedCards.length}</span>
                <span className="text-[#d6cfc5] mx-2 font-sans font-light">/</span>
                <span className="text-xl text-[#8B5E3C]">1</span>
              </p>
            </div>
            <button
              disabled={selectedCards.length !== 1 || isConfirming}
              onClick={handleConfirm}
              className={`px-8 py-4 rounded-xl font-bold text-sm tracking-widest uppercase transition-all duration-300 ${
                selectedCards.length === 1 && !isConfirming
                  ? 'bg-[#8B5E3C] hover:bg-[#734c30] text-white shadow-lg shadow-[#8B5E3C]/30 hover:-translate-y-1 active:translate-y-0'
                  : 'bg-[#f4ebe1] text-[#b3a89e] cursor-not-allowed'
              }`}
            >
              {isConfirming ? 'Сохранение...' : 'Отправить в альбом'}
            </button>
          </div>
        )}
      </div>

      {photos.length === 0 ? (
        <div className="text-center py-32 bg-white rounded-[3rem] border border-[#eae0d5] shadow-sm">
          <p className="text-2xl text-[#8c8c8c] font-serif italic">Фотографии для вашего профиля пока не загружены.</p>
        </div>
      ) : (
        <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-6 space-y-6 max-w-full">
          {photos.map((photo) => {
            const isSelected = selectedCards.includes(photo.id);
            return (
              <div 
                key={photo.id}
                onClick={() => toggleSelect(photo.id)}
                className={`group relative break-inside-avoid overflow-hidden rounded-[2rem] cursor-pointer transition-all duration-500 transform bg-white ${
                  isSelected 
                    ? 'ring-[5px] ring-[#D4AF37] ring-offset-[3px] ring-offset-[#FDFBF7] shadow-[0_0_25px_rgba(212,175,55,0.25)] scale-[0.98]' 
                    : 'hover:shadow-[0_20px_40px_rgba(139,94,60,0.12)] hover:-translate-y-2 border border-[#eae0d5]'
                }`}
              >
                <div className="w-full relative">
                  <img 
                    src={getFullUrl(photo.image)} 
                    alt="Снимок выпускника" 
                    className="w-full h-auto object-cover transition-transform duration-[1.5s] ease-out group-hover:scale-[1.03]"
                  />
                  {localStorage.getItem('studentId') !== 'null' && localStorage.getItem('studentId') !== 'teacher' && isSelected && (
                    <div className="absolute inset-0 bg-[#D4AF37]/5 transition-colors duration-300 pointer-events-none"></div>
                  )}
                  {localStorage.getItem('studentId') !== 'null' && localStorage.getItem('studentId') !== 'teacher' && (
                    <div className="absolute top-5 right-5 z-10">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 shadow-md ${
                        isSelected 
                          ? 'bg-[#D4AF37] text-white scale-110 shadow-[0_4px_12px_rgba(212,175,55,0.5)]' 
                          : 'bg-white/90 backdrop-blur-md text-[#d6cfc5] group-hover:bg-white group-hover:text-[#8B5E3C] group-hover:scale-105'
                      }`}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-24 text-center border-t border-[#eae0d5] pt-12">
        <button 
          onClick={handleLogout}
          className="text-[#8c8c8c] hover:text-[#2d2d2d] font-bold text-xs uppercase tracking-[0.2em] transition-colors border-b-2 border-transparent hover:border-[#2d2d2d] pb-1"
        >
          Завершить сеанс
        </button>
      </div>
    </div>
  );
}
