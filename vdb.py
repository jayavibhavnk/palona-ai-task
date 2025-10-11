## ipynb (you do not have to run this)

import weaviate.classes.config as wc

if client.collections.exists("Product"):
    client.collections.delete("Product")

client.collections.create(
    name="Product",
    properties=[
        wc.Property(name="product_name",   data_type=wc.DataType.TEXT),
        wc.Property(name="description",    data_type=wc.DataType.TEXT),
        wc.Property(name="specs_text",     data_type=wc.DataType.TEXT),
        wc.Property(name="image_url",      data_type=wc.DataType.TEXT),  # metadata
        wc.Property(name="image_blob",     data_type=wc.DataType.BLOB),  # used by Cohere
        wc.Property(name="price",          data_type=wc.DataType.TEXT),
        wc.Property(name="rating_overall", data_type=wc.DataType.TEXT),
        wc.Property(name="review_count",   data_type=wc.DataType.TEXT),
        wc.Property(name="asin",           data_type=wc.DataType.TEXT),
        wc.Property(name="url",            data_type=wc.DataType.TEXT),
    ],
    vector_config=[
        wc.Configure.Vectors.multi2vec_cohere(
            name="mm_vec",  # named vector
            text_fields=[
                wc.Multi2VecField(name="product_name", weight=0.25),
                wc.Multi2VecField(name="description",  weight=0.50),
                wc.Multi2VecField(name="specs_text",   weight=0.25),
            ],
            image_fields=[
                wc.Multi2VecField(name="image_blob", weight=1.0),
            ],
            # put vector index settings HERE (not at class level)
            vector_index_config=wc.Configure.VectorIndex.hnsw(
                distance_metric=wc.VectorDistances.COSINE,
                ef_construction=128,
                max_connections=64,
            ),
        )
    ],
)


