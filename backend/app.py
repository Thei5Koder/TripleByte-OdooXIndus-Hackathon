from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

def get_db_connection():
    try:
        return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="root", 
            database="inventory_db"
        )
    except Error as e:
        print(f"DB Error: {e}")
        return None

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB Fail"}), 500
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
    # Receipts: Late (Ready status) and In Operations (Draft/Waiting)
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Receipt' AND status='Ready'")
        late_receipts = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Receipt' AND status IN ('Draft', 'Waiting')")
        op_receipts = cursor.fetchone()['count']
        
        # Deliveries: Similar logic for the second card
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Delivery' AND status='Ready'")
        late_deliveries = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Delivery' AND status IN ('Draft', 'Waiting')")
        op_deliveries = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Delivery' AND status='Ready'")
        late_deliveries = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Delivery' AND status IN ('Draft', 'Waiting')")
        op_deliveries = cursor.fetchone()['count']

        # NEW: Fetch 'remaining' (perhaps items that are 'Waiting' specifically)
        cursor.execute("SELECT COUNT(*) as count FROM Operations WHERE document_type='Delivery' AND status='Waiting'")
        rem_deliveries = cursor.fetchone()['count']

        return jsonify({
           "receipts": {"late": late_receipts, "in_ops": op_receipts},
        "deliveries": {
            "late": late_deliveries, 
            "in_ops": op_deliveries,
            "remaining": rem_deliveries  # This matches what api.js is looking for!
        }
        }), 200
    finally:
        conn.close()

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # [cite: 44-49]
        query = "INSERT INTO Products (name, sku, category, unit_of_measure) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (data['name'], data['sku'], data['category'], data['uom']))
        conn.commit()
        return jsonify({"message": "Product Added"}), 201
    finally:
        conn.close()

# --- SAVE NEW RECEIPT WITH PRODUCTS ---
@app.route('/api/receipts', methods=['POST'])
def save_full_receipt():
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Ensure these column names match what we just added to MySQL
        query_op = """
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status) 
            VALUES ('Receipt', %s, %s, %s)
        """
        cursor.execute(query_op, (data['vendor'], data['date'], data['status']))
        
        # ... (rest of your product logic)
        
        conn.commit()
        return jsonify({"message": "Receipt saved to MySQL!"}), 201
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()
@app.route('/api/receipts', methods=['GET'])
def get_receipts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Operations WHERE document_type='Receipt' ORDER BY operation_id DESC")
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)
if __name__ == '__main__':
    app.run(debug=True, port=5000)