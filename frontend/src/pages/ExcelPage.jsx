import { useState, useEffect } from 'react';
import { FiTable, FiTrash2, FiDownload } from 'react-icons/fi';
import DocumentProcessingTabs from '../components/DocumentProcessingTabs';
import api from '../api/client';
import { useModal } from '../context/ModalContext';

const ExcelPage = () => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [loading, setLoading] = useState(false);
  const { showConfirm, showError, showSuccess } = useModal();
  
  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const response = await api.excel.getDocuments();
      console.log('Excel documents response:', response);
      setDocuments(response.data?.items || []);
    } catch (error) {
      console.error('Lỗi khi tải danh sách tài liệu:', error);
      showError('Không thể tải danh sách tài liệu', 'Lỗi tải dữ liệu');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDocuments();
  }, []);
  
  const handleSelectDocument = (document) => {
    setSelectedDocument(document);
  };
  
  const handleDeleteDocument = async (e, documentId) => {
    e.stopPropagation();
    
    const confirmed = await showConfirm(
      'Bạn có chắc chắn muốn xóa tài liệu này?',
      'Xác nhận xóa',
      { confirmText: 'Xóa', cancelText: 'Hủy' }
    );
    
    if (!confirmed) {
      return;
    }
    
    try {
      await api.excel.deleteDocument(documentId);
      showSuccess('Xóa tài liệu thành công', 'Đã xóa');
      fetchDocuments();
      if (selectedDocument?.id === documentId) {
        setSelectedDocument(null);
      }
    } catch (error) {
      console.error('Lỗi khi xóa tài liệu:', error);
      showError('Không thể xóa tài liệu', 'Lỗi xóa');
    }
  };
  
  const handleDownloadDocument = async (e, documentId) => {
    e.stopPropagation();
    
    try {
      window.open(api.excel.downloadDocument(documentId), '_blank');
    } catch (error) {
      console.error('Lỗi khi tải xuống tài liệu:', error);
      showError('Không thể tải xuống tài liệu', 'Lỗi tải xuống');
    }
  };
  
  return (
    <div className="container mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Tài liệu Excel</h1>
        <p className="text-gray-600">Quản lý và xử lý tài liệu Excel của bạn</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <div className="card mb-6">
            <h2 className="text-xl font-semibold mb-4">Danh sách tài liệu</h2>
            
            {loading ? (
              <div className="py-10 text-center">
                <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="mt-4 text-gray-600">Đang tải dữ liệu...</p>
              </div>
            ) : documents.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tên tài liệu
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Kích thước
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ngày tạo
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Thao tác
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {documents.map((doc) => (
                      <tr 
                        key={doc.id} 
                        className={`hover:bg-gray-50 cursor-pointer ${selectedDocument?.id === doc.id ? 'bg-primary-50' : ''}`}
                        onClick={() => handleSelectDocument(doc)}
                      >
                        <td className="px-4 py-3 text-sm text-gray-900">
                          <div className="flex items-center">
                            <FiTable className="text-green-500 mr-2" />
                            <span>{doc.original_filename || doc.title}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {doc.file_size ? `${(doc.file_size / (1024 * 1024)).toFixed(2)} MB` : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {doc.created_at ? new Date(doc.created_at).toLocaleDateString('vi-VN') : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 text-right">
                          <button 
                            className="p-1 text-gray-500 hover:text-gray-700 mr-1"
                            onClick={(e) => handleDownloadDocument(e, doc.id)}
                          >
                            <FiDownload className="h-5 w-5" />
                          </button>
                          <button 
                            className="p-1 text-red-500 hover:text-red-700"
                            onClick={(e) => handleDeleteDocument(e, doc.id)}
                          >
                            <FiTrash2 className="h-5 w-5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                Không có tài liệu nào
              </div>
            )}
          </div>
        </div>
        
        <div>
          <DocumentProcessingTabs
            documentType="excel"
            acceptedFileTypes={{
              'application/vnd.ms-excel': ['.xls'],
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
            }}
            operations={['to-pdf', 'to-word']}
            api={{
              uploadDocument: api.excel.uploadDocument,
              downloadDocument: api.excel.downloadDocument,
              getTaskStatus: api.excel.getTaskStatus,
              downloadProcessedDocument: api.excel.downloadProcessedDocument,
              convertToPdf: api.excel.convertToPdf,
              convertToWord: api.excel.convertToWord
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default ExcelPage; 