import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.api_config import APIConfig
def test_api():
    try:
        client = APIConfig.get_client()
        response = client.chat.completions.create(
            model=APIConfig.MODEL,
            messages=[
                {"role": "system", "content": "你是一个中医舌诊助手,需要根据舌象特征为用户提供健康建议"},
                {"role": "user", "content": "你好"}
            ],
            stream=False
        )
        print("✅ API测试成功！")
        print(f"思考过程：{response.choices[0].message.reasoning_content}")
        print(f"最终答案：{response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ API测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_api()