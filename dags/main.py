from airflow import DAG
from datetime import datetime, timedelta
import time
from airflow.providers.common.sql.sensors.sql import SqlSensor
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
import random


prefix = "SerhiiB"
CONNECTION_NAME = f"{prefix}_mysql"
pick_medal_id = "pick_medal"
pick_medal_task_id = "pick_medal_task"
gold_medal = "Gold"
silver_medal = "Silver"
bronze_medal = "Bronze"

default_args = {
    "owner": "airflow",
    "retries": 1,
}


def get_medal():
    medal = random.choice([bronze_medal, silver_medal, gold_medal])
    return medal


def pick_medal_task_func(ti):
    medal = ti.xcom_pull(task_ids=pick_medal_id)
    return f"count_{medal}"


def generate_delay():
    time.sleep(random.randint(5, 45))

def count_query(medal_type):
    return f"""
        INSERT INTO medals (medal_type, count, created_at)
        SELECT '{medal_type}', COUNT(*), NOW()
        FROM olympic_dataset.athlete_event_results
        WHERE medal = '{medal_type}';
    """

with DAG(
    f"{prefix}_hw_07",
    default_args=default_args,
    schedule_interval=None, 
    catchup=False,
    tags=[prefix],
) as dag:

    create_table = MySqlOperator(
        task_id="create_table",
        mysql_conn_id=CONNECTION_NAME,
        sql=f"""
        CREATE TABLE IF NOT EXISTS medals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            medal_type VARCHAR(255) NOT NULL,
            count INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        dag=dag,
    )

    pick_medal = PythonOperator(
        task_id=pick_medal_id,
        python_callable=get_medal,
    )

    pick_medal_task = BranchPythonOperator(
        task_id=pick_medal_task_id,
        python_callable=pick_medal_task_func,
    )

    count_Bronze = MySqlOperator(
        task_id=f"count_{bronze_medal}",
        mysql_conn_id=CONNECTION_NAME,
        sql=count_query(bronze_medal),
    )

    count_Silver = MySqlOperator(
        task_id=f"count_{silver_medal}",
        mysql_conn_id=CONNECTION_NAME,
        sql=count_query(silver_medal),
    )

    count_Gold = MySqlOperator(
        task_id=f"count_{gold_medal}",
        mysql_conn_id=CONNECTION_NAME,
        sql=count_query(gold_medal),
    )

    generate_delay_task = PythonOperator(
        task_id="generate_delay",
        python_callable=generate_delay,
        trigger_rule="one_success",
    )

    check_for_correctness = SqlSensor(
        task_id="check_for_correctness",
        conn_id=CONNECTION_NAME,
        sql="""
        SELECT 1 FROM medals
        WHERE TIMESTAMPDIFF(SECOND, created_at, NOW()) <= 30
        ORDER BY created_at DESC
        LIMIT 1;
        """,
        mode="poke",
        poke_interval=5,
        timeout=6,
    )

    create_table >> pick_medal >> pick_medal_task >> [count_Bronze, count_Silver, count_Gold]
    [count_Bronze, count_Silver, count_Gold] >> generate_delay_task >> check_for_correctness
        