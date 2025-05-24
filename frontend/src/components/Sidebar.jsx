import { Link, useLocation } from 'react-router-dom';
import { FiHome, FiFile, FiFileText, FiTable, FiFolder, FiArchive, FiX } from 'react-icons/fi';

const Sidebar = ({ mobile = false, closeSidebar }) => {
  const location = useLocation();
  
  const navigation = [
    { name: 'Trang chủ', icon: FiHome, href: '/' },
    { name: 'Tài liệu PDF', icon: FiFile, href: '/pdf' },
    { name: 'Tài liệu Word', icon: FiFileText, href: '/word' },
    { name: 'Tài liệu Excel', icon: FiTable, href: '/excel' },
    { name: 'Quản lý File', icon: FiFolder, href: '/files' },
    { name: 'Quản lý File Nén', icon: FiArchive, href: '/archives' },
  ];

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <div className="w-64 h-full bg-white shadow-sm overflow-y-auto">
      <div className="flex items-center justify-between px-4 h-16 border-b border-gray-100">
        {/* Logo chỉ hiện trên desktop (ẩn khi mobile) */}
        {!mobile && (
          <Link to="/" className="flex items-center">
            <span className="text-xl font-bold gradient-text">
              DocProcessor
            </span>
          </Link>
        )}
        {mobile && (
          <button 
            onClick={closeSidebar}
            className="text-gray-500 hover:text-gray-700"
          >
            <FiX className="h-6 w-6" />
          </button>
        )}
      </div>
      
      <nav className="mt-5 px-4 pb-4">
        <div className="space-y-1">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={`
                group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all
                ${isActive(item.href) 
                  ? 'bg-primary-50 text-primary-600' 
                  : 'text-gray-700 hover:bg-gray-50'}
              `}
              onClick={mobile ? closeSidebar : undefined}
            >
              <item.icon 
                className={`
                  mr-3 h-5 w-5 flex-shrink-0
                  ${isActive(item.href) 
                    ? 'text-primary-600' 
                    : 'text-gray-500 group-hover:text-primary-600'}
                `}
              />
              {item.name}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
};

export default Sidebar; 