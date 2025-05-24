import { useState } from 'react';
import { FiUpload, FiFile, FiDownload } from 'react-icons/fi';
import FileUploader from './FileUploader';
import TaskProgress from './TaskProgress';
import { useModal } from '../context/ModalContext';

const DocumentProcessingTabs = ({
  documentType = 'pdf',
  acceptedFileTypes = {},
  operations = [],
  api = {}
}) => {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [selectedOperation, setSelectedOperation] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const { showError, showSuccess } = useModal();

  const getDocumentTypeTitle = () => {
    switch (documentType) {
      case 'pdf':
        return 'Xử lý tài liệu PDF';
      case 'word':
        return 'Xử lý tài liệu Word';
      case 'excel':
        return 'Xử lý tài liệu Excel';
      case 'archives':
        return 'Xử lý tệp nén';
      default:
        return 'Xử lý tài liệu';
    }
  };

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;

    try {
      const file = files[0];
      const formData = new FormData();
      formData.append('file', file);
      
      // Tải lên file vào MinIO
      const response = await api.uploadDocument(formData);
      
      if (response.data && response.data.id) {
        // Lưu thông tin file để sử dụng sau
        setUploadedFile({
          id: response.data.id,
          name: file.name,
          size: file.size,
          type: file.type,
          originalData: response.data
        });
        showSuccess('Tải lên thành công', 'Hoàn thành');
      } else {
        showError('Không nhận được ID file', 'Lỗi xử lý');
      }
    } catch (error) {
      console.error('Lỗi khi tải lên file:', error);
      showError(`Lỗi: ${error.message || 'Không xác định'}`, 'Lỗi xử lý');
    }
  };
  
  const handleProcessFile = async (operation) => {
    if (!uploadedFile) return;
    
    setSelectedOperation(operation);
    
    try {
      let response;
      
      // Gọi API xử lý phù hợp dựa trên loại tài liệu và thao tác
      switch (operation) {
        case 'to-pdf':
          if (documentType === 'word') {
            response = await api.convertToPdf(uploadedFile.id);
          } else if (documentType === 'excel') {
            response = await api.convertToPdf(uploadedFile.id);
          }
          break;
        case 'to-word':
          if (documentType === 'pdf') {
            response = await api.convertToWord(uploadedFile.id);
          } else if (documentType === 'excel') {
            response = await api.convertToWord(uploadedFile.id);
          }
          break;
        case 'watermark':
          // Xử lý thêm watermark (cần bổ sung tham số)
          const watermarkText = prompt('Nhập nội dung watermark:');
          if (!watermarkText) return;
          
          const formData = new FormData();
          formData.append('document_id', uploadedFile.id);
          formData.append('watermark_text', watermarkText);
          
          response = await api.addWatermark(formData);
          break;
        // Thêm các thao tác khác tùy theo loại tài liệu
      }
      
      if (response && response.data && response.data.task_id) {
        setTaskId(response.data.task_id);
      } else {
        showError('Không nhận được task ID để theo dõi tiến trình', 'Lỗi xử lý');
      }
    } catch (error) {
      console.error('Lỗi khi xử lý file:', error);
      showError(`Lỗi: ${error.message || 'Không xác định'}`, 'Lỗi xử lý');
    }
  };
  
  const resetProcess = () => {
    setTaskId(null);
    setSelectedOperation(null);
  };
  
  const renderOperationButtons = () => {
    const operationLabels = {
      'to-pdf': 'Chuyển sang PDF',
      'to-word': 'Chuyển sang Word',
      'to-images': 'Chuyển sang hình ảnh',
      'encrypt': 'Mã hóa tài liệu',
      'decrypt': 'Giải mã tài liệu',
      'watermark': 'Thêm watermark',
      'sign': 'Ký tài liệu',
      'compress': 'Nén tệp',
      'decompress': 'Giải nén tệp'
    };
    
    // Hiển thị các thao tác phù hợp với loại tài liệu
    const availableOperations = [];
    
    if (documentType === 'pdf') {
      availableOperations.push('to-word', 'to-images', 'encrypt', 'decrypt', 'watermark', 'sign');
    } else if (documentType === 'word') {
      availableOperations.push('to-pdf', 'watermark');
    } else if (documentType === 'excel') {
      availableOperations.push('to-pdf', 'to-word');
    } else if (documentType === 'archives') {
      availableOperations.push('decompress');
    }
    
    return (
      <div className="grid grid-cols-2 gap-2 mt-4">
        {availableOperations.map(op => (
          <button
            key={op}
            className="btn btn-secondary"
            onClick={() => handleProcessFile(op)}
          >
            {operationLabels[op]}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="card bg-white">
      <h2 className="text-xl font-semibold mb-4">{getDocumentTypeTitle()}</h2>
      
      {!uploadedFile ? (
        <FileUploader
          acceptedFileTypes={acceptedFileTypes}
          onFileUploaded={handleFileUpload}
          multiple={false}
          title="Kéo thả hoặc click để chọn file"
        />
      ) : taskId ? (
        <div>
          <TaskProgress
            taskId={taskId}
            getTaskStatus={() => api.getTaskStatus(taskId)}
            downloadUrl={() => api.downloadProcessedDocument(taskId)}
            onCompleted={() => {}}
          />
          <button 
            className="mt-4 btn btn-secondary w-full"
            onClick={resetProcess}
          >
            Xử lý tài liệu khác
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-center p-3 bg-gray-50 rounded-lg">
            <FiFile className="text-primary-500 w-8 h-8 mr-3" />
            <div className="flex-1">
              <p className="font-medium">{uploadedFile.name}</p>
              <p className="text-sm text-gray-500">
                {uploadedFile.size < 1024 * 1024
                  ? `${Math.round(uploadedFile.size / 1024)} KB`
                  : `${Math.round(uploadedFile.size / (1024 * 1024) * 10) / 10} MB`}
              </p>
            </div>
            <button 
              className="text-primary-600 hover:text-primary-700"
              onClick={() => window.open(api.downloadDocument(uploadedFile.id), '_blank')}
            >
              <FiDownload className="w-5 h-5" />
            </button>
          </div>
          
          <div className="mt-4">
            <h3 className="text-md font-medium mb-2">Chọn thao tác xử lý:</h3>
            {renderOperationButtons()}
          </div>
          
          <button 
            className="mt-4 btn btn-outline w-full"
            onClick={() => setUploadedFile(null)}
          >
            Tải lên tài liệu khác
          </button>
        </div>
      )}
    </div>
  );
};

export default DocumentProcessingTabs; 