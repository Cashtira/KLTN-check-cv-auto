import os
import base64
import json
import io
import re
import time
import pdfplumber
from openai import OpenAI
from pdf2image import convert_from_path
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
POPPLER_PATH = r'E:\ToTNghiep\poppler-25.12.0\Library\bin' if os.name == 'nt' else None 

def clean_json_string(raw_str):
    """Lọc lấy phần JSON nằm trong cặp ngoặc []"""
    try:
        match = re.search(r'\[.*\]', raw_str, re.DOTALL)
        if match:
            return match.group(0)
        return raw_str.strip()
    except:
        return raw_str

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_scientific_articles(pdf_path):
    all_articles = []
    start_page = -1
    end_page = -1

    try:
        # BƯỚC 1: XÁC ĐỊNH DẢI TRANG
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if start_page == -1 and ("7.1.a" in text or "Bài báo khoa học" in text):
                    start_page = i
                if start_page != -1 and i > start_page:
                    if ("7.1.b" in text or "7.2" in text or "8. Chủ trì" in text):
                        end_page = i
                        break
            
            if start_page != -1 and end_page == -1:
                end_page = total_pages - 1

        if start_page == -1:
            start_page, end_page = 0, min(10, total_pages - 1)

        print(f">>> Target: Trang {start_page + 1} đến {end_page + 1}")

        # BƯỚC 2: CHUYỂN PDF THÀNH ẢNH
        images = convert_from_path(
            pdf_path, 
            dpi=300, 
            first_page=start_page + 1, 
            last_page=end_page + 1, 
            poppler_path=POPPLER_PATH
        )

        # BƯỚC 3: XỬ LÝ AI TỪNG TRANG ĐỘC LẬP
        for i, img in enumerate(images):
            p_num = start_page + i + 1
            base64_image = encode_image(img)
            
            print(f">>> Đang bóc tách trang {p_num}...")
            
            # Prompt rút gọn, không yêu cầu nối dòng phức tạp
            prompt = """
            Bạn là chuyên gia bóc tách tài liệu. Hãy trích xuất bảng 'Bài báo khoa học' thành JSON.
            YÊU CẦU CÁC TRƯỜNG DỮ LIỆU:
            - stt: Số thứ tự (TT).
            - title: Tên bài báo/báo cáo KH.
            - author_count: Số lượng tác giả (lấy giá trị số ở cột 'Số tác giả').
            - is_main: Trả về true nếu cột 'Là tác giả chính' ghi 'Có', ngược lại là false.
            - journal: Tên tạp chí hoặc kỷ yếu hội thảo/ISSN/ISBN.
            - category: Nội dung cột 'Loại tạp chí quốc tế uy tín' (ISI, Scopus, Q...).
            - year: Tháng, năm công bố.

            Chỉ trả về mảng JSON, không giải thích.
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                temperature=0
            )

            raw_content = response.choices[0].message.content
            json_str = clean_json_string(raw_content)
            
            try:
                page_data = json.loads(json_str)
                if isinstance(page_data, list):
                    all_articles.extend(page_data)
                    print(f"  - Đã lấy xong {len(page_data)} bài từ trang {p_num}.")
            except Exception as e:
                print(f"  - Lỗi JSON trang {p_num}: {e}")

            time.sleep(2)

    except Exception as e:
        print(f"Lỗi hệ thống Extractor: {e}")
            
    return all_articles