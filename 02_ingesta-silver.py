# Databricks notebook source
from pyspark.sql import functions as F

# 1. Leer la tabla directamente desde la Capa Bronze
df_bronze = spark.read.table("workspace.default.bronze_mining")

# 2. Identificar columnas numéricas
metadata_cols = ["date", "ingestion_timestamp", "source_file"]
numeric_cols = [c for c in df_bronze.columns if c not in metadata_cols]

# -------------------------------------------------------------------
# PASO A: Normalización de Formato (Casting & Trim)
# -------------------------------------------------------------------

# 1. Creamos una lista de expresiones en memoria de Python
numeric_exprs = [
    F.regexp_replace(F.col(c), ",", ".").cast("double").alias(c) 
    for c in numeric_cols
]

# 2. Aplicamos todas las transformaciones juntas en un solo .select()
df_silver = df_bronze.select(
    F.col("date"),                  # Mantenemos 'date' para procesarla luego (o meter su coalesce aquí)
    F.col("ingestion_timestamp"),
    F.col("source_file"),
    *numeric_exprs                # El asterisco desempaqueta las 20+ expresiones numéricas
)

# Convertir columna 'date' a Timestamp real (Formato en la Base de Datos)
df_silver = df_silver.withColumn(
    "timestamp", 
    F.coalesce(
        F.to_timestamp(F.col("date"), "yyyy-MM-dd HH:mm:ss"),
        F.to_timestamp(F.col("date"), "yyyy/MM/dd HH:mm:ss"),
        F.to_timestamp(F.col("date"), "dd/MM/yyyy HH:mm:ss"),
        F.to_timestamp(F.col("date"), "dd/MM/yyyy H:mm")
    )
).drop("date")

# -------------------------------------------------------------------
# PASO B: Reglas de Calidad e Integridad de Datos (Corregido)
# -------------------------------------------------------------------

# 1. Eliminar filas sin fecha válida
df_silver = df_silver.filter(F.col("timestamp").isNotNull())

# 2. Eliminar duplicados REALES (filas donde absolutamente TODAS las columnas sean idénticas)
df_silver = df_silver.dropDuplicates()

# 3. Filtrar límites físicos de las variables principales (0% al 100%)
df_silver = df_silver.filter(
    (F.col("pct_Iron_Feed") >= 0) & (F.col("pct_Iron_Feed") <= 100) &
    (F.col("pct_Silica_Feed") >= 0) & (F.col("pct_Silica_Feed") <= 100)
)

# -------------------------------------------------------------------
# PASO C: Metadatos de Auditoría de Silver
# -------------------------------------------------------------------
df_silver = df_silver.withColumn("silver_processed_at", F.current_timestamp())

# Muestra los resultados finales
print("Limpieza completada exitosamente.")
display(df_silver.limit(100))

filas_bronze = df_bronze.count()
filas_silver = df_silver.count()
eliminados = filas_bronze - filas_silver


print(f"Filas originales (Bronze): {filas_bronze:,}")
print(f"Filas limpias (Silver):     {filas_silver:,}")
print(f"Filas/Duplicados filtrados: {eliminados:,}")

# COMMAND ----------

table_silver_name = "workspace.default.silver_mining_quality"

(df_silver.write
 .format("delta")
 .mode("overwrite")
 .option("mergeSchema", "true")
 .saveAsTable(table_silver_name))

print(f"Tabla {table_silver_name} guardada con éxito en la Capa Silver.")