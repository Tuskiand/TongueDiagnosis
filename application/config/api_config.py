from openai import OpenAI
import os

class APIConfig:
    API_KEY = os.getenv('DASHSCOPE_API_KEY')
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL = "deepseek-r1"  # 使用百炼 deepseek-r1 模型
    
    @classmethod
    def get_client(cls):
        return OpenAI(
            api_key=cls.API_KEY,
            base_url=cls.BASE_URL
        )