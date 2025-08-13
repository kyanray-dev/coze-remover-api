import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from rembg import remove

# --- Pydantic模型：用于验证输入数据 ---
class ImageRequest(BaseModel):
    image_url: HttpUrl # 使用HttpUrl可以自动验证URL格式

# --- FastAPI应用实例 ---
app = FastAPI(
    title="Image Background Remover API",
    description="An API that takes an image URL, removes its background, and returns a new URL.",
    version="1.0.0",
)

# --- 从环境变量获取API密钥 (更安全的做法) ---
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "712e89fbd37f506fb7067aed31bf4bbf")

@app.get("/", summary="Root Endpoint", description="A simple hello world endpoint to check if the service is running.")
async def read_root():
    """ A simple endpoint to check if the service is online. """
    return {"message": "Image Background Remover API is running."}

@app.post("/process-image/", summary="Remove Image Background", description="Downloads an image, removes the background, and uploads the result.")
async def process_image(request: ImageRequest) -> dict:
    """
    This endpoint takes an image URL, removes the background,
    and returns the URL of the processed image.
    """
    try:
        # 1. 下载图片
        download_response = requests.get(str(request.image_url), timeout=15)
        download_response.raise_for_status() # 如果下载失败，会抛出异常
        input_image_bytes = download_response.content

        # 2. 移除背景
        output_image_bytes = remove(input_image_bytes)

        # 3. 上传到 imgbb
        upload_url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
        files_to_upload = {
            'image': ('no-bg.png', output_image_bytes, 'image/png')
        }
        upload_response = requests.post(upload_url, files=files_to_upload, timeout=30)
        upload_response.raise_for_status() # 如果上传失败，会抛出异常

        result_json = upload_response.json()

        # 4. 返回结果
        if result_json.get("success"):
            return {"processed_image_url": result_json["data"]["url"]}
        else:
            error_message = result_json.get("error", {}).get("message", "Unknown error from imgbb API")
            raise HTTPException(status_code=500, detail=f"imgbb API error: {error_message}")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Network error or invalid image URL: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")