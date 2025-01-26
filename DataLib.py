from pydantic import BaseModel

class Base_Info(BaseModel): 
    student_name: str = ''
    enrollment_date: str = ''
    grade: str = ''
    class_system: str = ''

class Subject_Score(BaseModel): 
    column1: str = ''
    column2: str = ''
    column3: str = ''
    column4: str = ''
    column5: str = ''
    column6: str = ''
    column7: str = ''
    column8: str = ''
    column9: str = ''
    column10: str = ''


class Background_Enhence(BaseModel):
    name: str = ''
    progress: str = ''
    timeline: str = ''
    expectation: str = ''

class Preference_Rank(BaseModel):
    top1 : str = ''
    top2 : str = ''
    top3 : str = ''
    supplimental: str = ''
    feature_explain: str = ''
    
        
class Student(BaseModel):
    name: str = ''
    id: str = ''
    grades: str = Subject_Score()