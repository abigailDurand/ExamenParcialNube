import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { getPredicciones } from '../services/prediccionService.js';
import { formatFechaLarga } from './format.js';
import CredencialesDemo from './CredencialesDemo.jsx';
import Spinner from './Spinner.jsx';

const MENSAJE_503 = 'Predicción no disponible por el momento';
const MENSAJE_ERROR = 'No se pudo cargar la predicción';

function PrediccionCard({ prediccion }) {
  const nivel = prediccion.nivel_afluencia;
  return (
    <article className={`tarjeta tarjeta-prediccion afluencia-${nivel.toLowerCase()}`}>
      <h2 className="prediccion-fecha">{formatFechaLarga(prediccion.fecha)}</h2>
      <p className="prediccion-visitantes">
        <strong>{prediccion.visitantes_predichos}</strong> visitantes
      </p>
      <p className="etiqueta-nivel">Afluencia {nivel}</p>
      <dl className="prediccion-clima">
        <div>
          <dt>Lluvia</dt>
          <dd>{prediccion.lluvia_mm != null ? `${prediccion.lluvia_mm} mm` : '—'}</dd>
        </div>
        <div>
          <dt>Temp. máxima</dt>
          <dd>{prediccion.temp_max != null ? `${Math.round(prediccion.temp_max)}°C` : '—'}</dd>
        </div>
      </dl>
      {prediccion.dato_incompleto && <p className="nota">Pronóstico de lluvia no disponible</p>}
    </article>
  );
}

export default function PrediccionesPublicas() {
  const [estado, setEstado] = useState({ cargando: true, datos: [], error: null });

  useEffect(() => {
    let activo = true;
    getPredicciones()
      .then((datos) => activo && setEstado({ cargando: false, datos, error: null }))
      .catch((err) => {
        if (!activo) return;
        setEstado({ cargando: false, datos: [], error: err.status === 503 ? MENSAJE_503 : MENSAJE_ERROR });
      });
    return () => {
      activo = false;
    };
  }, []);

  return (
    <main className="pagina">
      <header className="cabecera">
        <h1>Visitantes a Las Pavas</h1>
        <p className="subtitulo">Cueva de Las Pavas · Tingo María</p>
      </header>

      {estado.cargando && <Spinner texto="Cargando predicción…" />}
      {estado.error && <p className="tarjeta mensaje-error">{estado.error}</p>}
      {!estado.cargando && !estado.error && estado.datos.length === 0 && (
        <p className="tarjeta mensaje-error">{MENSAJE_503}</p>
      )}

      <section className="grilla-predicciones">
        {estado.datos.map((p) => (
          <PrediccionCard key={p.fecha} prediccion={p} />
        ))}
      </section>

      <footer className="pie">
        <Link to="/login" className="enlace-discreto">
          Ingresar como administrador
        </Link>
        <CredencialesDemo />
      </footer>
    </main>
  );
}
