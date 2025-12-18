import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Settings } from 'lucide-react';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const isHome = location.pathname === '/';
    const isLive = location.pathname === '/live';

    return (
        <div className="app-layout">
            {!isHome && !isLive && (
                <header className="app-header">
                    <button onClick={() => navigate('/')} className="back-button">
                        <ArrowLeft size={24} />
                        <span>Back to Menu</span>
                    </button>

                    <button className="settings-button">
                        <Settings size={24} />
                    </button>
                </header>
            )}
            <main className="app-content">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
