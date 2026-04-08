import pdfplumber
import re

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
                        if not table or len(table[0]) < 8 or len(table[0]) > 10:
                            continue
                        
                        for row in table:
                            clean_row = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                            
                            # Nhận diện STT (Phải là số ở cột đầu tiên)
                            stt_raw = clean_row[0].rstrip('.')
                            if stt_raw.isdigit():
                                title = clean_row[1]
                                # Chỉ lấy nếu tên bài báo đủ dài
                                if title and len(title) > 15:
                                    articles.append({
                                        "stt": stt_raw,
                                        "title": title,
                                        "journal": clean_row[4] if len(clean_row) > 4 else "",
                                        "year": clean_row[8] if len(clean_row) > 8 else ""
                                    })
                
                # Dừng lại khi thấy tiêu đề mục 8
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