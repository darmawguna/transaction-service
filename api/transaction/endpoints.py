"""Routes for transactions module"""
import os
from flask import Blueprint, jsonify, request
from helper.db_helper import get_connection
from helper.form_validation import get_form_data
from datetime import datetime
transactions_endpoints = Blueprint('transactions', __name__)
from redpanda_helper import produce_event
from transaction_summary import calculate_user_summary
from redpanda_helper import send_user_summary

# Konstanta untuk format tanggal
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

@transactions_endpoints.route('/', methods=['GET'])
def read():
    """Endpoint untuk membaca daftar transaksi"""
    connection = None
    cursor = None
    try:
        # Membuat koneksi ke database
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Query untuk mendapatkan daftar transaksi
        select_query = "SELECT * FROM transaction"
        cursor.execute(select_query)
        results = cursor.fetchall()
        
        if not results:
            return jsonify({"message": "No transactions found", "datas": []}), 200

        # Mengembalikan respons dalam format JSON
        return jsonify({"message": "OK", "datas": results}), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching data: {str(e)}"}), 500
    finally:
        if cursor:  # Pastikan cursor telah didefinisikan
            cursor.close()
        if connection:  # Pastikan connection telah didefinisikan
            connection.close()

@transactions_endpoints.route('/create', methods=['POST'])
def create():
    """Endpoint untuk membuat transaksi baru"""
    # Validasi input dari form
    try:
        required = get_form_data(["status", "user_id", "amount", "transaction_date"])  
        user_id = required["user_id"]
        amount = float(required["amount"])  # Pastikan amount berupa float
        status = required["status"]
        transaction_date = required["transaction_date"]  # Tanggal transaksi
        description = request.form.get('description', '')  # Deskripsi opsional
        
        # Validasi transaction_date
        try:
            transaction_date = datetime.strptime(transaction_date, DATE_FORMAT)
        except ValueError:
            return jsonify({"message": f"Invalid date format. Use {DATE_FORMAT}"}), 400

        # Validasi nilai amount
        if amount <= 0:
            return jsonify({"message": "Amount must be greater than 0"}), 400

    except KeyError as e:
        return jsonify({"message": f"Missing required field: {str(e)}"}), 400

    # Memasukkan data ke database
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Query untuk memasukkan transaksi baru
        insert_query = """
        INSERT INTO transaction (user_id, amount, transaction_date, status, description)
        VALUES (%s, %s, %s, %s, %s)
        """
        request_insert = (user_id, amount, transaction_date, status, description)
        cursor.execute(insert_query, request_insert)
        connection.commit()
        new_id = cursor.lastrowid
        
        
        # Jika status success, hitung dan kirim summary ke Redpanda
        if status == "success":
            summary_data = calculate_user_summary(user_id)
            send_user_summary("user_summary", summary_data)


        return jsonify({
            "transaction_id": new_id,
            "user_id": user_id,
            "amount": amount,
            "transaction_date": transaction_date.strftime(DATE_FORMAT),
            "status": status,
            "description": description,
            "message": "Transaction successfully created"
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": f"Error inserting data: {str(e)}"}), 500

    finally:
        if cursor:  # Pastikan cursor telah didefinisikan
            cursor.close()
        if connection:  # Pastikan connection telah didefinisikan
            connection.close()

@transactions_endpoints.route('/update/<int:transaction_id>', methods=['PUT'])
def update(transaction_id):
    connection = None
    cursor = None
    connection = get_connection()
    cursor = connection.cursor()
        # Periksa apakah transaksi ada
    cursor.execute("SELECT user_id FROM transaction WHERE transaction_id = %s", (transaction_id,))
    result = cursor.fetchone()
    if not result:
        return jsonify({"message": "Transaction not found"}), 404

    # Dapatkan user_id dari hasil query
    user_id = result[0]
    
    """ Edit Data Transaksi"""
    try:
        required = get_form_data(["status"])
        status = required["status"]
        valid_statuses = ['pending', 'success', 'failed', 'canceled']
        if status not in valid_statuses:
            return jsonify({"message": f"Invalid status. Must be one of {valid_statuses}"}), 400

    except KeyError as e:
        return jsonify({"message": f"Missing required field: {str(e)}"}), 400
     # Memasukkan data ke database
    
    try:
        # Query untuk memasukkan transaksi baru
        insert_query = "UPDATE transaction SET status = %s WHERE transaction_id = %s"

        request_insert = ( status, transaction_id )
        cursor.execute(insert_query, request_insert)
        connection.commit()
        
        if status == "success":
            summary_data = calculate_user_summary(user_id)
            send_user_summary("user_summary", summary_data)
        return jsonify({"message": "Transaction updated successfully"}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": f"Error inserting data: {str(e)}"}), 500
    finally:
        if cursor:  # Pastikan cursor telah didefinisikan
            cursor.close()
        if connection:  # Pastikan connection telah didefinisikan
            connection.close()
        
@transactions_endpoints.route('/cancel/<int:transaction_id>', methods=['POST'])
def cancel_transaction(transaction_id):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)


        # Query untuk memasukkan transaksi baru
        insert_query =  "SELECT * FROM transaction WHERE transaction_id = %s"
        cursor.execute(insert_query, (transaction_id,))
        transaction = cursor.fetchone()
        
        #validasi transaksi 
        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404
        
         # Validasi status transaksi
        if transaction['status'] in ['completed', 'failed', 'canceled']:
            return jsonify({"message": f"Transaction cannot be canceled. Current status: {transaction['status']}"}), 400

                # Perbarui status transaksi menjadi canceled
        update_query = "UPDATE transaction SET status = %s WHERE transaction_id = %s"
        cursor.execute(update_query, ('canceled', transaction_id))
        connection.commit()
        
        return jsonify({
            "message": "Transaction successfully canceled",
            "transaction_id": transaction_id,
            "previous_status": transaction['status'],
            "new_status": "canceled"
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": f"Error inserting data: {str(e)}"}), 500
    finally:
        if cursor:  # Pastikan cursor telah didefinisikan
            cursor.close()
        if connection:  # Pastikan connection telah didefinisikan
            connection.close()
        
