import { Link } from 'react-router-dom';
import { FiAlertTriangle, FiHome } from 'react-icons/fi';

const NotFoundPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <div className="h-24 w-24 bg-red-100 rounded-full flex items-center justify-center text-red-500">
            <FiAlertTriangle className="h-12 w-12" />
          </div>
        </div>
        
        <h1 className="text-4xl font-bold mb-2">404</h1>
        <h2 className="text-2xl font-medium mb-6">Không tìm thấy trang</h2>
        <p className="text-gray-600 mb-8">Trang bạn đang tìm kiếm không tồn tại hoặc đã bị xóa.</p>
        
        <Link to="/" className="btn btn-primary inline-flex items-center">
          <FiHome className="mr-2" />
          Quay về trang chủ
        </Link>
      </div>
    </div>
  );
};

export default NotFoundPage; 