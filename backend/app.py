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
    data = request.json
    print(f"DEBUG DATA RECEIVED: {data}") # Check your terminal to see if 'category' is here
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Save Receipt Header
        query_op = "INSERT INTO Operations (document_type, partner_name, scheduled_date, status) VALUES ('Receipt', %s, %s, %s)"
        cursor.execute(query_op, (data.get('vendor'), data.get('date'), data.get('status')))
        op_id = cursor.lastrowid

        for item in data.get('products', []):
            # 1. Clean the input (remove accidental spaces)
            clean_name = item['name'].strip()
            
            # 2. Search case-insensitively using LOWER()
            cursor.execute("SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s)", (clean_name,))
            existing_product = cursor.fetchone()

            if existing_product:
                product_id = existing_product['product_id']
            else:
                # Create NEW product if it truly doesn't exist
                category = item.get('category', 'General')
                sku = f"SKU-{clean_name[:3].upper()}-{op_id}"
                
                query_prod = "INSERT INTO products (name, category, sku, unit_of_measure) VALUES (%s, %s, %s, %s)"
                cursor.execute(query_prod, (clean_name, category, sku, 'Units'))
                product_id = cursor.lastrowid
                
                # Initialize inventory at 0
                cursor.execute("INSERT INTO inventory (product_id, location_id, quantity) VALUES (%s, 1, 0)", (product_id,))

            # 3. Link to Operation using the confirmed product_id
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Identify Document Type
        cursor.execute("SELECT document_type FROM Operations WHERE operation_id = %s", (op_id,))
        op_type = cursor.fetchone()['document_type']

        # 2. Get the items
        cursor.execute("SELECT product_id, quantity FROM operation_items WHERE operation_id = %s", (op_id,))
        items = cursor.fetchall()
        
        # 3. Mark as 'Done'
        cursor.execute("UPDATE Operations SET status = 'Done' WHERE operation_id = %s", (op_id,))
        
        for item in items:
            # Set math & locations based on your specific ledger design
            if op_type == 'Receipt':
                math_modifier = item['quantity']
                from_loc = None  # Coming from outside vendor
                to_loc = 1       # Going to Main Warehouse
            else: # Delivery
                math_modifier = -item['quantity']
                from_loc = 1     # Coming from Main Warehouse
                to_loc = None    # Going to outside customer
            
            # Update physical stock in inventory table
            cursor.execute("""
                UPDATE inventory SET quantity = quantity + %s 
                WHERE product_id = %s AND location_id = 1
            """, (math_modifier, item['product_id']))
            
            # 4. Log in the Stock Ledger using YOUR exact columns!
            cursor.execute("""
                INSERT INTO stock_ledger (product_id, operation_id, quantity_moved, from_location_id, to_location_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (item['product_id'], op_id, item['quantity'], from_loc, to_loc))

        conn.commit()
        return jsonify({"message": f"{op_type} validated successfully!"}), 200
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500
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
            clean_name = item['name'].strip() # Remove invisible spaces
            
            # Match case-insensitively!
            cursor.execute("SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s)", (clean_name,))
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
@app.route('/api/product-inventory', methods=['GET'])
def get_product_inventory():
    user_id = request.headers.get('X-User-ID') # Capture the ID from the secureFetch
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # Filter all queries by user_id
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch ledger entries using your actual columns
        query = """
            SELECT sl.ledger_id, p.name as product_name, sl.quantity_moved, 
                   sl.from_location_id, sl.to_location_id, sl.timestamp, sl.operation_id
            FROM stock_ledger sl
            JOIN products p ON sl.product_id = p.product_id
            ORDER BY sl.timestamp DESC
        """
        cursor.execute(query)
        history = cursor.fetchall()
        return jsonify(history), 200
    finally:
        conn.close()

# --- INTERNAL STOCK TRANSFER ---
@app.route('/api/transfer', methods=['POST'])
def save_transfer():
    data = request.json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Create the Operation Record
        query_op = "INSERT INTO Operations (document_type, partner_name, scheduled_date, status) VALUES ('Transfer', 'Internal Move', CURDATE(), 'Done')"
        cursor.execute(query_op)
        op_id = cursor.lastrowid
        
        source_loc = data['source_location']
        dest_loc = data['dest_location']

        for item in data['products']:
            product_id = item['product_id']
            qty = int(item['qty'])

            # 2. Subtract from Source Warehouse
            cursor.execute("""
                UPDATE inventory SET quantity = quantity - %s 
                WHERE product_id = %s AND location_id = %s
            """, (qty, product_id, source_loc))

            # 3. Add to Destination Warehouse
            # First, check if the product already has a row in the destination warehouse
            cursor.execute("SELECT * FROM inventory WHERE product_id = %s AND location_id = %s", (product_id, dest_loc))
            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE inventory SET quantity = quantity + %s 
                    WHERE product_id = %s AND location_id = %s
                """, (qty, product_id, dest_loc))
            else:
                cursor.execute("""
                    INSERT INTO inventory (product_id, location_id, quantity) 
                    VALUES (%s, %s, %s)
                """, (product_id, dest_loc, qty))

            # 4. Log in the Stock Ledger (Both locations filled!)
            cursor.execute("""
                INSERT INTO stock_ledger (product_id, operation_id, quantity_moved, from_location_id, to_location_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_id, op_id, qty, source_loc, dest_loc))
            
            # 5. Link to operation_items
            cursor.execute("INSERT INTO operation_items (operation_id, product_id, quantity) VALUES (%s, %s, %s)", 
                           (op_id, product_id, qty))

        conn.commit()
        return jsonify({"message": "Transfer successful!"}), 201
    except Exception as e:
        print(f"Transfer Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
@app.route('/api/locations', methods=['GET'])
def get_locations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM locations")
    results = cursor.fetchall()
    conn.close()
    return jsonify(results), 200

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