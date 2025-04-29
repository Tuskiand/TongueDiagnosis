from openai import OpenAI
import os

class APIConfig:
    API_KEY = os.getenv('DASHSCOPE_API_KEY')
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL = "qwq-plus-latest"  # 使用百炼 deepseek-r1 模型
    
    # 添加体质辨识的系统提示
    CONSTITUTION_PROMPT = """
    你现在是一个专业的中医师,需要根据病人的舌象特征判断其体质类型。
    已知九种体质类型:平和质、气虚质、阳虚质、阴虚质、痰湿质、湿热质、血瘀质、气郁质、特禀质。
    请根据以下舌象特征,分析可能的体质类型(可以是多种),并给出详细的分析依据和调理建议:
    1. 舌色特征:{tongue_color}
    2. 舌苔颜色:{coating_color} 
    3. 舌苔厚薄:{thickness}
    4. 是否腐腻:{rot_greasy}
    """
    
    @classmethod
    def get_client(cls):
        return OpenAI(
            api_key=cls.API_KEY,
            base_url=cls.BASE_URL
        )