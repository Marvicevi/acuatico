-- Agrega las categorías que la app ya calcula y que faltaban en la base en uso.
-- No borra datos. En una instalación nueva, schema_supabase.sql ya las incluye.
ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil E';
ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil D';
ALTER TYPE tipo_categoria ADD VALUE IF NOT EXISTS 'Infantil C';
