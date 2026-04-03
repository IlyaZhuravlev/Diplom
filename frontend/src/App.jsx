import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import GalleryPage from './pages/GalleryPage';
import SchedulePage from './pages/SchedulePage';
import StudentSelectPage from './pages/StudentSelectPage';
import PhotographerPage from './pages/PhotographerPage';
import AlbumEditorPage from './pages/AlbumEditorPage';

function Header() {
  return (
    <header className="w-full py-10 flex flex-col items-center justify-center bg-transparent">
      <h1 className="font-serif text-[2.75rem] md:text-5xl font-bold text-[#2d2d2d] tracking-[0.15em] mb-2 uppercase">Журавлик</h1>
      <p className="font-sans text-xs md:text-sm tracking-widest text-[#8c8c8c] uppercase font-medium text-center px-4">студия выпускных альбомов</p>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#FDFBF7] font-sans flex flex-col items-center">
        <Header />
        <main className="w-full pb-16 px-4 sm:px-6 lg:px-8 flex-1">
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/select-student" element={<StudentSelectPage />} />
            <Route path="/gallery" element={<GalleryPage />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/photographer" element={<PhotographerPage />} />
            <Route path="/album-editor" element={<AlbumEditorPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
