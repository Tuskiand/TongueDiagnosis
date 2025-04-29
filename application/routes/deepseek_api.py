from openai import OpenAI
import json
from starlette.responses import JSONResponse, StreamingResponse
from ..orm import create_new_chat_records, get_chat_record
from ..config.api_config import APIConfig

class DeepseekChatter:
    def __init__(self, system_prompt=None):
        self.client = APIConfig.get_client()
        self.messages = []
        
        # 初始化系统提示
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

    def chat_stream_first(self, user_input, feature, id, db, session_new_id):
        """首次对话流式响应"""
        self.messages = []
        self.messages.append({
            "role": "user",
            "content": f"舌象特征是{feature}, {user_input}"
        })

        try:
            response = self.client.chat.completions.create(
                model=APIConfig.MODEL,
                messages=self.messages,
                stream=True
            )

            def generate():
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield json.dumps({
                            "token": content,
                            "session_id": session_new_id,
                            "is_complete": False
                        }) + "\n"

                yield json.dumps({
                    "token": full_response,
                    "session_id": session_new_id,
                    "is_complete": True
                }) + "\n"

                self._save_to_db_async(db, full_response, session_new_id)

            return StreamingResponse(
                generate(),
                media_type='application/x-ndjson'
            )

        except Exception as e:
            print(f"[ERROR] API调用失败: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"API调用失败: {str(e)}"}
            )

    def chat_stream_add(self, id, db, session_id):
        """后续对话流式响应"""
        chat_records = get_chat_record(ID=id, sessionid=session_id, db=db)
        messages = []
        
        for record in chat_records:
            role = "user" if record.role == 1 else "assistant"
            messages.append({"role": role, "content": record.content})
        
        self.messages = messages

        try:
            response = self.client.chat.completions.create(
                model=APIConfig.MODEL,
                messages=self.messages,
                stream=True
            )

            def generate():
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield json.dumps({
                            "token": content,
                            "session_id": session_id,
                            "is_complete": False
                        }) + "\n"

                yield json.dumps({
                    "token": full_response,
                    "session_id": session_id,
                    "is_complete": True
                }) + "\n"

                self._save_to_db_async(db, full_response, session_id)

            return StreamingResponse(
                generate(),
                media_type='application/x-ndjson'
            )

        except Exception as e:
            print(f"[ERROR] API调用失败: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"API调用失败: {str(e)}"}
            )

    def _save_to_db_async(self, db, content, session_id):
        """异步保存对话记录"""
        import threading
        def save_task():
            try:
                create_new_chat_records(
                    db=db,
                    content=content,
                    session_id=session_id,
                    role=2
                )
            except Exception as e:
                print(f"[ERROR] 数据库保存失败: {str(e)}")

        threading.Thread(target=save_task).start()