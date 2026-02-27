import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hệ thống Kiểm tra LLKH Tự động")

# Cấu hình CORS để React có thể gọi API
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