import { useContext, useMemo } from 'react';
import PageHeaderContext, { PageHeaderConfig } from '../context/PageHeaderContext';

const usePageHeader = () => {
  const context = useContext(PageHeaderContext);

  const fallback = useMemo(() => ({
    setHeaderContent: (_config: PageHeaderConfig) => {},
    clearHeaderContent: () => {},
    headerConfig: {}
  }), []);

  return context ?? fallback;
};

export default usePageHeader;
