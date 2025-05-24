import { useState, useEffect } from 'react';
import { FiUser, FiMail, FiInfo, FiSave, FiCheck } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

const ProfilePage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    fullName: '',
    department: '',
    position: '',
    avatar: null
  });
  
  useEffect(() => {
    fetchUserProfile();
  }, []);
  
  const fetchUserProfile = async () => {
    setLoading(true);
    try {
      const response = await api.auth.getProfile();
      const userData = response.data;
      
      setFormData({
        username: userData.username || '',
        email: userData.email || '',
        fullName: userData.full_name || '',
        department: userData.department || '',
        position: userData.position || '',
        avatar: userData.avatar || null
      });
    } catch (error) {
      toast.error('Không thể tải thông tin người dùng');
      console.error('Lỗi khi tải thông tin người dùng:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({
        ...prev,
        avatar: file
      }));
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    setSaving(true);
    try {
      // Tạo FormData để gửi cả dữ liệu text và file
      const data = new FormData();
      data.append('username', formData.username);
      data.append('email', formData.email);
      data.append('full_name', formData.fullName);
      data.append('department', formData.department);
      data.append('position', formData.position);
      
      if (formData.avatar && formData.avatar instanceof File) {
        data.append('avatar', formData.avatar);
      }
      
      await api.auth.updateProfile(data);
      
      toast.success('Cập nhật thông tin thành công!');
      setSuccess(true);
      
      setTimeout(() => {
        setSuccess(false);
      }, 3000);
    } catch (error) {
      let errorMessage = 'Có lỗi xảy ra khi cập nhật thông tin.';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };
  
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-semibold mb-6">Thông tin cá nhân</h1>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col md:flex-row gap-6 mb-6">
              <div className="md:w-1/3 flex flex-col items-center">
                <div className="w-32 h-32 rounded-full bg-gray-200 overflow-hidden mb-4">
                  {formData.avatar ? (
                    <img 
                      src={formData.avatar instanceof File ? URL.createObjectURL(formData.avatar) : formData.avatar} 
                      alt="Avatar" 
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-100 text-gray-400">
                      <FiUser size={48} />
                    </div>
                  )}
                </div>
                
                <label className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer">
                  <span>Thay đổi avatar</span>
                  <input 
                    type="file" 
                    className="sr-only" 
                    accept="image/*"
                    onChange={handleFileChange}
                  />
                </label>
              </div>
              
              <div className="md:w-2/3">
                <div className="mb-4">
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                    Tên đăng nhập
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <FiUser className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      value={formData.username}
                      onChange={handleChange}
                      className="input pl-10"
                      placeholder="Tên đăng nhập"
                      disabled
                    />
                  </div>
                  <p className="mt-1 text-xs text-gray-500">Tên đăng nhập không thể thay đổi</p>
                </div>
                
                <div className="mb-4">
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    Email
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <FiMail className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      className="input pl-10"
                      placeholder="Email"
                    />
                  </div>
                </div>
                
                <div className="mb-4">
                  <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                    Họ và tên
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <FiInfo className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="fullName"
                      name="fullName"
                      type="text"
                      value={formData.fullName}
                      onChange={handleChange}
                      className="input pl-10"
                      placeholder="Họ và tên"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="mb-4">
                    <label htmlFor="department" className="block text-sm font-medium text-gray-700 mb-1">
                      Phòng ban
                    </label>
                    <input
                      id="department"
                      name="department"
                      type="text"
                      value={formData.department}
                      onChange={handleChange}
                      className="input"
                      placeholder="Phòng ban"
                    />
                  </div>
                  
                  <div className="mb-4">
                    <label htmlFor="position" className="block text-sm font-medium text-gray-700 mb-1">
                      Chức vụ
                    </label>
                    <input
                      id="position"
                      name="position"
                      type="text"
                      value={formData.position}
                      onChange={handleChange}
                      className="input"
                      placeholder="Chức vụ"
                    />
                  </div>
                </div>
              </div>
            </div>
            
            <div className="border-t border-gray-200 pt-4 mt-4">
              <button
                type="submit"
                disabled={saving}
                className={`flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                  success 
                    ? 'bg-green-600 hover:bg-green-700' 
                    : 'bg-primary-600 hover:bg-primary-700'
                } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500`}
              >
                {saving ? (
                  <>
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                    <span>Đang lưu...</span>
                  </>
                ) : success ? (
                  <>
                    <FiCheck className="h-5 w-5 mr-2" />
                    <span>Đã lưu</span>
                  </>
                ) : (
                  <>
                    <FiSave className="h-5 w-5 mr-2" />
                    <span>Lưu thông tin</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage; 