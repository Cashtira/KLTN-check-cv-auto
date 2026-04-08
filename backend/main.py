import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

# Import các module từ thư mục core
from core.extractor import extract_scientific_articles
from core.scorer import calculate_single_article_score

load_dotenv()

app = FastAPI(title="Hệ thống Kiểm tra LLKH Tự động")

# Cấu hình CORS để Frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo kết nối Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("CẢNH BÁO: Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env")
    
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cấu hình Pydantic Model cho đầu vào của API tính điểm đơn lẻ
class ArticleInput(BaseModel):
    title: str
    authors: str
    journal: str
    year: str

# CÁC API ENDPOINTS
@app.get("/")
async def root():
    return {
        "message": "Backend LLKH đã sẵn sàng!",
        "scope": "HĐGSNN Ngành CNTT 2025",
        "status": "Online"
    }

# API 1: Bóc tách bài báo từ file PDF
@app.post("/api/extract-cv")
async def upload_cv(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        data = extract_scientific_articles(temp_path)
        
        if not data:
            return {
                "filename": file.filename,
                "status": "Warning",
                "message": "Không tìm thấy dữ liệu bảng 7.1.a. File có thể là bản scan hoặc sai định dạng."
            }
        
        return {
            "filename": file.filename, 
            "total_articles": len(data), 
            "articles": data
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# API 2: Tính điểm cho MỘT bài báo cụ thể
@app.post("/api/score-article")
async def score_article(article: ArticleInput):
    try:
        score_result = calculate_single_article_score(
            supabase=supabase,
            title=article.title,
            authors=article.authors,
            journal_text=article.journal,
            year_str=article.year
        )
        return {
            "status": "Success",
            "data": score_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API 3: Bóc tách PDF và tự động chấm điểm toàn bộ CV
@app.post("/api/score-cv")
async def score_cv_full(file: UploadFile = File(...)):
    temp_path = f"temp_score_{file.filename}"
    try:
        # Bước 1: Lưu file PDF tạm
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Bước 2: Bóc tách dữ liệu
        extracted_data = extract_scientific_articles(temp_path)
        
        if not extracted_data:
            return {
                "filename": file.filename,
                "status": "Warning",
                "message": "Không tìm thấy dữ liệu bài báo khoa học trong PDF."
            }
        
        # Bước 3: Chạy vòng lặp chấm điểm cho từng bài
        scored_articles = []
        total_score = 0.0
        
        print(f"Bắt đầu chấm điểm {len(extracted_data)} bài báo cho hồ sơ: {file.filename}")
        
        for idx, article in enumerate(extracted_data):
            score_result = calculate_single_article_score(
                supabase=supabase,
                title=article["title"],
                authors="Không xác định", # Tạm thời chưa có logic bóc tách tác giả từ Mẫu 01
                journal_text=article["journal"],
                year_str=article["year"]
            )
            
            # Gắn thêm STT gốc từ PDF
            score_result["stt_pdf"] = article["stt"]
            scored_articles.append(score_result)
            total_score += score_result["max_score"]
            
            print(f"Đã chấm xong bài {idx + 1}/{len(extracted_data)}: {score_result['max_score']} điểm")
            
        # Bước 4: Trả về kết quả tổng quát
        return {
            "status": "Success",
            "filename": file.filename,
            "summary": {
                "total_articles": len(extracted_data),
                "total_max_score_estimated": total_score,
                "note": "Đây là điểm tối đa ước tính. Cần hội đồng kiểm tra các bài bị gắn cờ cảnh báo và xác định tác giả chính/phụ."
            },
            "detailed_scores": scored_articles
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)