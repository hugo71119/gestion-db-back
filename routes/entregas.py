from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

entregas_bp = Blueprint('entregas', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@entregas_bp.route('/', methods=['GET'])
def get_entregas():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT e.entrega_id, e.pedido_id, e.repartidor_id, e.vehiculo_id, '
            'e.fecha_salida, e.fecha_entrega, e.estado, '
            'r.nombre_completo AS repartidor, v.tipo AS vehiculo, v.placa '
            'FROM Entregas e '
            'JOIN Repartidores r ON e.repartidor_id = r.repartidor_id '
            'JOIN Vehiculos v    ON e.vehiculo_id   = v.vehiculo_id '
            'ORDER BY e.fecha_salida DESC'
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/<int:entrega_id>', methods=['GET'])
def get_entrega(entrega_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT e.entrega_id, e.pedido_id, e.repartidor_id, e.vehiculo_id, '
            'e.fecha_salida, e.fecha_entrega, e.estado, '
            'r.nombre_completo AS repartidor, v.tipo AS vehiculo, v.placa '
            'FROM Entregas e '
            'JOIN Repartidores r ON e.repartidor_id = r.repartidor_id '
            'JOIN Vehiculos v    ON e.vehiculo_id   = v.vehiculo_id '
            'WHERE e.entrega_id = ?',
            entrega_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Entrega no encontrada'}), 404
        return jsonify(row_to_dict(cursor, row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/repartidor/<int:repartidor_id>', methods=['GET'])
def entregas_por_repartidor(repartidor_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT e.entrega_id, e.pedido_id, e.repartidor_id, e.vehiculo_id, '
            'e.fecha_salida, e.fecha_entrega, e.estado, '
            'v.tipo AS vehiculo, v.placa '
            'FROM Entregas e JOIN Vehiculos v ON e.vehiculo_id = v.vehiculo_id '
            'WHERE e.repartidor_id = ? ORDER BY e.fecha_salida DESC',
            repartidor_id
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/<int:entrega_id>/estado', methods=['PUT'])
def actualizar_estado(entrega_id):
    data  = request.get_json()
    estado = data.get('estado')
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        if estado == 'Entregado':
            evidencia = data.get('evidencia', '')
            cursor.execute("OPEN SYMMETRIC KEY ClaveLogistica DECRYPTION BY CERTIFICATE CertificadoLogistica")
            cursor.execute(
                'UPDATE Entregas SET estado = ?, fecha_entrega = GETDATE(), '
                "evidencia_entrega = ENCRYPTBYKEY(KEY_GUID('ClaveLogistica'), ?) "
                'WHERE entrega_id = ?',
                estado, evidencia, entrega_id
            )
            cursor.execute("CLOSE SYMMETRIC KEY ClaveLogistica")
        else:
            cursor.execute(
                'UPDATE Entregas SET estado = ? WHERE entrega_id = ?',
                estado, entrega_id
            )
        conn.commit()
        return jsonify({'mensaje': 'Estado de entrega actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
