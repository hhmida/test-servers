from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.email import EmailOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def process_data(**kwargs):
    """Fonction de traitement des données complexe"""
    ti = kwargs['ti']
    
    # Simulation d'un traitement long
    import time
    time.sleep(10)
    
    # Simulation de la génération de résultats
    results = {
        'processed_items': 1500,
        'quality_score': 98.7,
        'errors_found': 12
    }
    
    # Push des résultats dans XCom pour les tâches suivantes
    for key, value in results.items():
        ti.xcom_push(key=key, value=value)

def validate_results(**kwargs):
    """Validation des résultats du traitement"""
    ti = kwargs['ti']
    
    # Récupération des données depuis XCom
    processed_items = ti.xcom_pull(task_ids='process_data_task', key='processed_items')
    quality_score = ti.xcom_pull(task_ids='process_data_task', key='quality_score')
    errors_found = ti.xcom_pull(task_ids='process_data_task', key='errors_found')
    
    # Logique de validation complexe
    if quality_score < 95 or errors_found > 20:
        raise ValueError(f"Qualité insuffisante: score={quality_score}, erreurs={errors_found}")
    
    print(f"Validation réussie pour {processed_items} éléments traités")

def generate_report(**kwargs):
    """Génération d'un rapport à partir des résultats"""
    ti = kwargs['ti']
    
    processed_items = ti.xcom_pull(task_ids='process_data_task', key='processed_items')
    quality_score = ti.xcom_pull(task_ids='process_data_task', key='quality_score')
    errors_found = ti.xcom_pull(task_ids='process_data_task', key='errors_found')
    
    report_content = f"""
    Rapport de traitement - {datetime.now().date()}
    ======================================
    Items traités: {processed_items}
    Score de qualité: {quality_score}%
    Erreurs détectées: {errors_found}
    """
    
    # Sauvegarde du rapport dans un fichier
    with open('/tmp/processing_report.txt', 'w') as f:
        f.write(report_content)
    
    # Push du chemin du rapport dans XCom
    ti.xcom_push(key='report_path', value='/tmp/processing_report.txt')

with DAG(
    'complex_processing_pipeline',
    default_args=default_args,
    description='Un DAG complexe sans branchements utilisant des opérateurs de base',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(2),
    catchup=False,
    tags=['example', 'complex'],
) as dag:

   
    # Tâche de préparation de l'environnement
    setup_env = BashOperator(
        task_id='setup_environment',
        bash_command='echo "Configuration de l\'environnement..." && '
                     'mkdir -p /tmp/data_processing && '
                     'echo "Env ready" > /tmp/data_processing/status.txt'
    )
    
    # Tâche de traitement principal
    process_data_task = PythonOperator(
        task_id='process_data_task',
        python_callable=process_data,
        provide_context=True
    )
    
    # Tâche de validation
    validate_task = PythonOperator(
        task_id='validate_results',
        python_callable=validate_results,
        provide_context=True
    )
    
    # Tâche de génération de rapport
    generate_report_task = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report,
        provide_context=True
    )
    
    # Tâche d'envoi de rapport par email
    send_report = EmailOperator(
        task_id='send_report_email',
        to='admin@example.com',
        subject='Rapport de traitement quotidien',
        html_content="""<h1>Rapport de traitement</h1>
        <p>Veuillez trouver ci-joint le rapport de traitement.</p>""",
        files=['/tmp/processing_report.txt']
    )
    
    # Tâche de nettoyage
    cleanup = BashOperator(
        task_id='cleanup',
        bash_command='echo "Nettoyage de l\'environnement..." && '
                     'rm -f /tmp/processing_report.txt && '
                     'rm -rf /tmp/data_processing'
    )
    
    
   
    
    # Tâche parallèle de sauvegarde
    backup_data = BashOperator(
        task_id='backup_data',
        bash_command='echo "Sauvegarde des données..." && '
                     'tar -czf /tmp/data_backup_$(date +%Y%m%d).tar.gz /tmp/data_processing'
    )
    echo_send = BashOperator(
        task_id="echo_send",
        bash_command="echo 'Envoi du rapport en cours...'"
    )
    # Orchestration des tâches
    setup_env >> process_data_task >> validate_task
    validate_task >> generate_report_task >> send_report >> cleanup
   # Cette tâche s'exécute en parallèle après le traitement
    process_data_task >> backup_data >> cleanup
    generate_report_task >> echo_send >> cleanup