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

def remove_duplicates_preserve_order(input_list):
    seen = set()  # 用于存储已访问的元素
    result = []
    for item in input_list:
        if item not in seen:  # 如果元素未出现过
            result.append(item)
            seen.add(item)
    return result

def connect_mysql(host, user, password, database, table,port=3306):
    # create a connection to the database
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    # read the table into a dataframe
    df = pd.read_sql_table(table, engine)
    return df

def connect_mysql_database(host, user, password, database, port=3306):
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    return engine

def read_mysql_table(engine, table):
    df = pd.read_sql_table(table, engine)
    return df


def get_deepseek_answer(api_key, model_name,system_prompt, user_prompt, input_text):
    """
    given the api_key, system_prompt, user_prompt and input_text, get the answer from llm
    """

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
                model = model_name, #"deepseek-reasoner", #"deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": input_text},
                ],
                stream=False
            )
    print(response.choices[0].message.content)

def get_student_exame_score():
    """
    得到学生考试成绩相关信息
    """
    pass

def get_student_language_score():
    """
    得到学生英语考试成绩相关信息
    """
    pass

def get_student_all_score(student_doc_path):
    """
    得到学生所有成绩
    """
    docx = docx_parser()
    result = docx.parse(student_doc_path)
    score = result['student_score']   

    res = ''
    for key in score:
        if key != 'column_name':
            for col, ele in score[key]:
                if len(ele) > 1:
                    res += ele
                    res += '\n'

    res = res.replace('分数','')
    # remove empty line between lines
    res = '\n'.join([x for x in res.split('\n') if x.strip()])

    return res


def get_student_intended_major(student_doc_path):
    """
    得到学生具体意向专业,和意向大类
    """
    docx = docx_parser()
    result = docx.parse(student_doc_path)
    top_intended_major,top_intended_category = [],[]

    # 3 个意向专业
    top1_major = result['student_preference']['major'].top1
    lines = top1_major.splitlines()
    if len(lines) > 1:
        top1_major = lines[1].strip()
        if len(top1_major) > 1:
            top_intended_major.append(top1_major)
        else:
            top_intended_major.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_major.append(lines[0].strip())



    top2_major = result['student_preference']['major'].top2
    lines = top2_major.splitlines()
    if len(lines) > 1:
        top2_major = lines[1].strip()
        if len(top2_major) > 1:
            top_intended_major.append(top2_major)
        else:
            top_intended_major.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_major.append(lines[0].strip())

    top3_major = result['student_preference']['major'].top3
    lines = top3_major.splitlines()
    if len(lines) > 1:
        top3_major = lines[1].strip()
        if len(top3_major) > 1:
            top_intended_major.append(top3_major)
        else:
            top_intended_major.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_major.append(lines[0].strip())
    

    # 3 个意向大类
    top1_category = result['student_preference']['category_student'].top1
    lines = top1_category.splitlines()
    if len(lines) > 1:
        if len(lines[1].strip()) > 1:
            top1_category = lines[1].strip()
            top_intended_category.append(top1_category)
        else:
            top_intended_category.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_category.append(lines[0].strip())

    top2_category = result['student_preference']['category_student'].top2
    lines = top2_category.splitlines()
    if len(lines) > 1:
        if len(lines[1].strip()) > 1:
            top2_category = lines[1].strip()
            top_intended_category.append(top2_category)
        else:
            top_intended_category.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_category.append(lines[0].strip())

    top3_category = result['student_preference']['category_student'].top3
    lines = top3_category.splitlines()
    if len(lines) > 1:
        if len(lines[1].strip()) > 1:
            top3_category = lines[1].strip()
            top_intended_category.append(top3_category)
        else:
            top_intended_category.append(lines[0].strip())
    elif len(lines) == 1:
        top_intended_category.append(lines[0].strip())

    return top_intended_major, top_intended_category


