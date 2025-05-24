import { Link } from 'react-router-dom';

const Logo = ({ className = '', isMobile = false }) => {
  return (
    <Link 
      to="/" 
      className={`text-xl font-bold gradient-text ${className}`}
    >
      DocProcessor
    </Link>
  );
};

export default Logo; 