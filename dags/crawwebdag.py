from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import minio
from datetime import datetime
from io import BytesIO,StringIO


# MinIO Configuration
endpoint = "minio:9000"  # Replace with your MinIO host and port
access_key = "rootuser"      # Replace with your access key
secret_key = "rootpassword"      # Replace with your secret key

# File Details
bucket_name1 = "rawfile"
bucket_name2 = "donefile"



# Create MinIO Client
minioClient = minio.Minio(
    endpoint, access_key=access_key, secret_key=secret_key, secure=False
)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'web_scraping_dag',
    default_args=default_args,
    description='A simple web scraping DAG',
    schedule_interval=timedelta(days=1),
    catchup = False
)

def selectdrop(driver, nameele):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, nameele))
    )
    name_select = Select(driver.find_element(By.NAME, nameele))
    name_select.first_selected_option

def crawl_data(**kwargs):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    kwargs['ti'].xcom_push(key='timestamp', value=timestamp)
    object_name1 = f"{timestamp}_raw.csv"
    options = Options()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')  # Overcome limited resource problems
    options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Firefox(options=options)
    driver.get("http://weather.uwyo.edu/upperair/sounding.html")
    driver.switch_to.frame(1)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "region"))
    )
    region = Select(driver.find_element(By.NAME, "region"))
    region.select_by_value("seasia")

    selectdrop(driver, "TYPE")
    selectdrop(driver, "YEAR")
    selectdrop(driver, "MONTH")
    selectdrop(driver, "FROM")
    selectdrop(driver, "TO")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "STNM"))
    )
    station_select = driver.find_element(By.NAME, "STNM")
    station_select.clear()
    station_select.send_keys("48453")
    station_select.send_keys(Keys.RETURN)

    time.sleep(1)

    new_window = driver.window_handles
    driver.switch_to.window(new_window[-1])
    new = driver.current_url

    response = requests.get(new)

    soup = BeautifulSoup(response.content, 'html.parser')

    pre_tag = soup.find("pre")
    if pre_tag:
        data_text = pre_tag.text
    driver.quit()
    csv_bytes = data_text.encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    minioClient.put_object(bucket_name1, object_name1,data=csv_buffer, length=len(csv_bytes),content_type='text/plain')

def process_data(**kwargs):
    timestamp = kwargs['ti'].xcom_pull(key='timestamp', task_ids='crawl_data')
    bucket_name1 = "rawfile"
    bucket_name2 = "donefile"
    object_name1 = f"{timestamp}_raw.csv"
    object_name2 = f"{timestamp}_done.csv"
    response = minioClient.get_object(bucket_name1, object_name1)
    csv_bytes = response.read()

    csv_string = csv_bytes.decode('utf-8')
    df = pd.read_csv(StringIO(csv_string), header=None,skiprows=2).drop(index=[2]).reset_index(drop=True)
    df = df.to_string(index=False).split('\n')

    for i in range(len(df)):
        df[i] = df[i].replace('       ', ' NaN ')
    df = df[1:]
    df = pd.DataFrame([x.split() for x in df])
    df.columns = [f"{col} ({unit})" for col, unit in zip(df.iloc[0], df.iloc[1])]
    df = df.iloc[2:].copy()
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)

    minioClient.put_object(bucket_name2, object_name2,data=csv_buffer, length=len(csv_bytes),content_type='application/csv')

crawl_task = PythonOperator(
    task_id='crawl_data',
    python_callable=crawl_data,
    dag=dag,
)

process_task = PythonOperator(
    task_id='process_data',
    python_callable=process_data,
    dag=dag,
)

crawl_task >> process_task
