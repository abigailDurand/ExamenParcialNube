import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router';
import { setUnauthorizedHandler } from '../services/api.js';
import LoginView from './LoginView.jsx';
import PrediccionesPublicas from './PrediccionesPublicas.jsx';
import ProtectedRoute from './ProtectedRoute.jsx';
import Spinner from './Spinner.jsx';

// El panel (con Recharts) se descarga solo cuando el administrador entra
const AdminPanel = lazy(() => import('./admin/AdminPanel.jsx'));

export default function App() {
  const navigate = useNavigate();

  useEffect(() => {
    // Cualquier 401 en un endpoint protegido → vuelve al login
    setUnauthorizedHandler(() => navigate('/login', { replace: true }));
  }, [navigate]);

  return (
    <Routes>
      <Route path="/" element={<PrediccionesPublicas />} />
      <Route path="/login" element={<LoginView />} />
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute>
            <Suspense fallback={<Spinner />}>
              <AdminPanel />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
