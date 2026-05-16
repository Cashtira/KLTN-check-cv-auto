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


# Cấu hình Pydantic Model - Nâng cấp để hỗ trợ tính điểm lẻ theo Điều 8
class ArticleInput(BaseModel):
    title: str
    authors: str = "Không xác định"
    journal: str
    year: str
    author_count: int = 1  # (mặc định là 1 tác giả)
    is_main: bool = True   # (mặc định là tác giả chính)


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
                "message": "Không tìm thấy dữ liệu bảng 7.1.a."
            }
        
        return {
            "filename": file.filename, 
            "total_articles": len(data), 
            "articles": data
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# API 2: Tính điểm cho MỘT bài báo cụ thể (Bộ tính lẻ bên trái)
@app.post("/api/score-article")
async def score_article(article: ArticleInput):
    try:
        score_result = calculate_single_article_score(
            supabase=supabase,
            title=article.title,
            authors=article.authors,
            journal_text=article.journal,
            year_str=article.year,
            author_count=article.author_count,  
            is_main=article.is_main             
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
        
        # Bước 2: Bóc tách dữ liệu từ AI
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
            # TẦNG BẢO VỆ TỪNG DÒNG: Nếu một bài lỗi, bỏ qua và chạy tiếp bài sau chứ không làm sập API
            try:
                # Sử dụng .get() để phòng thủ tối đa lỗi KeyError (thiếu trường thông tin)
                title = article.get("title", "Không rõ tên bài báo")
                journal = article.get("journal", "Không rõ tạp chí")
                year = article.get("year", "N/A")
                stt = article.get("stt", idx + 1)
                
                # Kiểm tra và ép kiểu an toàn cho Số tác giả (author_count)
                raw_author_count = article.get("author_count", 1)
                try:
                    author_count = int(raw_author_count) if raw_author_count else 1
                except:
                    author_count = 1  # Fallback nếu AI trả về định dạng chữ lạ
                
                # Kiểm tra tư cách tác giả chính (is_main)
                is_main = article.get("is_main", True)
                if isinstance(is_main, str):
                    is_main = True if is_main.lower() in ['true', 'có', 'yes', '1'] else False
                elif is_main is None:
                    is_main = True

                # Gọi hàm tính điểm đã nâng cấp Điều 8
                score_result = calculate_single_article_score(
                    supabase=supabase,
                    title=title,
                    authors="Không xác định",
                    journal_text=journal,
                    year_str=str(year),
                    author_count=author_count,
                    is_main=is_main
                )
                
                score_result["journal"] = journal

                # Gắn thêm STT gốc từ PDF để hiển thị lên bảng
                score_result["stt_pdf"] = stt
                score_result["author_count"] = author_count
                score_result["is_main"] = is_main
                scored_articles.append(score_result)
                total_score += score_result["max_score"]
                
                print(f"Đã chấm xong bài {idx + 1}/{len(extracted_data)}: {score_result['max_score']} điểm")
            
            except Exception as inner_e:
                print(f"CẢNH BÁO: Bỏ qua bài số {idx + 1} do lỗi xử lý dữ liệu: {inner_e}")
                continue  # Lệnh này giúp vòng lặp nhảy sang bài tiếp theo ngay lập tức
            
        # Bước 4: Trả về kết quả tổng quát cho Frontend
        return {
            "status": "Success",
            "filename": file.filename,
            "summary": {
                "total_articles": len(scored_articles),  # Chỉ đếm số bài tính điểm thành công
                "total_max_score_estimated": total_score,
                "note": "Hệ thống đã tự động quy đổi điểm theo Điều 8 (Tác giả chính hưởng 1/3, phần còn lại chia đều)."
            },
            "detailed_scores": scored_articles
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống nghiêm trọng: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)