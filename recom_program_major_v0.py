import os
from PreProcessing import docx_parser
import os
import pandas as pd
from sqlalchemy import create_engine
import openai
from openai import OpenAI
import mysql.connector
from mysql.connector import Error
import re
import json
import time
import faiss
from sentence_transformers import SentenceTransformer
# from FlagEmbedding import FlagModel

def remove_duplicates_preserve_order(input_list):
    seen = set()  # 用于存储已访问的元素
    result = []
    for item in input_list:
        if item not in seen:  # 如果元素未出现过
            result.append(item)
            seen.add(item)
    return result

def reorder_list(lst):
    if not lst:
        return []
    return [lst[i] for j in range(3) for i in range(j, len(lst), 3)]

def get_program_major(host, user, password, database, table, column_name, port=3306):
    """
    根据column_name列，得到所有不重复的major_list, 返回列表
    该函数可以用于得到大类专业，以及二级具体专业
    """
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    df = pd.read_sql_table(table, engine)
    major_list = list(set(df[column_name].tolist()))

    return major_list, df[['Major_ID',column_name]]

def get_program_info(host, user, password, database, table, columns_name, port=3306):
    """
    根据column_name列，得到所有不重复的major_list, 返回列表
    该函数可以用于得到大类专业，以及二级具体专业
    """
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    df = pd.read_sql_table(table, engine)

    final = df[columns_name]
    return final