def extend_intended_major(api_key,intended_major,all_candidates_majors):
    """
    扩展意向专业
    examples:
        intended_major = "工程类专业"
        all_candidates_majors = [
            "计算机工程", "土木工程", "商务旅游", "电子工程", 
            "数据科学", "人工智能", "英语教育", 
            "统计学", "生物工程", "药理学", "信息安全"
            ]
    """

    # 将候选专业列表转换为字符串形式
    all_majors_str = ", ".join(all_candidates_majors)

    user_prompt = f"""
    以下是一个意向专业：{intended_major}
    以及一个候选专业列表：[{all_majors_str}]

    请根据语义相似性，找到与意向专业最相近的三个候选专业，并返回一个 JSON 格式的列表。
    返回结果的格式如下：
    ["专业1", "专业2", "专业3"]
    """

    # 调用 DeepSeek API
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",  # 使用的模型
        messages=[
            {"role": "system", "content": "你是一名专业的教育顾问，擅长分析和匹配专业。"},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5  # 调整随机性
    )

    # 获取返回内容
    result = response.choices[0].message.content

    all_extended_majors = []
    json_match = re.search(r"\[.*\]", result, re.DOTALL)
    if json_match:
        json_data = json_match.group(0)
        all_extended_majors = json.loads(json_data)
    else:
        print("Error: No valid JSON found in the API response.")

    all_extended_majors = [intended_major] + all_extended_majors
    all_extended_majors = remove_duplicates_preserve_order(all_extended_majors)

    return all_extended_majors


def extend_multiple_intended_majors(api_key,intended_majors,all_candidates_majors,select_model='doubao'):
    """
    扩展意向专业
    examples:
        intended_majors = ["工程类专业","计算机类专业"]
        all_candidates_majors = [
            "计算机工程", "土木工程", "商务旅游", "电子工程", 
            "数据科学", "人工智能", "英语教育", 
            "统计学", "生物工程", "药理学", "信息安全"
            ]
    """

    # 将候选专业列表转换为字符串形式
    intended_majors_str = ", ".join(intended_majors)
    all_majors_str = ", ".join(all_candidates_majors)

    user_prompt = f"""
    以下是一些意向专业：{intended_majors_str}
    以及一个候选专业列表：[{all_majors_str}]

    请根据语义相似性，找到与每个意向专业最相近的最多三个候选专业，然后合并所有相近候选专业，并返回一个 JSON 格式的列表。
    返回结果的格式如下：
    ["专业1", "专业2", "专业3"， "专业4", "专业5", "专业6",...]
    """

    if select_model != 'doubao':
        # 调用 DeepSeek API
        print('使用deepseek v3')
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用的模型
            messages=[
                {"role": "system", "content": "你是一名专业的教育顾问，擅长分析和匹配专业。"},
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
                {"role": "system", "content": "你是一名专业的教育顾问，擅长分析和匹配专业"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2  # 调整随机性
        )


    # 获取返回内容
    result = response.choices[0].message.content

    all_extended_majors = []
    json_match = re.search(r"\[.*\]", result, re.DOTALL)
    if json_match:
        json_data = json_match.group(0)
        all_extended_majors = json.loads(json_data)
    else:
        print("Error: No valid JSON found in the API response.")

    all_extended_majors = intended_majors + all_extended_majors

    # remove duplicate majors and keep the order at the same time
    all_extended_majors = remove_duplicates_preserve_order(all_extended_majors)

    return all_extended_majors

def get_all_candidate_program_univ(engine,table1='UK_program_undergrad',table2='UK_department',table3='UK_school_undergrad'):
    """
    table1: UK_program_undergrad
    table2: UK_department
    table3: UK_school_undergrad
    """
    df1 = pd.read_sql_table(table1, engine)
    df2 = pd.read_sql_table(table2, engine)[['Department_ID','School_ID']]
    df3 = pd.read_sql_table(table3, engine)

    # merge df1 and df2 on Department_ID
    merged_df = pd.merge(df1, df2, on='Department_ID', how='left')
    # merge merged_df and df3 on School_ID
    merged_df = pd.merge(merged_df, df3, on='School_ID', how='left')

    return merged_df

def get_all_program_majors(engine,table,columns):
    """
    得到所有专业
    """
    all_majors = []
    df = pd.read_sql_table(table, engine)
    for column in columns:
        major = df[column].values.tolist()
        all_majors.extend(major)

    return list(set(all_majors))


def get_candidate_program_from_majors(engine,table,extended_majors,columns = ['Major','Major_New']):
    """
    根据学生扩展意向专业，得到候选项目
    """
    df = pd.read_sql_table(table, engine)

    # 对dataframe df, 保留columns 列里有 extended_majors 的行
    filtered_df = df[df[columns[0]].isin(extended_majors) | df[columns[1]].isin(extended_majors)]
    # filter out duplicate rows
    df_candidate_program = filtered_df.drop_duplicates().reset_index(drop=True)

    return df_candidate_program


def filter_program_by_exam_and_language(api_key,candidate_program, student_scores,select_model='doubao'):
    """
    通过考试成绩和语言成绩过滤项目
    """
    # 将 DataFrame 转换为 JSON 格式
    data_json = candidate_program.to_json(orient="records")

    # 构造 prompt
    # user_prompt = f"""
    #     以下是某些高校的项目要求和学生的成绩描述：
    #     项目要求, 请看列'Exam_Requirements' 和 'Language_Requirements'：
    #     {data_json}

    #     学生的成绩的描述：
    #     成绩描述：{student_scores}

    #     根据以下规则分析考试成绩和语言要求，并与学生的成绩描述进行对比，提供明确的分析和解释：
    #     1：分级规则：
    #     1.1： 对考试成绩和英语成绩分别按A-Level标准进行综合分级（A*, A, B, C, D, E, U），以统一标准评估成绩,注意，有些成绩要求可能已经按A-Level分好级了，如此就直接使用。
    #     1.2： 对学生的考试成绩和英语成绩也按A-Leval标准进行综合分级(A*, A, B, C, D, E, U)，作为比较依据。注意，有些学生的考试成绩可能已经按A-Level分好级了，如此就直接使用。
    #     2: 比较规则：
    #     2.1: 成绩符合要求： 如果学生成绩与要求等级完全匹配（如要求为A或B，学生成绩为A），标注为“成绩符合要求”。
    #     2.2: 成绩接近要求： 如果学生成绩稍低于要求（如要求为A，学生成绩为B），标注为“成绩接近要求”。
    #     2.3: 缺少相关成绩： 如果学生未提供某门考试或英语成绩，标注为“缺少相关成绩”。
    #     2.4: 成绩需要提高： 如果学生成绩显著低于要求（如要求为A，学生成绩为C或D），标注为“成绩需要提高”。
    #     3: 筛选规则：
    #     3.1: 如果学生成绩描述中某门考试出现多次，取最高成绩进行分析。
    #     3.2：只选择学生成绩中最好的3门与项目的成绩要求进行比较。也就是说，如果学生提供了5门成绩，只选最好的3门来与要求的成绩进行比较

        # 返回结果的格式是一个 JSON 列表，包含：
        # - Program_ID
        # - Explanation
        # - Language

        # 例如：
        # [
        #     {{"Program_ID": 101, "Explanation": "成绩符合要求"}},
        #     {{"Program_ID": 102, "Explanation": "成绩接近要求"}},
        #     {{"Program_ID": 103, "Explanation": "缺少相关成绩"}},
        #     {{"Program_ID": 103, "Explanation": "成绩不符合要求"}}
        # ]
        # """

    user_prompt = f"""
        以下是某些高校的项目要求和学生的成绩描述：
        项目要求, 请看列'Exam_Requirements' 和 'Language_Requirements'：
        {data_json}

        学生的成绩的描述：
        成绩描述：{student_scores}

        根据以下规则，分析学生的考试成绩和语言成绩，并与学校的申请要求进行对比，提供清晰的分析和解释：
        分析规则：
        1：成绩分级：
        1.1：申请要求分级：
        1.1.1：Exam_Requirements中定义了按A-Level标准的最低成绩要求（例如，AAB表示至少需要两门A和一门B）。这是申请该项目的最低标准。
        1.2：学生成绩分级：
        1.2.1：如果学生的成绩已经按A-Level标准分级（如A*, A, B等），直接使用。
        1.2.2：如果未分级，需要对每科成绩进行转换，按A-Level标准分级（A*, A, B, C, D, E, U），如果相同科目成绩出现多次，选最高的那次
        1.2.3：从学生的成绩中选取满足申请要求格式的最佳成绩组合（例如，找到最优的AAB组合）。
        2：语言要求：
        2.1：检查Language_Requirements中规定的最低语言要求，验证学生的语言成绩是否满足。

        成绩比较规则：
        成绩符合要求：如果学生的成绩完全匹配或优于要求（如申请要求为AAB，学生成绩为AAA），标注为“成绩符合要求”。
        成绩接近要求：如果学生成绩略低于要求（如申请要求为AAA，学生成绩为AAB），标注为“成绩接近要求”。
        缺少相关成绩：如果学生提供的考试数量不足以用来比较，标注为“缺少相关成绩”。比如要求最少3门课程成绩，学生只提供2门或1门，则为缺少相关成绩。
        成绩需要提高：如果学生成绩显著低于要求（如申请要求为AAA，学生成绩为CCC或DDD），标注为“成绩需要提高”。

        语言比较规则：
        达标：学生语言成绩满足申请项目中的语言要求。注意，学生语言成绩只要达到要求里面任何一个语言要求就行，比如要求里可能有IELTS或TOEFL，只要满足一样就属于达标。同时，如果申请要求中没有语言要求，则自动视为达标。
        不达标：学生语言成绩不满足申请项目中的语言要求
        缺失：学生还没有提供语言成绩


        返回结果的格式是一个 JSON 列表，包含：
        - Program_ID
        - Explanation
        - Language

        例如：
        [
            {{"Program_ID": 101, "Explanation": "成绩符合要求","Language":"达标"}},
            {{"Program_ID": 102, "Explanation": "成绩接近要求","Language":"不达标"}},
            {{"Program_ID": 103, "Explanation": "缺少相关成绩","Language":"达标"}},
            {{"Program_ID": 103, "Explanation": "成绩不符合要求","Language":"缺失"}}
        ]
        """
    
    if select_model != 'doubao':
        print('使用deepseek v3')
        # 调用 DeepSeek API
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用的模型
            messages=[
                {"role": "system", "content": "你是一名专业的教育顾问，专注于帮助学生申请英国高校。你擅长根据学生的学习成绩和语言能力、分析是否符合各高校的项目要求"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2  # 调整随机性
        )
    else:
        print('使用豆包')
        #doubao
        # client = OpenAI(api_key="50139153-f85c-4d77-90e9-41ee692c535e", base_url="https://ark.cn-beijing.volces.com/api/v3")
        client = OpenAI(api_key="20cfa121-c5f5-45fe-a4ad-b43ec11b209a", base_url="https://ark.cn-beijing.volces.com/api/v3")
        response = client.chat.completions.create(
            # 替换 <YOUR_ENDPOINT_ID> 为您的方舟推理接入点 ID
            model="ep-20241209113858-bmv9x", #"ep-20250128114936-c59tn",
            messages=[
                {"role": "system", "content": "你是一名专业的教育顾问，专注于帮助学生申请英国高校。你擅长根据学生的学习成绩和语言能力、分析是否符合各高校的项目要求"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2  # 调整随机性
        )
        result = response.choices[0].message.content

    # 获取返回内容
    result = response.choices[0].message.content

    df_check = pd.DataFrame()
    json_match = re.search(r"\[.*\]", result, re.DOTALL)
    if json_match:
        json_data = json_match.group(0)
        df_check_tmp = json.loads(json_data)
        df_check = pd.DataFrame(df_check_tmp)
    else:
        print("Error: No valid JSON found in the API response.")


    # merge df_check with candidate_program on Program_ID
    df_check = pd.merge(candidate_program, df_check, on='Program_ID', how='left')

    return df_check



def rank_program_by_majors(intended_majors,candidate_program):
    """
    按专业的顺序对候选项目进行排序
    """
    def limit_rows(group):
        # 对每个专业只保留前 3 行
        return group.head(3)
    
    # 对Major按是否出现在 intended_majors 中进行排序
    candidate_program['priority'] = candidate_program['Major'].apply(lambda x: intended_majors.index(x) if x in intended_majors else len(intended_majors))
    candidate_program = candidate_program.sort_values(by='priority').drop(columns=['priority'])
    candidate_program.reset_index(drop=True, inplace=True)
    # 每个在inented_majors 中的专业只保留前 3 个项目在前面
    priority_df = candidate_program[candidate_program['Major'].isin(intended_majors)]
    priority_df = priority_df.groupby('Major', group_keys=False).apply(limit_rows)
    # 将剩余部分作为非优先级部分
    non_priority_df = candidate_program[~candidate_program.index.isin(priority_df.index)]
    # 合并优先级部分和其他部分
    sorted_df = pd.concat([priority_df, non_priority_df]).reset_index(drop=True)


    return sorted_df

def get_fixed_number_of_candidate_program(candidate_program,keep_num=60):
    """
    候选项目太多时，只保留部分候选项目
    """
    unique_majors = candidate_program['Major'].unique().tolist()
    unique_majors_new = candidate_program['Major_New'].unique().tolist()
    unique_majors_new = [ele for ele in unique_majors_new if ele not in unique_majors]

    program_num_for_each_major = keep_num // (len(unique_majors) + len(unique_majors_new))

    def limit_rows(group):
        return group.head(program_num_for_each_major)
    
    # 对Major按是否出现在 unique_majors 中进行排序
    candidate_program['priority'] = candidate_program['Major'].apply(lambda x: unique_majors.index(x) if x in unique_majors else len(unique_majors))
    candidate_program = candidate_program.sort_values(by='priority').drop(columns=['priority'])
    candidate_program.reset_index(drop=True, inplace=True)

    # 每个在inented_majors 中的专业只保留前 3 个项目在前面
    priority_df = candidate_program[candidate_program['Major'].isin(unique_majors)]
    priority_df = priority_df.groupby('Major', group_keys=False).apply(limit_rows)
    # 剩余部分
    non_priority_df = candidate_program[~candidate_program.index.isin(priority_df.index)]
    
    # 将剩余部分按unique_majors_new专业排序
    non_priority_df['priority'] = non_priority_df['Major_New'].apply(lambda x: unique_majors_new.index(x) if x in unique_majors_new else len(unique_majors_new))
    non_priority_df = non_priority_df.sort_values(by='priority').drop(columns=['priority'])
    non_priority_df.reset_index(drop=True, inplace=True)
    # 每个在unique_majors_new 中的专业只保留前 3 个项目
    non_priority_df_v2 = non_priority_df[non_priority_df['Major_New'].isin(unique_majors_new)]
    non_priority_df_v2 = non_priority_df_v2.groupby('Major_New', group_keys=False).apply(limit_rows)

    # 剩余部分
    non_priority_df_v3 = non_priority_df[~non_priority_df.index.isin(non_priority_df_v2.index)]


    # 合并优先级部分和其他部分
    df_candidate = pd.concat([priority_df, non_priority_df_v2, non_priority_df_v3]).reset_index(drop=True).head(keep_num)


    return df_candidate

def rank_program_by_score_qs(candidate_program):
    """
    根据学生的成绩对候选项目进行排序,成绩为匹配的结果：
    成绩符合要求，成绩接近要求，缺少相关成绩，成绩需要提高
    """
    # 对dataframe candidate_program, 按照 Explanation里的成绩符合要求，成绩接近要求，缺少相关成绩，成绩需要提高 顺序进行排序
    rank_dict = {
        "成绩符合要求": 1,
        "成绩接近要求": 2,
        "缺少相关成绩": 3,
        "成绩需要提高": 4
    }
    candidate_program['rank'] = candidate_program['Explanation'].map(rank_dict)
    # sort it by rank and QS

    candidate_program = candidate_program.sort_values(by=['rank','QS'], ascending=[True,True])
    candidate_program = candidate_program.drop(columns=['rank']).reset_index(drop=True)
    return candidate_program

# if __name__ == "__main__":

#     start_time = time.time()

#     #==================basic info==========================================
#     print('initialization...')
#     host = "eli-tech.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"
#     user = "Eli_education"
#     password = "EliEducation2024!"
#     database = "Hailiang"
#     table = "UK_program_undergrad"
#     engine = connect_mysql_database(host, user, password, database)
#     columns = ['Major','Major_New']  

#     api_key = "sk-4dba8c314a964f15a6774089d754aef2"

#     student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2A（雨妗）\丁子淇--Alevel数据采集.docx'
#     # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2E (思雨)\数据采集要求-杜俊熙.docx'
#     # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASE(杨怡)\数据采集--任绪鑫.docx'
#     # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASF(雨田_佳铭)_\数据采集--仵同悦.docx'
#     # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部G2D(杨怡)\数据采集--吴众豪.docx'
    
#     #==================step 0: get all candidate programs==================
#     print('get all candidate programs...')
#     df_all_program = get_all_candidate_program_univ(engine)
#     print('number of all programs: ',len(df_all_program))

#     #==================step 1: get all programs majors=====================
#     print('get all programs majors...')
#     program_majors = get_all_program_majors(engine,table,columns)
#     print('number of all majors: ',len(program_majors))

#     #==================step 2: get student intended major==================
#     print('get student intended major...')
#     intended_major, intended_category = get_student_intended_major(student_doc_path)
#     all_possible_major_category = intended_major + intended_category
#     all_possible_major_category = [ele for ele in all_possible_major_category if len(ele)>1]
#     all_possible_major_category = remove_duplicates_preserve_order(all_possible_major_category)
#     all_possible_major_category = [ele for ele in all_possible_major_category if "理由" not in ele]
#     print('student intended major: ',all_possible_major_category)

#     # #==================step 3: get candidate program by intended majors======================
#     print('extend the intended major and search candidate program again...')
#     all_extended_majors = extend_multiple_intended_majors(api_key,all_possible_major_category,program_majors)
#     all_extended_majors = [ele for ele in all_extended_majors if ele in program_majors]
#     print('extended majors:',all_extended_majors)
#     df_candidate_program = get_candidate_program_from_majors(engine,table,all_extended_majors,columns = ['Major','Major_New'])
#     print('number of candidate program from extended intended majors: ',len(df_candidate_program))

#     # df_candidate_program = df_candidate_program.head(60)
#     print('reduce the number of candidate program...')
#     df_candidate_program = get_fixed_number_of_candidate_program(df_candidate_program,keep_num=60)
#     print('number of candidate program after reduction: ',len(df_candidate_program))

#     #==================step 4: get student score description===========================
#     print('get student score description...')
#     student_scores = get_student_all_score(student_doc_path)
#     print('student scores:',student_scores)

#     #==================step 5: filter program by exam and language====================
#     print('filter program by exam and language...')
#     print('be patient... it may take a few minutes to finish the comparison with llm ...')
#     keep_columns = ['Program_ID','Exam_Requirements','Language_Requirements']
#     df_candiate_program_filter = filter_program_by_exam_and_language(api_key,df_candidate_program[keep_columns], student_scores)
#     print('number of candidate program after comparing exam requirement with student exam score: ',len(df_candiate_program_filter))
#     #==================step 7: get final program and univ===========================
#     print('get more info of candidate program...')
#     df_candidate_program_info = pd.merge(df_candiate_program_filter[['Program_ID','Explanation']], df_all_program, on='Program_ID', how='left')
#     print('number of candidate program after merging with program info: ',len(df_candidate_program_info))

#     #==================step 6: rank program by majors===========================
#     print('rank program by majors...')
    
#     print('rank program by score and QS...')
#     final_candidate_program = rank_program_by_score_qs(df_candidate_program_info)
#     print('rank by majors...')
#     final_candidate_program = rank_program_by_majors(all_possible_major_category,final_candidate_program)
#     print('number of final candidate program: ',len(final_candidate_program))


#     #==================step 7: output final candidate program===========================
#     base_name = os.path.basename(student_doc_path).split('.')[0] + '.xlsx'
#     output_path = os.path.join(r'C:\Faliu\mizhou\eli\recommended_program',base_name)
#     final_candidate_program.to_excel(output_path,index=False)
#     print('output final candidate program to: ',output_path)

#     end_time = time.time()
#     print('total time cost: ',end_time - start_time)