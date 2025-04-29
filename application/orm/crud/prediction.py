from sqlalchemy.orm import Session
from ..models.prediction import TonguePrediction
from typing import Optional

def get_prediction_by_record_id(db: Session, record_id: str) -> Optional[TonguePrediction]:
    """获取指定record_id的舌像预测记录"""
    return db.query(TonguePrediction).filter(TonguePrediction.record_id == record_id).first()

def create_prediction(db: Session, record_id: str, status_code: int = 0) -> TonguePrediction:
    """创建新的舌像预测记录"""
    prediction = TonguePrediction(
        record_id=record_id,
        status_code=status_code
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction

def update_prediction(
    db: Session, 
    record_id: str, 
    tongue_color: Optional[str] = None,
    coating_color: Optional[str] = None,
    tongue_thickness: Optional[str] = None,
    rot_greasy: Optional[str] = None,
    status_code: Optional[int] = None
) -> Optional[TonguePrediction]:
    """更新舌像预测记录"""
    prediction = get_prediction_by_record_id(db, record_id)
    if not prediction:
        return None
    
    # 更新非空字段
    if tongue_color is not None:
        prediction.tongue_color = tongue_color
    if coating_color is not None:
        prediction.coating_color = coating_color
    if tongue_thickness is not None:
        prediction.tongue_thickness = tongue_thickness
    if rot_greasy is not None:
        prediction.rot_greasy = rot_greasy
    if status_code is not None:
        prediction.status_code = status_code
    
    db.commit()
    db.refresh(prediction)
    return prediction