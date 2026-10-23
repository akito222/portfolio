"""Glue ETL job: raw review CSV (Data Catalog) -> partitioned Parquet (+ catalog update).

Code version of the Glue Studio visual job built in the hands-on:

    [S3 source: Data Catalog table] -> [Change Schema: drop total_votes, vine]
        -> [S3 target: Parquet / Snappy, partition = product_category,
            "create table and update schema / add new partitions"]

Why this makes Athena cheaper / faster (Athena bills by bytes scanned):
  * Parquet is columnar  -> a query reads only the columns it references
  * Snappy compression   -> fewer bytes on S3
  * Partitioning         -> WHERE product_category = 'Books' reads only that folder
  * Dropping unused cols -> smaller files overall

Job parameters (set as DefaultArguments in infra/cloudformation/03-processing.yaml):
  --source_database --source_table --target_database --target_table --target_path
"""

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import ApplyMapping
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

DROP_COLUMNS = {"total_votes", "vine"}
PARTITION_KEYS = ["product_category"]

args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "source_database",
        "source_table",
        "target_database",
        "target_table",
        "target_path",
    ],
)

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# transformation_ctx is required for job bookmarks: with bookmarks enabled, only
# S3 objects that were not processed in a previous successful run are read.
source = glue_context.create_dynamic_frame.from_catalog(
    database=args["source_database"],
    table_name=args["source_table"],
    transformation_ctx="source",
)

# "Change Schema" node == ApplyMapping. Keep every column except the dropped ones,
# and pin types explicitly so that a bad crawler guess does not leak downstream.
# (OpenCSVSerDe tables may come in as all-string; ApplyMapping casts them.)
TYPES = {
    "customer_id": "long",
    "age": "int",
    "product_parent": "long",
    "star_rating": "int",
    "helpful_votes": "int",
}
mappings = []
for field in source.schema().fields:
    name = field.name
    if name in DROP_COLUMNS:
        continue
    src_type = field.dataType.typeName()
    mappings.append((name, src_type, name, TYPES.get(name, src_type)))

transformed = ApplyMapping.apply(frame=source, mappings=mappings, transformation_ctx="change_schema")

sink = glue_context.getSink(
    path=args["target_path"],
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=PARTITION_KEYS,
    enableUpdateCatalog=True,
    transformation_ctx="sink",
)
sink.setCatalogInfo(
    catalogDatabase=args["target_database"],
    catalogTableName=args["target_table"],
)
sink.setFormat("glueparquet", compression="snappy")
sink.writeFrame(transformed)

job.commit()
