import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Database, Power } from 'lucide-react';
import '../App.css';

const MenuButton = ({ icon: Icon, label, onClick, color }) => (
    <button
        onClick={onClick}
        className="menu-button"
        style={{ borderLeft: `6px solid ${color}` }}
    >
        <Icon size={32} color={color} />
        <span>{label}</span>
    </button>
);

const MenuScreen = () => {
    const navigate = useNavigate();

    const handleQuit = async () => {
        if (confirm("Shutdown the system?")) {
            try { await fetch('http://localhost:8000/shutdown', { method: 'POST' }); } catch (e) { }
            window.close(); // Try to close tab
            document.body.innerHTML = "<h1>System Shutdown. You can close this tab.</h1>";
        }
    };

    return (
        <div className="menu-container">
            <h1 className="menu-title">QC Sandal Detection System</h1>

            <div className="menu-grid">
                <MenuButton
                    icon={Camera}
                    label="Live Measure"
                    onClick={() => navigate('/live')}
                    color="#F44336"
                />
                <MenuButton
                    icon={Database}
                    label="Capture Dataset"
                    onClick={() => navigate('/dataset')}
                    color="#4CAF50"
                />
                <MenuButton
                    icon={Power}
                    label="Quit System"
                    onClick={handleQuit}
                    color="#607D8B"
                />
            </div>
        </div>
    );
};

export default MenuScreen;
