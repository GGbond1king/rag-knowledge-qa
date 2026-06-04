import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Settings,
  Database,
  MessageSquare,
  Menu,
  X,
  Sparkles
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const location = useLocation();

  const navItems = [
    { path: '/config', icon: Settings, label: '系统配置' },
    { path: '/knowledge', icon: Database, label: '知识库' },
    { path: '/chat', icon: MessageSquare, label: '智能对话' },
  ];

  return (
    <>
      {/* 移动端遮罩 */}
      {!collapsed && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={onToggle}
        />
      )}
      
      <aside
        className={`
          fixed top-0 left-0 h-full z-30
          bg-slate-900/95 backdrop-blur-xl border-r border-slate-700/50
          transition-all duration-300 ease-in-out flex flex-col
          ${collapsed ? '-translate-x-full lg:translate-x-0 lg:w-20' : 'translate-x-0 w-72'}
        `}
      >
        {/* Logo区域 */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-emerald-400 flex items-center justify-center shadow-lg shadow-cyan-500/25">
              <Sparkles className="w-5 h-5 text-slate-900" />
            </div>
            {!collapsed && (
              <div>
                <h1 className="text-base font-bold text-white tracking-tight">
                  RAG智能检索
                </h1>
                <p className="text-[10px] text-slate-400 -mt-0.5">Knowledge AI System</p>
              </div>
            )}
          </div>
          
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
                            (item.path !== '/config' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => {
                  if (window.innerWidth < 1024) onToggle();
                }}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-xl
                  transition-all duration-200 group relative
                  ${isActive 
                    ? 'bg-gradient-to-r from-cyan-500/15 to-emerald-500/10 text-cyan-300 shadow-sm' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }
                `}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-cyan-400 to-emerald-400 rounded-r-full" />
                )}
                
                <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-cyan-400' : ''}`} />
                
                {!collapsed && (
                  <span className="font-medium text-sm">{item.label}</span>
                )}
                
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                    {item.label}
                  </div>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* 底部信息 */}
        {!collapsed && (
          <div className="p-4 border-t border-slate-700/50">
            <div className="px-3 py-2 rounded-lg bg-slate-800/50">
              <p className="text-xs text-slate-500">系统状态</p>
              <p className="text-xs text-emerald-400 font-medium mt-0.5 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                运行中 v1.0.0
              </p>
            </div>
          </div>
        )}
        
        {/* 折叠按钮（桌面端） */}
        <button
          onClick={onToggle}
          className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 items-center justify-center bg-slate-700 hover:bg-slate-600 rounded-full border border-slate-600 text-slate-400 hover:text-white transition-all shadow-lg"
        >
          <Menu className="w-3.5 h-3.5" />
        </button>
      </aside>
    </>
  );
};

export default Sidebar;
