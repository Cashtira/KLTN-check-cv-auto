import React, { useState } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle, BrainCircuit, Loader2, Calculator, Copy, RefreshCw, AlertCircle, UserCheck, Users } from 'lucide-react';

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

function App() {
  // --- STATE CHO BÊN TRÁI (BỘ TÍNH ĐIỂM LẺ) ---
  const [singleInput, setSingleInput] = useState({ 
    title: '', 
    authors: 'Không xác định', 
    journal: '', 
    year: '',
    author_count: 1, 
    is_main: true    
  });
  const [singleScore, setSingleScore] = useState(null);
  const [singleLoading, setSingleLoading] = useState(false);

  // --- STATE CHO BÊN PHẢI (PHÂN TÍCH CV TỔNG THỂ) ---
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [editableArticles, setEditableArticles] = useState([]);
  const [totalScore, setTotalScore] = useState(0);

  // --- LOGIC GỌI API BÊN TRÁI ---
  const handleSingleScore = async () => {
    if (!singleInput.title || !singleInput.journal) return alert("Nhập đủ Tên bài và Tạp chí nhé!");
    setSingleLoading(true);
    
    const payload = {
      ...singleInput,
      author_count: parseInt(singleInput.author_count) || 1,
      is_main: singleInput.is_main === true || singleInput.is_main === 'true'
    };

    try {
      const response = await axios.post('https://kltn-check-cv-auto.onrender.com/api/score-article', payload);
      setSingleScore(response.data.data);
    } catch (error) {
      alert("Lỗi tính điểm lẻ, kiểm tra kết nối Backend nhé!");
    } finally {
      setSingleLoading(false);
    }
  };

  // Hàm copy từ bảng bên phải sang bộ công cụ tính lẻ bên trái
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

  // --- LOGIC GỌI API BÊN PHẢI ---
  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setEditableArticles([]);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await axios.post('https://kltn-check-cv-auto.onrender.com/api/score-cv', formData);
      const data = response.data;
      
      if (data.status === "Warning") {
        alert(data.message);
        setResult(data);
        return;
      }
      
      setResult(data);
      setEditableArticles(data.detailed_scores || []);
      setTotalScore(data.summary?.total_max_score_estimated || 0);
    } catch (error) {
      alert("Lỗi hệ thống khi phân tích CV!");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: COLORS.bg, overflow: 'hidden' }}>
      
      {/* --- CỘT TRÁI: CÔNG CỤ TÍNH ĐIỂM LẺ (FIXED SIDEBAR) --- */}
      <div style={{ 
        width: '350px', 
        backgroundColor: COLORS.sidebar, 
        borderRight: `1px solid ${COLORS.border}`,
        padding: '25px',
        display: 'flex',
        flexDirection: 'column',
        gap: '15px',
        overflowY: 'auto',
        boxShadow: '2px 0 10px rgba(0,0,0,0.01)',
        zIndex: 10
      }}>
        <h2 style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px', color: COLORS.primary, margin: '0 0 10px 0' }}>
          <Calculator size={20} /> Tính điểm một bài báo
        </h2>
        
        <div>
          <label style={labelStyle}>Tên bài báo</label>
          <textarea style={inputStyle} rows="3" value={singleInput.title} onChange={e => setSingleInput({...singleInput, title: e.target.value})} />
        </div>
        
        <div>
          <label style={labelStyle}>Tạp chí / Kỷ yếu hội thảo</label>
          <textarea style={inputStyle} rows="2" value={singleInput.journal} onChange={e => setSingleInput({...singleInput, journal: e.target.value})} />
        </div>
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Năm</label>
            <input style={inputStyle} type="text" value={singleInput.year} onChange={e => setSingleInput({...singleInput, year: e.target.value})} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Số tác giả</label>
            <input style={inputStyle} type="number" min="1" value={singleInput.author_count} onChange={e => setSingleInput({...singleInput, author_count: e.target.value})} />
          </div>
        </div>

        <div>
          <label style={labelStyle}>Vai trò tác giả</label>
          <select 
            style={inputStyle} 
            value={String(singleInput.is_main)} 
            onChange={e => setSingleInput({...singleInput, is_main: e.target.value === 'true'})}
          >
            <option value="true">Là tác giả chính (Có)</option>
            <option value="false">Tác giả thành viên (Không)</option>
          </select>
        </div>

        <button onClick={handleSingleScore} disabled={singleLoading} style={buttonStyle}>
          {singleLoading ? <RefreshCw className="animate-spin" size={18} /> : "Tính điểm bài này"}
        </button>

        {singleScore && (
          <div style={{ marginTop: '10px', padding: '15px', borderRadius: '8px', background: '#f0fdf4', border: '1px solid #bbf7d0', textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: COLORS.subtle }}>Rank tìm thấy: <span style={{fontWeight: 'bold', color: COLORS.primary}}>{singleScore.rank_found || 'N/A'}</span></div>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: COLORS.success, margin: '5px 0' }}>{singleScore.max_score}</div>
            <div style={{ fontSize: '11px', color: COLORS.subtle, lineHeight: 1.3 }}>{singleScore.rule_applied}</div>
          </div>
        )}
      </div>

      {/* --- CỘT PHẢI: KẾT QUẢ ĐÁNH GIÁ CẢ CV (SCROLLABLE CONTENT) --- */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '40px' }}>
        
        {/* Header ứng dụng */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
          <h1 style={{ margin: 0, fontSize: '26px', display: 'flex', alignItems: 'center', gap: '12px', fontWeight: '700' }}>
            <BrainCircuit color={COLORS.primary} size={32} /> Tính điểm cho CV
          </h1>
          <div style={{ color: COLORS.subtle, fontSize: '13px' }}>HĐGSNN Ngành CNTT | Mẫu lý lịch 01</div>
        </div>

        {/* Khung tải tệp PDF */}
        <div style={{ border: `2px dashed ${COLORS.border}`, borderRadius: '16px', padding: '30px', textAlign: 'center', background: 'white', marginBottom: '35px' }}>
          <input type="file" id="cvUpload" hidden onChange={e => setFile(e.target.files[0])} accept=".pdf" />
          <label htmlFor="cvUpload" style={{ cursor: 'pointer', display: 'block' }}>
            <Upload size={36} style={{ color: COLORS.subtle, marginBottom: '10px' }} />
            <div style={{ fontWeight: '600', fontSize: '15px' }}>{file ? file.name : "Kéo thả hoặc click chọn file PDF CV"}</div>
          </label>
          {file && !loading && (
            <button onClick={handleUpload} style={{ ...buttonStyle, width: '180px', margin: '15px auto 0', padding: '10px' }}>Chạy phân tích</button>
          )}
          {loading && (
            <div style={{ marginTop: '15px', color: COLORS.primary, fontWeight: '500' }}>
              <Loader2 className="animate-spin" style={{ margin: '0 auto 8px' }} />
              <div>Đang bóc tách thông tin & áp dụng Điều 8 quy đổi...</div>
            </div>
          )}
        </div>

        {/* Khối hiển thị cảnh báo từ hệ thống nếu status là Warning */}
        {result && result.status === "Warning" && (
          <div style={{ padding: '20px', background: '#fef2f2', color: '#991b1b', borderRadius: '12px', border: '1px solid #fee2e2', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle color="#b91c1c" />
            <div>
              <strong style={{ display: 'block' }}>Hệ thống không thể phân tích tệp tin này:</strong>
              {result.message}
            </div>
          </div>
        )}

        {/* Khối hiển thị kết quả phân tích chỉ vẽ khi status là Success */}
        {result && result.status === "Success" && (
          <div style={{ animation: 'fadeIn 0.4s ease' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#eff6ff', padding: '20px 25px', borderRadius: '12px', border: '1px solid #bfdbfe', marginBottom: '25px' }}>
              <div>
                <h3 style={{ margin: '0 0 5px', color: COLORS.primary, fontSize: '18px' }}>Kết quả CV: {result.filename}</h3>
                <p style={{ margin: 0, color: COLORS.subtle, fontSize: '14px' }}>Số bài: <b>{result.summary?.total_articles}</b> bài báo khoa học.</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '42px', fontWeight: '800', color: COLORS.success }}>{totalScore.toFixed(2)}</div>
              </div>
            </div>

            {/* Bảng kết quả nâng cấp cột */}
            <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '10px', overflow: 'hidden', border: `1px solid ${COLORS.border}`, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.01)' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: `2px solid ${COLORS.border}` }}>
                  <th style={thStyle}>STT</th>
                  <th style={{ ...thStyle, width: '35%' }}>Tên bài</th>
                  <th style={{ ...thStyle, width: '30%' }}>Tạp chí</th>
                  <th style={thStyle}><Users size={16} title="Số tác giả" /> Số TG</th>
                  <th style={thStyle}><UserCheck size={16} title="Tác giả chính" /> TG chính</th>
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
                      <div>{art.journal}</div>
                      {art.rank_found && art.rank_found !== 'N/A' && (
                        <span style={{ fontSize: '11px', background: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px', marginTop: '5px', display: 'inline-block', fontWeight: 'bold' }}>
                          Rank: {art.rank_found}
                        </span>
                      )}
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center', fontWeight: '600' }}>
                      {art.author_count || 1}
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <span style={{ 
                        fontSize: '12px', 
                        padding: '3px 8px', 
                        borderRadius: '12px', 
                        fontWeight: '600',
                        background: art.is_main ? '#ecfdf5' : '#f1f5f9',
                        color: art.is_main ? '#047857' : '#475569'
                      }}>
                        {art.is_main ? "Có" : "Không"}
                      </span>
                    </td>
                    <td style={tdStyle}>{art.extracted_year || art.year || 'N/A'}</td>
                    <td style={{ ...tdStyle, fontWeight: 'bold', color: COLORS.success, fontSize: '15px' }}>
                      {art.max_score ? art.max_score.toFixed(3) : '0.000'}
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <button onClick={() => copyToChecker(art)} title="Copy sang bộ tính lẻ bên trái" style={{ background: 'none', border: `1px solid ${COLORS.border}`, padding: '6px', borderRadius: '6px', cursor: 'pointer', color: COLORS.subtle, transition: 'all 0.2s' }}
                        onMouseOver={e => { e.currentTarget.style.borderColor = COLORS.primary; e.currentTarget.style.color = COLORS.primary; }}
                        onMouseOut={e => { e.currentTarget.style.borderColor = COLORS.border; e.currentTarget.style.color = COLORS.subtle; }}>
                        <Copy size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Style CSS */}
      <style>{`
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .table-row:hover { background-color: #f8fafc; }
        textarea:focus, input:focus, select:focus { outline: none; border-color: ${COLORS.primary}; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08); }
      `}</style>
    </div>
  );
}

const thStyle = { padding: '14px 16px', textAlign: 'left', fontSize: '13px', color: COLORS.subtle, fontWeight: '600' };
const tdStyle = { padding: '14px 16px', fontSize: '13.5px', color: COLORS.text, verticalAlign: 'top', lineHeight: '1.4' };

export default App;