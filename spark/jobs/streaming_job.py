from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, current_timestamp, from_unixtime,
    to_timestamp, trim, lower, to_date
)
from pyspark.sql.types import (
    StructType, StructField, StringType,
    LongType, BooleanType
)

import os

spark = (
    SparkSession.builder
    .appName("WikiPulse-Streaming")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# ---------------- CONFIGURATION ----------------

POSTGRES_URL = os.environ["POSTGRES_URL"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

JDBC_PROPERTIES = {
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# ---------------- EVENT SCHEMA ----------------

event_schema = StructType([
    StructField("id", LongType(), True),
    StructField("type", StringType(), True),
    StructField("namespace", LongType(), True),
    StructField("title", StringType(), True),
    StructField("comment", StringType(), True),
    StructField("timestamp", LongType(), True),
    StructField("user", StringType(), True),
    StructField("bot", BooleanType(), True),
    StructField("wiki", StringType(), True),
    StructField("server_name", StringType(), True),
    StructField("meta", StructType([
        StructField("id", StringType(), True),
        StructField("dt", StringType(), True),
        StructField("domain", StringType(), True),
        StructField("stream", StringType(), True)
    ]), True)
])

# ---------------- KAFKA SOURCE ----------------

kafka_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:9092")
    .option("subscribe", "wikipulse.raw")
    .option("startingOffsets", "latest")
    .load()
)

parsed_stream = (
    kafka_stream
    .select(
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("value").cast("string").alias("raw_json")
    )
    .withColumn("event", from_json(col("raw_json"), event_schema))
    .withColumn("ingest_time", current_timestamp())
)

# ---------------- BRONZE LAYER ----------------

bronze_stream = (
    parsed_stream
    .filter(col("event").isNotNull())
    .select(
        "kafka_topic",
        "kafka_partition",
        "kafka_offset",
        "raw_json",
        "event.*",
        "ingest_time"
    )
)

bronze_query = (
    bronze_stream.writeStream
    .format("parquet")
    .option("path", "/opt/wikipulse/data/bronze")
    .option("checkpointLocation", "/opt/wikipulse/data/checkpoints/bronze")
    .outputMode("append")
    .start()
)

# ---------------- SILVER LAYER ----------------

silver_base = (
    parsed_stream
    .filter(col("event").isNotNull())
    .select(
        col("event.meta.id").alias("event_id"),
        col("event.id").alias("revision_id"),
        trim(col("event.type")).alias("event_type"),
        col("event.namespace").alias("namespace"),
        trim(col("event.title")).alias("title"),
        trim(col("event.comment")).alias("comment"),
        trim(col("event.user")).alias("user"),
        col("event.bot").alias("is_bot"),
        lower(trim(col("event.wiki"))).alias("wiki"),
        lower(trim(col("event.server_name"))).alias("server_name"),
        lower(trim(col("event.meta.domain"))).alias("domain"),
        col("event.timestamp").alias("event_timestamp"),
        to_timestamp(
            from_unixtime(col("event.timestamp"))
        ).alias("event_time"),
        col("ingest_time")
    )
    .filter(
        col("event_id").isNotNull() &
        (trim(col("event_id")) != "") &
        col("event_type").isNotNull() &
        (col("event_type") != "") &
        col("title").isNotNull() &
        (col("title") != "") &
        col("user").isNotNull() &
        (col("user") != "") &
        col("wiki").isNotNull() &
        (col("wiki") != "") &
        col("event_time").isNotNull()
    )
    .withColumn("event_date", to_date(col("event_time")))
    .withWatermark("event_time", "10 minutes")
    .dropDuplicates(["event_id"])
)

# ---------------- SILVER PARQUET ----------------

silver_query = (
    silver_base.writeStream
    .format("parquet")
    .option("path", "/opt/wikipulse/data/silver")
    .option("checkpointLocation", "/opt/wikipulse/data/checkpoints/silver")
    .outputMode("append")
    .start()
)

# ---------------- POSTGRESQL SINK ----------------

def write_to_postgres(batch_df, batch_id):

    if batch_df.isEmpty():
        return

    postgres_df = batch_df.select(
        "event_id",
        "revision_id",
        "event_type",
        "namespace",
        "title",
        "comment",
        col("user").alias("username"),
        "is_bot",
        "wiki",
        "server_name",
        "domain",
        "event_timestamp",
        "event_time",
        "ingest_time",
        "event_date"
    )

    # Write current micro-batch to staging table
    (
        postgres_df.write
        .mode("append")
        .jdbc(
            url=POSTGRES_URL,
            table="wiki_events_staging",
            properties=JDBC_PROPERTIES
        )
    )

    # Merge staging records into the main table
    connection = spark._jvm.java.sql.DriverManager.getConnection(
        POSTGRES_URL,
        POSTGRES_USER,
        POSTGRES_PASSWORD
    )

    try:
        connection.setAutoCommit(False)

        statement = connection.createStatement()

        statement.executeUpdate("""
            INSERT INTO wiki_events (
                event_id,
                revision_id,
                event_type,
                namespace,
                title,
                comment,
                username,
                is_bot,
                wiki,
                server_name,
                domain,
                event_timestamp,
                event_time,
                ingest_time,
                event_date
            )
            SELECT DISTINCT ON (event_id)
                event_id,
                revision_id,
                event_type,
                namespace,
                title,
                comment,
                username,
                is_bot,
                wiki,
                server_name,
                domain,
                event_timestamp,
                event_time,
                ingest_time,
                event_date
            FROM wiki_events_staging
            ORDER BY event_id
            ON CONFLICT (event_id) DO NOTHING
        """)

        statement.executeUpdate("TRUNCATE TABLE wiki_events_staging")

        connection.commit()

        statement.close()

        print(f"PostgreSQL batch {batch_id} committed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


postgres_query = (
    silver_base.writeStream
    .foreachBatch(write_to_postgres)
    .option(
        "checkpointLocation",
        "/opt/wikipulse/data/checkpoints/postgres"
    )
    .outputMode("append")
    .start()
)

# ---------------- KEEP STREAMING ACTIVE ----------------

spark.streams.awaitAnyTermination()
