import os
from flask import Blueprint, jsonify, request
from flasgger import  swag_from
from helper.db_helper import get_connection
from helper.form_validation import get_form_data
transactions_endpoints = Blueprint('transactions', __name__)
from helper.transaction_summary import calculate_user_summary
from helper.redpanda_helper import send_user_summary
import requests
import msgpack


@transactions_endpoints.route('/', methods=['GET'])
@swag_from('./doc/get_data.yml')
def read():
    """Endpoint untuk membaca daftar transaksi"""
    connection = None
    cursor = None
    try:
        
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        
        select_query = "SELECT * FROM transaction"
        cursor.execute(select_query)
        results = cursor.fetchall()
        
        if not results:
            return jsonify({"message": "No transactions found", "datas": []}), 200

        return jsonify({"message": "OK", "datas": results}), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching data: {str(e)}"}), 500
    finally:
        if cursor:  
            cursor.close()
        if connection: 
            connection.close()

@transactions_endpoints.route('/create', methods=['POST'])
@swag_from('./doc/create_data.yml')
def create():
    """Endpoint untuk membuat transaksi baru"""
    
    try:
        required = get_form_data(["status", "user_id", "amount"])  
        user_id = required["user_id"]
        amount = float(required["amount"])  # Pastikan amount berupa float
        status = required["status"]

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
        cursor = connection.cursor(dictionary=True)

        
        insert_query = """
        INSERT INTO transaction (user_id, amount, status)
        VALUES (%s, %s, %s)
        """
        request_insert = (user_id, amount, status)
        cursor.execute(insert_query, request_insert)
        connection.commit()
        new_id = cursor.lastrowid
        
        
        if status == "success":
            summary_data = calculate_user_summary(user_id)
            print(summary_data)
            send_user_summary("user_summary", summary_data)

        return jsonify({
            "transaction_id": new_id,
            "user_id": user_id,
            "amount": amount,
            "status": status,
            "message": "Transaction successfully created"
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": f"Error inserting data: {str(e)}"}), 500

    finally:
        if cursor:  
            cursor.close()
        if connection:
            connection.close()

@transactions_endpoints.route('/update/<int:transaction_id>', methods=['PUT'])
@swag_from('./doc/edit_data.yml')
def update(transaction_id):
    """Endpoint untuk memperbarui transaksi"""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        
        cursor.execute("SELECT status, user_id FROM transaction WHERE transaction_id = %s", (transaction_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"message": "Transaction not found"}), 404

        
        if result['status'] in ['success', 'canceled']:
            return jsonify({"message": f"Transaction cannot be updated. Current status: {result['status']}"}), 400

        
        user_id = result['user_id']
        
        
        required = get_form_data(["status"])
        status = required["status"]
        valid_statuses = ['pending', 'success', 'failed', 'canceled']
        if status not in valid_statuses:
            return jsonify({"message": f"Invalid status. Must be one of {valid_statuses}"}), 400

        
        update_query = "UPDATE transaction SET status = %s WHERE transaction_id = %s"
        request_update = (status, transaction_id)
        cursor.execute(update_query, request_update)
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
        if cursor: 
            cursor.close()
        if connection:  
            connection.close()

@transactions_endpoints.route('/cancel/<int:transaction_id>', methods=['POST'])
@swag_from('./doc/cancel.yml')
def cancel_transaction(transaction_id):
    """Endpoint untuk membatalkan transaksi"""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        
        cursor.execute("SELECT status FROM transaction WHERE transaction_id = %s", (transaction_id,))
        transaction = cursor.fetchone()

        
        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404
        
       
        if transaction['status'] not in ['pending', 'failed']:
            return jsonify({"message": f"Transaction cannot be canceled. Current status: {transaction['status']}"}), 400

        
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
        if cursor:  
            cursor.close()
        if connection:  
            connection.close()


# TODO buat fungsi yang akan mengirimkan data transaction summary ke user-service
@transactions_endpoints.route('/get-summary-transaction/<int:user_id>', methods=['GET'])
@swag_from('./doc/get_transaction_summary.yml')
def get_summary_transaction(user_id):
    """Endpoint untuk mengirimkan summary transaksi"""
    url = f"http://127.0.0.1:5001/api/users/validate-user/{user_id}"  
    try:
        response = requests.get(url)  
        response.raise_for_status()  
        data = response.json()  
          
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    if data.get("message") == "true" :
        summary_data = calculate_user_summary(user_id)
        packed_data = msgpack.packb(summary_data)
        return packed_data, 200, {'Content-Type': 'application/msgpack'}
    else : 
        return jsonify({"message": "user not found"})
        