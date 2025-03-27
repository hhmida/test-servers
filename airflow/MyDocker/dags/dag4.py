"""DAG demonstrating the umbrella use case with dummy operators."""

import airflow.utils.dates
from airflow import DAG
from airflow.operators.dummy import DummyOperator

dag4 = DAG(
    dag_id="dag4",
    description="Exemples de création de DAGs.",
    start_date=airflow.utils.dates.days_ago(5),
    schedule_interval="@daily",
)

t1 = DummyOperator(task_id="t1", dag=dag4)
t2 = DummyOperator(task_id="t2", dag=dag4)
t3 = DummyOperator(task_id="t3", dag=dag4)
t4 = DummyOperator(task_id="t4", dag=dag4)
t5 = DummyOperator(task_id="t5", dag=dag4)
t6 = DummyOperator(task_id="t6", dag=dag4)
t7 = DummyOperator(task_id="t7", dag=dag4)
t8 = DummyOperator(task_id="t8", dag=dag4)
t9 = DummyOperator(task_id="t9", dag=dag4)
t10 = DummyOperator(task_id="t10", dag=dag4)


t1 >> [t2,t3] >> t4
t4 >> t5 >> [t6,t7,t8] 
t7 >> t9
[t7, t2, t6] >> t10