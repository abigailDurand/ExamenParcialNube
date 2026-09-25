import { useCallback, useEffect, useState } from 'react';
import { getLocations, getRecentConsultations, getWeather } from '../../services/weatherService.js';
import { formatFechaHora } from '../format.js';
import Spinner from '../Spinner.jsx';

const MENSAJE_ERROR_CLIMA = 'No se pudo obtener el clima de esta ubicación';

function claseClima(condicion) {
  if (['Despejado', 'Parcialmente nublado'].includes(condicion)) return 'clima-soleado';
  if (['Nublado', 'Neblina'].includes(condicion)) return 'clima-nublado';
  if (['Lluvia', 'Llovizna', 'Tormenta'].includes(condicion)) return 'clima-lluvia';
  return '';
}

function TarjetaResultado({ estado }) {
  if (estado.cargando) {
    return (
      <section className="tarjeta tarjeta-resultado">
        <Spinner texto="Consultando el clima…" />
      </section>
    );
  }
  if (estado.error) {
    return <section className="tarjeta tarjeta-resultado mensaje-error">{estado.error}</section>;
  }
  if (!estado.datos) return null;
  const { location, temperature, condition, humidity } = estado.datos;
  return (
    <section className={`tarjeta tarjeta-resultado ${claseClima(condition)}`}>
      <h2>{location}</h2>
      <dl className="datos-clima">
        <div>
          <dt>Temperatura</dt>
          <dd>{temperature}</dd>
        </div>
        <div>
          <dt>Estado</dt>
          <dd>{condition}</dd>
        </div>
        <div>
          <dt>Humedad</dt>
          <dd>{humidity}</dd>
        </div>
      </dl>
    </section>
  );
}

export default function ConsultaMeteorologica() {
  const [ubicaciones, setUbicaciones] = useState([]);
  const [seleccion, setSeleccion] = useState('');
  const [resultado, setResultado] = useState({ cargando: false, datos: null, error: null });
  const [recientes, setRecientes] = useState([]);

  const cargarRecientes = useCallback(() => {
    getRecentConsultations()
      .then(setRecientes)
      .catch(() => setRecientes([]));
  }, []);

  useEffect(() => {
    getLocations()
      .then(setUbicaciones)
      .catch(() => setUbicaciones([]));
    cargarRecientes();
  }, [cargarRecientes]);

  async function consultar(nombre) {
    setResultado({ cargando: true, datos: null, error: null });
    try {
      const datos = await getWeather(nombre);
      setResultado({ cargando: false, datos, error: null });
      cargarRecientes();
    } catch (err) {
      if (err.status === 401) return; // api.js ya redirige al login
      setResultado({ cargando: false, datos: null, error: MENSAJE_ERROR_CLIMA });
    }
  }

  function consultarReciente(nombre) {
    setSeleccion(nombre);
    consultar(nombre);
  }

  return (
    <div className="layout-consulta">
      <div className="columna-principal">
        <section className="tarjeta bloque-consulta">
          <label>
            Región
            <select value={seleccion} onChange={(e) => setSeleccion(e.target.value)}>
              <option value="">Selecciona una región...</option>
              {ubicaciones.map((u) => (
                <option key={u.id} value={u.name}>
                  {u.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="boton"
            disabled={!seleccion || resultado.cargando}
            onClick={() => consultar(seleccion)}
          >
            Consultar
          </button>
        </section>
        <TarjetaResultado estado={resultado} />
      </div>

      <aside className="sidebar-recientes">
        <h2>Consultas recientes</h2>
        {recientes.length === 0 && <p className="nota">Todavía no hay consultas.</p>}
        {recientes.map((c) => (
          <button
            type="button"
            key={`${c.location}-${c.created_at}`}
            className="tarjeta tarjeta-reciente"
            onClick={() => consultarReciente(c.location)}
          >
            <strong>{c.location}</strong>
            <span>{formatFechaHora(c.created_at)}</span>
          </button>
        ))}
      </aside>
    </div>
  );
}
