from ..config.api_config import APIConfig
from openai import OpenAI

class ConstitutionAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            api_key=APIConfig.API_KEY,
            base_url=APIConfig.BASE_URL
        )
    
    def analyze_constitution(self, tongue_features):
        """根据舌象特征分析体质"""
        prompt = APIConfig.CONSTITUTION_PROMPT.format(
            tongue_color=tongue_features['tongue_color'],
            coating_color=tongue_features['coating_color'],
            thickness=tongue_features['thickness'],
            rot_greasy=tongue_features['rot_greasy']
        )
        
        try:
            response = self.client.chat.completions.create(
                model=APIConfig.MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                "success": True,
                "constitution_analysis": response.choices[0].message.content,
                "features": tongue_features
            }
            
        except Exception as e:
            print(f"[ERROR] 体质分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }