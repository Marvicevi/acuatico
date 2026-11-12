-- Migración segura para la base que YA está en uso.
-- No borra filas ni cambia los presentes ya guardados.
-- Solo agrega el motivo y el detalle de cada asistencia.
-- Se puede ejecutar más de una vez.

ALTER TABLE asistencias ADD COLUMN IF NOT EXISTS motivo VARCHAR(40);
ALTER TABLE asistencias ADD COLUMN IF NOT EXISTS observacion TEXT;

-- Revisión. Las filas viejas siguen con su estado (Presente o Ausente)
-- y motivo/observacion vacíos hasta que el entrenador vuelva a guardar ese día.
SELECT id, id_nadador, fecha, estado, motivo, observacion
FROM asistencias
ORDER BY fecha DESC, id_nadador
LIMIT 50;
