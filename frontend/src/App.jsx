import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { supabase } from './supabaseClient'; 
import { Upload, FileText, CheckCircle, BrainCircuit, Loader2, Calculator, Copy, RefreshCw, AlertCircle, UserCheck, Users, LogOut, Lock, Mail, History, FileSearch } from 'lucide-react';

const COLORS = {
  bg: '#f8fafc',
  sidebar: '#ffffff',
  card: '#ffffff',
  text: '#1e293b',
  subtle: '#64748b',
  primary: '#2563eb',
  success: '#16a34a',
  border: '#e2e8f0',
};

const labelStyle = { fontSize: '13px', fontWeight: '600', color: COLORS.subtle, marginBottom: '5px', display: 'block' };
const inputStyle = { width: '100%', padding: '10px', borderRadius: '6px', border: `1px solid ${COLORS.border}`, fontSize: '14px', boxSizing: 'border-box', fontFamily: 'inherit' };
const buttonStyle = { backgroundColor: COLORS.primary, color: 'white', border: 'none', padding: '12px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%' };
const thStyle = { padding: '14px 12px', textAlign: 'left', fontSize: '12.5px', color: COLORS.subtle, fontWeight: '600' };
const tdStyle = { padding: '14px 12px', fontSize: '13px', color: COLORS.text, verticalAlign: 'top', lineHeight: '1.4' };

