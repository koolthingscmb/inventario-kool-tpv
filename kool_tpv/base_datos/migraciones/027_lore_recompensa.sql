-- Migración 027: campo lore_recompensa en niveles_fidelidad
-- Permite almacenar múltiples lores de aventura separados por |||
ALTER TABLE niveles_fidelidad ADD COLUMN lore_recompensa TEXT;
