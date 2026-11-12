-- Migración segura para la base que YA está en uso.
-- No borra tablas, no borra filas y no modifica tiempos, asistencias, usuarios ni marcas.
-- Solo agrega nadadores.anio_nacimiento y lo completa cuando la categoría actual
-- corresponde a una sola edad de la temporada 2026 (edad al 31 de diciembre).
--
-- 2026 − 11 = 2015. Infantil A nace en 2015, no en 2011.
-- 2011 en la temporada 2026 es Juvenil A2 (15 años).
-- Juvenil B (16, 17 o 18) y Mayores (19 o más) quedan sin año:
-- no se puede adivinar sin cambiarles la categoría.
--
-- Se puede ejecutar más de una vez: no pisa un año que ya esté guardado.

ALTER TABLE nadadores ADD COLUMN IF NOT EXISTS anio_nacimiento INTEGER;

-- Si en Supabase existe una columna "edad", se deja opcional.
-- No se borra ni se reescribe ningún valor.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'nadadores'
      AND column_name = 'edad'
  ) THEN
    EXECUTE 'ALTER TABLE nadadores ALTER COLUMN edad DROP NOT NULL';
  END IF;
END $$;

UPDATE nadadores
SET anio_nacimiento = CASE categoria::text
    WHEN 'Infantil E'  THEN 2018
    WHEN 'Infantil D'  THEN 2017
    WHEN 'Infantil C'  THEN 2016
    WHEN 'Infantil A'  THEN 2015
    WHEN 'Infantil B1' THEN 2014
    WHEN 'Infantil B2' THEN 2013
    WHEN 'Juvenil A1'  THEN 2012
    WHEN 'Juvenil A2'  THEN 2011
    ELSE anio_nacimiento
END
WHERE anio_nacimiento IS NULL
  AND categoria::text IN (
    'Infantil E', 'Infantil D', 'Infantil C', 'Infantil A',
    'Infantil B1', 'Infantil B2', 'Juvenil A1', 'Juvenil A2'
  );

-- Opcional, en una segunda ejecución aparte (no hace falta para los nadadores actuales).
-- Habilita guardar categorías de 8, 9 y 10 años. No modifica filas.
-- ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil C';
-- ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil D';
-- ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil E';

-- Revisión. Juvenil B y Mayores deben verse con anio_nacimiento vacío.
SELECT id, nombre, grupo, categoria, anio_nacimiento
FROM nadadores
ORDER BY nombre;
