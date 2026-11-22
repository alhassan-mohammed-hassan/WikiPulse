from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.hooks.base import BaseHook

import psycopg2


def refresh_gold_tables():
    conn_config = BaseHook.get_connection("wikipulse_postgres")

    conn = psycopg2.connect(
        host=conn_config.host,
        port=conn_config.port,
        dbname=conn_config.schema,
        user=conn_config.login,
        password=conn_config.password,
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT gold.refresh_all();")

        conn.commit()
        print("Gold tables refreshed successfully!")

    finally:
        conn.close()


default_args = {
    "owner": "wikipulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="wikipulse_gold_refresh",
    default_args=default_args,
    description="Refresh WikiPulse Gold analytical tables",
    start_date=datetime(2026, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    tags=["wikipulse", "gold", "analytics"],
) as dag:

    refresh_gold = PythonOperator(
        task_id="refresh_gold_tables",
        python_callable=refresh_gold_tables,
    )