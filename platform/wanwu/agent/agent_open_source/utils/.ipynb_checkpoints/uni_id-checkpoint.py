
import uuid

def generate_unique_id():
    unique_id = str(uuid.uuid4())  # 生成一个带破折号的UUID
    return unique_id.replace('-', '')  # 移除破折号
