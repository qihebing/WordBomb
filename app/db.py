import os

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "dbname=wordbomb user=postgres password=devpassword host=localhost port=5432",
)


def get_connection():
    return psycopg.connect(DATABASE_URL)
