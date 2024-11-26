from helper.db_helper import get_connection

def calculate_user_summary(user_id) : 
    """
    Fungsi untuk menghitung summary transaksi berdasarkan user_id.
    """
    connection = None
    cursor = None
    try: 
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
                # Query untuk menghitung total amount, jumlah transaksi, dan tanggal transaksi terakhir
        query = """
        SELECT 
            user_id,
            COUNT(*) AS amount_transaction,
            SUM(amount) AS total_amount,
            MAX(transaction_date) AS last_date_transaction
        FROM transaction
        WHERE user_id = %s AND status = 'success'
        GROUP BY user_id
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return {
                "user_id": user_id,
                "amount_transaction": 0,
                "total_amount": 0.0,
                "last_date_transaction": None
            }

        return result
    except Exception as e:
        raise Exception(f"Error calculating user summary: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()