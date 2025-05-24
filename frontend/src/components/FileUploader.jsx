import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiFile, FiX } from 'react-icons/fi';
import { useModal } from '../context/ModalContext';

const FileUploader = ({ 
  onFileUploaded, 
  acceptedFileTypes = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/msword': ['.doc'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
  },
  maxSize = 10 * 1024 * 1024,   multiple = false,
  title = "Tải lên tài liệu"
}) => {
  const [files, setFiles] = useState([]);
  const { showError, showSuccess } = useModal();
  
  const onDrop = useCallback((acceptedFiles) => {
        const validFiles = acceptedFiles.filter(file => file.size <= maxSize);
    const invalidFiles = acceptedFiles.filter(file => file.size > maxSize);
    
    if (invalidFiles.length > 0) {
      showError(`${invalidFiles.length} tệp vượt quá kích thước tối đa ${Math.round(maxSize / 1024 / 1024)}MB`, 'Kích thước quá lớn');
    }
    
    if (!multiple && validFiles.length > 0) {
      setFiles([validFiles[0]]);
    } else {
      setFiles(prev => [...prev, ...validFiles]);
    }
  }, [maxSize, multiple, showError]);
  
  const removeFile = (fileIndex) => {
    setFiles(files.filter((_, index) => index !== fileIndex));
  };
  
  const handleConfirmFiles = () => {
    if (files.length === 0) {
      showError('Vui lòng chọn ít nhất một tệp', 'Không có tệp');
      return;
    }
    
    try {
            onFileUploaded(multiple ? files : [files[0]]);
      showSuccess('Đã chọn file thành công!', 'Thành công');
    } catch (error) {
      console.error('Lỗi khi xử lý file:', error);
      showError('Đã xảy ra lỗi khi xử lý file', 'Lỗi');
    }
  };
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxSize: maxSize,
    multiple: multiple
  });
  
  const formatFileSize = (size) => {
    if (size < 1024) return size + ' B';
    else if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    else return (size / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="w-full">
      <h3 className="text-lg font-medium mb-3">{title}</h3>
      
      <div 
        {...getRootProps()} 
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-primary-400 bg-primary-50' 
            : 'border-gray-300 hover:border-primary-400'}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center py-4">
          <FiUpload className="w-12 h-12 text-gray-400 mb-3" />
          <p className="text-sm text-gray-600">
            {isDragActive
              ? 'Thả tệp để tải lên...'
              : 'Kéo và thả tệp vào đây, hoặc nhấp để chọn tệp'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Kích thước tối đa: {Math.round(maxSize / 1024 / 1024)}MB
          </p>
        </div>
      </div>
      
      {files.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium mb-2">Tệp đã chọn:</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {files.map((file, index) => (
              <div 
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center">
                  <FiFile className="w-5 h-5 text-gray-500 mr-2" />
                  <div>
                    <p className="text-sm font-medium truncate max-w-xs">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button 
                  onClick={() => removeFile(index)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <FiX className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
          
          <div className="mt-4">
            <button
              onClick={handleConfirmFiles}
              className="btn btn-primary w-full"
            >
              Chọn file này
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploader; 