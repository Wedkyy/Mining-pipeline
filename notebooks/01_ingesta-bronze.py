# Databricks notebook source
from pyspark.sql.functions import current_timestamp, col

# 1. Ruta del origen (Unity Catalog Volumes)
file_path = "/Volumes/workspace/default/mining/MiningProcess_Flotation_Plant_Database.csv"

# 2. Lectura RAW (todos los tipos como StringType para ingesta segura)
df_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "false")
    .csv(file_path)
)

# 3. Sanitización masiva de nombres (1 sola operación en el plan lógico)
clean_column_names = [
    col_name.replace("%", "pct").replace(" ", "_").strip() 
    for col_name in df_raw.columns
]
df_sanitized = df_raw.toDF(*clean_column_names)

# 4. Metadatos de auditoría y linaje
df_bronze = (
    df_sanitized
    .withColumn("ingestion_timestamp", current_timestamp())
    .withColumn("source_file", col("_metadata.file_path"))
)


display(df_bronze.limit(5))

# COMMAND ----------

#Nombre completo de la tabla
table_name = "workspace.default.bronze_mining"

#Guardar el DataFrame como Tabla Delta en la Capa Bronze
(df_bronze.write
 .format("delta")
 .mode("overwrite")
 .option("mergeSchema", "true")
 .saveAsTable(table_name))

print(f"Tabla {table_name} guardada con éxito en la Capa Bronze.")

# COMMAND ----------

