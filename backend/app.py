from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

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
    # 1. Grab the User ID from the secureFetch header
    user_id = request.headers.get('X-User-ID')
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 2. Save Receipt Header WITH user_id
        query_op = """
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status, user_id) 
            VALUES ('Receipt', %s, %s, %s, %s)
        """
        cursor.execute(query_op, (data.get('vendor'), data.get('date'), data.get('status'), user_id))
        op_id = cursor.lastrowid

        for item in data.get('products', []):
            clean_name = item['name'].strip()
            
            # 3. Search for product belonging to THIS user
            cursor.execute("SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s) AND user_id = %s", (clean_name, user_id))
            existing_product = cursor.fetchone()

            if existing_product:
                product_id = existing_product['product_id']
            else:
                # 4. Create NEW product for THIS user
                category = item.get('category', 'General')
                sku = f"SKU-{clean_name[:3].upper()}-{op_id}"
                
                query_prod = "INSERT INTO products (name, category, sku, unit_of_measure, user_id) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query_prod, (clean_name, category, sku, 'Units', user_id))
                product_id = cursor.lastrowid
                
                # 5. Initialize inventory record for THIS user
                cursor.execute("INSERT INTO inventory (product_id, location_id, quantity) VALUES (%s, 1, 0)", (product_id,))

            # Link item to the operation
            cursor.execute(
                "INSERT INTO operation_items (operation_id, product_id, quantity) VALUES (%s, %s, %s)",
                (op_id, product_id, item['qty'])
            )

        conn.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- VALIDATE OPERATION (The "Stock Multiplier") ---

