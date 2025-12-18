import React from 'react';

const SettingsOverlay = ({ isOpen, onClose, onSelectProfile }) => {
    if (!isOpen) return null;

    // Mock profiles for now
    const profiles = [
        { id: 1, name: "Profile A (Standard)" },
        { id: 2, name: "Profile B (Strict)" },
        { id: 3, name: "Profile C (Loose)" }
    ];

    return (
        <div style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
        }}>
            <div style={{
                background: 'white',
                padding: '30px',
                borderRadius: '12px',
                width: '500px',
                maxWidth: '90%',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
            }}>
                <h2 style={{ marginTop: 0, marginBottom: '20px', fontSize: '24px' }}>Select Profile</h2>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                    {profiles.map(p => (
                        <button
                            key={p.id}
                            onClick={() => { onSelectProfile(p); onClose(); }}
                            style={{
                                padding: '15px',
                                fontSize: '18px',
                                border: '1px solid #ddd',
                                borderRadius: '8px',
                                background: '#f8f9fa',
                                cursor: 'pointer',
                                textAlign: 'left'
                            }}
                        >
                            {p.name}
                        </button>
                    ))}
                </div>

                <button
                    onClick={onClose}
                    style={{
                        width: '100%',
                        padding: '10px',
                        background: '#e0e0e0',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '16px',
                        cursor: 'pointer'
                    }}
                >
                    Cancel
                </button>
            </div>
        </div>
    );
};

export default SettingsOverlay;
