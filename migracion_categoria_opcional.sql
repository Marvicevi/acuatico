-- Un nadador puede quedar sin categoría cuando su edad al 31 de diciembre
-- todavía no entra en la tabla FECHIDA. No borra fichas ni categorías ya guardadas.
ALTER TABLE nadadores ALTER COLUMN categoria DROP NOT NULL;