@app.route('/api/operations/<int:op_id>/validate', methods=['PUT'])
def validate_operation(op_id):
    # 1. Grab the User ID from the secureFetch header
    user_id = request.headers.get('X-User-ID')
    if not user_id: 
        return jsonify({"error": "Unauthorized: No User ID"}), 401

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 2. Verify ownership
        cursor.execute("SELECT * FROM Operations WHERE operation_id = %s", (op_id,))
        op = cursor.fetchone()
        
        if not op:
            return jsonify({"error": "Operation not found"}), 404
            
        # If operation has no user_id, current user claims it
        if op['user_id'] is None:
            cursor.execute("UPDATE Operations SET user_id = %s WHERE operation_id = %s", (user_id, op_id))
        elif str(op['user_id']) != str(user_id):
            return jsonify({"error": "Ownership mismatch"}), 403

        # 3. Process Stock & Log History
        cursor.execute("SELECT product_id, quantity FROM operation_items WHERE operation_id = %s", (op_id,))
        items = cursor.fetchall()
        
        for item in items:
            modifier = item['quantity'] if op['document_type'] == 'Receipt' else -item['quantity']
            
            # Update Inventory (Ensures product exists in inventory table)
            cursor.execute("""
                INSERT INTO inventory (product_id, location_id, quantity) 
                VALUES (%s, 1, %s) 
                ON DUPLICATE KEY UPDATE quantity = quantity + %s
            """, (item['product_id'], modifier, modifier))

            # --- THE FIX: ADD TO MOVE HISTORY LEDGER ---
            from_loc = None if op['document_type'] == 'Receipt' else 1
            to_loc = 1 if op['document_type'] == 'Receipt' else None

            cursor.execute("""
                INSERT INTO stock_ledger (product_id, operation_id, quantity_moved, from_location_id, to_location_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (item['product_id'], op_id, item['quantity'], from_loc, to_loc))

        # 4. Mark as Done
        cursor.execute("UPDATE Operations SET status = 'Done' WHERE operation_id = %s", (op_id,))
        conn.commit()
        return jsonify({"message": "Success! Stock updated and logged."}), 200

    except Exception as e:
        print(f"Validation Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
@app.route('/api/receipts', methods=['GET'])
def get_receipts():
    user_id = request.headers.get('X-User-ID') #
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Added user_id filter
    cursor.execute("SELECT * FROM Operations WHERE document_type='Receipt' AND user_id = %s ORDER BY operation_id DESC", (user_id,))
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)

@app.route('/api/deliveries', methods=['GET'])
def get_deliveries():
    user_id = request.headers.get('X-User-ID') #
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Added user_id filter
    cursor.execute("SELECT * FROM Operations WHERE document_type='Delivery' AND user_id = %s ORDER BY operation_id DESC", (user_id,))
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)

@app.route('/api/deliveries', methods=['POST'])
def save_delivery():
    # 1. Grab the User ID from the secureFetch header
    user_id = request.headers.get('X-User-ID')
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 2. Save Delivery Header WITH user_id
        query_op = """
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status, user_id) 
            VALUES ('Delivery', %s, %s, %s, %s)
        """
        cursor.execute(query_op, (data['customer'], data['date'], data['status'], user_id))
        op_id = cursor.lastrowid
        
        for item in data['products']:
            clean_name = item['name'].strip()
            
            # 3. Match product belonging to THIS user ONLY
            cursor.execute("SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s) AND user_id = %s", (clean_name, user_id))
            prod = cursor.fetchone()
            
            if prod:
                cursor.execute("INSERT INTO operation_items (operation_id, product_id, quantity) VALUES (%s, %s, %s)", 
                               (op_id, prod['product_id'], item['qty']))
            else:
                # Optional: Handle error if product doesn't exist for this user
                print(f"Product {clean_name} not found for user {user_id}")

        conn.commit()
        return jsonify({"message": "Delivery created"}), 201
    except Exception as e:
        print(f"Delivery Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
@app.route('/api/product-inventory', methods=['GET'])
def get_product_inventory():
    user_id = request.headers.get('X-User-ID') # The security handshake
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # This query joins products with their stock levels and warehouse names
        query = """
            SELECT p.product_id, p.name, p.category, p.sku, 
                   COALESCE(i.quantity, 0) as quantity, 
                   COALESCE(l.name, 'Main Warehouse') as warehouse
            FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id
            LEFT JOIN locations l ON i.location_id = l.location_id
            WHERE p.user_id = %s
        """
        cursor.execute(query, (user_id,))
        return jsonify(cursor.fetchall()), 200
    finally:
        conn.close()

# --- Updated Warehouse Route ---
@app.route('/api/locations', methods=['POST'])
def add_location():
    data = request.json
    user_id = request.headers.get('X-User-ID')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Ensure the new location is linked to the logged-in user
        cursor.execute(
            "INSERT INTO locations (name, address, capacity, user_id) VALUES (%s, %s, %s, %s)",
            (data['name'], data['address'], data['capacity'], user_id)
        )
        conn.commit()
        return jsonify({"message": "Location added!"}), 201
    finally:
        conn.close()
@app.route('/api/move-history', methods=['GET'])
def get_move_history():
    user_id = request.headers.get('X-User-ID') # The SaaS Handshake
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # Added WHERE p.user_id = %s to filter history by the owner
        query = """
            SELECT sl.ledger_id, p.name as product_name, sl.quantity_moved, 
                   sl.from_location_id, sl.to_location_id, sl.timestamp, sl.operation_id
            FROM stock_ledger sl
            JOIN products p ON sl.product_id = p.product_id
            WHERE p.user_id = %s
            ORDER BY sl.timestamp DESC
        """
        cursor.execute(query, (user_id,))
        return jsonify(cursor.fetchall()), 200
    finally:
        conn.close()
# --- INTERNAL STOCK TRANSFER ---
@app.route('/api/transfer', methods=['POST'])
def save_transfer():
    user_id = request.headers.get('X-User-ID')
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Operations (document_type, partner_name, scheduled_date, status, user_id) 
            VALUES ('Transfer', 'Internal Move', CURDATE(), 'Done', %s)
        """, (user_id,))
        op_id = cursor.lastrowid

        for item in data['products']:
            prod_id = item['product_id']
            qty = item['qty']
            source_loc = data['source_location']
            dest_loc = data['dest_location']

            # 1. Update Inventory Logic
            cursor.execute("""
                INSERT INTO inventory (product_id, location_id, quantity) 
                VALUES (%s, %s, %s) 
                ON DUPLICATE KEY UPDATE quantity = quantity + %s
            """, (prod_id, dest_loc, qty, qty))

            cursor.execute("""
                UPDATE inventory SET quantity = quantity - %s 
                WHERE product_id = %s AND location_id = %s
            """, (qty, prod_id, source_loc))

            # 2. THE MISSING PIECE: Log the move into the Ledger
            cursor.execute("""
                INSERT INTO stock_ledger (product_id, operation_id, quantity_moved, from_location_id, to_location_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (prod_id, op_id, qty, source_loc, dest_loc))

        conn.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        print(f"Transfer Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
@app.route('/api/locations', methods=['GET'])
def get_locations():
    user_id = request.headers.get('X-User-ID') # The SaaS Handshake
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # Only show warehouses belonging to YOU
        cursor.execute("SELECT * FROM locations WHERE user_id = %s", (user_id,))
        return jsonify(cursor.fetchall()), 200
    finally:
        conn.close()

# 3. UPDATE an existing warehouse
@app.route('/api/locations/<int:loc_id>', methods=['PUT'])
def update_location(loc_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    # Note: Address is kept read-only per your HTML design
    cursor.execute(
        "UPDATE locations SET name = %s, capacity = %s WHERE location_id = %s",
        (data['name'], data['capacity'], loc_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Location updated!"}), 200

# 4. DELETE a warehouse
@app.route('/api/locations/<int:loc_id>', methods=['DELETE'])
def delete_location(loc_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM locations WHERE location_id = %s", (loc_id,))
        conn.commit()
        return jsonify({"message": "Location deleted!"}), 200
    except Exception as e:
        # Prevents crashing if the warehouse has items currently in it!
        return jsonify({"error": "Cannot delete a warehouse that contains active inventory."}), 400
    finally:
        conn.close()
# 1. LOGIN ROUTE
# --- USER AUTHENTICATION & PROFILE ---

# 1. LOGIN ROUTE
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    
    # 1. DEFINE THE VARIABLE: Pull 'email' from the frontend data
    email = data.get('email') 
    password = data.get('password')

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 2. USE THE VARIABLE: Search using the defined 'email' variable
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        # 3. VERIFY: Check if user exists and password is correct
        if user and check_password_hash(user['password_hash'], password):
            return jsonify({
                "message": "Login successful",
                "user": {
                    "id": user['user_id'],
                    "full_name": user['full_name'], 
                    "email": user['email'],
                    "role": user['role']
                }
            }), 200
        else:
            return jsonify({"error": "Invalid email or password"}), 401
    finally:
        conn.close()

# 2. GET PROFILE ROUTE
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, username, email, role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            return jsonify(user), 200
        return jsonify({"error": "User not found"}), 404
    finally:
        conn.close()
if __name__ == '__main__':
    app.run(debug=True, port=5000)