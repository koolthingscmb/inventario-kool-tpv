-- Tool: delete_all_tickets.sql
-- WARNING: This will delete all rows in `ticket_lines` and `tickets`.
-- Only run if you are certain you want to remove all existing tickets.

BEGIN TRANSACTION;

DELETE FROM ticket_lines;
DELETE FROM tickets;

COMMIT;

-- Note: This file intentionally does NOT touch `payments` or `cierres`.
