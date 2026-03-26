from flask import Blueprint, jsonify, request
import pyodbc
from config import CONNECTION_STRING

reportes_bp = Blueprint('reportes', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

@reportes_bp.route('/clasificacion-clientes', methods=['GET'])
def clasificacion_clientes():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vw_clasificacion_clientes ORDER BY total_pedidos DESC')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/ranking-repartidores', methods=['GET'])
def ranking_repartidores():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vw_ranking_repartidores ORDER BY ranking')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/operaciones', methods=['GET'])
def operaciones_completas():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM vw_operaciones_completas ORDER BY fecha_pedido DESC')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/entregas-zona', methods=['GET'])
def entregas_zona():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('EXEC sp_reporte_entregas_zona')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/pivot-entregas-mes', methods=['GET'])
def pivot_entregas_mes():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('EXEC sp_pivot_entregas_mes')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/auditoria-pedidos', methods=['GET'])
def auditoria_pedidos():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Auditoria_Pedidos ORDER BY fecha DESC')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/log-errores', methods=['GET'])
def log_errores():
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Log_Errores ORDER BY fecha DESC')
        rows = cursor.fetchall()
        return jsonify([row_to_dict(cursor, r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/resumen', methods=['GET'])
def resumen():
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Pedidos")
        total_pedidos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE estado = 'Pendiente'")
        pedidos_pendientes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE estado = 'En ruta'")
        pedidos_en_ruta = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE estado = 'Entregado'")
        pedidos_entregados = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Clientes")
        total_clientes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Repartidores WHERE estado = 'Activo'")
        repartidores_activos = cursor.fetchone()[0]

        cursor.execute("SELECT ISNULL(SUM(monto),0) FROM Pagos")
        total_facturado = cursor.fetchone()[0]

        return jsonify({
            'total_pedidos':        total_pedidos,
            'pedidos_pendientes':   pedidos_pendientes,
            'pedidos_en_ruta':      pedidos_en_ruta,
            'pedidos_entregados':   pedidos_entregados,
            'total_clientes':       total_clientes,
            'repartidores_activos': repartidores_activos,
            'total_facturado':      float(total_facturado)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/resumen-repartidor/<int:repartidor_id>', methods=['GET'])
def resumen_repartidor(repartidor_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Entregas WHERE repartidor_id = ? AND estado = 'En transito'", repartidor_id)
        en_transito = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Entregas WHERE repartidor_id = ? AND estado = 'Entregado'", repartidor_id)
        entregadas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Entregas WHERE repartidor_id = ?", repartidor_id)
        total = cursor.fetchone()[0]

        cursor.execute("SELECT ranking FROM vw_ranking_repartidores WHERE repartidor_id = ?", repartidor_id)
        row = cursor.fetchone()
        ranking = row[0] if row else '-'

        cursor.execute(
            "SELECT TOP 5 e.entrega_id, p.direccion_entrega, e.estado, e.fecha_salida "
            "FROM Entregas e JOIN Pedidos p ON e.pedido_id = p.pedido_id "
            "WHERE e.repartidor_id = ? ORDER BY e.fecha_salida DESC",
            repartidor_id
        )
        recientes = [row_to_dict(cursor, r) for r in cursor.fetchall()]

        return jsonify({
            'en_transito':      en_transito,
            'entregadas':       entregadas,
            'total_entregas':   total,
            'ranking':          ranking,
            'recientes':        recientes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reportes_bp.route('/resumen-cliente/<int:cliente_id>', methods=['GET'])
def resumen_cliente(cliente_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'Pendiente'", cliente_id)
        pendientes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'En ruta'", cliente_id)
        en_ruta = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'Entregado'", cliente_id)
        entregados = cursor.fetchone()[0]

        cursor.execute("SELECT ISNULL(SUM(total),0) FROM Pedidos WHERE cliente_id = ?", cliente_id)
        total_gastado = cursor.fetchone()[0]

        cursor.execute(
            "SELECT TOP 5 pedido_id, direccion_entrega, estado, total, fecha_pedido "
            "FROM Pedidos WHERE cliente_id = ? ORDER BY fecha_pedido DESC",
            cliente_id
        )
        recientes = [row_to_dict(cursor, r) for r in cursor.fetchall()]

        return jsonify({
            'pendientes':    pendientes,
            'en_ruta':       en_ruta,
            'entregados':    entregados,
            'total_gastado': float(total_gastado),
            'recientes':     recientes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
