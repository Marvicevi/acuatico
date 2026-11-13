-- Quita el año suelto. La fecha de nacimiento completa es la que queda.
-- No borra nadadores ni sus fechas. Se puede ejecutar más de una vez.

ALTER TABLE nadadores DROP COLUMN IF EXISTS anio_nacimiento;
