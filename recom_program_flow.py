import os
from recom_program_main import *


if __name__ == "__main__":
    start_time = time.time()

    #==================basic info==========================================
    print('initialization...')
    host = "eli-tech.cd2ep9f6ojwf.us-east-2.rds.amazonaws.com"
    user = "Eli_education"
    password = "EliEducation2024!"
    database = "Hailiang"
    table = "UK_program_undergrad"
    engine = connect_mysql_database(host, user, password, database)
    columns = ['Major','Major_New']  

    api_key = "sk-4dba8c314a964f15a6774089d754aef2"

    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2A（雨妗）\丁子淇--Alevel数据采集.docx'
    student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2E (思雨)\数据采集要求-杜俊熙.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASE(杨怡)\数据采集--任绪鑫.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部ASF(雨田_佳铭)_\数据采集--仵同悦.docx'
    # student_doc_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel 致远部G2D(杨怡)\数据采集--吴众豪.docx'
    
    #==================step 0: get all candidate programs==================
    print('get all candidate programs...')
    df_all_program = get_all_candidate_program_univ(engine)
    print('number of all programs: ',len(df_all_program))

    #==================step 1: get all programs majors=====================
    print('get all programs majors...')
    program_majors = get_all_program_majors(engine,table,columns)
    print('number of all majors: ',len(program_majors))

    #==================step 2: get student intended major==================
    print('get student intended major...')
    intended_major, intended_category = get_student_intended_major(student_doc_path)
    all_possible_major_category = intended_major + intended_category
    all_possible_major_category = [ele for ele in all_possible_major_category if len(ele)>1]
    all_possible_major_category = remove_duplicates_preserve_order(all_possible_major_category)
    all_possible_major_category = [ele for ele in all_possible_major_category if "理由" not in ele]
    print('student intended major: ',all_possible_major_category)

    # #==================step 3: get candidate program by intended majors======================
    print('extend the intended major and search candidate program again...')
    all_extended_majors = extend_multiple_intended_majors(api_key,all_possible_major_category,program_majors,select_model='doubao')
    all_extended_majors = [ele for ele in all_extended_majors if ele in program_majors]
    all_extended_majors = all_extended_majors[:3*len(all_possible_major_category)]
    print('extended majors:',all_extended_majors)
    df_candidate_program = get_candidate_program_from_majors(engine,table,all_extended_majors,columns = ['Major','Major_New'])
    print('number of candidate program from extended intended majors: ',len(df_candidate_program))

    # df_candidate_program = df_candidate_program.head(60)
    print('reduce the number of candidate program...')
    df_candidate_program = get_fixed_number_of_candidate_program(df_candidate_program,keep_num=60)
    print('number of candidate program after reduction: ',len(df_candidate_program))

    #==================step 4: get student score description===========================
    print('get student score description...')
    student_scores = get_student_all_score(student_doc_path)
    print('student scores:',student_scores)

    #==================step 5: filter program by exam and language====================
    print('filter program by exam and language...')
    print('be patient... it may take a few minutes to finish the comparison with llm ...')
    keep_columns = ['Program_ID','Exam_Requirements','Language_Requirements']
    df_candiate_program_filter = filter_program_by_exam_and_language(api_key,df_candidate_program[keep_columns], student_scores,select_model='doubao')
    print('number of candidate program after comparing exam requirement with student exam score: ',len(df_candiate_program_filter))
    #==================step 7: get final program and univ===========================
    print('get more info of candidate program...')
    df_candidate_program_info = pd.merge(df_candiate_program_filter[['Program_ID','Explanation','Language']], df_all_program, on='Program_ID', how='left')
    print('number of candidate program after merging with program info: ',len(df_candidate_program_info))

    #==================step 6: rank program by majors===========================
    print('rank program by majors...')
    
    print('rank program by score and QS...')
    final_candidate_program = rank_program_by_score_qs(df_candidate_program_info)
    print('rank by majors...')
    final_candidate_program = rank_program_by_majors(all_possible_major_category,final_candidate_program)
    print('number of final candidate program: ',len(final_candidate_program))


    #==================step 7: output final candidate program===========================
    base_name = os.path.basename(student_doc_path).split('.')[0] + '.xlsx'
    output_path = os.path.join(r'C:\Faliu\mizhou\eli\recommended_program',base_name)
    final_candidate_program.to_excel(output_path,index=False)
    print('output final candidate program to: ',output_path)

    end_time = time.time()
    print('total time cost: ',end_time - start_time)