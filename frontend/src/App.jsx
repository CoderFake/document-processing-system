import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import PDFPage from './pages/PDFPage';
import WordPage from './pages/WordPage';
import ExcelPage from './pages/ExcelPage';
import FilesPage from './pages/FilesPage';
import ArchivesPage from './pages/ArchivesPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <>
      <Toaster 
        position="top-right"
        reverseOrder={false}
        gutter={8}
        toastOptions={{
          duration: 5000,
          style: {
            fontSize: '14px',
            fontWeight: '500',
            borderRadius: '8px',
            padding: '12px 16px',
          },
          error: {
            style: {
              background: '#FEF2F2',
              color: '#DC2626',
              border: '1px solid #FECACA',
            },
            duration: 5000,
          },
          success: {
            style: {
              background: '#F0FDF4',
              color: '#16A34A',
              border: '1px solid #BBF7D0',
            },
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/" element={<HomePage />} />
          <Route path="/pdf" element={<PDFPage />} />
          <Route path="/word" element={<WordPage />} />
          <Route path="/excel" element={<ExcelPage />} />
          <Route path="/archives" element={<ArchivesPage />} />
          <Route path="/files" element={<FilesPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  );
}

export default App; 