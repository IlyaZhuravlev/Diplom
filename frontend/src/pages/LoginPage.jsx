import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function LoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!password) {
      setError('Пожалуйста, введите код доступа');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await api.get('/classes/');
      const classes = response.data.results || response.data;
      
      const foundClass = classes.find(c => c.parent_password === password);
      
      if (foundClass) {
        localStorage.setItem('classId', foundClass.id);
        navigate('/select-student');
      } else {
        setError('Неверный код доступа. Проверьте ваш буклет.');
      }
    } catch (err) {
      console.error('Ошибка входа:', err);
      setError('Произошла ошибка при подключении к серверу.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center pt-8 md:pt-12">
      <div className="max-w-md w-full bg-white rounded-[2rem] shadow-2xl shadow-[#8B5E3C]/5 border border-[#8B5E3C]/10 p-10 pb-12 mt-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-2 bg-[#8B5E3C] opacity-90"></div>
        <h2 className="text-3xl font-serif text-center font-bold text-[#2d2d2d] mb-4">Добро пожаловать</h2>
        <p className="text-center text-[#8c8c8c] font-medium mb-10 leading-relaxed text-sm md:text-base">
          Введите эксклюзивный код доступа из памятки, чтобы открыть профессиональную галерею вашего класса.
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-2xl text-center text-sm border border-red-100 font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-xs uppercase tracking-widest font-bold text-[#8c8c8c] mb-2 pl-2">Код доступа</label>
            <input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-5 py-4 bg-[#FDFBF7] border border-[#eae0d5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B5E3C]/30 focus:border-[#8B5E3C] transition-all text-xl font-bold tracking-widest text-center text-[#2d2d2d]"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#8B5E3C] hover:bg-[#734c30] text-white py-4 rounded-xl font-bold text-lg transition-all hover:shadow-xl hover:shadow-[#8B5E3C]/30 hover:-translate-y-1 active:translate-y-0 disabled:opacity-70 disabled:hover:translate-y-0 disabled:shadow-none mt-4"
          >
            {isLoading ? 'АВТОРИЗАЦИЯ...' : 'ВОЙТИ В ГАЛЕРЕЮ'}
          </button>
        </form>
      </div>
    </div>
  );
}
