from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
import os
import tempfile 
import shutil
import json
import re

# 导入现有的功能模块
from api.difyApi import dify_get_file_content
from src.doc_structure_recognition import build_segments_struct,format_segments_output
from src.utils import save_segments2csv,build_toc
from src.pydantic_models import DocumentTOCResponse

app = FastAPI(
    title='一致性检查',
    description='政策文件一致性检查后端api',
    version='1.0.0'
)

@app.post("/api/extract-segments", response_model=DocumentTOCResponse)
async def extract_document_segments(
    file: UploadFile = File(...),
    save: bool = Form(False)
):
    """
    上传文档并提取分段内容
    """
    temp_file_path = None
    
    try:
        # 验证文件类型
        allowed_extensions = ['.txt', '.pdf', '.docx', '.md']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型': {file_extension}。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        # 获取文档内容
        file_content,key_words = dify_get_file_content(temp_file_path)
        
        if not file_content:
            raise HTTPException(
                status_code=500,
                detail='文档内容提取失败，请检查文件格式或Dify服务状态'
            )
        
        # 提取分段
        file_struct = build_segments_struct(
                                file_content = file_content,
                                file_name = file.filename
                            )
        segments = file_struct["segments"]
        
        if not segments:
            raise HTTPException(
                status_code=422,
                detail='未能从文档中提取到有效的政策条款，请检查文档格式'
            )

        # 创建树状返回结果
        toc_tree, counts = build_toc(segments)

        # 保留原有保存 CSV 的能力（使用扁平化文本输出）
        formatted_output = format_segments_output(
                        file_name=os.path.splitext(file.filename)[0],
                        segments=segments)
        
        if save:
            csv_file_path = save_segments2csv(
                formatted_output,
                file_name = os.path.splitext(file.filename)[0],
                output_dir = "E:/MyProjects/policy-consistency-check/py-backend/output"
            )
            print("已保存在：", csv_file_path)

            return {
                "success": True,
                "file": {"name": file.filename},
                "toc": toc_tree,
                "counts": counts,
                "save_path": csv_file_path
            }

        return {
            "success": True,
            "file": {"name": file.filename},
            "toc": toc_tree,
            "counts": counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=10010
    )
