# 所有函数定义在recom_program_major_v0.py中

# 使用说明

主要有以下几个步骤：

1. 获取大类专业并建立Faiss索引，调用函数 create_major_index()  
2. 获取项目并建立Faiss索引，调用函数 create_program_index()  
3. 提取用户输入的意向专业小类，意向专业小类备注信息，意向专业大类，以及用户输入的其他信息 这四类信息  
4. 根据提取到的用户输入信息，建立一个项目的黑名单和白名单，黑名单就是在之后不应该出现在推荐里的，白名单是可以出现在推荐里的  
5. 根据用户输入的意向专业小类进行项目推荐：调用函数 get_program_from_intended_major()  
6. 根据用户输入的意向专业小类其他备注信息进行项目推荐：调用函数 get_program_from_intended_major_other()  
7. 根据用户输入的意向专业大类进行专业推荐：调用函数 get_major_from_intended_category()  
8. 根据用户输入的其他信息进行专业推荐：调用函数 get_major_from_other_info()  


