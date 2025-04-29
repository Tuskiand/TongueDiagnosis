import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.api_config import APIConfig

def test_api():
    try:
        client = APIConfig.get_client()
        # 修改: 启用 stream=True
        response = client.chat.completions.create(
            model=APIConfig.MODEL,
            messages=[
                {"role": "system", "content": "你是一个中医舌诊助手,需要根据舌象特征为用户提供健康建议"},
                {"role": "user", "content": "你好"}
            ],
            stream=True  # 修改这里，启用流式模式
        )
        
        print("✅ API测试开始...")
        full_response = ""
        # 修改: 处理流式响应
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                print(f"接收到内容: {content}", end="", flush=True)
        
        print("\n✅ API测试成功！")
        print(f"完整回复: {full_response}")
        return True
        
    except Exception as e:
        print(f"❌ API测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_api()