import { useContext } from 'react';
import PageHeaderContext from '../context/PageHeaderContext';

const usePageHeader = () => {
  const context = useContext(PageHeaderContext);
  if (!context) {
    throw new Error('usePageHeader must be used within a PageHeaderContext provider');
  }
  return context;
};

export default usePageHeader;
