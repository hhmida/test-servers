"""DAG demonstrating the umbrella use case with dummy operators."""

import airflow.utils.dates
from airflow import DAG
from airflow.operators.dummy import DummyOperator


dag3 = DAG(
    dag_id="dag3",
    description="Exemples de création de DAGs.",
    start_date=airflow.utils.dates.days_ago(5),
    schedule_interval="@daily",
)
t1 = DummyOperator(task_id="t1", dag=dag3)
t2 = DummyOperator(task_id="t2", dag=dag3)
t3 = DummyOperator(task_id="t3", dag=dag3)

t1 >> [t2 , t3]