import { useState, useEffect } from 'react';
import { FiUpload, FiLock, FiUnlock, FiImage, FiFileText, FiCopy, FiFile, FiTrash2, FiDownload } from 'react-icons/fi';
import FileUploader from '../components/FileUploader';
import DocumentProcessingTabs from '../components/DocumentProcessingTabs';
import api from '../api/client';
import { useModal } from '../context/ModalContext';

const PDFPage = () => {
  const [pdfDocuments, setPdfDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [loading, setLoading] = useState(false);
  const { showConfirm, showError, showSuccess } = useModal();
  
  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const response = await api.pdf.getDocuments();
      console.log('PDF documents response:', response);
      setPdfDocuments(response.data?.items || []);
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
      await api.pdf.deleteDocument(documentId);
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
    e.stopPropagation(); // Ngăn chặn sự kiện click lan toả đến document row
    
    try {
      // Sử dụng window.open để mở trong tab mới - tự động chia sẻ cookies/auth với tab hiện tại
      window.open(api.pdf.downloadDocument(documentId), '_blank');
    } catch (error) {
      console.error('Lỗi khi tải xuống tài liệu:', error);
      showError('Không thể tải xuống tài liệu', 'Lỗi tải xuống');
    }
  };
  
  const filteredDocuments = activeTab === 'all' 
    ? pdfDocuments 
    : activeTab === 'encrypted' 
      ? pdfDocuments.filter(doc => doc.is_encrypted) 
      : pdfDocuments.filter(doc => !doc.is_encrypted);
  
  return (
    <div className="container mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Tài liệu PDF</h1>
        <p className="text-gray-600">Quản lý và xử lý tài liệu PDF của bạn</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <div className="card mb-6">
            <div className="flex border-b border-gray-200 mb-4">
              <button 
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'all' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setActiveTab('all')}
              >
                Tất cả tài liệu
              </button>
              <button 
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'encrypted' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setActiveTab('encrypted')}
              >
                Đã mã hóa
              </button>
              <button 
                className={`px-4 py-2 text-sm font-medium ${activeTab === 'normal' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
                onClick={() => setActiveTab('normal')}
              >
                Không mã hóa
              </button>
            </div>
            
            {loading ? (
              <div className="py-10 text-center">
                <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="mt-4 text-gray-600">Đang tải dữ liệu...</p>
              </div>
            ) : filteredDocuments.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tên tài liệu
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Trang
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Kích thước
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Trạng thái
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Thao tác
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredDocuments.map((doc) => (
                      <tr 
                        key={doc.id} 
                        className={`hover:bg-gray-50 cursor-pointer ${selectedDocument?.id === doc.id ? 'bg-primary-50' : ''}`}
                        onClick={() => handleSelectDocument(doc)}
                      >
                        <td className="px-4 py-3 text-sm text-gray-900">
                          <div className="flex items-center">
                            <FiFile className="text-red-500 mr-2" />
                            <span>{doc.original_filename || doc.title}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {doc.page_count || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {doc.file_size ? `${(doc.file_size / (1024 * 1024)).toFixed(2)} MB` : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {doc.is_encrypted ? (
                            <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                              <FiLock className="mr-1" /> Mã hóa
                            </span>
                          ) : (
                            <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              <FiUnlock className="mr-1" /> Không mã hóa
                            </span>
                          )}
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
                Không có tài liệu nào trong danh mục này
              </div>
            )}
          </div>
        </div>
        
        <div>
          <DocumentProcessingTabs
            documentType="pdf"
            acceptedFileTypes={{ 'application/pdf': ['.pdf'] }}
            operations={['to-word', 'to-images', 'encrypt', 'decrypt', 'watermark', 'sign']}
            api={{
              uploadDocument: api.pdf.uploadDocument,
              downloadDocument: api.pdf.downloadDocument,
              getTaskStatus: api.pdf.getTaskStatus,
              downloadProcessedDocument: api.pdf.downloadProcessedDocument,
              convertToWord: api.pdf.convertToWord,
              convertToImages: api.pdf.convertToImages,
              addWatermark: api.pdf.addWatermark,
              addSignature: api.pdf.addSignature,
              encryptDocument: api.pdf.encryptDocument,
              decryptDocument: api.pdf.decryptDocument
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default PDFPage; 