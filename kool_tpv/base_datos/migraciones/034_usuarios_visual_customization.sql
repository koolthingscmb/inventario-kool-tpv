-- Migración para personalización visual de usuarios (cajeros)
-- ui_color: Color asociado al usuario para la interfaz del TPV
-- banner_path: Ruta al icono/banner personalizado del usuario (preparado para futuro)

ALTER TABLE usuarios ADD COLUMN ui_color TEXT DEFAULT '#00FF00';
ALTER TABLE usuarios ADD COLUMN banner_path TEXT;
