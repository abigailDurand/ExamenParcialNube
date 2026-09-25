import { NavLink, Route, Routes, useNavigate } from 'react-router';
import { logout } from '../../services/authService.js';
import ConsultaMeteorologica from './ConsultaMeteorologica.jsx';
import Feriados from './Feriados.jsx';
import GraficoVisitas from './GraficoVisitas.jsx';
import Modelo from './Modelo.jsx';
import RegistrarVisitas from './RegistrarVisitas.jsx';

const SECCIONES = [
  { to: '/admin', label: 'Consulta Meteorológica', end: true },
  { to: '/admin/visitas', label: 'Registrar visitas' },
  { to: '/admin/feriados', label: 'Feriados' },
  { to: '/admin/modelo', label: 'Modelo' },
  { to: '/admin/grafico', label: 'Reales vs. predichas' },
];

export default function AdminPanel() {
  const navigate = useNavigate();

  function cerrarSesion() {
    logout();
    navigate('/', { replace: true });
  }

  return (
    <div className="pagina">
      <header className="cabecera cabecera-panel">
        <h1>Panel del administrador</h1>
        <button type="button" className="boton boton-secundario" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>

      <nav className="menu-panel" aria-label="Secciones del panel">
        {SECCIONES.map((s) => (
          <NavLink key={s.to} to={s.to} end={s.end} className="menu-item">
            {s.label}
          </NavLink>
        ))}
      </nav>

      <Routes>
        <Route index element={<ConsultaMeteorologica />} />
        <Route path="visitas" element={<RegistrarVisitas />} />
        <Route path="feriados" element={<Feriados />} />
        <Route path="modelo" element={<Modelo />} />
        <Route path="grafico" element={<GraficoVisitas />} />
      </Routes>
    </div>
  );
}
