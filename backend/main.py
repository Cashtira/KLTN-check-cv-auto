import os
import shutil
import pdfplumber
import re
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hệ thống Kiểm tra LLKH Tự động")

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

# LOGIC BÓC TÁCH BẢNG 7.1.a
def extract_scientific_articles(pdf_path):
    articles = []
    # Tìm mục 7.1 hoặc 7.1.a có chữ Bài báo khoa học
    start_pattern = re.compile(r"7\.1(\.a)?\.?\s*Bài báo khoa học", re.IGNORECASE)
    # Dừng lại khi gặp mục lớn tiếp theo (7.1.b, 7.2 hoặc 8)
    stop_pattern = re.compile(r"7\.1\.b|7\.2|8\.", re.IGNORECASE)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            is_collecting = False
            
            for page in pdf.pages:
                text = page.extract_text() or ""
                
                # Bật chế độ bóc tách khi thấy tiêu đề mục 7.1.a
                if start_pattern.search(text):
                    is_collecting = True
                
                if is_collecting:
                    tables = page.extract_tables()
                    for table in tables:
                        # Chỉ lấy bảng có đúng 9 cột (chuẩn Mẫu 01 mục 7.1.a)
                        # Giúp loại bỏ bảng Phần 6 (6 cột) và các bảng rác khác
                        if not table or len(table[0]) < 8 or len(table[0]) > 10:
                            continue
                        
                        for row in table:
                            clean_row = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                            
                            # Nhận diện STT (Phải là số ở cột đầu tiên)
                            stt_raw = clean_row[0].rstrip('.')
                            if stt_raw.isdigit():
                                title = clean_row[1]
                                # Chỉ lấy nếu tên bài báo đủ dài để tránh lấy nhầm tiêu đề bảng
                                if title and len(title) > 15:
                                    articles.append({
                                        "stt": stt_raw,
                                        "title": title,
                                        "journal": clean_row[4] if len(clean_row) > 4 else "",
                                        "year": clean_row[8] if len(clean_row) > 8 else ""
                                    })
                
                # Dừng lại khi thấy tiêu đề mục 8 (Chủ trì đề tài)
                if is_collecting and "8. Chủ trì" in text:
                    break
                    
    except Exception as e:
        print(f"Lỗi: {e}")
    
    # Loại bỏ trùng lặp nếu bảng bị lặp lại ở trang sau
    final_data = []
    seen = set()
    for a in articles:
        if a['title'].lower() not in seen:
            final_data.append(a)
            seen.add(a['title'].lower())
            
    return final_data

# Các API Endpoint

@app.get("/")
async def root():
    return {
        "message": "Backend LLKH đã sẵn sàng và kết nối Supabase!",
        "scope": "Ưu tiên ngành CNTT",
        "status": "Online"
    }

# API Thêm dữ liệu mẫu
@app.post("/api/seed-data")
async def seed_data():
    sample_articles = [
        {
            "title": "Nghiên cứu về Deep Learning trong chẩn đoán hình ảnh",
            "authors": "Nguyễn Văn A, Trần Thị B",
            "journal_name": "Tạp chí Khoa học và Công nghệ",
            "year": 2023,
            "doi": "10.1234/test.doi.001"
        },
        {
            "title": "Ứng dụng Blockchain trong quản lý chuỗi cung ứng",
            "authors": "Lê Văn C",
            "journal_name": "Kỷ yếu hội thảo quốc gia",
            "year": 2022,
            "doi": "10.5678/blockchain.2022"
        }
    ]
    # Chèn dữ liệu vào bảng 'articles'
    response = supabase.table("articles").insert(sample_articles).execute()
    return {"status": "Success", "data": response.data}

# API Tìm kiếm mờ
@app.get("/api/search")
async def search_article(query: str):
    if not query:
        return {"results": []}

    try:
        # Gọi hàm mới có trả về score
        response = supabase.rpc("search_articles_with_score", {"search_text": query}).execute()
        
        final_results = []
        for item in response.data:
            score = item["similarity_score"]
            
            # Logic phân loại nhãn
            if score >= 0.85:
                status = "Đúng"
            elif score >= 0.4:
                status = "Có thể tồn tại (Cần kiểm tra lại)"
            else:
                status = "Không giống nhiều"
            
            item["status_label"] = status
            final_results.append(item)

        # Nếu không có kết quả nào từ DB, hoặc điểm quá thấp
        if not final_results:
            return {
                "query": query,
                "status": "Bài báo không tồn tại trong DB nội bộ",
                "results": []
            }

        return {
            "query": query,
            "results": final_results,
            "best_match_status": final_results[0]["status_label"] if final_results else "Không tìm thấy"
        }
    except Exception as e:
        return {"error": str(e)}

#API bóc tách CV
@app.post("/api/extract-cv")
async def upload_cv(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    data = extract_scientific_articles(temp_path)
    os.remove(temp_path)
    
    # Kiểm tra nếu hoàn toàn không có bài báo nào
    if not data:
        return {
            "filename": file.filename,
            "status": "Warning",
            "message": "Không tìm thấy dữ liệu. File có thể là bản scan (ảnh) hoặc không đúng mẫu số 01. Hệ thống cần module OCR để xử lý."
        }
    
    return {
        "filename": file.filename, 
        "total_articles": len(data), 
        "articles": data
    }