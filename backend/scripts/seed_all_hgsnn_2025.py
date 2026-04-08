import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def seed_data():
    print("Bắt đầu nạp dữ liệu...")

    # 1. NẠP QUY TẮC QUỐC TẾ & HỘI NGHỊ CHUNG
    intl_rules = [
        {"category": "QUOC_TE", "rank_q": "Q1", "min_if": 5.0, "max_score": 3.0, "description": "SCI/SCIE/Scopus Q1, IF >= 5"},
        {"category": "QUOC_TE", "rank_q": "Q1", "min_if": 3.0, "max_score": 2.5, "description": "SCI/SCIE/Scopus Q1, IF >= 3"},
        {"category": "QUOC_TE", "rank_q": "Q1", "max_score": 2.0, "description": "SCI/SCIE/Scopus Q1 còn lại"},
        {"category": "QUOC_TE", "rank_q": "Q2", "max_score": 1.75},
        {"category": "QUOC_TE", "rank_q": "Q3", "max_score": 1.5},
        {"category": "QUOC_TE", "rank_q": "Q4", "max_score": 1.0},
        {"category": "QUOC_TE", "is_online": True, "max_score": 1.0, "description": "Quốc tế khác (Online)"},
        {"category": "QUOC_TE", "is_online": False, "max_score": 0.75, "description": "Quốc tế khác (Offline)"},
        {"category": "HOI_NGHI", "conf_rank": "A*", "max_score": 1.5},
        {"category": "HOI_NGHI", "conf_rank": "A", "max_score": 1.25},
        {"category": "HOI_NGHI", "conf_rank": "Other", "max_score": 1.0},
        {"category": "HOI_NGHI", "valid_from_year": 0, "max_score": 0.5, "description": "Hội nghị quốc gia (Chung)"}
    ]
    supabase.table("scoring_rules").insert(intl_rules).execute()
    print("Đã nạp xong quy tắc Quốc tế và Hội nghị chung.")

    # 2. HÀM XỬ LÝ 3 BẢNG
    def add_domestic(name, publisher, issns_data, scores):
        # Bước A: Tạo Tạp chí
        j_res = supabase.table("journals").insert(
            {"name": name, "publisher": publisher, "category": "TRONG_NUOC"}
        ).execute()
        j_id = j_res.data[0]['id']
        
        # Bước B: Nạp Đa mã ISSN (Xử lý chuỗi và object)
        if issns_data:
            identifiers = []
            for item in issns_data:
                if isinstance(item, dict):
                    identifier = {"journal_id": j_id, "code": item["code"]}
                    if "valid_from_date" in item:
                        identifier["valid_from_date"] = item["valid_from_date"]
                    if "type" in item:
                        identifier["type"] = item["type"]
                    identifiers.append(identifier)
                else:
                    identifiers.append({"journal_id": j_id, "code": item})
            supabase.table("journal_identifiers").insert(identifiers).execute()
            
        # Bước C: Nạp Quy tắc điểm (Map ID tạp chí)
        rule_list = []
        for year, score in scores.items():
            rule_list.append({"journal_id": j_id, "valid_from_year": year, "max_score": score})
        supabase.table("scoring_rules").insert(rule_list).execute()

    # 3. NẠP 22 DANH MỤC CHI TIẾT
    
    # Mục 4.1: FAIR
    add_domestic("Hội nghị FAIR", "HĐGSNN", [], {2019: 0.75, 0: 0.5}) 

    # Mục 5, 6, 7
    add_domestic("Acta Mathematica Vietnamica", "Viện Hàn lâm KH&CN VN", ["0251-4184"], {2020: 1.25, 0: 1.0})
    add_domestic("An toàn thông tin", "Ban Cơ yếu Chính phủ", ["2615-9570"], {2024: 0.75, 2020: 0.5})
    add_domestic("Công nghệ Thông tin & Truyền thông", "Bộ KH&CN", ["1859-3526"], {2024: 0.75, 2020: 0.5, 0: 1.0})

    # Mục 8: Đa mã
    add_domestic("VNU Journal: CS & CE", "ĐHQG Hà Nội", [
        {"code": "2615-9260", "type": "p-ISSN"},
        {"code": "2588-1086", "type": "e-ISSN"},
        {"code": "0866-8612", "type": "Old-ISSN"}
    ], {2024: 1.0, 2019: 0.75, 0: 0.5})

    # Mục 9, 10, 11
    add_domestic("Journal on Electronics and Communications", "Hội Vô tuyến-Điện tử VN", ["1859-378X"], {2019: 0.75, 0: 1.0})
    add_domestic("Journal on Information Tech. & Comm.", "Bộ KH&CN", ["1859-3534"], {2024: 1.0, 2020: 0.75, 0: 1.0})
    add_domestic("KHCN Thông tin và Truyền thông", "Học viện CNBCVT", ["2525-2224"], {2024: 0.75, 2020: 0.5})

    # Mục 12: Đa mã
    add_domestic("Vietnam Journal of Science and Technology", "Viện Hàn lâm KH&CN VN", [
        {"code": "2525-2518", "type": "p-ISSN"},
        {"code": "2815-5874", "type": "e-ISSN"},
        {"code": "0866-708X", "type": "Old-ISSN"}
    ], {2024: 1.0, 2020: 0.75, 0: 0.5})

    # Mục 13, 14, 15
    add_domestic("Khoa học và Kỹ thuật (CNTT-TT)", "Học viện KTQS", ["1859-0209"], {2024: 1.0, 2021: 0.75, 0: 0.5})
    add_domestic("Phát triển Khoa học và Công nghệ", "ĐHQG TP.HCM", ["1859-0128"], {0: 0.5})
    add_domestic("Tin học và Điều khiển học", "Viện Hàn lâm KH&CN VN", ["1813-9663"], {2025: 1.0, 2020: 1.25, 0: 1.0})

    # Mục 16: Nhảy mã ISSN theo thời gian
    add_domestic("KH&CN các trường ĐH kỹ thuật", "Nhóm các trường ĐH Kỹ thuật", [
        {"code": "0868-3980", "valid_from_date": "1996-12-01"},
        {"code": "2354-1083", "valid_from_date": "2015-03-01"},
        {"code": "2734-9381", "valid_from_date": "2021-03-01"},
        {"code": "2734-9373", "type": "e-ISSN"},
        "1859-1043"
    ], {0: 0.5})

    # Mục 17: Nhóm ĐH lớn (0.5 đ)
    universities_m17 = [
        "Đại học Thái Nguyên", "Đại học Huế", "Đại học Đà Nẵng", "Trường Đại học Cần Thơ",
        "Trường ĐH Sư phạm Hà Nội", "Trường ĐH Sư phạm TP. Hồ Chí Minh", "Trường Đại học Vinh", "Trường Đại học Đà Lạt"
    ]
    for uni in universities_m17:
        add_domestic(f"Tạp chí Khoa học: {uni}", uni, [], {0: 0.5})

    # Mục 18, 19, 20, 21
    add_domestic("Nghiên cứu KH&CN Quân sự", "Viện KH&CN Quân sự", [], {2024: 0.75, 0: 0.5})
    add_domestic("Ứng dụng Toán học", "Hội Toán học VN", ["1859-4492"], {2025: 0.0, 0: 0.5})
    add_domestic("Vietnam Journal of Mathematics", "Hội Toán học VN", ["0866-7179"], {2020: 1.25, 0: 1.0})
    add_domestic("KH&CN Việt Nam bản B", "Bộ KH&CN", [
        {"code": "1859-4794", "type": "p-ISSN"},
        {"code": "2615-9929", "type": "e-ISSN"}
    ], {2025: 0.5})

    # Mục 22: Nhóm ĐH đang xét 2025 (0.25 đ)
    universities_m22 = [
        "Trường ĐH Quy Nhơn", "Trường ĐH Trà Vinh", "Trường ĐH Nam Cần Thơ", 
        "Trường ĐH Ngoại ngữ Tin học", "Trường ĐH Công nghệ GTVT", 
        "Trường ĐH Mở TPHCM", "Trường ĐH Khoa học - Đại học Huế"
    ]
    for uni in universities_m22:
        add_domestic(f"Tạp chí Khoa học: {uni}", uni, [], {2025: 0.25})

    print("HOÀN THÀNH: Toàn bộ 22 danh mục đã được nạp thành công và an toàn vào 3 bảng!")

if __name__ == "__main__":
    seed_data()