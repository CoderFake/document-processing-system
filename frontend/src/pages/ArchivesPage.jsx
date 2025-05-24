import { useState, useEffect } from 'react';
import { FiArchive, FiFile, FiDownload, FiTrash2, FiUnlock, FiLock, FiPackage } from 'react-icons/fi';
import DocumentProcessingTabs from '../components/DocumentProcessingTabs';
import TaskProgress from '../components/TaskProgress';
import api from '../api/client';
import { useModal } from '../context/ModalContext';

const ArchivesPage = () => {
  const [archives, setArchives] = useState([]);
  const [selectedArchive, setSelectedArchive] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tasksStatus, setTasksStatus] = useState({});
  const [selectedFiles, setSelectedFiles] = useState([]);   
  const [allFiles, setAllFiles] = useState([]);   
  const { showConfirm, showPrompt, showError, showSuccess } = useModal();
  
    const fetchArchives = async () => {
    setLoading(true);
    try {
      const response = await api.archives.getArchives();
      console.log('Archives response:', response);
      setArchives(response.data?.items || []);
    } catch (error) {
      console.error('Lỗi khi tải danh sách tệp nén:', error);
      showError('Không thể tải danh sách tệp nén', 'Lỗi tải dữ liệu');
    } finally {
      setLoading(false);
    }
  };
  
    const fetchAllFiles = async () => {
    try {
        const [pdfResponse, wordResponse, excelResponse] = await Promise.all([
        api.pdf.getDocuments(),
        api.word.getDocuments(),
        api.excel.getDocuments()
      ]);
      
      const pdfFiles = pdfResponse.data?.items ? pdfResponse.data.items.map(f => ({...f, type: 'pdf'})) : [];
      const wordFiles = wordResponse.data?.items ? wordResponse.data.items.map(f => ({...f, type: 'word'})) : [];
      const excelFiles = excelResponse.data?.items ? excelResponse.data.items.map(f => ({...f, type: 'excel'})) : [];
      
            setAllFiles([...pdfFiles, ...wordFiles, ...excelFiles]);
    } catch (error) {
      console.error('Lỗi khi tải danh sách tệp:', error);
      showError('Không thể tải danh sách tệp để nén', 'Lỗi tải dữ liệu');
    }
  };
  
  useEffect(() => {
    fetchArchives();
    fetchAllFiles();
    
        const interval = setInterval(() => {
      checkTasksStatus();
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);
  
    const checkTasksStatus = async () => {
        const runningTasks = Object.entries(tasksStatus)
      .filter(([_, status]) => status.status === 'pending' || status.status === 'processing');
    
    if (runningTasks.length === 0) return;
    
    for (const [taskId, taskInfo] of runningTasks) {
      try {
                if (taskInfo.retryCount && taskInfo.retryCount >= 5) {
          const newStatus = { ...tasksStatus };
          newStatus[taskId] = {
            ...taskInfo,
            status: 'completed',
            description: `Hoàn thành ${taskInfo.description}`
          };
          setTasksStatus(newStatus);
          continue;
        }
        
        let response;
        switch (taskInfo.type) {
          case 'compress':
            response = await api.archives.getCompressStatus(taskId);
            break;
          case 'decompress':
            response = await api.archives.getDecompressStatus(taskId);
            break;
          case 'crack':
            response = await api.archives.getCrackStatus(taskId);
            break;
        }
        
                if (response && response.data) {
          const responseStatus = response.data.status;
          
                    if (responseStatus === 'not_found') {
            const newStatus = { ...tasksStatus };
            newStatus[taskId] = {
              ...taskInfo,
              retryCount: (taskInfo.retryCount || 0) + 1
            };
            setTasksStatus(newStatus);
            continue;
          }
          
                    if (responseStatus === 'completed' || responseStatus === 'failed') {
            const newStatus = { ...tasksStatus };
            newStatus[taskId] = {
              ...taskInfo,
              status: responseStatus,
              description: responseStatus === 'completed' 
                ? `Hoàn thành ${taskInfo.description}` 
                : `Lỗi: ${response.data.error || 'Không xác định'}`
            };
            setTasksStatus(newStatus);
            
                        if (responseStatus === 'completed') {
              fetchArchives();
            }
          } else {
                        const newStatus = { ...tasksStatus };
            newStatus[taskId] = {
              ...taskInfo,
              status: responseStatus
            };
            setTasksStatus(newStatus);
          }
        }
      } catch (error) {
        console.error(`Error checking task ${taskId} status:`, error);
        
                const newStatus = { ...tasksStatus };
        newStatus[taskId] = {
          ...taskInfo,
          retryCount: (taskInfo.retryCount || 0) + 1
        };
        setTasksStatus(newStatus);
      }
    }
  };
  
    const handleSelectArchive = (archive) => {
    setSelectedArchive(archive);
  };
  
    const handleDeleteArchive = async (e, archiveId) => {
    e.stopPropagation();     
    const confirmed = await showConfirm(
      'Bạn có chắc chắn muốn xóa tệp nén này?',
      'Xác nhận xóa',
      { confirmText: 'Xóa', cancelText: 'Hủy' }
    );
    
    if (!confirmed) return;
    
    try {
      await api.archives.deleteArchive(archiveId);
      showSuccess('Xóa tệp nén thành công', 'Đã xóa');
      fetchArchives();
      if (selectedArchive?.id === archiveId) {
        setSelectedArchive(null);
      }
    } catch (error) {
      console.error('Lỗi khi xóa tệp nén:', error);
      showError('Không thể xóa tệp nén', 'Lỗi xóa');
    }
  };
  
    const handleDownloadArchive = async (e, archiveId) => {
    e.stopPropagation();
    
    try {
      const response = await api.archives.downloadArchive(archiveId);
      
      // Tạo blob URL từ response
      const blob = new Blob([response.data], { 
        type: response.headers['content-type'] || 'application/zip' 
      });
      const url = window.URL.createObjectURL(blob);
      
      // Tạo link tạm thời để download
      const link = document.createElement('a');
      link.href = url;
      link.download = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') || `archive_${archiveId}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Lỗi khi tải xuống:', error);
      showError('Lỗi khi tải xuống archive');
    }
  };
  
    const handleDownloadProcessedFile = async (taskId) => {
    if (!taskId) return;
    
    try {
      const response = await api.archives.downloadProcessedFile(taskId);
      
      // Tạo blob URL từ response
      const blob = new Blob([response.data], { 
        type: response.headers['content-type'] || 'application/octet-stream' 
      });
      const url = window.URL.createObjectURL(blob);
      
      // Tạo link tạm thời để download
      const link = document.createElement('a');
      link.href = url;
      link.download = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') || `processed_${taskId}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Lỗi khi tải xuống tệp đã xử lý:', error);
      showError('Không thể tải xuống tệp đã xử lý');
    }
  };
  
    const toggleFileSelection = (file) => {
    if (selectedFiles.some(f => f.id === file.id)) {
      setSelectedFiles(selectedFiles.filter(f => f.id !== file.id));
    } else {
      setSelectedFiles([...selectedFiles, file]);
    }
  };
  
  const handleCompressFiles = async () => {
        const archiveFormat = await showPrompt(
      'Chọn một trong các định dạng: zip, rar, 7z',
      'Chọn định dạng nén',
      { 
        inputDefaultValue: 'zip',
        inputPlaceholder: 'Nhập định dạng nén',
        confirmText: 'Tiếp tục',
        cancelText: 'Hủy'
      }
    );
    
    if (!archiveFormat || !['zip', 'rar', '7z'].includes(archiveFormat.toLowerCase())) {
      showError('Định dạng không hợp lệ', 'Lỗi nhập liệu');
      return;
    }
    
        const outputFilename = await showPrompt(
      'Nhập tên cho tệp nén:',
      'Đặt tên tệp nén',
      { 
        inputDefaultValue: `archive_${Date.now()}.${archiveFormat}`,
        inputPlaceholder: 'Nhập tên file',
        confirmText: 'Tiếp tục',
        cancelText: 'Hủy'
      }
    );
    
    if (!outputFilename) return;
    
        const usePassword = await showConfirm(
      'Bạn có muốn đặt mật khẩu cho tệp nén không?',
      'Đặt mật khẩu',
      { confirmText: 'Có', cancelText: 'Không' }
    );
    
    let password = null;
    if (usePassword) {
      password = await showPrompt(
        'Nhập mật khẩu cho tệp nén:',
        'Đặt mật khẩu',
        { 
          inputPlaceholder: 'Nhập mật khẩu',
          confirmText: 'Xác nhận',
          cancelText: 'Hủy'
        }
      );
      
      if (!password) return;
    }
    
        const compressionLevelStr = await showPrompt(
      'Chọn mức độ nén từ 1-9 (9 là nén tốt nhất)',
      'Mức độ nén',
      { 
        inputDefaultValue: '6',
        inputPlaceholder: 'Nhập số từ 1-9',
        confirmText: 'Nén tệp',
        cancelText: 'Hủy'
      }
    );
    
    const compressionLevel = parseInt(compressionLevelStr);
    if (isNaN(compressionLevel) || compressionLevel < 1 || compressionLevel > 9) {
      showError('Mức độ nén không hợp lệ', 'Lỗi nhập liệu');
      return;
    }
    
        const fileIds = selectedFiles.map(f => f.id);      try {
      const response = await api.archives.compressFiles(fileIds, outputFilename, archiveFormat, password, compressionLevel);
      
            if (response.data) {
                if (response.data.status === 'completed') {
          showSuccess('Nén tệp tin thành công', 'Hoàn thành');
          
                    fetchArchives();
        } 
                else if (response.data.task_id) {
          const newStatus = { ...tasksStatus };
          newStatus[response.data.task_id] = {
            type: 'compress',
            status: 'pending',
            description: 'nén tệp tin',
            files: selectedFiles.map(f => f.original_filename || f.title).join(', ')
          };
          setTasksStatus(newStatus);
          showSuccess('Đã bắt đầu nén tệp tin', 'Đang xử lý');
        }
      }
      
            setSelectedFiles([]);
    } catch (error) {
      console.error('Lỗi khi nén tệp tin:', error);
      showError('Không thể nén tệp tin', 'Lỗi xử lý');
    }
  };

  return (
    <div className="container mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Tệp nén</h1>
        <p className="text-gray-600">Quản lý và xử lý tệp nén (zip, rar, 7z,...)</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <div className="card mb-6">
            <h2 className="text-xl font-semibold mb-4">Danh sách tệp nén</h2>
            
            {loading ? (
              <div className="py-10 text-center">
                <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="mt-4 text-gray-600">Đang tải dữ liệu...</p>
              </div>
            ) : archives.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tên tệp
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Loại
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
                    {archives.map((archive) => (
                      <tr 
                        key={archive.id} 
                        onClick={() => handleSelectArchive(archive)}
                        className={`cursor-pointer hover:bg-gray-50 ${selectedArchive?.id === archive.id ? 'bg-primary-50' : ''}`}
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <FiArchive className="flex-shrink-0 mr-2 text-indigo-500" />
                            <div className="ml-3">
                              <div className="font-medium text-gray-900">{archive.original_filename || archive.title}</div>
                              <div className="text-sm text-gray-500">{archive.file_size ? `${(archive.file_size / (1024 * 1024)).toFixed(2)} MB` : '-'}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          {archive.is_encrypted ? (
                            <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                              <FiLock className="mr-1" /> Đã khóa
                            </span>
                          ) : (
                            <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              <FiUnlock className="mr-1" /> Không khóa
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {archive.archive_type || 'ZIP'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {archive.is_encrypted ? (
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
                            onClick={(e) => handleDownloadArchive(e, archive.id)}
                          >
                            <FiDownload className="h-5 w-5" />
                          </button>
                          <button 
                            className="p-1 text-red-500 hover:text-red-700"
                            onClick={(e) => handleDeleteArchive(e, archive.id)}
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
                Không có tệp nén nào
              </div>
            )}
          </div>
          
          {/* Hiển thị danh sách tác vụ đang chạy */}
          {Object.entries(tasksStatus).length > 0 && (
            <div className="card mb-6">
              <h2 className="text-xl font-semibold mb-4">Tác vụ đang xử lý</h2>
              
              {Object.entries(tasksStatus).map(([taskId, taskInfo]) => (
                <div key={taskId} className="mb-4">
                  <h3 className="text-md font-medium mb-2">
                    {taskInfo.description.charAt(0).toUpperCase() + taskInfo.description.slice(1)}: {taskInfo.files || ''}
                  </h3>
                  
                  <TaskProgress 
                    taskId={taskId}
                    getTaskStatus={() => {
                      switch (taskInfo.type) {
                        case 'compress':
                          return api.archives.getCompressStatus(taskId);
                        case 'decompress':
                          return api.archives.getDecompressStatus(taskId);
                        case 'crack':
                          return api.archives.getCrackStatus(taskId);
                        default:
                          return Promise.resolve({ data: { status: 'unknown' } });
                      }
                    }}
                    downloadUrl={() => api.archives.downloadProcessedFile(taskId)}
                    onCompleted={() => {
                                            fetchArchives();
                    }}
                  />
                </div>
              ))}
            </div>
          )}
          
          {/* Danh sách tệp để nén */}
          {allFiles.length > 0 && (
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Tệp tin có thể nén</h2>
              
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  Chọn các tệp bạn muốn nén thành một tệp nén
                </p>
                
                <div className="max-h-60 overflow-y-auto">
                  {allFiles.map((file) => (
                    <div key={`${file.type}-${file.id}`} className="flex items-center p-2 border-b">
                      <input 
                        type="checkbox"
                        className="mr-3 h-4 w-4"
                        checked={selectedFiles.some(f => f.id === file.id && f.type === file.type)}
                        onChange={() => toggleFileSelection(file)}
                      />
                      <div className="flex items-center">
                        <FiFile className={`mr-2 ${
                          file.type === 'pdf' ? 'text-red-500' : 
                          file.type === 'word' ? 'text-blue-500' : 
                          'text-green-500'
                        }`} />
                        <span>{file.original_filename || file.title}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {selectedFiles.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Tệp đã chọn: {selectedFiles.length}</p>
                  <button 
                    className="btn btn-primary w-full"
                    onClick={handleCompressFiles}
                  >
                    Nén các tệp đã chọn
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div>
          <DocumentProcessingTabs
            documentType="archives"
            acceptedFileTypes={{
              'application/zip': ['.zip'],
              'application/x-rar-compressed': ['.rar'],
              'application/x-7z-compressed': ['.7z'],
              'application/gzip': ['.gz'],
              'application/x-tar': ['.tar']
            }}
            operations={['security']}
            api={api.archives}
          />
        </div>
      </div>
    </div>
  );
};

export default ArchivesPage; 