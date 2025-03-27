"""DAG demonstrating the umbrella use case with dummy operators."""

import airflow.utils.dates
from airflow import DAG
from airflow.operators.dummy import DummyOperator


dag2 = DAG(
    dag_id="dag2",
    description="Exemples de création de DAGs.",
    start_date=airflow.utils.dates.days_ago(5),
    schedule_interval="@daily",
)
t1 = DummyOperator(task_id="t1", dag=dag2)
t2 = DummyOperator(task_id="t2", dag=dag2)
t3 = DummyOperator(task_id="t3", dag=dag2)

t1 >> t2 >> t3