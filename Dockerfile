# Base image for Airflow
FROM apache/airflow:2.10.3


# Switch to airflow user and install pymysql and MySQL provider
USER airflow
RUN pip install apache-airflow-providers-mysql pymysql