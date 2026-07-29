import psycopg

def get_connection():
    return psycopg.connect(
        "dbname=wordbomb user=postgres password=devpassword host=localhost port=5432"
    )