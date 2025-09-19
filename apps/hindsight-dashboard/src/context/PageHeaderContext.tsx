import React from 'react';

export interface PageHeaderConfig {
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export interface PageHeaderContextValue {
  setHeaderContent: (config: PageHeaderConfig) => void;
  clearHeaderContent: () => void;
  headerConfig: PageHeaderConfig;
}

const PageHeaderContext = React.createContext<PageHeaderContextValue | undefined>(undefined);

export default PageHeaderContext;
