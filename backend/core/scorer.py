import re
import requests
import difflib
from supabase import Client
from datetime import datetime

# Hàm phụ: Gọi API Crossref (Giữ nguyên logic của Kha)
def fetch_crossref_info(title: str):
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": title,
        "select": "title,container-title,event,issued,type,is-referenced-by-count",
        "rows": 3
    }
    headers = {
        "User-Agent": "KLTN_AutoCheck/1.0 (mailto:karsein.dev@example.com)"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=7)
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            for paper in items:
                api_title = paper.get("title", [""])[0]
                similarity = difflib.SequenceMatcher(None, title.lower(), api_title.lower()).ratio()
                if similarity >= 0.85:
                    api_year = 0
                    issued = paper.get("issued", {}).get("date-parts", [[]])
                    if issued and len(issued[0]) > 0:
                        api_year = issued[0][0]
                    is_conference = paper.get("type") == "proceedings-article"
                    venue_list = paper.get("container-title", [paper.get("event", "Không rõ")])
                    venue_str = venue_list[0] if venue_list else "Không rõ"
                    return {
                        "found": True,
                        "venue": venue_str,
                        "is_conference": is_conference,
                        "citations": paper.get("is-referenced-by-count", 0),
                        "api_year": api_year
                    }
            return {"found": False}
        else:
            print(f"Lỗi API Crossref: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối API Crossref: {e}")
    return {"found": False}


def calculate_single_article_score(
    supabase: Client, 
    title: str, 
    authors: str, 
    journal_text: str, 
    year_str: str,
    author_count: int = 1, # Trường mới nhận từ Extractor (Mặc định là 1)
    is_main: bool = True   # Trường mới nhận từ Extractor (Mặc định là tác giả chính)
):
    year_match = re.search(r'\d{4}', year_str)
    year = int(year_match.group(0)) if year_match else 0

    issn_match = re.search(r'(?:ISSN|ISBN)[\s:]*([A-Za-z0-9\- ]+)', journal_text, re.IGNORECASE)
    code = None
    if issn_match:
        raw_code = issn_match.group(1).replace(" ", "").strip()
        code = raw_code[:9]
    
    # BƯỚC 1: XÁC MINH TRỰC TUYẾN
    api_data = fetch_crossref_info(title)
    
    warnings = []
    if not api_data["found"]:
        warnings.append("CẢNH BÁO: Không tìm thấy metadata trực tuyến. Cần kiểm tra bản cứng hoặc yêu cầu cung cấp DOI.")
    else:
        api_year = api_data.get("api_year")
        if api_year and api_year > 0 and year > 0 and abs(api_year - year) > 1:
            warnings.append(f"NGHI VẤN: Năm xuất bản khai báo ({year}) không khớp với hệ thống quốc tế ({api_year}).")

    # Khởi tạo giá trị mặc định để gom về một luồng xử lý cuối hàm
    base_score = 0.5
    rule_applied = "Không thể phân loại. Tạm tính mức tối thiểu 0.5 điểm."
    rank_found = "N/A"

    # BƯỚC 2: TÌM ĐIỂM GỐC (BASE SCORE) THEO DANH MỤC TẠP CHÍ
    if not code:
        rule_applied = "Không bóc tách được mã ISSN/ISBN để tra cứu."
    else:
        # TẦNG 1: TẠP CHÍ NỘI ĐỊA
        id_response = supabase.table("journal_identifiers").select("journal_id").eq("code", code).execute()
        if id_response.data:
            journal_id = id_response.data[0]["journal_id"]
            rules_response = supabase.table("scoring_rules") \
                .select("max_score, valid_from_year") \
                .eq("journal_id", journal_id) \
                .lte("valid_from_year", year) \
                .order("valid_from_year", desc=True) \
                .limit(1) \
                .execute()
            
            if rules_response.data:
                rule = rules_response.data[0]
                base_score = rule["max_score"]
                rule_applied = f"Tạp chí nội địa. Áp dụng mốc điểm năm {rule['valid_from_year']}."

        # TẦNG 2: TẠP CHÍ QUỐC TẾ (SCIMAGO) - Chạy nếu chưa khớp tầng 1
        if base_score == 0.5 and rank_found == "N/A" and "Tạp chí nội địa" not in rule_applied:
            scimago_code = code.replace("-", "") 
            scimago_res = supabase.table("scimago_rankings").select("rank_q, title").ilike("issn", f"%{scimago_code}%").execute()
            
            if scimago_res.data:
                rank = scimago_res.data[0]["rank_q"]
                rank_found = rank
                venue_title = scimago_res.data[0]["title"]
                
                q_rule = supabase.table("scoring_rules").select("max_score").eq("category", "QUOC_TE").eq("rank_q", rank).execute()
                base_score = q_rule.data[0]["max_score"] if q_rule.data else 1.0
                rule_applied = f"Tạp chí SCImago ({venue_title}). Hạng {rank}."
                if rank == "Q1":
                    rule_applied += " Cần minh chứng IF chuẩn để nâng điểm."

        # TẦNG 3: FALLBACK QUỐC TẾ TỪ DỮ LIỆU API - Chạy nếu 2 tầng trên tịt
        if base_score == 0.5 and rank_found == "N/A" and api_data["found"] and "Mã ISSN/ISBN" not in rule_applied:
            if api_data["is_conference"]:
                conf_rule = supabase.table("scoring_rules").select("max_score").eq("category", "HOI_NGHI").eq("conf_rank", "Khác").execute()
                base_score = conf_rule.data[0]["max_score"] if conf_rule.data else 1.0
                rule_applied = f"Hội nghị quốc tế ({api_data['venue']}). Tính mức Hội nghị còn lại."
            else:
                journal_rule = supabase.table("scoring_rules").select("max_score").eq("category", "QUOC_TE").eq("is_online", True).execute()
                base_score = journal_rule.data[0]["max_score"] if journal_rule.data else 1.0
                rule_applied = f"Tạp chí quốc tế ngoài SCImago ({api_data['venue']}). Tính mức Tạp chí khác (Online)."

    # BƯỚC 3: ÁP DỤNG ĐIỀU 8 QUY ĐỔI ĐIỂM THEO SỐ TÁC GIẢ
    try:
        n_authors = int(author_count) if author_count else 1
    except:
        n_authors = 1

    final_score = base_score
    if n_authors > 1:
        # Phần 2/3 chia đều cho N người
        shared_part = ((2 / 3) * base_score) / n_authors
        
        if is_main:
            # Tác giả chính: Hưởng 1/3 riêng + phần chia đều
            final_score = ((1 / 3) * base_score) + shared_part
        else:
            # Tác giả phụ: Chỉ hưởng phần chia đều
            final_score = shared_part
            
        final_score = round(final_score, 3) # Lấy 3 chữ số thập phân theo chuẩn hội đồng
        rule_applied += f" [Quy đổi Điều 8: {n_authors} tác giả, {'TG chính' if is_main else 'TG phụ'} (Điểm gốc: {base_score})]"
    else:
        rule_applied += " [Bài báo độc bản/1 tác giả, hưởng 100% điểm]"

    # Trả về kết quả khớp với cấu trúc Frontend đang đọc
    return {
        "title": title,
        "journel": journal_text,
        "extracted_year": year,
        "extracted_code": code,
        "max_score": final_score, 
        "rank_found": rank_found, 
        "rule_applied": rule_applied,
        "verified_online": api_data["found"],
        "warnings": warnings, 
        "crossref_info": api_data
    }