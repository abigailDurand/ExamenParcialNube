import { useState } from 'react';
import { registrarVisita } from '../../services/prediccionService.js';
import { formatFechaLarga, hoyIso } from '../format.js';

export default function RegistrarVisitas() {
  const [fecha, setFecha] = useState(hoyIso());
  const [cantidad, setCantidad] = useState('');
  const [mensaje, setMensaje] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const numero = Number(cantidad);
    if (!fecha || cantidad === '' || !Number.isInteger(numero) || numero < 0) {
      setMensaje({ tipo: 'error', texto: 'Ingresa una fecha y una cantidad entera mayor o igual a 0' });
      return;
    }
    setEnviando(true);
    setMensaje(null);
    try {
      const visita = await registrarVisita(fecha, numero);
      setMensaje({
        tipo: 'ok',
        texto: `Registrado: ${visita.cantidad_visitantes} visitantes el ${formatFechaLarga(visita.fecha)}`,
      });
      setCantidad('');
    } catch (err) {
      if (err.status !== 401) setMensaje({ tipo: 'error', texto: 'No se pudo registrar la visita' });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="tarjeta seccion-panel">
      <h2>Registrar visitas reales</h2>
      <form className="formulario-fila" onSubmit={handleSubmit} noValidate>
        <label>
          Fecha
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        </label>
        <label>
          Cantidad de visitantes
          <input
            type="number"
            min="0"
            step="1"
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
        </label>
        <button type="submit" className="boton" disabled={enviando}>
          Registrar
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
