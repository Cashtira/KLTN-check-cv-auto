import re
import requests
import difflib
from supabase import Client
from datetime import datetime

# Hàm phụ: Gọi API Crossref (Đã lắp Fuzzy Search)
def fetch_crossref_info(title: str):
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": title, # Dùng query.bibliographic sẽ quét chính xác hơn
        "select": "title,container-title,event,issued,type,is-referenced-by-count",
        "rows": 3 # Lấy 3 kết quả đầu tiên để dò tìm
    }
    headers = {
        "User-Agent": "KLTN_AutoCheck/1.0 (mailto:karsein.dev@example.com)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=7)
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            
            # Quét qua top 3 kết quả trả về
            for paper in items:
                api_title = paper.get("title", [""])[0]
                
                # Đánh giá độ tương đồng của 2 tên bài báo
                # difflib sẽ tính toán ra một tỷ lệ từ 0.0 đến 1.0
                similarity = difflib.SequenceMatcher(None, title.lower(), api_title.lower()).ratio()
                
                # Giống trên 85% thì xác định là tìm thấy
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
            
            # Nếu vòng lặp chạy xong mà không có bài nào giống quá 85% -> Trả về False
            return {"found": False}
            
        else:
            print(f"Lỗi API Crossref: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối API Crossref: {e}")
        
    return {"found": False}

def calculate_single_article_score(supabase: Client, title: str, authors: str, journal_text: str, year_str: str):
    year_match = re.search(r'\d{4}', year_str)
    year = int(year_match.group(0)) if year_match else 0

    issn_match = re.search(r'(?:ISSN|ISBN)[\s:]*([A-Za-z0-9\- ]+)', journal_text, re.IGNORECASE)
    code = None
    if issn_match:
        raw_code = issn_match.group(1).replace(" ", "").strip()
        code = raw_code[:9]
    
    # BƯỚC 1: XÁC MINH TRỰC TUYẾN
    api_data = fetch_crossref_info(title)
    
    result = {
        "title": title,
        "extracted_year": year,
        "extracted_code": code,
        "max_score": 0.0,
        "rule_applied": "Chưa xác định",
        "verified_online": api_data["found"],
        "warnings": [], 
        "crossref_info": api_data
    }

    if not api_data["found"]:
        result["warnings"].append("CẢNH BÁO: Không tìm thấy metadata trực tuyến. Cần kiểm tra bản cứng hoặc yêu cầu cung cấp DOI.")
    else:
        api_year = api_data.get("api_year")
        if api_year and api_year > 0 and year > 0 and abs(api_year - year) > 1:
            result["warnings"].append(f"NGHI VẤN: Năm xuất bản khai báo ({year}) không khớp với hệ thống quốc tế ({api_year}).")

    # BƯỚC 2: TÍNH ĐIỂM
    if not code:
        result["rule_applied"] = "Không bóc tách được mã ISSN/ISBN để tra cứu."
        return result

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
            result["max_score"] = rule["max_score"]
            result["rule_applied"] = f"Tạp chí nội địa. Áp dụng mốc điểm năm {rule['valid_from_year']}."
            return result

    # TẦNG 2: TẠP CHÍ QUỐC TẾ (SCIMAGO)
    # Loại bỏ dấu gạch ngang để khớp với định dạng của SCImago Database
    scimago_code = code.replace("-", "") 
    scimago_res = supabase.table("scimago_rankings").select("rank_q, title").ilike("issn", f"%{scimago_code}%").execute()
    
    if scimago_res.data:
        rank = scimago_res.data[0]["rank_q"]
        venue_title = scimago_res.data[0]["title"]
        
        q_rule = supabase.table("scoring_rules").select("max_score").eq("category", "QUOC_TE").eq("rank_q", rank).execute()
        score = q_rule.data[0]["max_score"] if q_rule.data else 1.0
        
        result["max_score"] = score
        result["rule_applied"] = f"Tạp chí SCImago ({venue_title}). Hạng {rank}."
        if rank == "Q1":
            result["rule_applied"] += " Cần minh chứng IF >= 3.0 hoặc IF >= 5.0 để nâng lên 2.5 hoặc 3.0 điểm."
        return result

    # TẦNG 3: FALLBACK QUỐC TẾ TỪ DỮ LIỆU API
    if api_data["found"]:
        if api_data["is_conference"]:
            conf_rule = supabase.table("scoring_rules").select("max_score").eq("category", "HOI_NGHI").eq("conf_rank", "Khác").execute()
            score = conf_rule.data[0]["max_score"] if conf_rule.data else 1.0
            
            result["max_score"] = score
            result["rule_applied"] = f"Hội nghị quốc tế ({api_data['venue']}). Mặc định tính mức Hội nghị còn lại."
        else:
            journal_rule = supabase.table("scoring_rules").select("max_score").eq("category", "QUOC_TE").eq("is_online", True).execute()
            score = journal_rule.data[0]["max_score"] if journal_rule.data else 1.0
            
            result["max_score"] = score
            result["rule_applied"] = f"Tạp chí quốc tế ngoài SCImago ({api_data['venue']}). Mặc định tính mức Tạp chí khác (Online)."
        return result

    result["max_score"] = 0.5 
    result["rule_applied"] = "Không thể phân loại. Tạm tính mức tối thiểu 0.5 điểm."
    
    return result