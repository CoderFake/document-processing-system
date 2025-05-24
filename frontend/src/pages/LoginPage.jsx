import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { FiUser, FiLock, FiEye, FiEyeOff } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';

const getErrorMessage = (error) => {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    if (error.detail) return error.detail;
    if (error.message) return error.message;
    if (error.msg) return error.msg;
    return JSON.stringify(error);
  }
  return 'Đã xảy ra lỗi. Vui lòng thử lại.';
};

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const from = location.state?.from?.pathname || '/';
  
  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!username.trim() || !password.trim()) {
      toast.error('Vui lòng nhập đầy đủ thông tin đăng nhập');
      return;
    }
    
    try {
      setLoading(true);
      
      const result = await login(username, password);
      
      if (result.success) {
        navigate(from);
      } else {
        toast.error(result.message || 'Có lỗi xảy ra khi đăng nhập. Vui lòng thử lại sau.');
      }
    } catch (error) {
      toast.error('Có lỗi xảy ra khi đăng nhập. Vui lòng thử lại sau.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-dark">
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500/10 via-secondary-500/10 to-purple-500/10"></div>
      
      <div className="max-w-md w-full mx-4 relative">
        <div className="absolute -top-10 -left-10 w-32 h-32 bg-gradient-accent rounded-full filter blur-xl opacity-30 animate-blob"></div>
        <div className="absolute -bottom-14 -right-14 w-40 h-40 bg-gradient-accent rounded-full filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
        
        <div className="card bg-white shadow-xl border border-gray-200 z-10 relative">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold gradient-text">DocProcessor</h1>
            <p className="text-gray-600 mt-2">Đăng nhập để tiếp tục</p>
          </div>
          
          <form onSubmit={handleLogin}>
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
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input pl-10"
                  placeholder="Nhập tên đăng nhập"
                  disabled={loading}
                />
              </div>
            </div>
            
            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Mật khẩu
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <FiLock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-10 pr-10"
                  placeholder="Nhập mật khẩu"
                  disabled={loading}
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <FiEyeOff className="h-5 w-5" /> : <FiEye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-gradient-accent hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
            </button>
          </form>
          
          <div className="mt-6 text-center text-sm">
            <a href="#" className="text-primary-600 hover:text-primary-500">
              Quên mật khẩu?
            </a>
          </div>
          
          <div className="mt-6 text-center text-sm">
            <p className="text-gray-600">
              Chưa có tài khoản?{' '}
              <Link to="/register" className="text-primary-600 hover:text-primary-500">
                Đăng ký ngay
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage; 