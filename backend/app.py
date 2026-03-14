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
        cursor.execute("""
                    SELECT COUNT(*) as count FROM Operations 
                    WHERE document_type='Receipt' 
                    AND status='Ready' 
                    AND scheduled_date < CURDATE()
                """)
        late_receipts = cursor.fetchone()['count']
                
                # 2. IN OPERATIONS: Anything still being processed (Draft/Waiting) 
                # OR 'Ready' items that are for TODAY or the FUTURE
        cursor.execute("""
                    SELECT COUNT(*) as count FROM Operations 
                    WHERE document_type='Receipt' 
                    AND (status IN ('Draft', 'Waiting') OR (status='Ready' AND scheduled_date >= CURDATE()))
                """)
        op_receipts = cursor.fetchone()['count']
                
                # 3. DELIVERIES: Apply the same smart date logic
        cursor.execute("""
                    SELECT COUNT(*) as count FROM Operations 
                    WHERE document_type='Delivery' AND status='Ready' AND scheduled_date < CURDATE()
                """)
        late_deliveries = cursor.fetchone()['count']
                
        cursor.execute("""
                    SELECT COUNT(*) as count FROM Operations 
                    WHERE document_type='Delivery' AND (status IN ('Draft', 'Waiting') OR (status='Ready' AND scheduled_date >= CURDATE()))
                """)
        op_deliveries = cursor.fetchone()['count']

                # 4. REMAINING: Keep your existing logic for this
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
        # 1. Insert into Operations table 
        query_op = """
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status) 
            VALUES ('Receipt', %s, %s, %s)
        """
        cursor.execute(query_op, (data['vendor'], data['date'], data['status']))
        operation_id = cursor.lastrowid

        # 2. Insert into operation_items (Mapping products to this receipt) [cite: 54-55]
        for item in data['products']:
            # Find product_id by name first (simplified for hackathon)
            cursor.execute("SELECT product_id FROM products WHERE name = %s", (item['name'],))
            prod = cursor.fetchone()
            if prod:
                query_item = "INSERT INTO operation_items (operation_id, product_id, quantity) VALUES (%s, %s, %s)"
                cursor.execute(query_item, (operation_id, prod[0], item['qty']))

        conn.commit()
        return jsonify({"message": "Receipt draft saved!", "id": operation_id}), 201
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()

# --- VALIDATE OPERATION (The "Stock Multiplier") ---
@app.route('/api/operations/<int:op_id>/validate', methods=['PUT'])
def validate_operation(op_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # 1. Get the items in this operation [cite: 54-55]
        cursor.execute("SELECT product_id, quantity FROM operation_items WHERE operation_id = %s", (op_id,))
        items = cursor.fetchall()
        
        # 2. Update status to 'Done' [cite: 22, 56]
        cursor.execute("UPDATE Operations SET status = 'Done' WHERE operation_id = %s", (op_id,))
        
        for item in items:
            # 3. Increase Stock in Inventory table 
            cursor.execute("""
                UPDATE inventory SET quantity = quantity + %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))
            
            # 4. Log the movement in the Stock Ledger 
            cursor.execute("""
                INSERT INTO stock_ledger (product_id, operation_id, quantity_change, transaction_type)
                VALUES (%s, %s, %s, 'Receipt')
            """, (item['product_id'], op_id, item['quantity']))

        conn.commit()
        return jsonify({"message": "Stock updated successfully!"}), 200
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
@app.route('/api/deliveries', methods=['POST'])
def save_delivery():
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Insert main operation [cite: 33, 61]
        query = """
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status) 
            VALUES ('Delivery', %s, %s, %s)
        """
        cursor.execute(query, (data['customer'], data['date'], data['status']))
        op_id = cursor.lastrowid
        
        # Save product items to link them [cite: 62-63]
        for item in data['products']:
            cursor.execute("SELECT product_id FROM products WHERE name = %s", (item['name'],))
            prod = cursor.fetchone()
            if prod:
                cursor.execute("INSERT INTO operation_items (operation_id, product_id, quantity) VALUES (%s, %s, %s)", 
                               (op_id, prod[0], item['qty']))
        
        conn.commit()
        return jsonify({"message": "Delivery created"}), 201
    finally:
        conn.close()

# --- FETCH DELIVERIES ---
@app.route('/api/deliveries', methods=['GET'])
def get_deliveries():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Operations WHERE document_type='Delivery' ORDER BY operation_id DESC")
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)
if __name__ == '__main__':
    app.run(debug=True, port=5000)