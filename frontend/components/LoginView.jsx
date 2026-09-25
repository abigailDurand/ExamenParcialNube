import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { login } from '../services/authService.js';
import CredencialesDemo from './CredencialesDemo.jsx';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MENSAJE_CREDENCIALES = 'Correo o contraseña incorrectos';

function validar(email, password) {
  if (!email.trim() || !password) return 'Ingresa tu correo y tu contraseña';
  if (!EMAIL_REGEX.test(email.trim())) return 'El correo no tiene un formato válido';
  return null;
}

export default function LoginView() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const errorValidacion = validar(email, password);
    if (errorValidacion) {
      setError(errorValidacion); // no se llama a la API
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      await login(email.trim(), password);
      navigate('/admin', { replace: true });
    } catch (err) {
      setError(err.status === 401 ? err.message || MENSAJE_CREDENCIALES : err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="pagina pagina-centrada">
      <form className="tarjeta tarjeta-login" onSubmit={handleSubmit} noValidate>
        <h1>Iniciar sesión</h1>
        <label>
          Correo
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? 'Ingresando…' : 'Iniciar sesión'}
        </button>
        {error && (
          <p className="mensaje-error" role="alert">
            {error}
          </p>
        )}
        <Link to="/" className="enlace-discreto">
          ← Volver a la predicción
        </Link>
        <CredencialesDemo />
      </form>
    </main>
  );
}
