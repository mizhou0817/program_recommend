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
    return major_list

def extend_major_description(major_list,select_model='doubao'):
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
            if select_model != 'doubao':
                # 调用 DeepSeek API
                print('使用deepseek v3')
                client = OpenAI(api_key="sk-4dba8c314a964f15a6774089d754aef2", base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model="deepseek-chat",  # 使用的模型
                    messages=[
                        {"role": "system", "content": "你是一名专业的教育顾问，擅长给学生或父母用简短文字描述专业"},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2  # 调整随机性
                )
            else:
                print('使用豆包')
                #doubao
                client = OpenAI(api_key="20cfa121-c5f5-45fe-a4ad-b43ec11b209a",#"50139153-f85c-4d77-90e9-41ee692c535e", 
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
            else:
                print("Error: No valid JSON found in the API response.")

        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return major_list


def extend_description_to_input(input_str,select_model='doubao'):
    """
    根据input_str，进行扩展描述
    """

    user_prompt = f"""
    根据以下输入：{input_str}
    添加一百字左右的简短扩展描述，该描述应该包括适合什么样的专业类型，以及大概就业方向，并返回一个字符串。
    返回结果的格式如下：
    “input_str:扩展描述”
    """
    try_count = 0
    while try_count < 3:
        try:
            if select_model != 'doubao':
                # 调用 DeepSeek API
                print('使用deepseek v3')
                client = OpenAI(api_key="sk-4dba8c314a964f15a6774089d754aef2", base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model="deepseek-chat",  # 使用的模型
                    messages=[
                        {"role": "system", "content": "你是一名专业的教育顾问，擅长根据学生或父母对专业或就业的描述来概括学生或家长感兴趣的专业信息和就业方向"},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2  # 调整随机性
                )
            else:
                print('使用豆包')
                #doubao
                client = OpenAI(api_key="20cfa121-c5f5-45fe-a4ad-b43ec11b209a",#"50139153-f85c-4d77-90e9-41ee692c535e", 
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
            return result
        
        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return input_str

def infer_related_category_and_major_from_additional_info(input_str,select_model='doubao'):
    """
    根据input_str，进行扩展描述
    """

    user_prompt = f"""
    以下为学生本人或学生父母，或教育专家顾问输入的相关信息：{input_str}
    请通过这些信息推荐三个大类别专业和三个小类别专业，并对这些专业做个简单的描述，同时给出推荐理由。如果给定的是无效信息，请对应给出现在流行的三个大类专业个三个小类专业。请返回一个 JSON 格式的列表。
    返回结果的格式如下：
    ["大类专业1: 描述1，理由：理由描述", "大类专业2: 描述2，理由：理由描述", "大类专业3: 描述3，理由：理由描述","小类专业1: 描述1，理由：理由描述", "小类专业2: 描述2，理由：理由描述", "小类专业3: 描述3，理由：理由描述"]
    """
    try_count = 0
    while try_count < 5:
        try:
            if select_model != 'doubao':
                # 调用 DeepSeek API
                print('使用deepseek v3')
                client = OpenAI(api_key="sk-4dba8c314a964f15a6774089d754aef2", base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model="deepseek-chat",  # 使用的模型
                    messages=[
                        {"role": "system", "content": "你是一名专业的教育顾问，擅长从学生或家长或顾问的文字描述中发现学生潜在的意向专业和意向大类"},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2  # 调整随机性
                )
            else:
                print('使用豆包')
                #doubao
                client = OpenAI(api_key="20cfa121-c5f5-45fe-a4ad-b43ec11b209a",#"50139153-f85c-4d77-90e9-41ee692c535e", 
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
            infer_category_and_major = []
            json_match = re.search(r"\[.*\]", result, re.DOTALL)
            if json_match:
                json_data = json_match.group(0)
                infer_category_and_major = json.loads(json_data)
                return infer_category_and_major
            else:
                print("No valid JSON found in the API response.")

            
        except Exception as e:
            print('第',try_count,'次运行错误，继续尝试')
            try_count += 1
            continue

    return []



def create_major_index(major_list,path_to_save_faiss_index,path_to_save_major_list,path_to_save_major_description_list,select_model='doubao'):
    """
    创建专业向量库,并保存Faiss索引和句子（专业）顺序
    """
    if select_model == 'doubao' or select_model == 'deepseek':
        majors_description = extend_major_description(major_list,select_model)
        print(majors_description)
    else:
        majors_description = major_list

    # 加载 SentenceTransformer 模型
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    # 计算句子嵌入，并归一化
    sentence_vectors = model.encode(majors_description, normalize_embeddings=True) #sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

    # 创建 Faiss 索引
    d = sentence_vectors.shape[1]  # 获取嵌入向量维度
    index = faiss.IndexFlatIP(d)  # 使用内积（IP）作为相似度度量
    index.add(sentence_vectors)  # 添加已有的句子向量

    # 保存 Faiss 索引和句子顺序
    faiss.write_index(index, path_to_save_faiss_index)
    with open(path_to_save_major_list, "w", encoding="utf-8") as f:
        json.dump(major_list, f, ensure_ascii=False, indent=4)

    with open(path_to_save_major_description_list, "w", encoding="utf-8") as f:
        json.dump(majors_description, f, ensure_ascii=False, indent=4)

    print(f"Index保存到： {path_to_save_faiss_index}")
    print(f"专业信息保存到： {path_to_save_major_list}")


def search_candidate_major(intend_major,path_to_save_faiss_index,path_to_save_major_list,path_to_save_major_description_list,extract_top_k=1):
    """
    根据学生输入的意向专业，使用向量搜索得到最匹配的专业
    """
    # 加载 Faiss 索引
    if os.path.exists(path_to_save_faiss_index) and os.path.exists(path_to_save_major_list) and os.path.exists(path_to_save_major_description_list):
        loaded_index = faiss.read_index(path_to_save_faiss_index)
        with open(path_to_save_major_list, "r", encoding="utf-8") as f:
            loaded_sentences = json.load(f)
        with open(path_to_save_major_description_list, "r", encoding="utf-8") as f:
            loaded_sentences_description = json.load(f)
        print(f"加载Index: {path_to_save_faiss_index}")
        print(f"加载专业信息： {path_to_save_major_list}")
    else:
        print(f"Error: Index or sentences file not found at {path_to_save_faiss_index} or {path_to_save_major_list}")
        return []
    
    # 计算输入意向专业的向量
    # model = SentenceTransformer('shibing624/text2vec-base-chinese')
    model = SentenceTransformer("moka-ai/m3e-base")
    sentence_vectors = model.encode([intend_major], normalize_embeddings=True)

    # 使用 Faiss 索引进行搜索
    D, I = loaded_index.search(sentence_vectors, k=extract_top_k)  # 搜索最相似的1个句子

    candidate_majors = []
    for ele in I[0]:
        candidate_majors.append(loaded_sentences[ele])
        print('输入的专业:',intend_major)
        print('向量搜索出来的专业:',loaded_sentences[ele])
        print('搜索出来的专业以及描述:',loaded_sentences_description[ele])


    return candidate_majors



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


    major_other = result['student_preference']['major'].supplimental
    if len(major_other.strip()) > 1:
        other_info += major_other.strip() + '\n'
    

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
    
    
    return top_intended_major, top_intended_category, other_info



def search_flow(student_doc_path):
    """
    根据学生信息表，使用向量搜索找出最近的意向专业，包括大类和小类
    """
    pass

if __name__ == "__main__":
    start_time = time.time()
    print('starting search')

    #====================== 1： 得到大类专业并建立Faiss索引 ======================
    host = "eli-tech.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"
    user = "Eli_education"
    password = "EliEducation2024!"
    database = "Hailiang"

    table = "UK_major_undergrad"  #"UK_program_undergrad" #"UK_major_undergrad"
    column_name = "Major_Name_CH"  #"Major_New" #"Major_Name_CH"
    level0_majors = get_program_major(host, user, password, database, table, column_name, port=3306)
    print(level0_majors)
    print('大类专业数量:',len(level0_majors))

    # 对大类专业建立faiss索引
    path_to_save_faiss_index_level0 = 'level0_majors_faiss_index2.index'
    path_to_save_major_list_level0 = 'level0_majors_major_list2.json'
    path_to_save_major_description_list_level0 = 'level0_majors_major_description_list2.json'
    if not os.path.exists(path_to_save_faiss_index_level0):
        print('=====================对大类专业建立Faiss索引=====================')
        create_major_index(level0_majors,path_to_save_faiss_index_level0,path_to_save_major_list_level0,path_to_save_major_description_list_level0,select_model='doubao')


    #================================2：得到小类专业并建立Faiss索引 ======================
    # 得到小类专业
    host = "eli-tech.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"
    user = "Eli_education"
    password = "EliEducation2024!"
    database = "Hailiang"

    table = "UK_program_undergrad" 
    column_name = "Major_New"  
    level1_majors = get_program_major(host, user, password, database, table, column_name, port=3306)
    print(level1_majors)
    print('小类专业数量:',len(level1_majors))

    # 对小类专业建立faiss索引
    path_to_save_faiss_index_level1 = 'level1_majors_faiss_index2.index'    
    path_to_save_major_list_level1 = 'level1_majors_major_list2.json'
    path_to_save_major_description_list_level1 = 'level1_majors_major_description_list2.json'
    if not os.path.exists(path_to_save_faiss_index_level1):
        print('=======================对小类专业建立Faiss索引=======================')
        create_major_index(level1_majors,path_to_save_faiss_index_level1,path_to_save_major_list_level1,path_to_save_major_description_list_level1,select_model='doubao')



    #===============================3：得到学生输入表中的意向大类专业，小类专业，其他意向信息 ======================
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2A（雨妗）\丁子淇--Alevel数据采集.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2E (思雨)\数据采集要求-杜俊熙.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASE(杨怡)\数据采集--任绪鑫.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASF(雨田_佳铭)_\数据采集--仵同悦.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部G2D(杨怡)\数据采集--吴众豪.docx'

    print('=========================得到学生意向大类专业，小类专业，其他意向信息=========================')
    intended_major, intended_category, other_info = get_student_intended_category_major_other_info(student_doc_path)
    print('学生意向小类专业:',intended_major)
    print('学生意向大类专业:',intended_category)
    print('学生相关的其他信息:',other_info)



    #======================4：根据学生意向小类展业，大类专业，以及其他信息使用向量搜索得到对应最匹配的专业 ======================
    # a: 根据学生意向小类专业，使用向量搜索得到对应最匹配的专业
    recomm_major_list_level1 = []
    if len(intended_major) > 0:
        print('============================根据学生意向小类专业，使用向量搜索得到对应最匹配的专业============================')
        top_k = 3
        for major in intended_major:
            candidate_major = search_candidate_major(major,path_to_save_faiss_index_level1,path_to_save_major_list_level1,path_to_save_major_description_list_level1,extract_top_k=top_k)
            recomm_major_list_level1.extend(candidate_major)

    # 去除重复的专业
    recomm_major_list_level1 = reorder_list(recomm_major_list_level1)
    recomm_major_list_level1 = remove_duplicates_preserve_order(recomm_major_list_level1)[:3]
    


    # b: 根据学生意向大类专业，使用向量搜索得到对应最匹配的专业

    recomm_major_list_level0 = []
    if len(intended_category) > 0:
        print('========================================根据学生意向大类专业，使用向量搜索得到对应最匹配的专业========================================')
        top_k = 3
        for category in intended_category:
            category = extend_description_to_input(category,select_model='doubao')
            candidate_major = search_candidate_major(category,path_to_save_faiss_index_level0,path_to_save_major_list_level0,path_to_save_major_description_list_level0,extract_top_k=top_k)
            recomm_major_list_level0.extend(candidate_major)

    # 去除重复的专业
    recomm_major_list_level0 = reorder_list(recomm_major_list_level0)
    recomm_major_list_level0 = remove_duplicates_preserve_order(recomm_major_list_level0)[:3]

    # c: 根据学生意向其他信息，使用向量搜索得到对应最匹配的专业
    recomm_major_list_other_level0,recomm_major_list_other_level1 = [], []
    if len(other_info) > 0:
        print('========================================根据学生意向其他信息，使用向量搜索得到对应最匹配的专业========================================')
        # 使用llm在other_info中提取出意向专业
        other_info_more = infer_related_category_and_major_from_additional_info(other_info,select_model='doubao')
        print('从其他信息中总结推算出的意向专业大类与小类:',other_info_more)
        reasons = []
        for ele in other_info_more:
            reason = '理由：' + ele.split('理由:')[-1]
            reasons.append(reason)

        # 使用向量搜索得到对应最匹配的专业,前三个为大类，后三个为小类
        for major in other_info_more[:3]:
            candidate_major = search_candidate_major(major,path_to_save_faiss_index_level0,path_to_save_major_list_level0,path_to_save_major_description_list_level0,extract_top_k=3)
            recomm_major_list_other_level0.extend(candidate_major)
        recomm_major_list_other_level0 = remove_duplicates_preserve_order(reorder_list(recomm_major_list_other_level0))[:3]
        for major in other_info_more[3:]:
            candidate_major = search_candidate_major(major,path_to_save_faiss_index_level1,path_to_save_major_list_level1,path_to_save_major_description_list_level1,extract_top_k=3)
            recomm_major_list_other_level1.extend(candidate_major)
        recomm_major_list_other_level1 = remove_duplicates_preserve_order(reorder_list(recomm_major_list_other_level1))[:3]


    #========================5：输出最后结果 ======================
    print('\n\n\n================================================================================================================')
    print('================================================================================================================')
    print('===========================================最终专业搜索结果======================================================')
    print('========================学生的意向专业，大类专业，其他意向信息，向量搜索得到对应最匹配的专业：========================')
    print('================================================================================================================')
    print('================================================================================================================')
    print('\n\n')
    if len(intended_major) > 0:

        print('采集到的学生意向专业小类：',intended_major)
        print('向量搜索出来的对应专业小类为：',recomm_major_list_level1,'\n\n')
    else:
        print('采集到的学生意向专业小类为空\n\n')

    if len(intended_category) > 0:
        print('采集到的学生意向专业大类：',intended_category)
        print('向量搜索出来的对应专业大类为：',recomm_major_list_level0,'\n\n')
    else:
        print('采集到的学生意向专业大类为空\n\n')

    if len(other_info) > 0:
        print('采集到的有关学生的其他信息如下：',other_info.replace('\n', ' '))
        print('\n向量搜索出来的专业大类为：',recomm_major_list_other_level0)
        print('向量搜索出来的专业小类为：',recomm_major_list_other_level1,'\n\n')
    else:
        print('采集到的学生其他意向信息为空\n\n')

    
    final_major_level0 = recomm_major_list_level0 + recomm_major_list_other_level0
    final_major_level1 = recomm_major_list_level1 + recomm_major_list_other_level1

    final_major_level0 = remove_duplicates_preserve_order(final_major_level0)[:3]
    final_major_level1 = remove_duplicates_preserve_order(final_major_level1)[:3]

    print('最终搜索出来的专业大类为：',final_major_level0)
    print('最终搜索出来的专业小类为：',final_major_level1,'\n\n')




    end_time = time.time()
    print(f'Total time: {end_time - start_time} seconds')


    

