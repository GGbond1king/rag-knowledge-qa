import React, { useState } from 'react';
import Sidebar from './Sidebar';
import { Menu } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
      />
      
      <main
        className={`
          min-h-screen transition-all duration-300
          ${sidebarCollapsed ? 'lg:ml-20' : 'lg:ml-72'}
        `}
      >
        {/* 移动端顶栏 */}
        <header className="sticky top-0 z-10 h-14 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800 px-4 flex items-center gap-3 lg:hidden">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="p-2 rounded-lg hover:bg-slate-800 text-slate-400"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="font-semibold text-sm">RAG智能检索</span>
        </header>

        <div className="p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
