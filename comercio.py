import requests
import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import timedelta,datetime

#AIRFLOW

# argumentos por defecto para el DAG
default_args = {
    'owner': 'DanielMendieta',
    'start_date': datetime(2023,6,18),
    'retries':2,
    'retry_delay': timedelta(minutes=5)
}

BC_dag = DAG(
    dag_id='Productos_ETL',
    default_args=default_args,
    description='Primer trabajo con Airflow',
    schedule_interval="@daily",
    catchup=False
)

#CONEXIÓN API.

url = "https://random-data-api.com/api/commerce/random_commerce?size=100"
response = requests.get(url)
data = response.json()
tabla = pd.DataFrame(data)

#COMIENZO CON LA LIMPIEZA:

#DESCARTO COLUMNAS POCO RELEVANTE.
del tabla ["id"]
del tabla ["uid"]
del tabla ["price_string"]
del tabla ["promo_code"]

#ME QUEDO SOLO CON LOS PRIMEROS 50 RESULTADOS
tabla.drop(range(50,100), axis = 0, inplace=True)

#BORRAMOS POSIBLES DUPLICADOS
tabla.drop_duplicates()

#ORDENAMOS LOS PRODUCTOS DE VALOR MAS ELEVADO AL MAS ECONOMICO.
tabla.sort_values(by=['price'], inplace=True, ascending=False)

#CAMBIO EL NOMBRE DE LAS COLUMNAS.
tabla.columns= ['Color', 'Sector', 'Material','Nombre', 'Precio']
tabla
    

#PASO 2 - CONEXIÓN A AMAZON REDSHIFT.
def redshiftDB():
    urll="data-engineer-cluster.cyhh5bfevlmn.us-east-1.redshift.amazonaws"
    data_base="data-engineer-database"
    user="mendietadaniel1994_coderhouse"
    pwd= 'xxxxx'
        
    try:
        conn = psycopg2.connect(
            host='data-engineer-cluster.cyhh5bfevlmn.us-east-1.redshift.amazonaws.com',
            dbname=data_base,
            user=user,
            password=pwd,
            port='5439'
            )
        print("Conexión Exitosa.")
    
    except:    
        print("Algo salio mal.")
        
#PASO 3 - CREACIÓN DE LA TABLA.

    try:
        dtypes= tabla.dtypes #NOS MUESTRA QUE TIPO DE DATOS ES EJ: FLOAT, OBJECT ETC
        columnas= list(dtypes.index ) #NOS MUESTRA NOMBRE DE LAS COLUMNAS Y LAS CONVIERTE EN UNA LISTA
        tipos= list(dtypes.values) #NOS MUESTRA EL TIPO DE DATO DE LOS VALORES Y LAS CONVIERTE EN UNA LISTA
        conversorDetipos = {'int64': 'INT','int32': 'INT','float64': 'FLOAT','object': 'VARCHAR(50)','bool':'BOOLEAN'}
        sql_dtypes = [conversorDetipos[str(dtype)] for dtype in tipos] # CONVERTIMOS TODO EN CADENA
        column_defs = [f"{name} {data_type}" for name, data_type in zip(columnas, sql_dtypes)] #DEFINIMOS LAS COLUMNAS Y SU TIPO PARA LA TABLA
        cur = conn.cursor() #APUNTAMOS A LA BASE DE DATOS
        sql = f"CREATE TABLE Productos (id INT IDENTITY(1,1) PRIMARY KEY, {', '.join (column_defs)});" #CREAMOS TABLA CON CLAVE PRIMARIA
        cur.execute(sql)
        conn.commit()
        print ('Tabla Creada.')
    except:
        print("No fue posible crear la tabla.")  
#PASO 4 - INTRODUCCION DE DATOS Y FINAL DEL PROCESO.           

    try:
        values = [tuple(x) for x in tabla.to_numpy()]
        sqll = f"INSERT INTO Productos ({', '.join(columnas)}) VALUES %s"
        execute_values(cur, sqll, values)
        conn.commit()
        print ("Datos Ingresados.")
    
    except:    
        print("Error al cargar.")    
    
    finally:
        conn.close()
        print("Conexión Terminada.")     
        
#TASK AIRFLOW        
task_1 = PythonOperator(
    task_id='Conexion_Creacion_Insercion',
    python_callable=redshiftDB,
    dag=BC_dag,
)

task_1 
