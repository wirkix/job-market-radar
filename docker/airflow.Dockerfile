FROM apache/airflow:2.10.4-python3.11

USER airflow
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt

# dbt gets its own venv, isolated from Airflow's environment — see
# requirements-dbt.txt for why they can't share one pip resolve.
COPY requirements-dbt.txt /tmp/requirements-dbt.txt
RUN python -m venv /opt/airflow/dbt-venv \
    && /opt/airflow/dbt-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/requirements-dbt.txt

# Makes `from scraper...` / `from enrich...` importable from DAG code without
# installing this project as a package.
ENV PYTHONPATH=/opt/airflow/project
