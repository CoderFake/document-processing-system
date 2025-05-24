import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL + '/api/v1';

let modalService = null;

export const setModalService = (service) => {
  modalService = service;
};

const getErrorMessage = (error) => {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    if (error.detail) {
      if (Array.isArray(error.detail)) {
        return error.detail.map(err => {
          if (err.msg) {
            return `${err.loc && err.loc.length > 1 ? err.loc[1] : ''}: ${err.msg}`;
          }
          return JSON.stringify(err);
        }).join(', ');
      }
      return error.detail;
    }
    if (error.message) return error.message;
    if (error.msg) return error.msg;
    return JSON.stringify(error);
  }
  return 'Đã xảy ra lỗi. Vui lòng thử lại.';
};

const showError = (message) => {
  if (message && typeof message === 'object') {
    message = getErrorMessage(message);
  }
  toast.error(message);
};

const showSuccess = (message, title = 'Thành công') => {
  toast.success(message);
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if(error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({resolve, reject});
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token;
          return apiClient(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('Không có refresh token');
        }
        
                const response = await apiClient.post('/auth/refresh-token', { 
          refresh_token: refreshToken 
        });
        
        const { access_token, refresh_token } = response.data;
        
                localStorage.setItem('token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        
                apiClient.defaults.headers.common['Authorization'] = 'Bearer ' + access_token;
        originalRequest.headers['Authorization'] = 'Bearer ' + access_token;
        
                processQueue(null, access_token);
        
                return apiClient(originalRequest);
      } catch (err) {
                processQueue(err, null);
        
                localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        showError('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    
        if (error.response) {
            switch (error.response.status) {
        case 403:
          showError('Bạn không có quyền truy cập vào tài nguyên này.');
          break;
        case 404:
          showError('Tài nguyên không tồn tại.');
          break;
        case 422:
          const validationError = error.response.data?.detail || 'Dữ liệu không hợp lệ';
          showError(validationError);
          break;
        case 500:
          showError('Lỗi server. Vui lòng thử lại sau.');
          break;
        default:
          const errorMessage = error.response.data?.detail || 'Đã xảy ra lỗi. Vui lòng thử lại.';
          showError(errorMessage);
      }
    } else {
      showError('Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.');
    }
    return Promise.reject(error);
  }
);

const api = {
  baseURL: API_BASE_URL,
  
    dashboard: {
    getStats: () => 
      apiClient.get('/user/stats'),
    getRecentDocuments: (limit = 10) => 
      apiClient.get('/user/recent-documents', { params: { limit } }),
  },
  
    auth: {
    login: (username, password) => {
            const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      return apiClient.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
    },
    register: (username, password, email, fullName) => {
      const data = {
        username,
        email,
        password
      };
      
      if (fullName) {
        data.full_name = fullName;
      }
      
      console.log('Register data:', data);
      
      return apiClient.post('/auth/register', data);
    },
    refreshToken: (refresh_token) => 
      apiClient.post('/auth/refresh-token', { refresh_token }),
    logout: () => 
      apiClient.post('/auth/logout', { refresh_token: localStorage.getItem('refresh_token') }),
    getProfile: () => 
      apiClient.get('/auth/me'),
    updateProfile: (profileData) =>
      apiClient.put('/auth/profile', profileData),
  },
  
    pdf: {
    getDocuments: (params) => 
      apiClient.get('/pdf/', { params }),
    uploadDocument: (formData) => 
      apiClient.post('/pdf/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    getDocument: (id) => 
      apiClient.get(`/pdf/${id}`),
    deleteDocument: (id) => 
      apiClient.delete(`/pdf/${id}`),
    encryptDocument: (formData) => 
      apiClient.post(`/pdf/encrypt`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    decryptDocument: (formData) => 
      apiClient.post(`/pdf/decrypt`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    convertToWord: (formData) => 
      apiClient.post(`/pdf/convert/to-word`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    convertToImages: (formData) => 
      apiClient.post(`/pdf/convert/to-images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    mergeDocuments: (formData) => 
      apiClient.post(`/pdf/merge`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    downloadDocument: (id) =>
      `${API_BASE_URL}/pdf/download/${id}`,
        getTaskStatus: (taskId) =>
      apiClient.get(`/pdf/status/${taskId}`),
        downloadProcessedDocument: (taskId) =>
      `${API_BASE_URL}/pdf/download/processed/${taskId}`,
        addWatermark: (formData) => {
      return apiClient.post('/pdf/watermark', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        addSignature: (formData) => {
      return apiClient.post('/pdf/sign', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        crackPassword: (formData) => {
      return apiClient.post('/pdf/crack', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        convertFileToWord: (fileOrFormData) => {
      let formData;
      
      if (fileOrFormData instanceof FormData) {
        formData = fileOrFormData;
      } else {
        formData = new FormData();
        formData.append('file', fileOrFormData);
      }
      
      return apiClient.post('/pdf/convert/to-word', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
  },
  
    word: {
    getDocuments: (params) => 
      apiClient.get('/word/', { params }),
    uploadDocument: (formData) => 
      apiClient.post('/word/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    getDocument: (id) => 
      apiClient.get(`/word/${id}`),
    deleteDocument: (id) => 
      apiClient.delete(`/word/${id}`),
    convertToPdf: (id) => 
      apiClient.post(`/word/convert/to-pdf`, { document_id: id }),
    downloadDocument: (id) =>
      `${API_BASE_URL}/word/download/${id}`,
        getTaskStatus: (taskId) =>
      apiClient.get(`/word/status/${taskId}`),
        downloadProcessedDocument: (taskId) =>
      `${API_BASE_URL}/word/download/processed/${taskId}`,
        convertFileToPdf: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiClient.post('/word/convert/to-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        addWatermark: (file, watermarkText, position = 'center', opacity = 0.5) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('watermark_text', watermarkText);
      formData.append('position', position);
      formData.append('opacity', opacity);
      
      return apiClient.post('/word/watermark', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        applyTemplate: (templateId, data, outputFormat = 'docx') => {
      const formData = new FormData();
      formData.append('template_id', templateId);
      formData.append('data', typeof data === 'string' ? data : JSON.stringify(data));
      formData.append('output_format', outputFormat);
      
      return apiClient.post('/word/templates/apply', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        getTemplates: (category = null, params = {}) => {
      if (category) {
        params.category = category;
      }
      return apiClient.get('/word/templates', { params });
    },
        createBatchDocuments: (templateId, dataFile, outputFormat = 'docx') => {
      const formData = new FormData();
      formData.append('template_id', templateId);
      formData.append('data_file', dataFile);
      formData.append('output_format', outputFormat);
      
      return apiClient.post('/word/batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        createInternshipReport: (formData) => {
      return apiClient.post('/word/templates/internship-report', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        createRewardReport: (formData) => {
      return apiClient.post('/word/templates/reward-report', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        createLaborContract: (formData) => {
      return apiClient.post('/word/templates/labor-contract', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        createInvitations: (dataFile, outputFormat = 'docx') => {
      const formData = new FormData();
      formData.append('data_file', dataFile);
      formData.append('output_format', outputFormat);
      
      return apiClient.post('/word/templates/invitation', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
  },
  
    excel: {
    getDocuments: (params) => 
      apiClient.get('/excel/', { params }),
    uploadDocument: (formData) => 
      apiClient.post('/excel/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    getDocument: (id) => 
      apiClient.get(`/excel/${id}`),
    deleteDocument: (id) => 
      apiClient.delete(`/excel/${id}`),
    convertToPdf: (id) => 
      apiClient.post(`/excel/convert/to-pdf`, { document_id: id }),
    convertToWord: (id) => 
      apiClient.post(`/excel/convert/to-word`, { document_id: id }),
    downloadDocument: (id) =>
      `${API_BASE_URL}/excel/download/${id}`,
        getTaskStatus: (taskId) =>
      apiClient.get(`/excel/status/${taskId}`),
        downloadProcessedDocument: (taskId) =>
      `${API_BASE_URL}/excel/download/processed/${taskId}`,
        convertFileToPdf: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiClient.post('/excel/convert/to-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        convertFileToWord: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiClient.post('/excel/convert/to-word', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        applyTemplate: (templateId, data, outputFormat = 'xlsx') => {
      const formData = new FormData();
      formData.append('template_id', templateId);
      formData.append('data', typeof data === 'string' ? data : JSON.stringify(data));
      formData.append('output_format', outputFormat);
      
      return apiClient.post('/excel/templates/apply', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
        getTemplates: (category = null, params = {}) => {
      if (category) {
        params.category = category;
      }
      return apiClient.get('/excel/templates', { params });
    },
        mergeFiles: (files, outputFilename) => {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      formData.append('output_filename', outputFilename);
      
      return apiClient.post('/excel/merge', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
  },
  
    archives: {
        getArchives: (params) => 
      apiClient.get('files/archives', { params }),
    
        uploadArchive: (formData) => 
      apiClient.post('/files/archives/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),
    
        compressFiles: (fileIds, outputFilename, archiveFormat = 'zip', password = null, compressionLevel = 6) => {
      const formData = new FormData();
      formData.append('file_ids', Array.isArray(fileIds) ? fileIds.join(',') : fileIds);
      formData.append('output_filename', outputFilename);
      formData.append('compression_type', archiveFormat);
      formData.append('compression_level', compressionLevel.toString());
      
      if (password) {
        formData.append('password', password);
      }
      
      return apiClient.post('/files/compress', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    },
    
        decompressArchive: (archiveId, password = null, extractAll = true, filePaths = null) => {
      const formData = new FormData();
      formData.append('archive_id', archiveId);
      formData.append('extract_all', extractAll);
      
      if (password) {
        formData.append('password', password);
      }
      
      if (filePaths) {
        formData.append('file_paths', Array.isArray(filePaths) ? filePaths.join(',') : filePaths);
      }
      
      return apiClient.post('/files/decompress', formData);
    },
    
        crackArchivePassword: (archiveId, maxLength = 6) => {
      const formData = new FormData();
      formData.append('archive_id', archiveId);
      formData.append('max_length', maxLength);
      
      return apiClient.post('/files/crack', formData);
    },
    
        downloadArchive: (archiveId) =>
      `${API_BASE_URL}/files/archives/download/${archiveId}`,
    
        deleteArchive: (archiveId, permanent = false) =>
      apiClient.delete(`/files/archives/${archiveId}?permanent=${permanent}`),
    
        getCompressStatus: (taskId) =>
      apiClient.get(`/files/status/compress/${taskId}`),
    
    getDecompressStatus: (taskId) =>
      apiClient.get(`/files/status/decompress/${taskId}`),
    
    getCrackStatus: (taskId) =>
      apiClient.get(`/files/status/crack/${taskId}`),
    
        downloadProcessedFile: (taskId) =>
      `${API_BASE_URL}/files/download/processed/${taskId}`,
  },
};

export const notifications = {
  showError,
  showSuccess
};

export default api; 