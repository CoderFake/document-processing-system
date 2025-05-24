import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import { FiUser } from 'react-icons/fi';

const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar cho màn hình lớn */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>
      
      {/* Sidebar responsive cho mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div 
            className="fixed inset-0 bg-white/30" 
            onClick={toggleSidebar}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg z-50">
            <Sidebar mobile={true} closeSidebar={toggleSidebar} />
          </div>
        </div>
      )}
      
      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar toggleSidebar={toggleSidebar} />
        
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-50">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
        
        <footer className="py-4 px-6 bg-white border-t border-gray-100">
          <div className="text-center text-sm text-gray-500">
            © {new Date().getFullYear()} Hệ thống Xử lý Tài liệu
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Layout; 