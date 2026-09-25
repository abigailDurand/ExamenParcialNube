import { useCallback, useEffect, useState } from 'react';
import { agregarFeriado, getFeriados, quitarFeriado } from '../../services/prediccionService.js';
import { formatFechaLarga } from '../format.js';
import Spinner from '../Spinner.jsx';

export default function Feriados() {
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [feriados, setFeriados] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [nuevaFecha, setNuevaFecha] = useState('');
  const [nuevoNombre, setNuevoNombre] = useState('');
  const [mensaje, setMensaje] = useState(null);

  const cargar = useCallback(() => {
    setCargando(true);
    getFeriados(anio)
      .then(setFeriados)
      .catch(() => setFeriados([]))
      .finally(() => setCargando(false));
  }, [anio]);

  useEffect(cargar, [cargar]);

  async function handleAgregar(event) {
    event.preventDefault();
    if (!nuevaFecha || !nuevoNombre.trim()) {
      setMensaje({ tipo: 'error', texto: 'Ingresa la fecha y el nombre del feriado' });
      return;
    }
    try {
      await agregarFeriado(nuevaFecha, nuevoNombre.trim());
      setMensaje({ tipo: 'ok', texto: 'Feriado agregado' });
      setNuevaFecha('');
      setNuevoNombre('');
      cargar();
    } catch (err) {
      if (err.status === 409) setMensaje({ tipo: 'error', texto: 'Ya existe un feriado en esa fecha' });
      else if (err.status !== 401) setMensaje({ tipo: 'error', texto: 'No se pudo agregar el feriado' });
    }
  }

  async function handleQuitar(fecha) {
    try {
      await quitarFeriado(fecha);
      setMensaje({ tipo: 'ok', texto: 'Feriado quitado' });
      cargar();
    } catch (err) {
      if (err.status !== 401) setMensaje({ tipo: 'error', texto: 'No se pudo quitar el feriado' });
    }
  }

  return (
    <section className="tarjeta seccion-panel">
      <h2>Feriados</h2>

      <label className="selector-anio">
        Año
        <input type="number" value={anio} onChange={(e) => setAnio(Number(e.target.value))} />
      </label>

      {cargando ? (
        <Spinner />
      ) : (
        <ul className="lista-feriados">
          {feriados.length === 0 && <li className="nota">No hay feriados registrados para {anio}.</li>}
          {feriados.map((f) => (
            <li key={f.fecha}>
              <span>
                <strong>{formatFechaLarga(f.fecha)}</strong> — {f.nombre}
              </span>
              <button type="button" className="boton boton-secundario" onClick={() => handleQuitar(f.fecha)}>
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <form className="formulario-fila" onSubmit={handleAgregar} noValidate>
        <label>
          Fecha
          <input type="date" value={nuevaFecha} onChange={(e) => setNuevaFecha(e.target.value)} />
        </label>
        <label>
          Nombre
          <input type="text" value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} />
        </label>
        <button type="submit" className="boton">
          Agregar
        </button>
      </form>
      {mensaje && (
        <p className={mensaje.tipo === 'ok' ? 'mensaje-ok' : 'mensaje-error'} role="status">
          {mensaje.texto}
        </p>
      )}
    </section>
  );
}
