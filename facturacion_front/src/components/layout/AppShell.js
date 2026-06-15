import React from 'react';
import BottomNav from './BottomNav';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import '../../css/app-shell.css';

export default function AppShell({ children }) {
  return (
    <div className="saas-shell">
      <Topbar />
      <div className="saas-shell-main">
        <Sidebar />
        <main className="saas-content">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
