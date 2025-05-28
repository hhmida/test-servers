from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
# Définition des paramètres du DAG
default_args = {
"owner": "airflow",
"depends_on_past": False,
"start_date": datetime(2024, 3, 20),
"retries": 1,
"retry_delay": timedelta(minutes=5),
}
# Création du DAG
dag = DAG(
"uvt_example",
default_args=default_args,
schedule_interval="@daily",
catchup=False,
)
# Tâche 1 : FileSensor (attend un fichier)
file_sensor_task = FileSensor(
task_id="wait_for_file",
filepath="/tmp/my_file.txt",
fs_conn_id="fs_default",
poke_interval=5,
timeout=60,
mode="poke",
dag=dag,
)
# Tâche 2 : PythonOperator
def print_hello():
    print("Hello, Airflow!")
python_task = PythonOperator(
task_id="print_message",
python_callable=print_hello,
dag=dag,
)
# Tâche 3 : BashOperator
bash_task = BashOperator(
task_id="run_bash_command",
bash_command="rm /tmp/my_file.txt",
dag=dag,
)
# Définition du flow des tâches
file_sensor_task >> [python_task , bash_task]