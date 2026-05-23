import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

# Import các module từ thư mục core
from core.extractor import extract_scientific_articles
from core.scorer import calculate_single_article_score

load_dotenv()

app = FastAPI(title="Hệ thống Kiểm tra LLKH Tự động")

# Cấu hình CORS để Frontend gọi API local
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
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Cấu hình Pydantic Model - Tính điểm lẻ bên trái
class ArticleInput(BaseModel):
    title: str
    authors: str = "Không xác định"
    journal: str
    year: str
    author_count: int = 1  
    is_main: bool = True   
    candidate_name: str = "Nguyễn Minh Kha"


@app.get("/")
async def root():
    return {
        "message": "Backend LLKH đã sẵn sàng!",
        "scope": "HĐGSNN Ngành CNTT 2025",
        "status": "Online"
    }


# API 1: Bóc tách bài báo từ file PDF (Thuần thô)
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
            is_main=article.is_main,
            candidate_name=article.candidate_name             
        )
        return {
            "status": "Success",
            "data": score_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API 3: Bóc tách PDF và tự động KIỂM KÊ - LƯU LỊCH SỬ DASHBOARD PHÂN QUYỀN
@app.post("/api/score-cv")
async def score_cv_full(
    file: UploadFile = File(...), 
    candidate_name: str = Form("Nguyễn Minh Kha"), # <-- ĐÃ ĐỔI THÀNH MINH KHA
    user_id: str = Form(...) # <-- ĐÃ BỔ SUNG: Hứng mã định danh từ Frontend gửi lên ngầm
):
    temp_path = f"temp_score_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extracted_data = extract_scientific_articles(temp_path)
        
        if not extracted_data:
            return {
                "filename": file.filename,
                "status": "Warning",
                "message": "Không tìm thấy dữ liệu bài báo khoa học trong PDF."
            }
        
        scored_articles = []
        total_score = 0.0
        
        for idx, article in enumerate(extracted_data):
            try:
                title = article.get("title", "Không rõ tên bài báo")
                journal = article.get("journal", "Không rõ tạp chí")
                year = article.get("year", "N/A")
                stt = article.get("stt", idx + 1)
                
                raw_author_count = article.get("author_count", 1)
                try:
                    author_count = int(raw_author_count) if raw_author_count else 1
                except:
                    author_count = 1  
                
                is_main = article.get("is_main", True)
                if isinstance(is_main, str):
                    is_main = True if is_main.lower() in ['true', 'có', 'yes', '1'] else False
                elif is_main is None:
                    is_main = True

                score_result = calculate_single_article_score(
                    supabase=supabase,
                    title=title,
                    authors="Không xác định",
                    journal_text=journal,
                    year_str=str(year),
                    author_count=author_count,
                    is_main=is_main,
                    candidate_name=candidate_name
                )
                
                score_result["journal"] = journal
                score_result["stt_pdf"] = stt
                score_result["author_count"] = author_count
                score_result["is_main"] = is_main
                scored_articles.append(score_result)
                total_score += score_result["max_score"]
            
            except Exception as inner_e:
                print(f"CẢNH BÁO: Bỏ qua dòng lỗi số {idx + 1}: {inner_e}")
                continue  
            
        # --- ĐOẠN GHI NHẬT KÝ ĐÃ ĐƯỢC ĐỒNG BỘ CỘT USER_ID ---
        if scored_articles:
            valid_score = sum(
                art["max_score"] for art in scored_articles 
                if art.get("check_title", {}).get("status") is True 
                and art.get("check_author_count", {}).get("status") is True
            )
            
            correct_count = sum(
                1 for art in scored_articles 
                if art.get("check_title", {}).get("status") is True 
                and art.get("check_author_count", {}).get("status") is True
            )
            accuracy_rate = (correct_count / len(scored_articles) * 100) if len(scored_articles) > 0 else 0.0
            
            # Đóng gói dữ liệu truyền trực tiếp xuống bảng cv_histories
            history_payload = {
                "user_id": user_id, # <-- ĐÃ BỔ SUNG: Truyền ID tài khoản xuống DB
                "file_name": file.filename,
                "candidate_name": candidate_name,
                "total_articles": len(scored_articles),
                "valid_score": round(float(valid_score), 2),
                "total_score": round(float(total_score), 2),
                "accuracy_rate": round(float(accuracy_rate), 2)
            }
            
            try:
                supabase.table("cv_histories").insert(history_payload).execute()
                print(f"-> Đã lưu lịch sử thẩm định hồ sơ {candidate_name} xuống Supabase thành công!")
            except Exception as db_e:
                print(f"-> Lỗi ghi log lịch sử xuống database: {db_e}")

        return {
            "status": "Success",
            "filename": file.filename,
            "summary": {
                "total_articles": len(scored_articles),  
                "total_max_score_estimated": total_score
            },
            "detailed_scores": scored_articles
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống nghiêm trọng: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)