def extend_major_description(major_list,api_key):
    """
    根据major_list，得到每个major的描述信息,组成一个诸如['major_name:description']的列表
    """
    # 将候选专业列表转换为字符串形式
    majors_str = ", ".join(major_list)

    user_prompt = f"""
    以下是一些类别比较大的专业：{majors_str}
    请对每个专业添加一百字左右的简短描述，该描述应该包括专业名称，专业特点，以及就业方向，并返回一个 JSON 格式的列表。
    返回结果的格式如下：
    ["专业1: 描述1", "专业2: 描述2", "专业3: 描述3",...]
    """
    try_count = 0
    while try_count < 3:
        try:
            print('使用豆包')
            client = OpenAI(api_key=api_key,#"50139153-f85c-4d77-90e9-41ee692c535e", 
                            base_url="https://ark.cn-beijing.volces.com/api/v3")
            response = client.chat.completions.create(
                # 替换 <YOUR_ENDPOINT_ID> 为您的方舟推理接入点 ID
                model="ep-20241209113858-bmv9x",#"ep-20250128114936-c59tn",
                messages=[
                    {"role": "system", "content": "你是一名专业的教育顾问，擅长给学生或父母用简短文字描述专业"},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # 调整随机性
            )

            # 获取返回内容
            result = response.choices[0].message.content

            majors_description = []
            json_match = re.search(r"\[.*\]", result, re.DOTALL)
            if json_match:
                json_data = json_match.group(0)
                majors_description = json.loads(json_data)
                return majors_description

        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return major_list

def create_major_index(major_list,path_to_save_faiss_index,path_to_save_major_list,api_key):
    """
    创建专业向量库,并保存Faiss索引和句子（专业）顺序
    """
    if len(api_key) > 10:
        majors_description = extend_major_description(major_list,api_key)
        print(majors_description)
    else:
        majors_description = major_list

    # 加载 SentenceTransformer 模型
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    # model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    # # 计算句子嵌入，并归一化
    sentence_vectors = model.encode(majors_description, normalize_embeddings=True) #sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

    # 创建 Faiss 索引
    d = sentence_vectors.shape[1]  # 获取嵌入向量维度
    index = faiss.IndexFlatIP(d)  # 使用内积（IP）作为相似度度量
    index.add(sentence_vectors)  # 添加已有的句子向量

    # 保存 Faiss 索引和句子顺序
    faiss.write_index(index, path_to_save_faiss_index)
    with open(path_to_save_major_list, "w", encoding="utf-8") as f:
        json.dump(major_list, f, ensure_ascii=False, indent=4)

    print(f"Index保存到： {path_to_save_faiss_index}")
    print(f"对应原信息保存到： {path_to_save_major_list}")

def create_program_index(program_dataframe,path_to_save_faiss_index,path_to_save_program_dataframe):
    """
    创建专业向量库,并保存Faiss索引和句子（专业）顺序
    """ 

    # 建立一个新列，内容为program_name_en和program_description的拼接
    program_dataframe['program_name_description'] = program_dataframe['Program_Name_EN'].astype(str) + ':' + program_dataframe['Program_Description'].astype(str)
    # program_dataframe = program_dataframe.head(10)
    program_name_description_list = program_dataframe['program_name_description'].tolist()

    # 加载 SentenceTransformer 模型
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    # model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    # # 计算句子嵌入，并归一化
    sentence_vectors = model.encode(program_name_description_list, normalize_embeddings=True) #sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

    # 创建 Faiss 索引
    d = sentence_vectors.shape[1]  # 获取嵌入向量维度
    index = faiss.IndexFlatIP(d)  # 使用内积（IP）作为相似度度量
    index.add(sentence_vectors)  # 添加已有的句子向量

    # 保存 Faiss 索引和句子顺序
    faiss.write_index(index, path_to_save_faiss_index)
    # save program_dataframe as json file 并且支持中文
    program_dataframe.to_json(path_to_save_program_dataframe, orient='records', lines=True, force_ascii=False)


    print(f"Index保存到： {path_to_save_faiss_index}")
    print(f"对应原信息保存到： {path_to_save_program_dataframe}")

def get_student_intended_category_major_other_info(student_doc_path):
    """
    得到学生具体意向专业,意向大类,其他来自学生，父母或顾问的意向信息
    """
    docx = docx_parser()
    result = docx.parse(student_doc_path)
    top_intended_major,top_intended_category, other_info = [],[],''

    deleted_info = ["（具体专业名称和理由）","具体专业名称和理由","（大类和理由）","大类和理由","顾问帮助学生推荐的申请本科的大类","例如地区、职业、各种相关的","同上","可以超过三个，无想法则不填","先给子分类，给不出来则给大类，给得出来则跳过下面的问题","【艺术与人文（人文社科和艺术需要分开，艺术涉及到作品集的特殊要求）、工程与技术、生命科学与医学、自然科学、社会科学与管理】五个大类里面选，至多两个，最少一个","可以超过三个，无想法则不填","【艺术与人文、工程与技术、生命科学与医学、自然科学、社会科学与管理】五个大类里面选，至多两个"]

    # 3 个意向专业
    top1_major = result['student_preference']['major'].top1
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top1_major = top1_major.replace(info, '')
        # replace \n with ''
        top1_major = top1_major.replace('\n', ' ')
    if len(top1_major.strip()) > 1:
        top_intended_major.append(top1_major.strip())


    top2_major = result['student_preference']['major'].top2
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top2_major = top2_major.replace(info, '')
        # replace \n with ''
        top2_major = top2_major.replace('\n', ' ')
    if len(top2_major.strip()) > 1:
        top_intended_major.append(top2_major.strip())


    top3_major = result['student_preference']['major'].top3
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top3_major = top3_major.replace(info, '')
        # replace \n with ''
        top3_major = top3_major.replace('\n', ' ')
    if len(top3_major.strip()) > 1:
        top_intended_major.append(top3_major.strip())



    intended_major_other = result['student_preference']['major'].supplimental
    for info in deleted_info:
        intended_major_other = intended_major_other.replace(info, '')
    # replace \n with ''
    intended_major_other = intended_major_other.replace('\n', ' ')


    # 3 个意向大类
    top1_category = result['student_preference']['category_student'].top1
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top1_category = top1_category.replace(info, '')
        # replace \n with ''
        top1_category = top1_category.replace('\n', ' ')
    if len(top1_category.strip()) > 1:
        top_intended_category.append(top1_category.strip())


    top2_category = result['student_preference']['category_student'].top2
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top2_category = top2_category.replace(info, '')
        # replace \n with ''
        top2_category = top2_category.replace('\n', ' ')
    if len(top2_category.strip()) > 1:
        top_intended_category.append(top2_category.strip())

    top3_category = result['student_preference']['category_student'].top3
    # 去掉deleted_info中的内容
    for info in deleted_info:
        top3_category = top3_category.replace(info, '')
        # replace \n with ''
        top3_category = top3_category.replace('\n', ' ')
    if len(top3_category.strip()) > 1:
        top_intended_category.append(top3_category.strip())

    category_other = result['student_preference']['category_student'].supplimental
    if len(category_other.strip()) > 1:
        other_info += category_other.strip() + '\n'

    # 其他意向信息
    expert_suggests = result['student_preference']
    expert_suggest = ''
    for key in expert_suggests:
        if key not in ['major','category_student','area','school','grade1_subject','grade2_subject','supplimental']:
            for col, ele in expert_suggests[key]:
                if len(ele.strip()) > 1:
                    expert_suggest += ele.strip() + '\n'

    if len(expert_suggest.strip()) > 1:  
        other_info += expert_suggest.strip()
    

    # 其他信息
    additional_info = result['addition_info']
    if len(additional_info) > 1:
        other_info += '\n'.join(additional_info)

    
    # 在other_info中，去掉deleted_info中的内容
    for info in deleted_info:
        other_info = other_info.replace(info, '')

    # 清理other_info,去掉多余的换行符
    other_info = re.sub(r'\n+', '\n', other_info)

    # 去掉长度小于2的行
    other_info = '\n'.join([line for line in other_info.split('\n') if len(line.strip()) > 2])
    
    
    return top_intended_major, intended_major_other,top_intended_category, other_info

def search_candidate_program(intend_majors,path_to_save_faiss_index,path_to_save_program_dataframe):
    """
    根据学生输入的意向专业，使用向量搜索得到最匹配的专业
    """

    # 加载 Faiss 索引
    if os.path.exists(path_to_save_faiss_index) and os.path.exists(path_to_save_program_dataframe):
        loaded_index = faiss.read_index(path_to_save_faiss_index)
        df_program = pd.read_json(path_to_save_program_dataframe, orient='records', lines=True)

        print(f"加载Index: {path_to_save_faiss_index}")
        print(f"加载专业信息： {path_to_save_program_dataframe}")
    else:
        print(f"Error: Index or sentences file not found at {path_to_save_faiss_index} or {path_to_save_program_dataframe}")
        return []
    
    # 计算输入意向专业的向量
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    # model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    # print('输入为：',intend_majors)
    sentence_vectors = model.encode(intend_majors, normalize_embeddings=True)

    # 如果是一维的，将其转换为二维
    if sentence_vectors.ndim == 1:
        sentence_vectors = sentence_vectors.reshape(1, -1)
    print(sentence_vectors.shape)

    # 使用 Faiss 索引进行搜索
    D, I = loaded_index.search(sentence_vectors, k=300)  # 搜索最相似的1个句子

    all_index,all_distance,all_majors= [],[],[]
    for i in range(len(I)):
        all_index.extend(I[i])
        all_distance.extend(D[i])
        all_majors.extend(len(I[0]) * [intend_majors[i]])

    # print('all_index:',all_index)
    # print('all_distance:',all_distance)
    # print('all_majors:',all_majors)

    # extract all_index rows from df_program and add corresponding distance to df_program
    df_program_filtered = df_program.iloc[all_index]
    df_program_filtered['向量相似性'] = all_distance
    df_program_filtered['意向专业小类'] = all_majors

    return df_program_filtered

def search_candidate_major(intended_category,path_to_save_faiss_index,path_to_save_major_list):
    """
    根据学生输入的意向专业，使用向量搜索得到最匹配的专业
    """

    # 加载 Faiss 索引
    if os.path.exists(path_to_save_faiss_index) and os.path.exists(path_to_save_major_list):
        loaded_index = faiss.read_index(path_to_save_faiss_index)
        with open(path_to_save_major_list, "r", encoding="utf-8") as f:
            loaded_sentences = json.load(f)

        print(f"加载Index: {path_to_save_faiss_index}")
        print(f"加载专业信息： {path_to_save_major_list}")
    else:
        print(f"Error: Index or sentences file not found at {path_to_save_faiss_index} or {path_to_save_major_list}")
        return []
    
    # 计算输入意向专业的向量
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    # model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
    sentence_vectors = model.encode([intended_category], normalize_embeddings=True)

    # 使用 Faiss 索引进行搜索
    D, I = loaded_index.search(sentence_vectors, k=300)  # 搜索最相似的1个句子

    all_index,all_distance,all_majors= [],[],[]
    for i in range(len(I)):
        all_index.extend(I[i])
        all_distance.extend(D[i])
        all_majors.extend(len(I[0]) * [intended_category])

    # print('all_index:',all_index)
    # print('all_distance:',all_distance)
    # print('all_majors:',all_majors)

    df = pd.DataFrame()
    df['匹配的大类专业'] = loaded_sentences
    
    df_filtered = df.iloc[all_index]
    df_filtered['向量相似性'] = all_distance
    df_filtered['LLM改写的用户输入意向专业大类或标注信息'] = all_majors


    return df_filtered


def extend_description_to_input(input_str,api_key):
    """
    根据输入input_str，进行扩展描述
    """

    user_prompt = f"""
    根据以下输入：{input_str}
    添加一百字左右的简短扩展描述，该描述应该包括适合什么样的专业类型，主要做什么以及大概就业方向。注意，如果输入项中有表达对某些领域不感兴趣，或是不喜欢，或是兴趣一般，请过滤掉这些不感兴趣的部分并重写输入项语句，然后在此基础上添加扩展描述。如果输入语句比较长请过滤掉无用信息以及不感兴趣的专业信息并重新组织输入语句，然后在此基础上添加扩展描述。

    则返回结果的格式如下：
    "input_str:扩展描述"
    """
    try_count = 0
    while try_count < 3:
        try:
            print('使用豆包')
            #doubao
            client = OpenAI(api_key=api_key,#"50139153-f85c-4d77-90e9-41ee692c535e", 
                            base_url="https://ark.cn-beijing.volces.com/api/v3")
            response = client.chat.completions.create(
                # 替换 <YOUR_ENDPOINT_ID> 为您的方舟推理接入点 ID
                model="ep-20241209113858-bmv9x",#"ep-20250128114936-c59tn",
                messages=[
                    {"role": "system", "content": "你是一名专业的教育顾问，擅长给学生或父母用简短文字描述专业"},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # 调整随机性
            )

            # 获取返回内容
            result = response.choices[0].message.content
            print('results:',result)
            return result
        
        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return input_str

def extract_negative_description_from_input(input_str,api_key):
    """
    根据输入input_str，提取用户不喜欢或不感兴趣的专业方向
    """

    user_prompt = f"""
    根据以下输入：{input_str}
    提取出用户表示不喜欢，不感兴趣，感觉很难，没动力学，或着不考虑的专业方向，然后进行简单的描述。注意，如果输入没有包含不喜欢，不感兴趣，没动力，或是兴趣一般的专业描述，请返回空值。
    例如，输入为：“工程与技术 学生相对生物兴趣一般，暂时对计算机有一定想法”，则返回诸如：“生物：生物有关的学科，例如生物工程，生物制药，生物科学等”
    如果输入为：“父亲是做建筑设计相关行业“， 因为输入没有包含任何表示不喜欢的专业方向，则返回为："".
    """
    try_count = 0
    while try_count < 3:
        try:
            print('使用豆包')
            #doubao
            client = OpenAI(api_key=api_key,#"50139153-f85c-4d77-90e9-41ee692c535e", 
                            base_url="https://ark.cn-beijing.volces.com/api/v3")
            response = client.chat.completions.create(
                # 替换 <YOUR_ENDPOINT_ID> 为您的方舟推理接入点 ID
                model="ep-20241209113858-bmv9x",#"ep-20250128114936-c59tn",
                messages=[
                    {"role": "system", "content": "你是一名专业的教育顾问，擅长通过学生或父母的描述提取出学生不感兴趣的专业方向，并把不感兴趣的专业描述出来"},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # 调整随机性
            )

            # 获取返回内容
            result = response.choices[0].message.content
            print('results:',result)
            return result
        
        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return ""



def get_program_from_intended_major(intended_major,path_to_save_faiss_index,path_to_save_program_dataframe,similarity_threshold,black_list_program_id,white_list_program_id):
    """
    根据学生输入的意向专业，使用向量搜索得到最匹配的program
    """
    df_intended_major_to_program = pd.DataFrame()
    if len(intended_major) > 0:
        df_intended_major_to_program = search_candidate_program(intended_major, path_to_save_faiss_index,path_to_save_program_dataframe)
        df_intended_major_to_program_tmp = df_intended_major_to_program[df_intended_major_to_program['向量相似性'] >= similarity_threshold]
        if len(df_intended_major_to_program_tmp) < 3:
            df_intended_major_to_program = df_intended_major_to_program.head(3)
        else:
            df_intended_major_to_program = df_intended_major_to_program_tmp

        if len(df_intended_major_to_program) > 0:
            if len(black_list_program_id) > 0:
                df_intended_major_to_program = df_intended_major_to_program[~df_intended_major_to_program['Program_ID'].isin(black_list_program_id)]
            df_intended_major_to_program = df_intended_major_to_program.drop_duplicates(subset=['Program_ID'], keep='first')
            df_intended_major_to_program = df_intended_major_to_program.sort_values(by='向量相似性', ascending=False).reset_index(drop=True)
    
    if len(df_intended_major_to_program) > 0 and len(white_list_program_id) > 0:
        df_intended_major_to_program = df_intended_major_to_program[df_intended_major_to_program['Program_ID'].isin(white_list_program_id)].reset_index(drop=True)

    if len(df_intended_major_to_program) > 30:
        df_intended_major_to_program = df_intended_major_to_program.head(30)


    return df_intended_major_to_program

def get_program_from_intended_major_other(intended_major_other,path_to_save_faiss_index,path_to_save_program_dataframe,api_key,similarity_threshold,black_list_program_id,white_list_program_id):
    """
    根据学生输入的意向专业其他信息，使用向量搜索得到最匹配的program
    """
    df_intended_major_other_to_program = pd.DataFrame()
    intended_major_other = intended_major_other.strip()
    if len(intended_major_other) > 1:
        intended_major_other_extended = extend_description_to_input(intended_major_other,api_key)
        df_intended_major_other_to_program = search_candidate_program(intended_major_other_extended, path_to_save_faiss_index,path_to_save_program_dataframe)    
        df_intended_major_other_to_program['LLM改写的意向专业小类信息'] = len(df_intended_major_other_to_program) * [intended_major_other]
        df_intended_major_other_to_program_tmp = df_intended_major_other_to_program[df_intended_major_other_to_program['向量相似性'] >= similarity_threshold]
        if len(df_intended_major_other_to_program_tmp) < 3:
            df_intended_major_other_to_program = df_intended_major_other_to_program.head(3)
        else:
            df_intended_major_other_to_program = df_intended_major_other_to_program_tmp

        if len(df_intended_major_other_to_program)>0:
            if len(black_list_program_id) > 0:
                df_intended_major_other_to_program = df_intended_major_other_to_program[~df_intended_major_other_to_program['Program_ID'].isin(black_list_program_id)]
            df_intended_major_other_to_program = df_intended_major_other_to_program.drop_duplicates(subset=['Program_ID'], keep='first')
            df_intended_major_other_to_program = df_intended_major_other_to_program.sort_values(by='向量相似性', ascending=False).reset_index(drop=True)

    if len(df_intended_major_other_to_program) > 0 and len(white_list_program_id) > 0:
        df_intended_major_other_to_program = df_intended_major_other_to_program[df_intended_major_other_to_program['Program_ID'].isin(white_list_program_id)].reset_index(drop=True)

    if len(df_intended_major_other_to_program) > 25:
        df_intended_major_other_to_program = df_intended_major_other_to_program.head(25)


    return df_intended_major_other_to_program


def get_major_from_intended_category(intended_category,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,similarity_threshold,df_major_id,white_list_major_list,black_list_major_id):
    """
    根据学生输入的意向专业大类，使用向量搜索得到最匹配的专业
    """
    df_intended_category_to_major = pd.DataFrame()
    if len(intended_category) > 0:
        for category in intended_category:
            extended_category = extend_description_to_input(category,api_key)
            df_candidate_major_tmp = search_candidate_major(extended_category,path_to_save_faiss_index_level0,path_to_save_major_list_level0)
            df_candidate_major_tmp['用户输入的意向大类或其他标注信息'] = len(df_candidate_major_tmp) * [category]
            df_intended_category_to_major = pd.concat([df_intended_category_to_major,df_candidate_major_tmp])

        df_intended_category_to_major_tmp = df_intended_category_to_major[df_intended_category_to_major['向量相似性'] >= similarity_threshold]
        if len(df_intended_category_to_major_tmp) < 3:
            df_intended_category_to_major = df_intended_category_to_major.head(3)
        else:
            df_intended_category_to_major = df_intended_category_to_major_tmp

        df_intended_category_to_major = df_intended_category_to_major.merge(df_major_id, left_on='匹配的大类专业', right_on='Major_Name_CH', how='left')
    
    if len(white_list_major_list) > 0 and len(df_intended_category_to_major) > 0:
        df_intended_category_to_major = df_intended_category_to_major[df_intended_category_to_major['Major_Name_CH'].isin(white_list_major_list)]

    if len(df_intended_category_to_major) > 0:
        if len(black_list_major_id) > 0:
            df_intended_category_to_major = df_intended_category_to_major[~df_intended_category_to_major['Major_ID'].isin(black_list_major_id)]
        df_intended_category_to_major = df_intended_category_to_major.drop_duplicates(subset=['Major_ID'], keep='first')
        df_intended_category_to_major = df_intended_category_to_major.sort_values(by='向量相似性', ascending=False).reset_index(drop=True)
    
    
    return df_intended_category_to_major


def get_major_from_other_info(other_info,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,similarity_threshold,df_major_id,white_list_major_list,black_list_major_id):
    """
    根据学生输入的其他信息，使用向量搜索得到最匹配的专业
    """

    df_other_info_to_major = pd.DataFrame()
    other_info = other_info.strip()
    if len(other_info) > 1:
        extended_other_info = extend_description_to_input(other_info,api_key)
        df_other_info = search_candidate_major(extended_other_info, path_to_save_faiss_index_level0,path_to_save_major_list_level0)
        df_other_info['用户输入的其他信息'] = len(df_other_info) * [other_info]

        df_other_info_to_major_tmp = df_other_info[df_other_info['向量相似性'] >= similarity_threshold]
        if len(df_other_info_to_major_tmp) < 3:
            df_other_info_to_major = df_other_info_to_major.head(3)
        else:
            df_other_info_to_major = df_other_info_to_major_tmp

        df_other_info_to_major = df_other_info_to_major.merge(df_major_id, left_on='匹配的大类专业', right_on='Major_Name_CH', how='left')
        if len(white_list_major_list) > 0:
            df_other_info_to_major = df_other_info_to_major[df_other_info_to_major['Major_Name_CH'].isin(white_list_major_list)]

    if len(df_other_info_to_major) > 0:
        if len(black_list_major_id) > 0:
            df_other_info_to_major = df_other_info_to_major[~df_other_info_to_major['Major_ID'].isin(black_list_major_id)]
        df_other_info_to_major = df_other_info_to_major.drop_duplicates(subset=['Major_ID'], keep='first')  
        df_other_info_to_major = df_other_info_to_major.sort_values(by='向量相似性', ascending=False).reset_index(drop=True)
    
    return df_other_info_to_major

def get_program_black_list(input_strs,path_to_save_faiss_index,path_to_save_program_dataframe,api_key):
    negative_major_description = extract_negative_description_from_input(input_strs,api_key)
    print('negative description:',negative_major_description)
    if len(negative_major_description) > 2:
        df_negative_program = search_candidate_program(negative_major_description, path_to_save_faiss_index,path_to_save_program_dataframe)    
        df_negative_program_tmp = df_negative_program[df_negative_program['向量相似性'] >= 0.82]
        if len(df_negative_program_tmp) < 3:
            df_negative_program = df_negative_program.head(3)
        else:
            df_negative_program = df_negative_program_tmp

        return df_negative_program['Program_ID'].tolist()

    return []

def get_major_black_list(input_strs,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,df_major_id):
    """
    """
    negative_major_description = extract_negative_description_from_input(input_strs,api_key)
    print('negative description:',negative_major_description)
    if len(negative_major_description) > 2:
        df_other_info = search_candidate_major(negative_major_description, path_to_save_faiss_index_level0,path_to_save_major_list_level0)
        df_other_info_to_major_tmp = df_other_info[df_other_info['向量相似性'] >= 0.82]
        if len(df_other_info_to_major_tmp) < 3:
            df_other_info_to_major = df_other_info.head(3)
        else:
            df_other_info_to_major = df_other_info_to_major_tmp

        df_other_info_to_major = df_other_info_to_major.merge(df_major_id, left_on='匹配的大类专业', right_on='Major_Name_CH', how='left')
        return df_other_info_to_major['Major_ID'].tolist()
    else:
        return []


def get_major_white_list(input_str,path_to_save_major_list,api_key):
    """
    根据输入input_str，提取用户感兴趣的专业方向
    """
    

    # 加载大类专业列表
    with open(path_to_save_major_list, "r", encoding="utf-8") as f:
        loaded_sentences = json.load(f)

    all_major_strs = "; ".join(loaded_sentences)

    user_prompt = f"""
    根据以下输入：{input_str}
    先去除掉用户不感兴趣或不喜欢或是觉的比较难的专业方向，然后总结提取或推断出用户可能感兴趣或有用的专业方向。注意，只要不是用户表现出不喜欢或不感兴趣或不考虑的专业方向，输入中涉及的专业信息都可以默认是用户感兴趣的专业方向。然后，在下面的专业列表中,选出与用户兴趣相关的专业:{all_major_strs}.请尽量找出多的相关或相近的专业。
    例如，如果输入为：“工程与技术 学生相对生物兴趣一般，暂时对计算机有一定想法”，则应该返回与计算机，工程与技术相关的专业，而不能返回与生物相关的专业。比如返回：['数据科学和人工智能','计算机科学与信息系统','统计学与运筹学','电气与电子工程','机械、航空与制造工程','矿物与采矿工程','化学工程','土木与结构工程']
    请最终返回一个 JSON 格式的列表，格式如下：
    ["专业1, "专业2", "专业3",...]
    """
    try_count = 0
    while try_count < 3:
        try:
            print('使用豆包')
            #doubao
            client = OpenAI(api_key=api_key,#"50139153-f85c-4d77-90e9-41ee692c535e", 
                            base_url="https://ark.cn-beijing.volces.com/api/v3")
            response = client.chat.completions.create(
                # 替换 <YOUR_ENDPOINT_ID> 为您的方舟推理接入点 ID
                model="ep-20241209113858-bmv9x",#"ep-20250128114936-c59tn",
                messages=[
                    {"role": "system", "content": "你是一名专业的教育顾问，擅长在用户的描述中剔除用户不感兴趣的专业，然后总结，推断，提取出学生可能兴趣或有用的专业方向"},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # 调整随机性
            )

            # 获取返回内容
            result = response.choices[0].message.content
            selected_majors = []
            json_match = re.search(r"\[.*\]", result, re.DOTALL)
            if json_match:
                json_data = json_match.group(0)
                selected_majors = json.loads(json_data)
                return selected_majors
        
        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return []


def get_program_id_white_list(major_white_list,host,user,password,database,uk_major_undergrad_table = "UK_major_undergrad",uk_program_major_map_table="UK_program_major_map",port=3306):
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    df_major_undergrad = pd.read_sql_table(uk_major_undergrad_table, engine)
    df_program_major_map = pd.read_sql_table(uk_program_major_map_table, engine)


    # 取df_major_undergrad 中 Major_Name_CH 在 major_white_list 中的行
    df_major_undergrad_tmp = df_major_undergrad[df_major_undergrad['Major_Name_CH'].isin(major_white_list)]

    # 取df_program_major_map 中 Major_ID 在 df_major_undergrad_tmp['Major_ID'] 中的行
    df_program_major_map_tmp = df_program_major_map[df_program_major_map['Major_ID'].isin(df_major_undergrad_tmp['Major_ID'])]

    # 返回所有的Program_ID
    return df_program_major_map_tmp['Program_ID'].unique().tolist()


if __name__ == "__main__":


    start_time = time.time()
    print('starting search')

    #====================== 1： 得到大类专业并建立Faiss索引 ======================
    host = "elitech-database.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"  #"eli-tech.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"
    user = "Eli_education"
    password = "EliEducation2024!"
    database = "Hailiang"

    table = "UK_major_undergrad"  #"UK_program_undergrad" #"UK_major_undergrad"
    column_name = "Major_Name_CH"  #"Major_New" #"Major_Name_CH"
    level0_majors, df_major_id = get_program_major(host, user, password, database, table, column_name, port=3306)
    print(level0_majors)
    print('大类专业数量:',len(level0_majors))

    # 对大类专业建立faiss索引
    # path_to_save_faiss_index_level0 = 'major_faiss_index_bge.index'
    # path_to_save_major_list_level0 = 'major_list_bge.json'
    path_to_save_faiss_index_level0 = 'major_faiss_index.index'
    path_to_save_major_list_level0 = 'major_list.json'
    api_key = '20cfa121-c5f5-45fe-a4ad-b43ec11b209a'

    if not os.path.exists(path_to_save_faiss_index_level0):
        print('=====================对大类专业建立Faiss索引=====================')
        create_major_index(level0_majors,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key)
        print('大类专业索引建立完成')
    #====================== 2： 建立 program索引 ======================
    table = "UK_program_undergrad" 
    columns_name = ["Program_ID","Program_Name_EN","Program_Description"]  
    df_program = get_program_info(host, user, password, database, table, columns_name, port=3306)

    # path_to_save_faiss_index = 'program_faiss_index_bge.index'
    # path_to_save_program_dataframe = 'program_dataframe_bge.json'
    path_to_save_faiss_index = 'program_faiss_index.index'
    path_to_save_program_dataframe = 'program_dataframe.json'
    if not os.path.exists(path_to_save_faiss_index):
        print('=====================对program建立Faiss索引=====================')
        create_program_index(df_program,path_to_save_faiss_index,path_to_save_program_dataframe)
        print('program索引建立完成')



    #===============================3：得到学生输入表中的意向大类专业，小类专业，其他意向信息 ======================
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2A（雨妗）\丁子淇--Alevel数据采集.docx'
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2E (思雨)\数据采集要求-杜俊熙.docx'
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASE(杨怡)\数据采集--任绪鑫.docx'
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASF(雨田_佳铭)_\数据采集--仵同悦.docx'
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部G2D(杨怡)\数据采集--吴众豪.docx'


    similarity_threshold= 0.65  #0.45(bge)   #0.65(m3e)

    print('=========================得到学生意向大类专业，小类专业，其他意向信息=========================')
    intended_major, intended_major_other,intended_category, other_info = get_student_intended_category_major_other_info(student_doc_path)
    print('学生意向小类专业:',intended_major)
    print('学生意向小类专业其他信息:',intended_major_other)
    print('学生意向大类专业:',intended_category)
    print('学生相关的其他信息:',other_info)


    # 建立黑名单 白名单
    black_list_program_id,black_list_major_id,white_list_program_id,white_list_major_list = [],[],[],[]

    all_input_strs = intended_major + [intended_major_other] + intended_category + [other_info]
    all_input_strs = ','.join(all_input_strs)
    if len(all_input_strs.strip()) > 2:
        black_list_program_id = get_program_black_list(all_input_strs,path_to_save_faiss_index,path_to_save_program_dataframe,api_key)

    if len(all_input_strs.strip()) > 2:
        black_list_major_id = get_major_black_list(all_input_strs,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,df_major_id)

    # white list
    if len(all_input_strs.strip()) > 2:
        white_list_major_list = get_major_white_list(all_input_strs,path_to_save_major_list_level0,api_key)
        print('白名单专业:',white_list_major_list)

    if len(white_list_major_list) > 0:
        white_list_program_id = get_program_id_white_list(white_list_major_list,host,user,password,database)
        # print('白名单项目ID:',white_list_program_id)
        print('白名单项目数量:',len(white_list_program_id))



    print('========================================================================================================')
    print('========================================================================================================')
    print('========================================================================================================')
    print('采集到的学生意向专业小类：',intended_major)
    df_intended_major_to_program = get_program_from_intended_major(intended_major,path_to_save_faiss_index,path_to_save_program_dataframe,similarity_threshold,black_list_program_id,white_list_program_id)
    df_intended_major_to_program.to_excel('意向专业小类的项目推荐.xlsx',index=False)
    print('\n\n')


    print('采集到的学生意向专业小类其他信息：',intended_major_other)
    df_intended_major_other_to_program = get_program_from_intended_major_other(intended_major_other,path_to_save_faiss_index,path_to_save_program_dataframe,api_key,similarity_threshold,black_list_program_id,white_list_program_id)
    df_intended_major_other_to_program.to_excel('意向专业小类其他信息的项目推荐.xlsx',index=False)
    print('\n\n')


    print('采集到的学生意向专业大类：',intended_category)
    df_candidate_major = get_major_from_intended_category(intended_category,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,similarity_threshold,df_major_id,white_list_major_list,black_list_major_id)
    df_candidate_major.to_excel('大类专业推荐.xlsx',index=False)

    print('\n\n')


    print('采集到的学生其他信息：',other_info)
    df_other_info = get_major_from_other_info(other_info,path_to_save_faiss_index_level0,path_to_save_major_list_level0,api_key,similarity_threshold,df_major_id,white_list_major_list,black_list_major_id)
    df_other_info.to_excel("学生其他信息专业推荐.xlsx", index=False)
    print('\n\n')

    end_time = time.time()
    print(f'Total time: {end_time - start_time} seconds')

