-- Migración 033: Configuración de Google Drive para Backup Automático
-- Añade claves a la tabla configuracion

INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('backup_drive_enabled', '0');
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('backup_drive_folder_name', 'KOOL_TPV_Backups');
