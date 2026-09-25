import { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getVisitas } from '../../services/prediccionService.js';
import { formatFechaCorta, hoyIso, sumarDias } from '../format.js';
import Spinner from '../Spinner.jsx';

export default function GraficoVisitas() {
  const [hasta, setHasta] = useState(hoyIso());
  const [desde, setDesde] = useState(sumarDias(hoyIso(), -30));
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!desde || !hasta || desde > hasta) {
      setError('La fecha "desde" debe ser anterior a "hasta"');
      return;
    }
    setCargando(true);
    setError(null);
    getVisitas(desde, hasta)
      .then((filas) =>
        setDatos(
          filas.map((f) => ({
            fecha: formatFechaCorta(f.fecha),
            reales: f.cantidad_visitantes,
            predichas: f.visitantes_predichos,
          })),
        ),
      )
      .catch((err) => err.status !== 401 && setError('No se pudieron cargar las visitas'))
      .finally(() => setCargando(false));
  }, [desde, hasta]);

  return (
    <section className="tarjeta seccion-panel">
      <h2>Visitas reales vs. predichas</h2>
      <div className="formulario-fila">
        <label>
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label>
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
      </div>

      {error && <p className="mensaje-error">{error}</p>}
      {cargando && !error && <Spinner />}
      {!cargando && !error && datos.length === 0 && (
        <p className="nota">No hay visitas registradas en ese rango.</p>
      )}
      {!cargando && !error && datos.length > 0 && (
        <div className="grafico">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="var(--borde)" strokeDasharray="3 3" />
              <XAxis dataKey="fecha" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="reales" name="Reales" stroke="var(--serie-reales)" strokeWidth={2} dot={false} />
              <Line
                type="monotone"
                dataKey="predichas"
                name="Predichas"
                stroke="var(--serie-predichas)"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
