from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

repartidores_bp = Blueprint('repartidores', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@repartidores_bp.route('/', methods=['GET'])
def get_repartidores():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT repartidor_id, nombre_completo, telefono, usuario, estado FROM Repartidores'
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@repartidores_bp.route('/disponibles', methods=['GET'])
def get_disponibles():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT repartidor_id, nombre_completo, telefono, usuario FROM Repartidores WHERE estado = ?',
            'Activo'
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@repartidores_bp.route('/<int:repartidor_id>', methods=['GET'])
def get_repartidor(repartidor_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT repartidor_id, nombre_completo, telefono, usuario, estado FROM Repartidores WHERE repartidor_id = ?',
            repartidor_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Repartidor no encontrado'}), 404
        return jsonify(row_to_dict(cursor, row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@repartidores_bp.route('/', methods=['POST'])
def crear_repartidor():
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'EXEC sp_registrar_repartidor ?, ?, ?, ?, ?',
            data['nombre_completo'],
            data.get('licencia_conducir', ''),
            data.get('telefono', ''),
            data['usuario'],
            data['contrasena']
        )
        conn.commit()
        return jsonify({'mensaje': 'Repartidor registrado'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@repartidores_bp.route('/<int:repartidor_id>/estado', methods=['PUT'])
def cambiar_estado(repartidor_id):
    data  = request.get_json()
    estado = data.get('estado')
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Repartidores SET estado = ? WHERE repartidor_id = ?',
            estado, repartidor_id
        )
        conn.commit()
        return jsonify({'mensaje': 'Estado actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
