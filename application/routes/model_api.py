import os
import time

from fastapi import APIRouter, Depends, UploadFile, Body, Form, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from tempfile import SpooledTemporaryFile
from fastapi.responses import StreamingResponse
import json
from typing import Generator

from .deepseek_api import DeepseekChatter  # 替换 OllamaStreamChatter
from ..core import get_current_user
from ..models import schemas
from ..orm.database import get_db
from ..orm import write_event, write_result, get_record_by_location, get_chat_record, get_all_chat_id, get_result, create_new_session, create_new_chat_records
from ..config import Settings

from ..net.predict import TonguePredictor
from ..services.constitution_service import ConstitutionAnalyzer

router_tongue_analysis = APIRouter()

feature_map = {
    "舌色": {
        0: "淡白舌",
        1: "淡红舌",
        2: "红舌",
        3: "绛舌",
        4: "青紫舌"
    },
    "舌苔颜色": {
        0: "白苔",
        1: "黄苔",
        2: "灰黑苔"
    },
    "厚薄": {
        0: "薄",
        1: "厚"
    },
    "腐腻": {
        0: "腻",
        1: "腐"
    }
}

def format_tongue_features(tongue_color,
                           coating_color,
                           tongue_thickness,
                           rot_greasy):
    """
    将舌诊特征数值转换为中文描述
    参数：
        tongue_color: 舌色（0-4）
        coating_color: 舌苔颜色（0-2）
        tongue_thickness: 厚薄（0-1）
        rot_greasy: 腐腻（0-1）
    返回：
        格式化后的特征字符串
    """
    try:
        features = [
            f"舌色：{feature_map['舌色'][tongue_color]}",
            f"舌苔颜色：{feature_map['舌苔颜色'][coating_color]}",
            f"厚薄：{feature_map['厚薄'][tongue_thickness]}",
            f"腐腻：{feature_map['腐腻'][rot_greasy]}"
        ]
        return "，".join(features)
    except KeyError as e:
        missing_key = int(str(e).split("'")[1])
        return f"错误：检测到无效特征值 {missing_key}，请检查输入范围"

class UserInput(BaseModel):
    input: str
@router_tongue_analysis.post('/session/{sessionId}')
async def upload(sessionId: int,
                 user_input: UserInput,
                 user: schemas.UserBase = Depends(get_current_user),
                 db: Session = Depends(get_db),
                 ):
    if not user:
        return schemas.BaseModel(
            code=101,
            message="can not find user",
            data=None
        )
    else:
        # user_input = "告诉我我的体质怎么样"
        bot = DeepseekChatter(
            system_prompt="你现在是一个专门用于舌诊的ai中医医生，我会在最开始告诉你用户舌头的四个图像特征，请你按照中医知识给用户一些建议"
        )
        create_new_chat_records(db=db, content=user_input.input, session_id=sessionId, role=1)
        return bot.chat_stream_add(user.id, db, sessionId)

class inputPicture(BaseModel):
    file_data: UploadFile
    user_input: str
    name: str
