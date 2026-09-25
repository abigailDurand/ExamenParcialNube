import { useEffect, useState } from 'react';
import { getMetricas, reentrenarModelo } from '../../services/prediccionService.js';
import { formatFechaHora } from '../format.js';
import Spinner from '../Spinner.jsx';

const MENSAJE_503 = 'Predicción no disponible por el momento';

export default function Modelo() {
  const [metricas, setMetricas] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [reentrenando, setReentrenando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMetricas()
      .then(setMetricas)
      .catch((err) => err.status !== 401 && setError(err.status === 503 ? MENSAJE_503 : 'No se pudieron cargar las métricas'))
      .finally(() => setCargando(false));
  }, []);

  async function handleReentrenar() {
    setReentrenando(true);
    setError(null);
    try {
      setMetricas(await reentrenarModelo());
    } catch (err) {
      if (err.status !== 401) setError(err.message || 'No se pudo reentrenar el modelo');
    } finally {
      setReentrenando(false);
    }
  }

  return (
    <section className="tarjeta seccion-panel">
      <h2>Modelo predictivo</h2>
      {cargando && <Spinner />}
      {error && <p className="mensaje-error">{error}</p>}
      {metricas && (
        <dl className="datos-modelo">
          <div>
            <dt>Versión</dt>
            <dd>v{metricas.version}</dd>
          </div>
          <div>
            <dt>MAE</dt>
            <dd>{metricas.mae.toFixed(2)} visitantes</dd>
          </div>
          <div>
            <dt>R²</dt>
            <dd>{metricas.r2.toFixed(3)}</dd>
          </div>
          <div>
            <dt>Datos de entrenamiento</dt>
            <dd>
              {metricas.registros} días{metricas.entrenado_con_sinteticos ? ' (incluye datos sintéticos)' : ''}
            </dd>
          </div>
          <div>
            <dt>Entrenado</dt>
            <dd>{formatFechaHora(metricas.entrenado_en)}</dd>
          </div>
        </dl>
      )}
      <button type="button" className="boton" onClick={handleReentrenar} disabled={reentrenando}>
        {reentrenando ? 'Reentrenando…' : 'Reentrenar'}
      </button>
    </section>
  );
}
