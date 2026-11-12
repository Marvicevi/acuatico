-- No borra nadadores, tiempos ni usuarios.
-- Agrega la fecha de nacimiento completa y el catálogo de grupos.
-- Ejecútalo en el editor SQL de Supabase antes de renombrar grupos en la app.
-- No ejecutes schema_supabase.sql en esta base: ese archivo borra las tablas.

ALTER TABLE nadadores ADD COLUMN IF NOT EXISTS fecha_nacimiento DATE;

CREATE TABLE IF NOT EXISTS grupos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO grupos (nombre)
SELECT DISTINCT TRIM(grupo)
FROM nadadores
WHERE grupo IS NOT NULL AND TRIM(grupo) <> ''
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO grupos (nombre) VALUES
    ('Competitivo'),
    ('Precompetitivo'),
    ('Formativo'),
    ('Elite'),
    ('Master')
ON CONFLICT (nombre) DO NOTHING;

-- La fecha queda vacía a propósito cuando solo se conoce el año.
-- No se inventa el 01/01.

SELECT id, nombre FROM grupos ORDER BY nombre;

SELECT id, nombre, fecha_nacimiento, anio_nacimiento, grupo
FROM nadadores
ORDER BY nombre;
