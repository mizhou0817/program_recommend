# 定义下基本操作的函数，比如创建program index, 连接数据库等

import os
import pandas as pd
import pymysql
from sqlalchemy import create_engine
import faiss


def connect_mysql(host, user, password, database, table):
    # create a connection to the database
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}")
    # read the table into a dataframe
    df = pd.read_sql_table(table, engine)
    return df


def create_faiss_index(embeddings_array, index_path):
    """
    given the embeddings array, creat a faiss index

    """
