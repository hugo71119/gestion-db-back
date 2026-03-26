from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

clientes_bp = Blueprint('clientes', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@clientes_bp.route('/', methods=['GET'])
def get_clientes():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('EXEC sp_consultar_clientes_descifrados')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientes_bp.route('/<int:cliente_id>', methods=['GET'])
def get_cliente(cliente_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT cliente_id, nombre_completo, email, telefono, direccion, tipo_documento, fecha_registro '
            'FROM Clientes WHERE cliente_id = ?',
            cliente_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        return jsonify(row_to_dict(cursor, row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientes_bp.route('/', methods=['POST'])
def crear_cliente():
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'EXEC sp_registrar_cliente ?, ?, ?, ?, ?, ?',
            data['nombre_completo'],
            data['email'],
            data.get('telefono', ''),
            data.get('direccion', ''),
            data.get('tipo_documento', ''),
            data.get('numero_documento', '')
        )
        conn.commit()
        return jsonify({'mensaje': 'Cliente registrado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientes_bp.route('/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente(cliente_id):
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Clientes SET nombre_completo=?, telefono=?, direccion=? WHERE cliente_id=?',
            data.get('nombre_completo'),
            data.get('telefono'),
            data.get('direccion'),
            cliente_id
        )
        conn.commit()
        return jsonify({'mensaje': 'Cliente actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clientes_bp.route('/<int:cliente_id>', methods=['DELETE'])
def eliminar_cliente(cliente_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Clientes WHERE cliente_id = ?', cliente_id)
        conn.commit()
        return jsonify({'mensaje': 'Cliente eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
