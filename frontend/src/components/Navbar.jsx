import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiMenu, FiBell, FiUser, FiLogOut, FiSearch } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const Navbar = ({ toggleSidebar }) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const toggleUserMenu = () => {
    setShowUserMenu(!showUserMenu);
  };
  
  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Đăng xuất thành công');
      navigate('/login');
    } catch (error) {
      console.error('Lỗi khi đăng xuất:', error);
    }
  };

  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-30 shadow-sm">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <button
              onClick={toggleSidebar}
              className="text-gray-500 hover:text-gray-700 md:hidden"
            >
              <FiMenu className="h-6 w-6" />
            </button>
            
            <div className="ml-4 md:ml-0 block md:hidden">
              <Link to="/" className="flex items-center">
                <span className="text-xl font-bold bg-gradient-to-r from-primary-600 to-primary-500 text-transparent bg-clip-text gradient-text">
                  DocProcessor
                </span>
              </Link>
            </div>
          </div>
          
          <div className="hidden md:block max-w-md w-full mx-4">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiSearch className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-md bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                placeholder="Tìm kiếm tài liệu..."
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <button className="p-2 rounded-full text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500">
              <FiBell className="h-5 w-5" />
            </button>
            
            <div className="relative">
              <button
                onClick={toggleUserMenu}
                className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <div className="h-8 w-8 rounded-full bg-gradient-to-r from-primary-600 to-primary-500 flex items-center justify-center text-white">
                  <FiUser className="h-5 w-5" />
                </div>
              </button>
              
              {showUserMenu && (
                <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 z-40">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">{user?.username || 'Người dùng'}</p>
                    <p className="text-xs text-gray-500 truncate">{user?.email || ''}</p>
                  </div>
                  <Link
                    to="/profile"
                    className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <FiUser className="mr-2 h-4 w-4" />
                    Hồ sơ
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <FiLogOut className="mr-2 h-4 w-4" />
                    Đăng xuất
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar; 