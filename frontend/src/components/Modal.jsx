import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { FiX, FiAlertCircle, FiCheckCircle, FiInfo } from 'react-icons/fi';

const Modal = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  type = 'info',  // 'info', 'success', 'error', 'confirm', 'prompt'
  onConfirm = null,
  onCancel = null,
  confirmText = 'Xác nhận',
  cancelText = 'Hủy',
  inputLabel = '',
  inputDefaultValue = '',
  inputPlaceholder = '',
  maxWidth = 'sm'  // 'sm', 'md', 'lg'
}) => {
  const modalRef = useRef(null);
  const inputRef = useRef(null);
  
  // Xử lý click outside để đóng modal
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (modalRef.current && !modalRef.current.contains(event.target)) {
        if (onCancel) onCancel();
        else onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'hidden'; // Ngăn scroll body
      
      // Focus vào input nếu là prompt
      if (type === 'prompt' && inputRef.current) {
        setTimeout(() => {
          inputRef.current.focus();
        }, 50);
      }
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'auto'; // Khôi phục scroll body
    };
  }, [isOpen, onClose, onCancel, type]);
  
  // Xử lý ESC để đóng modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (onCancel) onCancel();
        else onClose();
      }
    };
    
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose, onCancel]);
  
  const handleConfirm = () => {
    if (type === 'prompt' && onConfirm && inputRef.current) {
      onConfirm(inputRef.current.value);
    } else if (onConfirm) {
      onConfirm();
    }
    onClose();
  };
  
  const handleCancel = () => {
    if (onCancel) onCancel();
    onClose();
  };
  
  // Icons dựa vào loại modal
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <FiCheckCircle className="h-8 w-8 text-green-500" />;
      case 'error':
        return <FiAlertCircle className="h-8 w-8 text-red-500" />;
      case 'confirm':
        return <FiAlertCircle className="h-8 w-8 text-yellow-500" />;
      case 'prompt':
        return <FiInfo className="h-8 w-8 text-blue-500" />;
      default:
        return <FiInfo className="h-8 w-8 text-primary-500" />;
    }
  };
  
  // Max width classes
  const maxWidthClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full'
  };
  
  if (!isOpen) return null;
  
  return createPortal(
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50 p-4">
      <div 
        ref={modalRef}
        className={`bg-white rounded-lg shadow-xl w-full ${maxWidthClasses[maxWidth] || 'max-w-md'} overflow-hidden transform transition-all`}
      >
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getIcon()}
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          </div>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-500 focus:outline-none"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>
        
        <div className="px-6 py-4">
          {type === 'prompt' ? (
            <div className="mb-4">
              {children && <p className="mb-4 text-gray-600">{children}</p>}
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {inputLabel}
              </label>
              <input
                ref={inputRef}
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                defaultValue={inputDefaultValue}
                placeholder={inputPlaceholder}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleConfirm();
                }}
              />
            </div>
          ) : (
            <div>{children}</div>
          )}
        </div>
        
        {(type === 'confirm' || type === 'prompt') && (
          <div className="px-6 py-3 bg-gray-50 flex justify-end space-x-2">
            <button
              type="button"
              className="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              onClick={handleCancel}
            >
              {cancelText}
            </button>
            <button
              type="button"
              className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              onClick={handleConfirm}
            >
              {confirmText}
            </button>
          </div>
        )}
        
        {(type === 'success' || type === 'error' || type === 'info') && (
          <div className="px-6 py-3 bg-gray-50 flex justify-end">
            <button
              type="button"
              className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              onClick={onClose}
            >
              Đóng
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

export default Modal; 