@router_tongue_analysis.post('/session')
async def upload(file_data: UploadFile = File(...),
                user_input: str = Form(...),
                name: str = Form(...),
                user: schemas.UserBase = Depends(get_current_user),
                db: Session = Depends(get_db)):
    try:
        if not user:
            return schemas.BaseModel(
                code=101,
                message="can not find user",
                data=None
            )

        # 模型分析
        def analysis(img: SpooledTemporaryFile, record_id: int, function):
            """
            模型分析
            :param img: 图片
            :param record_id: 事件id
            :param function: 保存结果的函数
            :return: None
            """
            predictor = TonguePredictor()
            predictor.predict(img=img, record_id=record_id, fun=function)

        # 保存图片
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file_data.filename)[1]
        filename = f"{timestamp}{file_extension}"
        file_location = f"{Settings.IMG_PATH}/{filename}"
        with open(file_location, "wb") as f:
            contents = await file_data.read()
            f.write(contents)
        f.close()

        # 写入事件
        img_db_path = f"{Settings.IMG_DB_PATH}/{filename}"
        code = write_event(user_id=user.id, img_src=img_db_path, state=0, db=db)

        # 模型调用
        if code == 0:  #成果分析结果
            record = get_record_by_location(img_db_path, db=db)
            analysis(img=file_data.file, record_id=record.id, function=write_result)
            #从这里开始会有很长一段时间的模型运行时间
            
            # 增加最大等待时间和检查间隔
            max_attempts = 30  # 30次 × 2秒 = 60秒
            attempt = 0
            
            while attempt < max_attempts:
                print(f"[INFO] 等待分析结果, 尝试次数: {attempt + 1}")
                result1 = get_result(img_db_path, db=db)
                if result1.state != 0:
                    break
                time.sleep(2)  # 增加间隔时间到2秒
                attempt += 1

            result = get_result(img_db_path, db=db)
            if result.state != 1:
                return schemas.BaseModel(
                    code=result.state,
                    message="图片有问题，请看code",
                    data=None
                )
            tongue_color = result.tongue_color
            coating_color = result.coating_color
            tongue_thickness = result.tongue_thickness
            rot_greasy = result.rot_greasy
            #此时4个特征都出来了
            
            # 在这里添加体质分析代码
            analyzer = ConstitutionAnalyzer()
            constitution_result = analyzer.analyze_constitution({
                "tongue_color": tongue_color,
                "coating_color": coating_color,
                "thickness": tongue_thickness,
                "rot_greasy": rot_greasy
            })
            
            # 合并分析结果
            feature = format_tongue_features(tongue_color, coating_color, 
                                            tongue_thickness, rot_greasy)
            
            combined_result = {
                "tongue_features": feature,
                "constitution_analysis": constitution_result.get("constitution_analysis", "")
            }
            
            #接下来开始对接deepseek
            # user_input = "告诉我我的体质怎么样
            bot = DeepseekChatter(
                system_prompt="你现在是一个专门用于舌诊的ai中医医生，我会在最开始告诉你用户舌头的四个图像特征，请你按照中医知识给用户一些建议"
            )
            new_message = create_new_session(ID=user.id, db=db, tittle=name)
            session_new_id = new_message.id
            create_new_chat_records(db=db, content=user_input, session_id=session_new_id, role=1)
            return bot.chat_stream_first(user_input, combined_result, user.id, db, session_new_id)
        else:
            return schemas.UploadResponse(
                code=201,
                message="operation failed",
                data=None
            )
    except Exception as e:
        return schemas.BaseModel(
            code=500,
            message=f"Internal server error: {str(e)}",
            data=None
        )

@router_tongue_analysis.get("/record/{sessionid}", response_model=schemas.ChatSessionRecordsResponse)
async def get_chat_records_by_session(sessionid: int,
                                      db: Session = Depends(get_db),
                                      user: schemas.UserBase = Depends(get_current_user)
                                      ):
    """
    获取用户的指定的对话记录
    :param sessionid: int
    :param db: Session, router传入的db，用于链接数据库
    :param user: User
    :return: ChatSessionRecordsResponse
    """
    if not user:
        return schemas.ChatSessionRecordsResponse(
            code=101,
            message="can not find user",
            data={"records": []}
        )
    else:
        chat_record = get_chat_record(ID=user.id, sessionid=sessionid, db=db)
        if chat_record == 102 or chat_record == 103:
            return schemas.ChatSessionRecordsResponse(
                code=chat_record,
                message="operation failed",
                data={"records": []}
            )
        else:
            records = []
            for record in chat_record:
                records.append(schemas.ChatRecordResponse(
                    content=record.content,
                    create_at=record.create_at,
                    role=record.role
                ))
            data_temp = {
                "records": records
            }
            return schemas.ChatSessionRecordsResponse(
                code=0,
                message="operation success",
                data=data_temp,
            )

@router_tongue_analysis.get("/session", response_model=schemas.SessionIdResponse)
async def get_chat_records_id(db: Session = Depends(get_db),
                              user: schemas.UserBase = Depends(get_current_user)):
    if not user:
        return schemas.SessionIdResponse(
            code=101,
            message="can not find user",
            data=[]
        )
    else:
        chat_id_records = get_all_chat_id(ID=user.id, db=db)
        data_temp = []
        for record in chat_id_records:
            data_temp.append(schemas.SessionId(
                session_id=record.id,
                name=record.tittle
            ))
        return schemas.SessionIdResponse(
            code=0,
            message="operation success",
            data=data_temp
        )

@router_tongue_analysis.post('/analyze-constitution')
async def analyze_constitution(
    tongue_color: str,
    coating_color: str,
    thickness: str,  
    rot_greasy: str,
    user: schemas.UserBase = Depends(get_current_user)
):
    """体质分析接口"""
    if not user:
        return schemas.ResponseModel(
            code=101,
            message="未找到用户信息",
            data=None
        )
        
    try:
        analyzer = ConstitutionAnalyzer()
        result = analyzer.analyze_constitution({
            "tongue_color": tongue_color,
            "coating_color": coating_color, 
            "thickness": thickness,
            "rot_greasy": rot_greasy
        })
        
        if not result["success"]:
            return schemas.ResponseModel(
                code=500,
                message="体质分析失败",
                data=None
            )
            
        return schemas.ResponseModel(
            code=0,
            message="分析成功",
            data=result
        )
        
    except Exception as e:
        return schemas.ResponseModel(
            code=500,
            message=f"服务器内部错误: {str(e)}",
            data=None
        )

