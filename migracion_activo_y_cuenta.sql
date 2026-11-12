-- Migración segura para la base que YA está en uso.
-- No borra nadadores, tiempos, asistencias ni cuentas.
-- Quien ya está en la base queda activo. Nada desaparece hasta que
-- alguien desmarque la casilla Activo en Perfiles.
-- Se puede ejecutar más de una vez.

ALTER TABLE nadadores ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT true;
UPDATE nadadores SET activo = true WHERE activo IS NULL;

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS id_nadador INTEGER REFERENCES nadadores(id) ON DELETE SET NULL;

SELECT id, nombre, grupo, activo FROM nadadores ORDER BY nombre;
SELECT id, nombre, email, rol, id_nadador FROM usuarios ORDER BY nombre;