function App() {
  // --- STATE QUẢN LÝ TÀI KHOẢN (SUPABASE AUTH) ---
  const [session, setSession] = useState(null);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);

  // --- STATE QUẢN LÝ CHUYỂN TAB DASHBOARD ---
  const [activeTab, setActiveTab] = useState('evaluate'); // 'evaluate' (Chấm CV) hoặc 'dashboard' (Lịch sử)
  const [historyList, setHistoryList] = useState([]);

  // --- STATE CỦA BỘ TÍNH ĐIỂM LÊN GIAO DIỆN ---
  // Đã bỏ candidate_name khỏi bộ tính lẻ bên trái theo ý Kha
  const [singleInput, setSingleInput] = useState({ title: '', authors: 'Không xác định', journal: '', year: '', author_count: 1, is_main: true });
  const [singleScore, setSingleScore] = useState(null);
  const [singleLoading, setSingleLoading] = useState(false);
  
  const [candidateName, setCandidateName] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [editableArticles, setEditableArticles] = useState([]);
  const [totalScore, setTotalScore] = useState(0);

  // LẮNG NGHE TRẠNG THÁI ĐĂNG NHẬP
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Tự động chạy khi có User đăng nhập thành công
  useEffect(() => {
    if (session?.user) {
      fetchDashboardHistory();
      // ĐỔI MẶC ĐỊNH: Lấy phần tên trước chữ @ của Email làm tên hiển thị ban đầu
      const emailPrefix = session.user.email.split('@')[0];
      setCandidateName(emailPrefix);
    }
  }, [session]);

  // HÀM TẢI LỊCH SỬ DASHBOARD
  const fetchDashboardHistory = async () => {
    try {
      const { data, error } = await supabase
        .from('cv_histories')
        .select('*')
        .eq('user_id', session?.user?.id)
        .order('checked_at', { ascending: false });
      if (!error) setHistoryList(data || []);
    } catch (err) {
      console.error("Lỗi tải lịch sử Dashboard:", err);
    }
  };

  // LOGIC ĐĂNG KÝ / ĐĂNG NHẬP
  const handleAuthAction = async (e) => {
    e.preventDefault();
    if (!authEmail || !authPassword) return alert("Vui lòng nhập đầy đủ thông tin!");
    setAuthLoading(true);

    try {
      if (isRegisterMode) {
        const { error } = await supabase.auth.signUp({ email: authEmail, password: authPassword });
        if (error) throw error;
        alert("Đăng ký thành công! Hãy đăng nhập hệ thống.");
        setIsRegisterMode(false);
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email: authEmail, password: authPassword });
        if (error) throw error;
      }
    } catch (error) {
      alert(error.message || "Lỗi xác thực!");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setResult(null);
    setEditableArticles([]);
    setHistoryList([]);
    setActiveTab('evaluate');
  };

  // TÍNH ĐIỂM LẺ BÀI BÁO BÊN TRÁI
  const handleSingleScore = async () => {
    if (!singleInput.title || !singleInput.journal) return alert("Nhập đủ Tên bài và Tạp chí nhé!");
    setSingleLoading(true);
    // Gửi kèm candidate_name cố định là tên tài khoản hiện tại lên backend
    const payload = { 
      ...singleInput, 
      author_count: parseInt(singleInput.author_count) || 1, 
      is_main: singleInput.is_main === true,
      candidate_name: candidateName 
    };
    try {
      const response = await axios.post('http://localhost:8000/api/score-article', payload);
      setSingleScore(response.data.data);
    } catch (error) {
      alert("Lỗi kết nối Backend!");
    } finally {
      setSingleLoading(false);
    }
  };

  const copyToChecker = (art) => {
    setSingleInput({
      title: art.title || '',
      authors: 'Không xác định',
      journal: art.journal || '',
      year: art.extracted_year ? String(art.extracted_year) : (art.year ? String(art.year) : ''),
      author_count: art.author_count !== undefined ? art.author_count : 1,
      is_main: art.is_main !== undefined ? art.is_main : true
    });
  };

  // UPLOAD PHÂN TÍCH TOÀN BỘ FILE CV PDF
  const handleUpload = async () => {
    if (!file || !session?.user) return;
    setLoading(true);
    setResult(null);
    setEditableArticles([]);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('candidate_name', candidateName);
    formData.append('user_id', session.user.id);

    try {
      const response = await axios.post('http://localhost:8000/api/score-cv', formData);
      const data = response.data;
      if (data.status === "Warning") {
        alert(data.message);
        setResult(data);
        return;
      }
      setResult(data);
      setEditableArticles(data.detailed_scores || []);
      setTotalScore(data.summary?.total_max_score_estimated || 0);
      fetchDashboardHistory(); 
    } catch (error) {
      alert("Lỗi hệ thống khi phân tích CV!");
    } finally {
      setLoading(false);
    }
  };

  const correctArticlesCount = editableArticles.filter(art => art.check_title?.status === true && art.check_author_count?.status === true).length;
  const validArticlesScore = editableArticles.filter(art => art.check_title?.status === true && art.check_author_count?.status === true).reduce((sum, art) => sum + (art.max_score || 0), 0);

  // XUẤT FILE EXCEL BÁO CÁO
  const handleExportExcel = () => {
    if (editableArticles.length === 0) return alert("Chưa có dữ liệu để xuất file!");
    import('xlsx').then((XLSX) => {
      const excelRows = [
        ["BÁO CÁO THẨM ĐỊNH VÀ KIỂM KÊ LÝ LỊCH KHOA HỌC TỰ ĐỘNG"],
        ["Tên hồ sơ file PDF:", result?.filename || "N/A"],
        ["Người thực hiện thẩm định:", candidateName],
        ["Tổng số bài báo bóc tách:", `${editableArticles.length} bài`],
        ["Điểm các bài báo hợp lệ (Thực đạt):", `${validArticlesScore.toFixed(2)} điểm`],
        ["Tổng điểm tất cả bài báo (Kê khai):", `${totalScore.toFixed(2)} điểm`],
        ["Tỉ lệ số bài báo kê khai đúng:", `${correctArticlesCount}/${editableArticles.length} bài (${((correctArticlesCount / editableArticles.length) * 100).toFixed(0)}%)`],
        [],
        ["STT PDF", "Tên bài báo khai báo", "Đối chiếu tên (API)", "Tạp chí / Kỷ yếu hội thảo", "Số lượng tác giả", "Đối chiếu Số TG", "Vai trò tác giả chính", "Đối chiếu Vai trò", "Năm xuất bản", "Điểm quy đổi"]
      ];

      editableArticles.forEach((art) => {
        excelRows.push([art.stt_pdf, art.title, art.check_title?.message || "Không rõ", art.journal, art.author_count || 1, art.check_author_count?.message || "Khớp", art.is_main ? "Có" : "Không", art.check_is_main?.message || "Khớp", art.extracted_year || art.year || "N/A", art.max_score ? parseFloat(art.max_score.toFixed(3)) : 0.000]);
      });

      const worksheet = XLSX.utils.aoa_to_sheet(excelRows);
      worksheet['!cols'] = [{ wch: 8 }, { wch: 45 }, { wch: 20 }, { wch: 35 }, { wch: 10 }, { wch: 18 }, { wch: 12 }, { wch: 25 }, { wch: 12 }, { wch: 12 }];
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "KetQuaThamDinh");
      const safeName = candidateName.replace(/\s+/g, '_');
      XLSX.writeFile(workbook, `Bao_Cao_Tham_Dinh_LLKH_${safeName}.xlsx`);
    });
  };

  // RENDER MÀN HÌNH ĐĂNG NHẬP CHÍNH GIỮA (ĐÃ FIX OVERFLOW)
  if (!session) {
    return (
      <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: '#f1f5f9', display: 'flex', alignItems: 'center', justifyInverted: 'center', justifyContent: 'center', zIndex: 9999 }}>
        <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05)', width: '380px', border: `1px solid ${COLORS.border}` }}>
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <div style={{ display: 'inline-flex', padding: '12px', borderRadius: '12px', backgroundColor: '#eff6ff', marginBottom: '15px' }}>
              <BrainCircuit color={COLORS.primary} size={36} />
            </div>
            <h2 style={{ margin: '0 0 5px 0', fontSize: '22px', fontWeight: 'bold', color: COLORS.text }}>Hệ thống Kiểm kê LLKH</h2>
            <p style={{ margin: 0, fontSize: '13px', color: COLORS.subtle }}>{isRegisterMode ? "Đăng ký tài khoản kiểm kê mới" : "Đăng nhập để quản lý Dashboard"}</p>
          </div>

          <form onSubmit={handleAuthAction} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div>
              <label style={labelStyle}>Email trường học</label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color={COLORS.subtle} style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input style={{ ...inputStyle, paddingLeft: '38px' }} type="email" placeholder="name@university.edu.vn" value={authEmail} onChange={e => setAuthEmail(e.target.value)} />
              </div>
            </div>
            <div>
              <label style={labelStyle}>Mật khẩu bảo mật</label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color={COLORS.subtle} style={{ position: 'absolute', left: '12px', top: '13px' }} />
                <input style={{ ...inputStyle, paddingLeft: '38px' }} type="password" placeholder="••••••••" value={authPassword} onChange={e => setAuthPassword(e.target.value)} />
              </div>
            </div>
            <button type="submit" disabled={authLoading} style={buttonStyle}>
              {authLoading ? <RefreshCw className="animate-spin" size={18} /> : (isRegisterMode ? "Tạo tài khoản" : "Đăng nhập hệ thống")}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: COLORS.subtle }}>
            {isRegisterMode ? "Đã có tài khoản hệ thống? " : "Chưa được cấp tài khoản? "}
            <span style={{ color: COLORS.primary, fontWeight: '600', cursor: 'pointer' }} onClick={() => setIsRegisterMode(!isRegisterMode)}>
              {isRegisterMode ? "Đăng nhập ngay" : "Đăng ký thử nghiệm"}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: COLORS.bg, overflow: 'hidden' }}>
      
      {/* BỘ TÍNH ĐIỂM LẺ BÊN TRÁI (ĐÃ BỎ Ô HỌ TÊN ĐỐI CHIẾU THEO Ý KHA) */}
      <div style={{ width: '350px', backgroundColor: COLORS.sidebar, borderRight: `1px solid ${COLORS.border}`, padding: '25px', display: 'flex', flexDirection: 'column', gap: '15px', overflowY: 'auto' }}>
        <h2 style={{ fontSize: '17px', display: 'flex', alignItems: 'center', gap: '10px', color: COLORS.primary, margin: '0 0 10px 0' }}>
          <Calculator size={18} /> Tính điểm một bài báo
        </h2>
        <div>
          <label style={labelStyle}>Tên bài báo khoa học</label>
          <textarea style={inputStyle} rows="4" value={singleInput.title} onChange={e => setSingleInput({...singleInput, title: e.target.value})} placeholder="Nhập tiêu đề bài báo..." />
        </div>
        <div>
          <label style={labelStyle}>Tạp chí / Kỷ yếu hội thảo</label>
          <textarea style={inputStyle} rows="2" value={singleInput.journal} onChange={e => setSingleInput({...singleInput, journal: e.target.value})} placeholder="Nhập tên tạp chí hoặc mã ISSN..." />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Năm xuất bản</label>
            <input style={inputStyle} type="text" value={singleInput.year} onChange={e => setSingleInput({...singleInput, year: e.target.value})} placeholder="2025" />
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Số tác giả</label>
            <input style={inputStyle} type="number" min="1" value={singleInput.author_count} onChange={e => setSingleInput({...singleInput, author_count: e.target.value})} />
          </div>
        </div>
        <div>
          <label style={labelStyle}>Vai trò tham gia</label>
          <select style={inputStyle} value={String(singleInput.is_main)} onChange={e => setSingleInput({...singleInput, is_main: e.target.value === 'true'})}>
            <option value="true">Tác giả chính / liên hệ (Có)</option>
            <option value="false">Tác giả thành viên (Không)</option>
          </select>
        </div>
        <button onClick={handleSingleScore} disabled={singleLoading} style={buttonStyle}>
          {singleLoading ? <RefreshCw className="animate-spin" size={18} /> : "Tính toán số điểm"}
        </button>
        {singleScore && (
          <div style={{ marginTop: '5px', padding: '12px', borderRadius: '8px', background: '#f0fdf4', border: '1px solid #bbf7d0', textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: COLORS.subtle }}>Phân hạng danh mục: <span style={{fontWeight: 'bold', color: COLORS.primary}}>{singleScore.rank_found || 'N/A'}</span></div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: COLORS.success, margin: '2px 0' }}>{singleScore.max_score}</div>
            <div style={{ fontSize: '11px', color: COLORS.subtle, lineHeight: 1.3 }}>{singleScore.rule_applied}</div>
          </div>
        )}
      </div>

      {/* CỘT PHẢI CHÍNH: CHỨC NĂNG HỆ THỐNG CÓ CHUYỂN TAB */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '35px' }}>
        
        {/* Header thông tin người dùng */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1 style={{ margin: 0, fontSize: '24px', display: 'flex', alignItems: 'center', gap: '12px', fontWeight: '700' }}>
            <BrainCircuit color={COLORS.primary} size={28} /> Hệ thống Thẩm định Lý lịch Khoa học
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span style={{ fontSize: '13px', color: COLORS.subtle }}>Tài khoản: <b>{session.user.email}</b></span>
            <button onClick={handleSignOut} style={{ background: 'none', border: `1px solid ${COLORS.border}`, padding: '6px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', color: '#b91c1c', fontWeight: '600' }}>
              <LogOut size={14} /> Đăng xuất
            </button>
          </div>
        </div>

        {/* THANH DIỀU HƯỚNG TAB QUẢN LÝ THEO Ý KHA */}
        <div style={{ display: 'flex', gap: '25px', borderBottom: `1px solid ${COLORS.border}`, marginBottom: '25px' }}>
          <button 
            onClick={() => setActiveTab('evaluate')}
            style={{
              padding: '12px 4px', background: 'none', border: 'none',
              borderBottom: activeTab === 'evaluate' ? `3px solid ${COLORS.primary}` : '3px solid transparent',
              color: activeTab === 'evaluate' ? COLORS.primary : COLORS.subtle,
              fontWeight: '700', cursor: 'pointer', fontSize: '14.5px', display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <FileSearch size={17} /> Thẩm định tệp CV PDF
          </button>
          <button 
            onClick={() => setActiveTab('dashboard')}
            style={{
              padding: '12px 4px', background: 'none', border: 'none',
              borderBottom: activeTab === 'dashboard' ? `3px solid ${COLORS.primary}` : '3px solid transparent',
              color: activeTab === 'dashboard' ? COLORS.primary : COLORS.subtle,
              fontWeight: '700', cursor: 'pointer', fontSize: '14.5px', display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <History size={17} /> Lịch sử chấm
          </button>
        </div>

        {/* --- NỘI DUNG TAB 1: THẨM ĐỊNH HỒ SƠ --- */}
        {activeTab === 'evaluate' && (
          <div>
            {/* Tên người thực hiện (Mặc định ăn theo email, sửa được) */}
            <div style={{ background: 'white', padding: '15px 20px', borderRadius: '12px', border: `1px solid ${COLORS.border}`, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '15px' }}>
              <label style={{ fontSize: '14px', fontWeight: '600', color: COLORS.text, whiteSpace: 'nowrap' }}>Tên người thực hiện / Ứng viên:</label>
              <input style={{ ...inputStyle, width: '320px' }} type="text" value={candidateName} onChange={e => setCandidateName(e.target.value)} placeholder="Nhập tên xuất báo cáo Excel..." />
            </div>

            {/* Khung Kéo thả PDF */}
            <div style={{ border: `2px dashed ${COLORS.border}`, borderRadius: '16px', padding: '30px', textAlign: 'center', background: 'white', marginBottom: '25px' }}>
              <input type="file" id="cvUpload" hidden onChange={e => setFile(e.target.files[0])} accept=".pdf" />
              <label htmlFor="cvUpload" style={{ cursor: 'pointer', display: 'block' }}>
                <Upload size={32} style={{ color: COLORS.subtle, marginBottom: '8px' }} />
                <div style={{ fontWeight: '600', fontSize: '14px' }}>{file ? file.name : "Chọn hoặc kéo thả file lý lịch khoa học PDF (Bảng 7.1.a)"}</div>
              </label>
              {file && !loading && (
                <button onClick={handleUpload} style={{ ...buttonStyle, width: '160px', margin: '12px auto 0', padding: '8px' }}>Chạy phân tích</button>
              )}
              {loading && (
                <div style={{ marginTop: '12px', color: COLORS.primary, fontWeight: '500', fontSize: '13px' }}>
                  <Loader2 className="animate-spin" style={{ margin: '0 auto 6px' }} />
                  <div>Đang kích hoạt AI trích xuất thực thể & kiểm tra phân quyền...</div>
                </div>
              )}
            </div>

            {result && result.status === "Warning" && (
              <div style={{ padding: '15px', background: '#fef2f2', color: '#991b1b', borderRadius: '12px', border: '1px solid #fee2e2', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
                <AlertCircle color="#b91c1c" size={18} />
                <div><b>Cảnh báo tệp:</b> {result.message}</div>
              </div>
            )}

            {/* Khối kết quả phân tích */}
            {result && result.status === "Success" && (
              <div style={{ animation: 'fadeIn 0.4s ease' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#eff6ff', padding: '20px 25px', borderRadius: '12px', border: `1px solid ${COLORS.border}`, marginBottom: '20px' }}>
                  <div>
                    <h3 style={{ margin: '0 0 5px', color: COLORS.primary, fontSize: '17px' }}>Kết quả tệp: {result.filename}</h3>
                    <p style={{ margin: 0, color: COLORS.subtle, fontSize: '13px' }}>Người thực hiện: <b>{candidateName}</b> | Tổng số bóc tách: <b>{result.summary?.total_articles}</b> bài.</p>
                    <p style={{ margin: '6px 0 0 0', color: COLORS.text, fontSize: '13px', fontWeight: '600' }}>
                      Tỉ lệ số bài báo kê đúng: <span style={{ color: COLORS.primary, fontSize: '14px' }}>{correctArticlesCount}/{editableArticles.length}</span> bài ({editableArticles.length > 0 ? ((correctArticlesCount / editableArticles.length) * 100).toFixed(0) : 0}%)
                    </p>
                  </div>
                  
                  <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '10px' }}>
                    <div style={{ fontSize: '34px', fontWeight: '800', color: COLORS.success, lineHeight: 1 }}>
                      {validArticlesScore.toFixed(2)}
                      <span style={{ color: COLORS.subtle, fontSize: '20px', fontWeight: '600' }}>/{totalScore.toFixed(2)}</span>
                      <span style={{ fontSize: '13px', color: COLORS.subtle, fontWeight: 'normal', marginLeft: '5px' }}>điểm</span>
                    </div>
                    <button onClick={handleExportExcel} style={{ backgroundColor: COLORS.success, color: 'white', border: 'none', padding: '8px 14px', borderRadius: '6px', fontWeight: '600', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                      <FileText size={15} /> Xuất báo cáo Excel
                    </button>
                  </div>
                </div>

                <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '10px', overflow: 'hidden', border: `1px solid ${COLORS.border}` }}>
                  <thead>
                    <tr style={{ background: '#f8fafc', borderBottom: `2px solid ${COLORS.border}` }}>
                      <th style={thStyle}>STT</th>
                      <th style={{ ...thStyle, width: '25%' }}>Tên bài khai báo</th>
                      <th style={thStyle}>Đối chiếu tên</th>
                      <th style={{ ...thStyle, width: '20%' }}>Tạp chí</th>
                      <th style={thStyle}>Số TG</th>
                      <th style={thStyle}>Đối chiếu Số TG</th>
                      <th style={thStyle}>TG chính</th>
                      <th style={thStyle}>Đối chiếu Vai trò</th>
                      <th style={thStyle}>Năm</th>
                      <th style={thStyle}>Điểm</th>
                      <th style={{ ...thStyle, textAlign: 'center' }}>Copy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editableArticles.map((art, idx) => (
                      <tr key={idx} className="table-row" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                        <td style={tdStyle}>{art.stt_pdf}</td>
                        <td style={{ ...tdStyle, fontWeight: '500' }}>{art.title}</td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '6px', fontWeight: '600', background: art.check_title?.status ? '#e6f4ea' : '#fce8e6', color: art.check_title?.status ? '#137333' : '#c5221f', display: 'inline-block', whiteSpace: 'nowrap' }}>
                            {art.check_title?.message}
                          </span>
                        </td>
                        <td style={tdStyle}>
                          <div>{art.journal}</div>
                          {art.rank_found && art.rank_found !== 'N/A' && (
                            <span style={{ fontSize: '11px', background: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px', marginTop: '5px', display: 'inline-block', fontWeight: 'bold' }}>Rank: {art.rank_found}</span>
                          )}
                        </td>
                        <td style={{ ...tdStyle, textAlign: 'center', fontWeight: '600' }}>{art.author_count || 1}</td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '6px', fontWeight: '600', background: !art.check_title?.status ? '#f1f5f9' : (art.check_author_count?.status ? '#e6f4ea' : '#fce8e6'), color: !art.check_title?.status ? '#475569' : (art.check_author_count?.status ? '#137333' : '#c5221f'), display: 'inline-block', whiteSpace: 'nowrap' }}>
                            {art.check_author_count?.message}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, textAlign: 'center' }}>
                          <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '12px', fontWeight: '600', background: art.is_main ? '#ecfdf5' : '#f1f5f9', color: art.is_main ? '#047857' : '#475569' }}>{art.is_main ? "Có" : "Không"}</span>
                        </td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '6px', fontWeight: '600', background: !art.check_title?.status ? '#f1f5f9' : (art.check_is_main?.status ? '#e6f4ea' : '#fef7e0'), color: !art.check_title?.status ? '#475569' : (art.check_is_main?.status ? '#137333' : '#b06000'), display: 'inline-block', whiteSpace: 'nowrap' }}>
                            {art.check_is_main?.message}
                          </span>
                        </td>
                        <td style={tdStyle}>{art.extracted_year || art.year || 'N/A'}</td>
                        <td style={{ ...tdStyle, fontWeight: 'bold', color: COLORS.success, fontSize: '14px' }}>{art.max_score ? art.max_score.toFixed(3) : '0.000'}</td>
                        <td style={{ ...tdStyle, textAlign: 'center' }}>
                          <button onClick={() => copyToChecker(art)} style={{ background: 'none', border: `1px solid ${COLORS.border}`, padding: '5px', borderRadius: '6px', cursor: 'pointer', color: COLORS.subtle }}>
                            <Copy size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* --- NỘI DUNG TAB 2: DASHBOARD LỊCH SỬ CHẤM --- */}
        {activeTab === 'dashboard' && (
          <div style={{ background: 'white', padding: '25px', borderRadius: '16px', border: `1px solid ${COLORS.border}`, animation: 'fadeIn 0.3s ease' }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', fontWeight: '700', color: COLORS.text, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} color={COLORS.primary} /> Lịch sử kiểm kê tài khoản của bạn
            </h3>
            
            {historyList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: COLORS.subtle, fontSize: '13px', background: '#f8fafc', borderRadius: '8px', border: `1px dashed ${COLORS.border}` }}>
                Bạn chưa thực hiện lượt thẩm định hồ sơ nào. Toàn bộ lịch sử phân quyền lưu trữ sẽ hiện tại đây.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: `2px solid ${COLORS.border}` }}>
                    <th style={{ padding: '12px 10px', textAlign: 'left', color: COLORS.subtle, fontWeight: '600' }}>Thời gian thực hiện</th>
                    <th style={{ padding: '12px 10px', textAlign: 'left', color: COLORS.subtle, fontWeight: '600' }}>Tên tệp hồ sơ PDF</th>
                    <th style={{ padding: '12px 10px', textAlign: 'left', color: COLORS.subtle, fontWeight: '600' }}>Người chấm / Ứng viên</th>
                    <th style={{ padding: '12px 10px', textAlign: 'center', color: COLORS.subtle, fontWeight: '600' }}>Số lượng bài</th>
                    <th style={{ padding: '12px 10px', textAlign: 'center', color: COLORS.subtle, fontWeight: '600' }}>Tỉ lệ đúng hành chính</th>
                    <th style={{ padding: '12px 10px', textAlign: 'right', color: COLORS.subtle, fontWeight: '600' }}>Tổng mốc điểm đạt</th>
                  </tr>
                </thead>
                <tbody>
                  {historyList.map((hist, i) => (
                    <tr key={i} className="table-row" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                      {/* ĐÃ FIX: Đổi chuẩn cú pháp sang new Date() của JavaScript */}
                      <td style={{ padding: '14px 10px', color: COLORS.subtle }}>{new Date(hist.checked_at).toLocaleString('vi-VN')}</td>
                      <td style={{ padding: '14px 10px', fontWeight: '500', color: COLORS.text }}>{hist.file_name}</td>
                      <td style={{ padding: '14px 10px' }}>{hist.candidate_name}</td>
                      <td style={{ padding: '14px 10px', textAlign: 'center' }}>{hist.total_articles} bài</td>
                      <td style={{ padding: '14px 10px', textAlign: 'center', fontWeight: '700', color: hist.accuracy_rate >= 80 ? COLORS.success : '#d97706' }}>{hist.accuracy_rate}%</td>
                      <td style={{ padding: '14px 10px', textAlign: 'right', fontWeight: '800', color: COLORS.primary, fontSize: '14px' }}>{hist.valid_score}/{hist.total_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

      </div>

      <style>{`
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .table-row:hover { background-color: #f8fafc; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        textarea:focus, input:focus, select:focus { outline: none; border-color: ${COLORS.primary}; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08); }
      `}</style>
    </div>
  );
}

export default App;