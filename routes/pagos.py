from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

pagos_bp = Blueprint('pagos', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@pagos_bp.route('/', methods=['GET'])
def get_pagos():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT pg.pago_id, pg.pedido_id, pg.fecha_pago, pg.metodo_pago, pg.monto, '
            'c.nombre_completo AS cliente '
            'FROM Pagos pg '
            'JOIN Pedidos p  ON pg.pedido_id  = p.pedido_id '
            'JOIN Clientes c ON p.cliente_id  = c.cliente_id '
            'ORDER BY pg.fecha_pago DESC'
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pagos_bp.route('/', methods=['POST'])
def registrar_pago():
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("OPEN SYMMETRIC KEY ClaveLogistica DECRYPTION BY CERTIFICATE CertificadoLogistica")
        cursor.execute(
            "INSERT INTO Pagos (pedido_id, metodo_pago, referencia_pago, monto) "
            "VALUES (?, ?, ENCRYPTBYKEY(KEY_GUID('ClaveLogistica'), ?), ?)",
            data['pedido_id'],
            data['metodo_pago'],
            data.get('referencia_pago', ''),
            data['monto']
        )
        cursor.execute("CLOSE SYMMETRIC KEY ClaveLogistica")
        conn.commit()
        return jsonify({'mensaje': 'Pago registrado'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
