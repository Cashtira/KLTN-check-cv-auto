import os
import csv
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def seed_scimago():
    print("Bắt đầu đọc file SCImago và nạp vào Supabase...")
    
    # Đường dẫn tới file CSV theo năm
    csv_file_path = "scripts/scimagojr 2024.csv" 
    
    try:
        # SCImago thường dùng dấu chấm phẩy (;) làm phân cách
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            
            batch_data = []
            count = 0
            
            for row in reader:
                title = row.get('Title', '')
                issn = row.get('Issn', '')
                rank_q = row.get('SJR Best Quartile', '')
                
                # Bỏ qua những tạp chí bị thiếu mã ISSN hoặc chưa được xếp hạng Q
                if not issn or not rank_q or rank_q == '-':
                    continue
                    
                batch_data.append({
                    "title": title,
                    "issn": issn,
                    "rank_q": rank_q,
                    "year": 2024
                })
                
                # Đẩy từng batch 1000 dòng để Supabase không bị nghẽn
                if len(batch_data) == 1000:
                    supabase.table("scimago_rankings").insert(batch_data).execute()
                    count += 1000
                    print(f"Đã nạp thành công {count} tạp chí...")
                    batch_data = [] # Xóa bộ đệm để nạp đợt tiếp theo
            
            # Đẩy nốt phần lẻ còn sót lại
            if batch_data:
                supabase.table("scimago_rankings").insert(batch_data).execute()
                count += len(batch_data)
                
            print(f"HOÀN THÀNH! Tổng cộng đã nạp {count} tạp chí quốc tế vào hệ thống.")
            
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {csv_file_path}.")
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    seed_scimago()