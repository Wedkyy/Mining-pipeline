# Databricks notebook source
from pyspark.sql import functions as F
# Requerimiento 1

df_silver = spark.read.table("workspace.default.silver_mining_quality")
# 1. Agregación Horaria y Cálculos de Calidad
df_gold_calidad_silice = (
    df_silver
    # Agrupamos por la hora truncada de la fecha
    .groupBy(F.date_trunc('hour', F.col('timestamp')).alias('fecha_hora'),
             F.to_date(F.col('timestamp')).alias('Fecha'))
    .agg(
        # Promedio de sílice en la hora (redondeado a 4 decimales)
        F.round(F.avg('pct_Silica_Concentrate'), 4).alias('promedio_silice_concentrado'),
        
        # Conteo total de registros en la hora (para contexto)
        F.count('*').alias('total_registros_hora')
    )
    # Flag binario basado en si el promedio de la hora superó la norma
    .withColumn(
        'flag_fuera_de_norma',
        F.when(F.col('promedio_silice_concentrado') > 1.5, 1).otherwise(0),

    )
    # Ordenamos cronológicamente
    .orderBy('fecha_hora')
)

# Mostrar resultado en Databricks
display(df_gold_calidad_silice)

# COMMAND ----------

(
    df_gold_calidad_silice.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.default.gold_calidad_silice_hour")
)

# COMMAND ----------

    # Requerimiento 2
from pyspark.sql import functions as F
# Cargar capa Silver
df_silver = spark.read.table("workspace.default.silver_mining_quality")

# Agregación y Métricas de Eficiencia
df_gold_eficiencia_reactivos = (
    df_silver
    .groupBy(F.date_trunc('hour', F.col('timestamp')).alias('fecha_hora'))
    .agg(
        # Promedios de entrada
        F.round(F.avg('pct_Iron_Feed'), 2).alias('iron_feed'),
        F.round(F.avg('pct_Silica_Feed'), 2).alias('silica_feed'),
        # Promedios de consumo de reactivos
        F.round(F.avg('Amina_Flow'), 2).alias('promedio_amina_flow'),
        F.round(F.avg('Starch_Flow'), 2).alias('promedio_starch_flow'),
        F.round(F.avg('Ore_Pulp_pH'), 2).alias('promedio_pulp_ph'),
        F.round(F.avg('Ore_Pulp_Flow'), 2).alias('promedio_pulp_flow'),
        
        # Quality target: Pureza de Hierro
        F.round(F.avg('pct_Iron_Concentrate'), 4).alias('iron_con')
    )
    # Flag de cumplimiento de pureza (>= 65%)
    .withColumn(
        'flag_cumple_pureza',
        F.when(F.col('iron_con') >= 65.0, 1).otherwise(0)
    )
    # KPI de Eficiencia de Amina (Flujo por punto de hierro)
    .withColumn(
    'ganancia_por_amina',
    F.when(F.col('iron_con')-F.col('iron_feed') > 0,
           F.round(F.col('promedio_amina_flow') / (F.col('iron_con') - F.col('iron_feed')), 4)
    ).otherwise(None)
)
)

# Visualizar en Databricks
display(df_gold_eficiencia_reactivos)


# COMMAND ----------

(
    df_gold_eficiencia_reactivos.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.default.gold_eficiencia_reactivos")
)

# COMMAND ----------

from pyspark.sql import functions as F

# Requerimiento 3

df_silver = spark.read.table("workspace.default.silver_mining_quality")
# 1. Base horaria limpia y agregada
gold_estabilidad_calidad = (
    df_silver
    .withColumn("hora", F.hour(F.col("timestamp")))
    .withColumn(
        "turno",
        F.when((F.col("hora") >= 8) & (F.col("hora") < 20), F.lit("DIA")).otherwise(F.lit("NOCHE"))
    )
    .groupBy(
        F.date_trunc("hour", F.col("timestamp")).alias("fecha_hora"),
        F.col("turno")
    )
    .agg(
        # 1. Entrada (Mina)
        F.round(F.avg("pct_Iron_Feed"), 2).alias("iron_feed"),
        F.round(F.avg("pct_Silica_Feed"), 2).alias("silica_feed"),
        
        # 2. Control de Reactivos
        F.round(F.avg("Amina_Flow"), 2).alias("amina_flow"),
        F.round(F.avg("Starch_Flow"), 2).alias("starch_flow"),
        
        # 3. Salida (Concentrado Producto Final)
        F.round(F.avg("pct_Iron_Concentrate"), 2).alias("iron_concentrate"),
        F.round(F.avg("pct_Silica_Concentrate"), 2).alias("silica_concentrate")
    )
    # Deltas de proceso (Enriquecimiento y Remoción)
    .withColumn("delta_ganancia_hierro", F.round(F.col("iron_concentrate") - F.col("iron_feed"), 2))
    .withColumn("delta_reduccion_silice", F.round(F.col("silica_feed") - F.col("silica_concentrate"), 2))
    
    # Flag de Calidad y Estabilidad de Producto Comercial
    # Concentrado con buen Fe (>= 66.5%) y baja impureza de Sílice (<= 1.5%)
    .withColumn(
        "flag_producto_estable_ok",
        F.when(
            (F.col("iron_concentrate") >= 66.5) & (F.col("silica_concentrate") <= 1.5), 
            1
        ).otherwise(0)
    )
    .orderBy("fecha_hora")
)

display(gold_estabilidad_calidad)

# COMMAND ----------

(
    gold_estabilidad_calidad.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.default.gold_estabilidad_turno")
)