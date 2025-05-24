import { useState, useEffect } from 'react';
import { FiDownload, FiAlertTriangle, FiCheck } from 'react-icons/fi';
import { useModal } from '../context/ModalContext';

const TaskProgress = ({ taskId, getTaskStatus, downloadUrl, onCompleted }) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('pending');
  const [taskError, setTaskError] = useState(null);
  const [result, setResult] = useState(null);
  const { showError, showSuccess } = useModal();

  useEffect(() => {
    if (!taskId) return;

    const checkStatus = async () => {
      try {
        const response = await getTaskStatus();
        
        if (response && response.data) {
          const { status, progress, error, result } = response.data;
          
          setStatus(status);
          setProgress(progress || 0);
          
          if (error) {
            setTaskError(error);
          }
          
          if (result) {
            setResult(result);
          }
          
                    if (status === 'completed' || status === 'failed') {
            if (status === 'failed' && error) {
              showError(`Xảy ra lỗi: ${error}`, 'Lỗi xử lý');
            } else if (status === 'completed') {
              showSuccess('Xử lý tài liệu đã hoàn tất!', 'Hoàn thành');
              if (onCompleted) {
                onCompleted(result);
              }
            }
          }
        }
      } catch (error) {
        console.error('Lỗi khi kiểm tra trạng thái tác vụ:', error);
      }
    };
    
        checkStatus();
    
        const interval = setInterval(checkStatus, 2000);
    
        return () => clearInterval(interval);
  }, [taskId, getTaskStatus, onCompleted]);
  
    return (
    <div className="my-4 p-4 bg-gray-50 rounded-lg">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium text-gray-700">
          {status === 'pending' && 'Đang chuẩn bị...'}
          {status === 'processing' && 'Đang xử lý...'}
          {status === 'completed' && <span className="flex items-center text-green-600"><FiCheck className="mr-1" /> Hoàn thành</span>}
          {status === 'failed' && <span className="flex items-center text-red-600"><FiAlertTriangle className="mr-1" /> Thất bại</span>}
        </div>
        <div className="text-sm text-gray-500">
          {Math.round(progress * 100)}%
        </div>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className="bg-gradient-to-r from-primary-500 to-primary-600 h-2.5 rounded-full" 
          style={{ width: `${progress * 100}%` }}
        ></div>
      </div>
      
      {status === 'completed' && downloadUrl && (
        <div className="mt-3 flex justify-end">
          <button 
            onClick={() => {
                            const iframe = document.createElement('iframe');
              iframe.style.display = 'none';
              document.body.appendChild(iframe);
              
                            iframe.src = downloadUrl();
              
                            setTimeout(() => {
                document.body.removeChild(iframe);
              }, 1000);
            }}
            className="flex items-center px-3 py-1.5 text-sm text-white bg-primary-600 rounded-md hover:bg-primary-700"
          >
            <FiDownload className="mr-1" /> Tải xuống
          </button>
        </div>
      )}
      
      {taskError && (
        <div className="mt-2 text-sm text-red-600">
          Lỗi: {taskError}
        </div>
      )}
    </div>
  );
};

export default TaskProgress; 