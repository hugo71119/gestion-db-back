from flask import Blueprint, request, jsonify
import pyodbc
from config import CONNECTION_STRING

productos_bp = Blueprint('productos', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@productos_bp.route('/', methods=['GET'])
def get_productos():
    """Lista todos los productos disponibles. Acepta filtro ?categoria=X"""
    try:
        conn      = get_conn()
        cursor    = conn.cursor()
        categoria = request.args.get('categoria')
        todos = request.args.get('todos')
        if categoria:
            cursor.execute(
                'SELECT * FROM Productos WHERE disponible = 1 AND categoria = ? ORDER BY categoria, nombre',
                categoria
            )
        elif todos:
            cursor.execute('SELECT * FROM Productos ORDER BY categoria, nombre')
        else:
            cursor.execute(
                'SELECT * FROM Productos WHERE disponible = 1 ORDER BY categoria, nombre'
            )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/categorias', methods=['GET'])
def get_categorias():
    """Devuelve las categorías únicas disponibles."""
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT DISTINCT categoria FROM Productos WHERE disponible = 1 ORDER BY categoria'
        )
        return jsonify([row[0] for row in cursor.fetchall()])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/<int:producto_id>', methods=['GET'])
def get_producto(producto_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Productos WHERE producto_id = ?', producto_id)
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Producto no encontrado'}), 404
        return jsonify(row_to_dict(cursor, row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/', methods=['POST'])
def crear_producto():
    """Solo admin. Crea un producto en el catálogo."""
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Productos (nombre, descripcion, precio, categoria, disponible) '
            'VALUES (?, ?, ?, ?, ?)',
            data['nombre'],
            data.get('descripcion', ''),
            data['precio'],
            data.get('categoria', 'General'),
            data.get('disponible', True)
        )
        conn.commit()
        return jsonify({'mensaje': 'Producto registrado'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/<int:producto_id>', methods=['PUT'])
def actualizar_producto(producto_id):
    """Solo admin. Actualiza un producto."""
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Productos SET nombre=?, descripcion=?, precio=?, categoria=?, disponible=? '
            'WHERE producto_id=?',
            data.get('nombre'),
            data.get('descripcion'),
            data.get('precio'),
            data.get('categoria'),
            data.get('disponible'),
            producto_id
        )
        conn.commit()
        return jsonify({'mensaje': 'Producto actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
