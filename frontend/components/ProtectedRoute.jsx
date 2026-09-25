import { Navigate } from 'react-router';
import { isAuthenticated } from '../services/authService.js';

export default function ProtectedRoute({ children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return children;
}
