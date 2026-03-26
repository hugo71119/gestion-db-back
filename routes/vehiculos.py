from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

vehiculos_bp = Blueprint('vehiculos', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@vehiculos_bp.route('/', methods=['GET'])
def get_vehiculos():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Vehiculos ORDER BY tipo')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@vehiculos_bp.route('/disponibles', methods=['GET'])
def get_disponibles():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Vehiculos WHERE estado = 'Disponible'")
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@vehiculos_bp.route('/', methods=['POST'])
def crear_vehiculo():
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Vehiculos (tipo, placa, capacidad, estado) VALUES (?,?,?,?)',
            data['tipo'],
            data['placa'],
            data.get('capacidad', 0),
            data.get('estado', 'Disponible')
        )
        conn.commit()
        return jsonify({'mensaje': 'Vehiculo registrado'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@vehiculos_bp.route('/<int:vehiculo_id>', methods=['PUT'])
def actualizar_vehiculo(vehiculo_id):
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Vehiculos SET tipo=?, capacidad=?, estado=? WHERE vehiculo_id=?',
            data.get('tipo'),
            data.get('capacidad'),
            data.get('estado'),
            vehiculo_id
        )
        conn.commit()
        return jsonify({'mensaje': 'Vehiculo actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
