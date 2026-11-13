-- Las cuentas que ya existen quedan como están: no se les pide cambiar la clave.
-- Solo una cuenta creada después, desde el panel del master, entra obligada
-- a reemplazar la contraseña temporal en su primer ingreso.
-- Se puede ejecutar más de una vez. No borra filas ni cambia claves.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS debe_cambiar_clave BOOLEAN DEFAULT false;
UPDATE usuarios SET debe_cambiar_clave = false WHERE debe_cambiar_clave IS NULL;
