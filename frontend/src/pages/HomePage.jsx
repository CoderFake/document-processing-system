import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiFile, FiFileText, FiTable, FiUpload, FiClock } from 'react-icons/fi';
import FileUploader from '../components/FileUploader';
import api from '../api/client';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';

const HomePage = () => {
  const [recentDocuments, setRecentDocuments] = useState([]);
  const [stats, setStats] = useState({
    totalDocuments: 0,
    pdfCount: 0,
    wordCount: 0,
    excelCount: 0
  });
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
          const [statsResponse, recentDocsResponse] = await Promise.all([
          api.dashboard.getStats(),
          api.dashboard.getRecentDocuments(5)        
        ]);
        if (statsResponse.data) {
          setStats(statsResponse.data);
        }
          if (recentDocsResponse.data) {
            if (recentDocsResponse.data.items) {
              setRecentDocuments(recentDocsResponse.data.items);
          } else if (Array.isArray(recentDocsResponse.data)) {
            setRecentDocuments(recentDocsResponse.data);
          } else {
            setRecentDocuments([]);
          }
        }
      } catch (error) {
        console.error('Lỗi khi tải dữ liệu dashboard:', error);
        toast.error('Không thể tải dữ liệu dashboard');
        
                setRecentDocuments([]);
        
        setStats({
          totalDocuments: 0,
          pdfCount: 0,
          wordCount: 0,
          excelCount: 0
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);
  
  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    
    const formData = new FormData();
    formData.append('file', files[0]);
    
    try {
      const fileName = files[0].name.toLowerCase();
      let response;
      
      if (fileName.endsWith('.pdf')) {
        response = await api.pdf.uploadDocument(formData);
        toast.success('Tải lên tài liệu PDF thành công!');
      } else if (fileName.endsWith('.docx') || fileName.endsWith('.doc')) {
        response = await api.word.uploadDocument(formData);
        toast.success('Tải lên tài liệu Word thành công!');
      } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
        response = await api.excel.uploadDocument(formData);
        toast.success('Tải lên tài liệu Excel thành công!');
      } else {
        toast.error('Định dạng tệp không được hỗ trợ');
        return null;
      }
      
            const [statsResponse, recentDocsResponse] = await Promise.all([
        api.dashboard.getStats(),
        api.dashboard.getRecentDocuments(5)
      ]);
      
      if (statsResponse.data) {
        setStats(statsResponse.data);
      }
      
      if (recentDocsResponse.data) {
        setRecentDocuments(recentDocsResponse.data);
      }
      
      return response.data;
    } catch (error) {
      console.error('Lỗi khi tải lên:', error);
      toast.error('Có lỗi xảy ra khi tải lên tài liệu');
      throw error;
    }
  };
  
  const getIconForType = (type) => {
    switch (type) {
      case 'pdf': return <FiFile className="text-red-500" />;
      case 'word': return <FiFileText className="text-blue-500" />;
      case 'excel': return <FiTable className="text-green-500" />;
      default: return <FiFile />;
    }
  };
  
  const formatFileSize = (sizeInBytes) => {
    if (!sizeInBytes || typeof sizeInBytes !== 'number') return '-';
    
    if (sizeInBytes < 1024 * 1024) {
      return `${(sizeInBytes / 1024).toFixed(1)} KB`;
    } else {
      return `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
    }
  };
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('vi-VN');
    } catch (error) {
      return dateStr;
    }
  };
  
  return (
    <div className="container mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Xin chào, {user?.full_name || user?.username || 'Người dùng'}</h1>
        <p className="text-gray-600">Chào mừng đến với hệ thống xử lý tài liệu</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="col-span-1 md:col-span-2">
          <div className="card bg-gradient-accent text-white">
            <h2 className="text-xl font-semibold mb-4">Xử lý tài liệu nhanh chóng</h2>
            <p className="mb-6">Tải lên, chuyển đổi và quản lý tài liệu của bạn với giao diện dễ sử dụng</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Link to="/pdf" className="bg-white/20 hover:bg-white/30 p-4 rounded-lg transition-all text-center">
                <FiFile className="h-8 w-8 mx-auto mb-2" />
                <span>Tài liệu PDF</span>
              </Link>
              <Link to="/word" className="bg-white/20 hover:bg-white/30 p-4 rounded-lg transition-all text-center">
                <FiFileText className="h-8 w-8 mx-auto mb-2" />
                <span>Tài liệu Word</span>
              </Link>
              <Link to="/excel" className="bg-white/20 hover:bg-white/30 p-4 rounded-lg transition-all text-center">
                <FiTable className="h-8 w-8 mx-auto mb-2" />
                <span>Tài liệu Excel</span>
              </Link>
            </div>
          </div>
        </div>
        
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Thống kê</h2>
          {loading ? (
            <div className="flex justify-center items-center py-6">
              <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Tổng tài liệu</span>
                <span className="text-2xl font-bold">{stats.totalDocuments}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-red-50 p-3 rounded-lg">
                  <FiFile className="h-5 w-5 text-red-500 mb-1" />
                  <span className="text-sm text-gray-600">PDF</span>
                  <div className="text-lg font-semibold">{stats.pdfCount}</div>
                </div>
                <div className="bg-blue-50 p-3 rounded-lg">
                  <FiFileText className="h-5 w-5 text-blue-500 mb-1" />
                  <span className="text-sm text-gray-600">Word</span>
                  <div className="text-lg font-semibold">{stats.wordCount}</div>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <FiTable className="h-5 w-5 text-green-500 mb-1" />
                  <span className="text-sm text-gray-600">Excel</span>
                  <div className="text-lg font-semibold">{stats.excelCount}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 card">
          <h2 className="text-xl font-semibold mb-4">Tài liệu gần đây</h2>
          
          {loading ? (
            <div className="flex justify-center items-center py-10">
              <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : recentDocuments.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tên tài liệu
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Loại
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Kích thước
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ngày
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentDocuments.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div className="flex items-center">
                          {getIconForType(doc.type)}
                          <span className="ml-2">{doc.name || doc.filename || doc.title || doc.original_filename}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 uppercase">
                        {doc.type}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatFileSize(doc.size || doc.file_size)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <div className="flex items-center">
                          <FiClock className="mr-1" />
                          {formatDate(doc.date || doc.upload_date || doc.created_at)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Không có tài liệu nào gần đây
            </div>
          )}
        </div>
        
        <div className="card">
          <FileUploader 
            onFileUploaded={handleFileUpload}
            title="Tải lên nhanh"
            acceptedFileTypes={{
              'application/pdf': ['.pdf'],
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
              'application/msword': ['.doc'],
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
              'application/vnd.ms-excel': ['.xls']
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default HomePage; 