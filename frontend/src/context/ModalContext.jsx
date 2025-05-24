import { createContext, useState, useContext, useEffect } from 'react';
import Modal from '../components/Modal';
import { setModalService } from '../api/client';

const ModalContext = createContext();

export const useModal = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModal must be used within a ModalProvider');
  }
  return context;
};

export const ModalProvider = ({ children }) => {
  const [modalState, setModalState] = useState({
    isOpen: false,
    title: '',
    content: '',
    type: 'info',
    confirmText: 'Xác nhận',
    cancelText: 'Hủy',
    onConfirm: null,
    onCancel: null,
    inputLabel: '',
    inputDefaultValue: '',
    inputPlaceholder: '',
    maxWidth: 'sm'
  });

    const closeModal = () => {
    setModalState(prevState => ({
      ...prevState,
      isOpen: false
    }));
  };

    const showAlert = (content, title = 'Thông báo', type = 'info') => {
    setModalState({
      isOpen: true,
      title,
      content,
      type,
      confirmText: 'Đóng',
      onConfirm: closeModal,
      onCancel: closeModal,
      maxWidth: 'sm'
    });

    return new Promise(resolve => {
      setModalState(prevState => ({
        ...prevState,
        onConfirm: () => {
          closeModal();
          resolve(true);
        }
      }));
    });
  };

    const showConfirm = (content, title = 'Xác nhận', options = {}) => {
    const { confirmText = 'Xác nhận', cancelText = 'Hủy', maxWidth = 'sm' } = options;

    setModalState({
      isOpen: true,
      title,
      content,
      type: 'confirm',
      confirmText,
      cancelText,
      onConfirm: closeModal,
      onCancel: closeModal,
      maxWidth
    });

    return new Promise(resolve => {
      setModalState(prevState => ({
        ...prevState,
        onConfirm: () => {
          closeModal();
          resolve(true);
        },
        onCancel: () => {
          closeModal();
          resolve(false);
        }
      }));
    });
  };

    const showPrompt = (content, title = 'Nhập thông tin', options = {}) => {
    const { 
      confirmText = 'Xác nhận', 
      cancelText = 'Hủy', 
      inputLabel = '', 
      inputDefaultValue = '',
      inputPlaceholder = '',
      maxWidth = 'sm'
    } = options;

    setModalState({
      isOpen: true,
      title,
      content,
      type: 'prompt',
      confirmText,
      cancelText,
      inputLabel,
      inputDefaultValue,
      inputPlaceholder,
      onConfirm: closeModal,
      onCancel: closeModal,
      maxWidth
    });

    return new Promise(resolve => {
      setModalState(prevState => ({
        ...prevState,
        onConfirm: (value) => {
          closeModal();
          resolve(value);
        },
        onCancel: () => {
          closeModal();
          resolve(null);
        }
      }));
    });
  };

    const showSuccess = (content, title = 'Thành công') => {
    return showAlert(content, title, 'success');
  };

    const showError = (content, title = 'Lỗi') => {
    return showAlert(content, title, 'error');
  };

  const value = {
    showAlert,
    showConfirm,
    showPrompt,
    showSuccess,
    showError,
    closeModal
  };
  
    useEffect(() => {
    setModalService(value);
    return () => setModalService(null);
  }, []);

  return (
    <ModalContext.Provider value={value}>
      {children}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        type={modalState.type}
        onConfirm={modalState.onConfirm}
        onCancel={modalState.onCancel}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
        inputLabel={modalState.inputLabel}
        inputDefaultValue={modalState.inputDefaultValue}
        inputPlaceholder={modalState.inputPlaceholder}
        maxWidth={modalState.maxWidth}
      >
        {modalState.content}
      </Modal>
    </ModalContext.Provider>
  );
};

export default ModalContext; 