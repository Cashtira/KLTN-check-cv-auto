import React, { useEffect, useState } from 'react';

export default function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Gọi API từ Backend FastAPI
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    fetch(`${apiUrl}/api/admin/users-summary`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.success) {
          setUsers(resData.data);
        } else {
          alert("Lỗi lấy dữ liệu: " + resData.error);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  // Định nghĩa các hằng số định dạng bảng
  const thStyle = { padding: '12px 10px', textAlign: 'left', color: '#64748b', fontWeight: '600', borderBottom: '2px solid #e2e8f0' };
  const tdStyle = { padding: '14px 10px', borderBottom: '1px solid #e2e8f0' };

  if (loading) return <div style={{ textAlign: 'center', padding: '30px', color: '#64748b', fontSize: '13px' }}>Đang tải dữ liệu quản trị tài khoản...</div>;

  return (
    <div style={{ marginTop: '15px', animation: 'fadeIn 0.3s ease' }}>
      {users.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '30px', color: '#64748b', fontSize: '13px', background: '#f8fafc', borderRadius: '8px', border: '1px dashed #e2e8f0' }}>
          Chưa có dữ liệu tài khoản nào trong hệ thống.
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#f8fafc' }}>
              <th style={{ ...thStyle, width: '60px' }}>STT</th>
              <th style={thStyle}>Email Người Dùng</th>
              <th style={thStyle}>Ngày Tạo Tài Khoản</th>
              <th style={{ ...thStyle, textAlign: 'center' }}>Số Lần Quét CV</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user, index) => (
              <tr key={user.id} className="table-row">
                <td style={{ ...tdStyle, color: '#64748b' }}>{index + 1}</td>
                <td style={{ ...tdStyle, fontWeight: '500', color: '#1e293b' }}>{user.email}</td>
                <td style={{ ...tdStyle, color: '#64748b' }}>
                  {new Date(user.created_at).toLocaleDateString('vi-VN')}
                </td>
                <td style={{ ...tdStyle, textAlign: 'center' }}>
                  <span style={{ 
                    padding: '4px 10px', 
                    borderRadius: '12px', 
                    fontWeight: '600', 
                    background: user.total_scans > 0 ? '#e6f4ea' : '#f1f5f9', 
                    color: user.total_scans > 0 ? '#137333' : '#475569',
                    display: 'inline-block'
                  }}>
                    {user.total_scans} lần
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}