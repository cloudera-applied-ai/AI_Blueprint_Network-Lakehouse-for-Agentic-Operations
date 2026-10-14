import { createContext, useContext, useState, ReactNode } from 'react';

interface TabsContextType {
  activeTab: string;
  setActiveTab: (value: string) => void;
}

const TabsContext = createContext<TabsContextType | undefined>(undefined);

export const Tabs = ({
  defaultValue,
  value,
  onValueChange,
  children,
  className = '',
}: {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}) => {
  const [internal, setInternal] = useState(defaultValue);
  // Controlled when `value` is provided; otherwise uncontrolled (unchanged behavior).
  const activeTab = value !== undefined ? value : internal;
  const setActiveTab = (v: string) => {
    if (value === undefined) setInternal(v);
    onValueChange?.(v);
  };

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
};

export const TabsList = ({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) => {
  return (
    <div className={`flex gap-1 border-b border-gray-600 overflow-x-auto ${className}`}>
      {children}
    </div>
  );
};

/**
 * Cloudera 2025 brand tab: indigo label, orange underline when active
 * (mirrors the orange accent bar on the white slide template).
 */
export const TabsTrigger = ({
  value,
  children,
  variant = 'default',
}: {
  value: string;
  children: ReactNode;
  variant?: 'default' | 'orange';
}) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');

  const { activeTab, setActiveTab } = context;
  const isActive = activeTab === value;

  const activeStyles = variant === 'orange'
    ? 'text-brand-orange border-brand-orange'
    : 'text-brand-indigo border-brand-orange';

  const inactiveStyles = variant === 'orange'
    ? 'text-brand-orange/80 border-transparent hover:text-brand-orange hover:border-brand-orange-lt'
    : 'text-brand-indigo/60 border-transparent hover:text-brand-indigo hover:border-brand-blue-lt';

  return (
    <button
      onClick={() => setActiveTab(value)}
      className={`-mb-px px-4 py-2.5 text-sm font-semibold whitespace-nowrap flex-shrink-0 border-b-2 transition-colors ${
        isActive ? activeStyles : inactiveStyles
      }`}
    >
      {children}
    </button>
  );
};

export const TabsContent = ({
  value,
  children,
}: {
  value: string;
  children: ReactNode;
}) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');

  const { activeTab } = context;

  if (activeTab !== value) return null;

  return <div>{children}</div>
};
