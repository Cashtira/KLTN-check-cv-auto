import re
import requests
import difflib
from supabase import Client
from datetime import datetime

# Hàm phụ 1: Gọi API Crossref (Đã nâng cấp bốc thêm mảng author)
def fetch_crossref_info(title: str):
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": title,
        "select": "title,container-title,event,issued,type,is-referenced-by-count,author",
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
                    
                    # Trích xuất thông tin tác giả từ hệ thống quốc tế
                    authors_api = paper.get("author", [])
                    author_count_api = len(authors_api)
                    
                    return {
                        "found": True,
                        "venue": venue_str,
                        "is_conference": is_conference,
                        "citations": paper.get("is-referenced-by-count", 0),
                        "api_year": api_year,
                        "authors_api": authors_api,
                        "author_count_api": author_count_api
                    }
            return {"found": False}
        else:
            print(f"Lỗi API Crossref: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối API Crossref: {e}")
    return {"found": False}


# Hàm phụ 2: Chuẩn hóa xóa dấu tiếng Việt phục vụ so khớp tên tác giả chính
def normalize_str(s):
    if not s: 
        return ""
    import unicodedata
    s = s.lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


# HÀM CHÍNH TÍNH ĐIỂM & ĐỐI CHIẾU KIỂM KÊ
def calculate_single_article_score(
    supabase: Client, 
    title: str, 
    authors: str, 
    journal_text: str, 
    year_str: str,
    author_count: int = 1,
    is_main: bool = True,
    candidate_name: str = "Nguyễn Minh Kha"
):
    year_match = re.search(r'\d{4}', year_str)
    year = int(year_match.group(0)) if year_match else 0

    issn_match = re.search(r'(?:ISSN|ISBN)[\s:]*([A-Za-z0-9\- ]+)', journal_text, re.IGNORECASE)
    code = None
    if issn_match:
        raw_code = issn_match.group(1).replace(" ", "").strip()
        code = raw_code[:9]
    
    # BƯỚC 1: TRA CỨU DATABASE NỘI BỘ TRƯỚC (LAZY LOADING)
    base_score = 0.5
    rule_applied = "Không thể phân loại. Tạm tính mức tối thiểu 0.5 điểm."
    rank_found = "N/A"

    if code:
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

        # TẦNG 2: TẠP CHÍ QUỐC TẾ (SCIMAGO)
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

    # BƯỚC 2: GỌI API ĐỂ THỰC HIỆN KIỂM KÊ VÀ ĐỐI CHIẾU THÔNG TIN
    api_data = fetch_crossref_info(title)
    
    # TẦNG 3: FALLBACK QUỐC TẾ (Nếu DB nội bộ không khớp)
    if base_score == 0.5 and rank_found == "N/A" and api_data["found"] and "Mã ISSN/ISBN" not in rule_applied:
        if api_data["is_conference"]:
            conf_rule = supabase.table("scoring_rules").select("max_score").eq("category", "HOI_NGHI").eq("conf_rank", "Khác").execute()
            base_score = conf_rule.data[0]["max_score"] if conf_rule.data else 1.0
            rule_applied = f"Hội nghị quốc tế ({api_data['venue']}). Tính mức Hội nghị còn lại."
        else:
            journal_rule = supabase.table("scoring_rules").select("max_score").eq("category", "QUOC_TE").eq("is_online", True).execute()
            base_score = journal_rule.data[0]["max_score"] if journal_rule.data else 1.0
            rule_applied = f"Tạp chí quốc tế ngoài SCImago ({api_data['venue']}). Tính mức Tạp chí khác (Online)."

    # BƯỚC 3: KHỞI TẠO LOGIC KIỂM KÊ ĐỐI CHIẾU 3 CỘT THEO KHUNG CHẤM ĐỒ ÁN
    check_title = {"status": True, "message": "Khớp"} if api_data["found"] else {"status": False, "message": "Không tìm thấy"}
    check_author_count = {"status": True, "message": "Khớp"}
    check_is_main = {"status": True, "message": "Khớp"}
    warnings = []

    if not api_data["found"]:
        warnings.append("CẢNH BÁO: Không tìm thấy metadata trực tuyến. Cần kiểm tra bản cứng.")
        check_author_count = {"status": False, "message": "Chưa đối chiếu"}
        check_is_main = {"status": False, "message": "Chưa đối chiếu"}
    else:
        # 1. Đối chiếu Số lượng tác giả
        api_count = api_data.get("author_count_api", 1)
        if int(author_count) != api_count:
            check_author_count = {"status": False, "message": f"Lệch (Hệ thống: {api_count})"}
        
        # 2. Đối chiếu Vai trò Tác giả chính
        norm_candidate = normalize_str(candidate_name)
        api_authors = api_data.get("authors_api", [])
        
        api_is_main = False
        found_candidate_in_api = False
        
        if api_authors:
            # Kiểm tra xem ứng viên có phải tác giả đầu tiên (First Author) hay không
            first_auth = api_authors[0]
            first_comb = normalize_str(first_auth.get("given", "")) + normalize_str(first_auth.get("family", ""))
            first_comb_alt = normalize_str(first_auth.get("family", "")) + normalize_str(first_auth.get("given", ""))
            
            if norm_candidate in first_comb or norm_candidate in first_comb_alt or first_comb in norm_candidate:
                api_is_main = True
                found_candidate_in_api = True
            else:
                # Quét xem ứng viên có nằm ở danh sách tác giả thành viên đứng sau không
                for auth in api_authors[1:]:
                    auth_comb = normalize_str(auth.get("given", "")) + normalize_str(auth.get("family", ""))
                    auth_comb_alt = normalize_str(auth.get("family", "")) + normalize_str(auth.get("given", ""))
                    if norm_candidate in auth_comb or norm_candidate in auth_comb_alt or auth_comb in norm_candidate:
                        api_is_main = False
                        found_candidate_in_api = True
                        break
        
        # Đánh giá mức độ khớp vai trò kê khai
        if found_candidate_in_api:
            if is_main != api_is_main:
                check_is_main = {"status": False, "message": "Nghi vấn (Hệ thống xếp TG phụ)" if is_main else "Nghi vấn (Hệ thống xếp TG chính)"}
        else:
            if is_main:
                check_is_main = {"status": False, "message": "Nghi vấn (Không thấy tên đứng đầu)"}

        # Đối chiếu năm xuất bản
        api_year = api_data.get("api_year")
        if api_year and api_year > 0 and year > 0 and abs(api_year - year) > 1:
            warnings.append(f"NGHI VẤN: Năm xuất bản khai báo ({year}) không khớp với hệ thống quốc tế ({api_year}).")

    # BƯỚC 4: ÁP DỤNG ĐIỀU 8 QUY ĐỔI ĐIỂM THEO SỐ TÁC GIẢ
    try:
        n_authors = int(author_count) if author_count else 1
    except:
        n_authors = 1

    final_score = base_score
    if n_authors > 1:
        shared_part = ((2 / 3) * base_score) / n_authors
        if is_main:
            final_score = ((1 / 3) * base_score) + shared_part
        else:
            final_score = shared_part
            
        final_score = round(final_score, 3)
        rule_applied += f" [Quy đổi Điều 8: {n_authors} tác giả, {'TG chính' if is_main else 'TG phụ'} (Điểm gốc: {base_score})]"
    else:
        rule_applied += " [Bài báo độc bản/1 tác giả, hưởng 100% điểm]"

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
        "crossref_info": api_data,
        "check_title": check_title,
        "check_author_count": check_author_count,
        "check_is_main": check_is_main
    }