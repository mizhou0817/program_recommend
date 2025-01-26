from io import BytesIO

from docx import Document

# from agents.data_preprocess.DataLib import Subject_Score, Background_Enhence, Preference_Rank
from DataLib import Subject_Score, Background_Enhence, Preference_Rank


class docx_parser():
    def __init__(self):
        pass

    @staticmethod
    def base_info_parser(lst):
        return {
            'student_name': lst[1][1],
            'grade': lst[2][1],
            'class_system': lst[3][1],
            'enrollment_date': lst[4][1],
        }
    
    @staticmethod
    def score_parser(lst):
        fields = list(Subject_Score.__fields__.keys())
        result = {}
        # 先添加必须的列名
        if len(lst) > 0:
            result['column_name'] = Subject_Score(**dict(zip(fields, lst[0][:])))
        # 动态添加每一行成绩
        row_names = ['row1', 'row2', 'row3', 'row4', 'row5', 'row6', 'row7', 'row8']
        for i in range(1, min(len(lst),8)):  # 最多处理8行成绩
            result[row_names[i-1]] = Subject_Score(**dict(zip(fields, lst[i][:])))  
        return result

    @staticmethod
    def BE_parser(lst):
        fields = list(Background_Enhence.__fields__.keys())
        result = []
        for item in lst[1:]:
            be = Background_Enhence(**dict(zip(fields, item[1:])))
            result.append(be)
        return result

    @staticmethod
    def pre_parser(lst):
        fields = list(Preference_Rank.__fields__.keys())
        result = {}
        preference_keys = ['area', 'major', 'category_student', 'school', 
                         'category_consultant', 'grade1_subject', 'grade2_subject', 'supplimental']
        feature_explain = ['学生申请学校偏好地区','学生及家长申请本科的意向专业，可能是关键词也可能是专业名称','学生及家长申请本科的大类，应属于supplimental中给出五个大类中的某一个','学生及家长申请本科的意向学校','顾问帮助学生推荐的申请本科的大类','','','','']

        for i, key in enumerate(preference_keys, 1):
            if i < len(lst):
                result[key] = Preference_Rank(**dict(zip(fields, lst[i][1:])))
                result[key].feature_explain = feature_explain[i-1]
        return result

    def parse(self, docx_path):
        if isinstance(docx_path, bytes):
            file_stream = BytesIO(docx_path)
            doc = Document(file_stream)
        else:
            doc = Document(docx_path)
        tables_data = []
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)

            tables_data.append(table_data)

        base_info = docx_parser.base_info_parser(tables_data[0])
        score = docx_parser.score_parser(tables_data[1])
        be = docx_parser.BE_parser(tables_data[2])
        intention = docx_parser.pre_parser(tables_data[3])
        addition_info = ['\n'.join(x) for x in tables_data[4]]

        return {
            'student_base_info': base_info,
            'student_score': score,
            'background_enhance': be,
            'student_preference': intention,
            'addition_info': addition_info
        }



# if __name__ == "__main__":
#     docx_path = r'C:\Faliu\mizhou\eli\数据采集1.10\数据采集1.10\Alevel\Alevel G2A（雨妗）\丁子淇--Alevel数据采集.docx'
#     docx = docx_parser()
#     result = docx.parse(docx_path)
#     print(result)