import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout/Layout';
import ConfigPage from './pages/ConfigPage';
import KnowledgePage from './pages/KnowledgePage';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
            borderRadius: '12px',
            fontSize: '14px',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#1e293b',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#1e293b',
            },
          },
        }}
      />
      
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/config" replace />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
