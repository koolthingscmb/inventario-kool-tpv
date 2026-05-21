# -*- coding: utf-8 -*-
from decimal import Decimal

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.modulos.ticket.ticket_repository import TicketRepository


def test_listar_tickets_returns_total_as_decimal():
    db = Database(':memory:')
    db.connect()

    cur = db.connection.cursor()
    cur.execute(
        """
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_ticket INTEGER,
            created_at TEXT,
            total INTEGER,
            cajero TEXT,
            cliente TEXT,
            forma_pago TEXT,
            ticket_text TEXT
        )
        """
    )

    insert_q = (
        "INSERT INTO tickets (num_ticket, created_at, total, cajero, cliente, forma_pago, ticket_text) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )

    # insert a ticket with 12.34 euros
    cents = prepare_for_db(Decimal('12.34'))
    cur.execute(insert_q, (1001, '2026-05-21T12:00:00', int(cents), 'juan', 'ACME', 'EFECTIVO', 'texto'))
    db.connection.commit()

    repo = TicketRepository(db)
    results = repo.listar_tickets()

    assert isinstance(results, list)
    assert len(results) == 1

    r = results[0]
    assert r['num_ticket'] == 1001
    assert r['cajero'] == 'juan'
    assert isinstance(r['total'], Decimal)
    # exact equality to 12.34 euros
    assert r['total'] == Decimal('12.34')

    db.close_connection()
