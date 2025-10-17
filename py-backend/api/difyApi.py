import os
import requests

DIFY_URL = "http://180.184.42.136/v1"
UPLOAD_FILE_URL = f"{DIFY_URL}/files/upload"
WORKFLOW_RUN_URL = f"{DIFY_URL}/workflows/run"

def upload_file(dify_api_key, upload_file_url, file_path, user: str = "wk") -> str:
    """
    上传文件到Dify API
    """
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        print(f"错误：file_path必须是字符串类型，当前类型为{type(file_path)}")
        return None
        
    headers = {
        "Authorization": f"Bearer {dify_api_key}"
    }
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    try:
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        # 根据文件扩展名确定文件类型和MIME类型
        if ext == "pdf":
            file_type = "PDF"
            mime_type = "application/pdf"
        elif ext == "docx":
            file_type = "DOCX"
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in ["md", "markdown"]:
            file_type = "MARKDOWN"
            mime_type = "text/markdown"
        elif ext == "txt":
            file_type = "TXT"
            mime_type = "text/plain"
        elif ext in ["jpg", "jpeg"]:
            file_type = "IMAGE"
            mime_type = "image/jpeg"
        elif ext == "png":
            file_type = "IMAGE"
            mime_type = "image/png"
        elif ext == "webp":
            file_type = "IMAGE"
            mime_type = "image/webp"
        elif ext == "gif":
            file_type = "IMAGE"
            mime_type = "image/gif"
        else:
            # 默认处理为文本文件
            file_type = "TXT"
            mime_type = "application/octet-stream"
            print(f"警告: 未识别的文件类型 '{ext}'，将作为二进制文件处理")
        
        print(f"上传文件中... 文件类型: {file_type}")
        with open(file_path, 'rb') as file:
            files = {
                'file': (filename, file, mime_type)
            }
            data = {
                "user": user,
                "type": file_type
            }
            
            response = requests.post(upload_file_url, headers=headers, files=files, data=data, verify=False)
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 201:
                print("文件上传成功")
                return response.json().get("id")
            else:
                print(f"文件上传失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
                
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {str(e)}")
        return None
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None

def run_workflow(data, workflow_run_url, dify_api_key="", response_mode="blocking"):
    user = f"ww"
    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }

    if "user" not in data:
        data["user"] = user

    if "response_mode" not in data:
        data["response_mode"] = response_mode

    try:
        print("运行工作流...")
        response = requests.post(workflow_run_url, headers=headers, json=data)
        if response.status_code == 200:
            print("工作流执行成功")
            response_data= response.json()
            return response_data
        else:
            print(f"工作流执行失败，状态码: {response.status_code}")
            return {"status": "error", "message": f"Failed to execute workflow, status code: {response.status_code}"}
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return {"status": "error", "message": str(e)}

def dify_get_file_content(file_path,dify_api_key=""):
    "先上传文件，再运行工作流，获取文件内容"
    api_token = "app-PqEJD4uzxPxFL3lY1zq1fbM3" if not dify_api_key else dify_api_key

    # 第一步
    file_id = upload_file(
        dify_api_key = api_token,
        upload_file_url = UPLOAD_FILE_URL,
        file_path = file_path
    )

    print("文件id为：", file_id)

    workflow_run_data = {
        "inputs": {
            "file": {
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "document"
            }
        }
    }

    # 第二步
    workflow_result = run_workflow(
        data = workflow_run_data,
        workflow_run_url = WORKFLOW_RUN_URL,
        dify_api_key = api_token
    )

    if workflow_result["data"]["status"] == "succeeded":
        print("文档内容提取工作流运行成功")
        file_content = workflow_result["data"]["outputs"]["result"]
        if "key_words" in workflow_result["data"]["outputs"]:
            key_words = workflow_result["data"]["outputs"]["key_words"]
            return file_content, key_words
        return file_content, {}
    else:
        print("文档内容提取工作流运行失败")
        return None

def dify_get_keywords(file_name:str="",file_content:str=""):
    """
    调用 Dify 工作流，根据文件名字与文件内容提取关键信息（标题、摘要、起效/废止时间等）。
    """
    api_token = "app-70cbxYWSjSjzhIg2WciXgpCi"

    payload = {
        "inputs": {
            "name": file_name or "",
            "file_content": file_content or "",
        },
        "response_mode": "blocking",
        "user": "ww",
    }

    try:
        result = run_workflow(
            data=payload,
            workflow_run_url=WORKFLOW_RUN_URL,
            dify_api_key=api_token,
            response_mode="blocking",
        )

        data = result.get("data", {}) if isinstance(result, dict) else {}
        if data.get("status") == "succeeded":
            outputs = data.get("outputs", {})
            return outputs.get("result")
        else:
            # 返回 None 表示失败或未就绪
            return None
    except Exception as e:
        print(f"获取政策关键信息失败: {str(e)}")
        return None

# dify知识库操作：