import { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/client';
import toast from 'react-hot-toast';

const getErrorMessage = (error) => {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    if (error.detail) return error.detail;
    if (error.message) return error.message;
    if (error.msg) return error.msg;
    if (error.response?.data?.detail) return error.response.data.detail;
    return 'Lỗi không xác định';
  }
  return 'Đã xảy ra lỗi. Vui lòng thử lại.';
};

const AuthContext = createContext({
  isAuthenticated: false,
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  loading: false
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.auth.getProfile();
        setUser(response.data);
      } catch (error) {
        localStorage.removeItem('token');
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const response = await api.auth.login(username, password);
      
      const { access_token, refresh_token } = response.data;
      
      if (!access_token) {
        return { 
          success: false, 
          message: 'Không nhận được token truy cập' 
        };
      }
      
      localStorage.setItem('token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }
      
      setToken(access_token);
      
      try {
        const userResponse = await api.auth.getProfile();
        setUser(userResponse.data);
      } catch (profileError) {
        console.error('Lỗi khi lấy thông tin người dùng:', profileError);
        // Nếu không lấy được thông tin người dùng, cũng nên đăng xuất
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        setToken(null);
        return { 
          success: false, 
          message: 'Không thể lấy thông tin người dùng' 
        };
      }
      
      return { success: true };
    } catch (error) {
      console.error("Lỗi đăng nhập:", error);
      return { 
        success: false, 
        message: typeof error.response?.data?.detail === 'string' 
          ? error.response.data.detail 
          : getErrorMessage(error) 
      };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      if (token) {
        await api.auth.logout();
      }
    } catch (error) {
      console.error('Lỗi đăng xuất:', error);
    } finally {
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        user,
        token,
        login,
        logout,
        loading
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export default AuthContext; 