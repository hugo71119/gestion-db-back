from flask import Blueprint, request, jsonify, session
import pyodbc
from config import CONNECTION_STRING

pedidos_bp = Blueprint('pedidos', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@pedidos_bp.route('/', methods=['GET'])
def get_pedidos():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        estado = request.args.get('estado')
        cliente_session = session.get('cliente_id')

        if cliente_session:
            if estado:
                cursor.execute(
                    'SELECT p.*, c.nombre_completo AS cliente '
                    'FROM Pedidos p JOIN Clientes c ON p.cliente_id = c.cliente_id '
                    'WHERE p.cliente_id = ? AND p.estado = ? ORDER BY p.fecha_pedido DESC',
                    cliente_session, estado
                )
            else:
                cursor.execute(
                    'SELECT p.*, c.nombre_completo AS cliente '
                    'FROM Pedidos p JOIN Clientes c ON p.cliente_id = c.cliente_id '
                    'WHERE p.cliente_id = ? ORDER BY p.fecha_pedido DESC',
                    cliente_session
                )
        elif estado:
            cursor.execute(
                'SELECT p.*, c.nombre_completo AS cliente '
                'FROM Pedidos p JOIN Clientes c ON p.cliente_id = c.cliente_id '
                'WHERE p.estado = ? ORDER BY p.fecha_pedido DESC',
                estado
            )
        else:
            cursor.execute(
                'SELECT p.*, c.nombre_completo AS cliente '
                'FROM Pedidos p JOIN Clientes c ON p.cliente_id = c.cliente_id '
                'ORDER BY p.fecha_pedido DESC'
            )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def get_pedido(pedido_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT p.*, c.nombre_completo AS cliente '
            'FROM Pedidos p JOIN Clientes c ON p.cliente_id = c.cliente_id '
            'WHERE p.pedido_id = ?',
            pedido_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Pedido no encontrado'}), 404

        cliente_session = session.get('cliente_id')
        if cliente_session and row_to_dict(cursor, row).get('cliente_id') != cliente_session:
            return jsonify({'error': 'No autorizado'}), 403

        pedido = row_to_dict(cursor, row)

        cursor.execute(
            'SELECT * FROM Detalle_Pedidos WHERE pedido_id = ?', pedido_id
        )
        detalles = [row_to_dict(cursor, r) for r in cursor.fetchall()]
        pedido['detalles'] = detalles

        cursor.execute(
            'SELECT e.entrega_id, e.estado AS estado_entrega, e.fecha_salida, e.fecha_entrega, '
            'r.repartidor_id, r.nombre_completo AS repartidor_nombre, r.telefono AS repartidor_telefono, '
            'v.placa AS vehiculo_placa '
            'FROM Entregas e '
            'JOIN Repartidores r ON e.repartidor_id = r.repartidor_id '
            'JOIN Vehiculos v ON e.vehiculo_id = v.vehiculo_id '
            'WHERE e.pedido_id = ?',
            pedido_id
        )
        entrega_row = cursor.fetchone()
        if entrega_row:
            pedido['entrega'] = row_to_dict(cursor, entrega_row)

        return jsonify(pedido)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pedidos_bp.route('/', methods=['POST'])
def crear_pedido():
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'EXEC sp_generar_pedido ?, ?',
            data['cliente_id'],
            data['direccion_entrega']
        )
        row = None
        while True:
            if cursor.description is not None:
                row = cursor.fetchone()
                break
            if not cursor.nextset():
                break
        pedido_id = row[0] if row else None

        if pedido_id and data.get('detalles'):
            for det in data['detalles']:
                cursor.execute(
                    'INSERT INTO Detalle_Pedidos (pedido_id, producto, cantidad, precio_unitario) VALUES (?,?,?,?)',
                    pedido_id,
                    det['producto'],
                    det['cantidad'],
                    det['precio_unitario']
                )
            cursor.execute(
                'UPDATE Pedidos SET total = (SELECT SUM(subtotal) FROM Detalle_Pedidos WHERE pedido_id = ?) WHERE pedido_id = ?',
                pedido_id, pedido_id
            )

        conn.commit()
        return jsonify({'mensaje': 'Pedido creado', 'pedido_id': pedido_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pedidos_bp.route('/<int:pedido_id>/estado', methods=['PUT'])
def actualizar_estado(pedido_id):
    data  = request.get_json()
    estado = data.get('estado')
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Pedidos SET estado = ? WHERE pedido_id = ?',
            estado, pedido_id
        )
        conn.commit()
        return jsonify({'mensaje': 'Estado actualizado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pedidos_bp.route('/<int:pedido_id>/asignar', methods=['POST'])
def asignar_repartidor(pedido_id):
    data         = request.get_json() or {}
    repartidor_id = data.get('repartidor_id')
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        if repartidor_id:
            vehiculo_id = data.get('vehiculo_id')
            if not vehiculo_id:
                return jsonify({'error': 'Debe seleccionar un vehículo'}), 400

            cursor.execute("SELECT placa FROM Vehiculos WHERE vehiculo_id = ? AND estado = 'Disponible'", vehiculo_id)
            veh = cursor.fetchone()
            if not veh:
                return jsonify({'error': 'El vehículo seleccionado no está disponible'}), 400
            placa = veh[0]

            cursor.execute('SELECT NEXT VALUE FOR seq_folio_entregas')
            folio = 'ENT-' + str(cursor.fetchone()[0])

            cursor.execute(
                "INSERT INTO Entregas (pedido_id, repartidor_id, vehiculo_id, estado, fecha_salida) "
                "VALUES (?,?,?,'En transito',GETDATE())",
                pedido_id, repartidor_id, vehiculo_id
            )
            cursor.execute("UPDATE Pedidos      SET estado = 'En ruta'   WHERE pedido_id     = ?", pedido_id)
            cursor.execute("UPDATE Repartidores SET estado = 'Inactivo'  WHERE repartidor_id = ?", repartidor_id)
            cursor.execute("UPDATE Vehiculos    SET estado = 'En uso'    WHERE vehiculo_id   = ?", vehiculo_id)

            cursor.execute('SELECT nombre_completo FROM Repartidores WHERE repartidor_id = ?', repartidor_id)
            nombre = cursor.fetchone()[0]
            conn.commit()
            return jsonify({'repartidor_asignado': nombre, 'vehiculo_asignado': placa, 'folio_entrega': folio})

        else:
            cursor.execute('EXEC sp_asignar_repartidor ?', pedido_id)
            row = None
            while True:
                if cursor.description is not None:
                    row = cursor.fetchone()
                    break
                if not cursor.nextset():
                    break
            conn.commit()
            if row:
                return jsonify({'repartidor_asignado': row[0], 'vehiculo_asignado': row[1], 'folio_entrega': row[2]})
            return jsonify({'error': 'No se pudo asignar'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pedidos_bp.route('/cliente/<int:cliente_id>', methods=['GET'])
def pedidos_por_cliente(cliente_id):
    cliente_session = session.get('cliente_id')
    if cliente_session and cliente_session != cliente_id:
        return jsonify({'error': 'No autorizado'}), 403

    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM Pedidos WHERE cliente_id = ? ORDER BY fecha_pedido DESC',
            cliente_id
        )
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
