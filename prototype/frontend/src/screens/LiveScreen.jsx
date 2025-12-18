import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import SettingsOverlay from '../components/SettingsOverlay';
import '../App.css';

// Hardcoded Presets from Python code
const SKU_COLORS = {
    0: "#B0BEC5", // Gray
    1: "#2196F3", // Blue
    2: "#E91E63", // Pink
    3: "#9C27B0", // Purple
    4: "#FF9800"  // Orange
};

const DEFAULT_PRESETS = [
    { sku: "E-0123M", size: "36", color: 1 }, { sku: "E-0123M", size: "37", color: 1 },
    { sku: "E-0123M", size: "38", color: 1 }, { sku: "E-0123M", size: "39", color: 1 },
    { sku: "E-0123M", size: "40", color: 1 }, { sku: "E-0123M", size: "41", color: 1 },
    { sku: "E-0123M", size: "42", color: 1 }, { sku: "E-0123M", size: "43", color: 1 },
    { sku: "E-9008L", size: "38", color: 2 }, { sku: "E-9008L", size: "39", color: 2 },
    { sku: "E-9008L", size: "40", color: 2 }, { sku: "E-9008L", size: "41", color: 2 },
    { sku: "X-5000-Pro", size: "S", color: 3 }, { sku: "X-5000-Pro", size: "M", color: 3 },
    { sku: "X-5000-Pro", size: "L", color: 3 },
    { sku: "A-1001X", size: "38", color: 2 }, { sku: "A-1001X", size: "39", color: 2 },
    { sku: "A-1001X", size: "40", color: 2 },
    { sku: "B-2020Y", size: "S", color: 3 }, { sku: "B-2020Y", size: "M", color: 3 },
    { sku: "B-2020Y", size: "L", color: 3 }, { sku: "B-2020Y", size: "XL", color: 3 },
    { sku: "C-3030Z", size: "40", color: 4 }, { sku: "C-3030Z", size: "41", color: 4 },
    { sku: "C-3030Z", size: "42", color: 4 }
];

// Group by SKU
const GROUPED_PRESETS = DEFAULT_PRESETS.reduce((acc, item) => {
    if (!acc[item.sku]) acc[item.sku] = [];
    acc[item.sku].push(item);
    return acc;
}, {});

const LiveScreen = () => {
    const navigate = useNavigate();
    const [data, setData] = useState({ status: "IDLE" });
    const [goodCount, setGoodCount] = useState(0);
    const [bsCount, setBsCount] = useState(0);
    const [selectedSku, setSelectedSku] = useState("---");
    const [selectedSize, setSelectedSize] = useState("---");
    const [isOverlayOpen, setIsOverlayOpen] = useState(false);
    const [activeProfile, setActiveProfile] = useState("Shift 1, Team A");

    useEffect(() => {
        const handleKeyDown = (e) => {
            // Toggle Overlay with 'S'
            if (e.key.toLowerCase() === 's') {
                setIsOverlayOpen(prev => !prev);
            }
            // Close with 'Escape'
            if (e.key === 'Escape') {
                setIsOverlayOpen(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const [isLive, setIsLive] = useState(true);
    const [frozenData, setFrozenData] = useState(null);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws");

        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                if (isLive) {
                    setData(parsed);
                }
                // Logic for counters...
                if (parsed.pass_fail === "PASS" && data.pass_fail !== "PASS") setGoodCount(c => c + 1);
                if (parsed.pass_fail === "FAIL" && data.pass_fail !== "FAIL") setBsCount(c => c + 1);
            } catch (e) { }
        };
        return () => ws.close();
    }, [isLive, data.pass_fail]);

    const handleCapture = () => {
        setIsLive(!isLive); // Toggle Live/Freeze
        if (isLive) {
            setFrozenData(data); // Save the current frame info
        }
    };

    const handlePresetClick = (item) => {
        setSelectedSku(item.sku);
        setSelectedSize(item.size);
    };

    const currentDisplayData = isLive ? data : frozenData || data;

    const getBigResultClass = () => {
        if (currentDisplayData.pass_fail === "PASS") return "pass";
        if (currentDisplayData.pass_fail === "FAIL") return "reject";
        return "idle";
    };

    const getBigResultText = () => {
        if (currentDisplayData.pass_fail === "PASS") return "GOOD";
        if (currentDisplayData.pass_fail === "FAIL") return "REJECT";
        return "IDLE";
    };

    return (
        <div className="live-screen-container">
            <SettingsOverlay
                isOpen={isOverlayOpen}
                onClose={() => setIsOverlayOpen(false)}
                onSelectProfile={(p) => setActiveProfile(p.name)}
            />

            {/* LEFT PANEL: PRESETS */}
            <div className="left-panel">
                <div className="presets-header">
                    <h2>Presets</h2>
                    <div className="info-bar"> {activeProfile} </div>
                    <button
                        className="btn"
                        onClick={() => setIsOverlayOpen(true)}
                        style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #ccc', background: '#eee', cursor: 'pointer' }}
                    >
                        Edit
                    </button>
                </div>

                <div className="presets-scroll">
                    {Object.keys(GROUPED_PRESETS).map(sku => (
                        <div key={sku}>
                            <div className="preset-group-title">{sku}</div>
                            <div className="preset-grid">
                                {GROUPED_PRESETS[sku].map((item, idx) => (
                                    <button
                                        key={idx}
                                        className={`preset-btn ${selectedSize === item.size && selectedSku === item.sku ? 'active' : ''}`}
                                        style={{ backgroundColor: SKU_COLORS[item.color] }}
                                        onClick={() => handlePresetClick(item)}
                                    >
                                        {item.size}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* RIGHT PANEL: PREVIEW & STATS */}
            <div className="right-panel">
                <div className="top-controls">
                    <button className="circle-btn" onClick={() => navigate('/')}>←</button>
                    <button
                        className={`btn ${isLive ? 'primary' : 'fail'}`}
                        onClick={handleCapture}
                        style={{ flexGrow: 1, margin: '0 10px', fontSize: '1.2rem' }}
                    >
                        {isLive ? "CAPTURE" : "RESUME LIVE"}
                    </button>
                    <button className="circle-btn" onClick={() => setIsOverlayOpen(true)}>⚙️</button>
                </div>

                <div className="preview-box" onClick={handleCapture} style={{ cursor: 'pointer' }}>
                    {currentDisplayData.image ? (
                        <img src={`data:image/jpeg;base64,${currentDisplayData.image}`} alt="Result" />
                    ) : (
                        <span>Review Frameshot</span>
                    )}
                    {!isLive && <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(255,0,0,0.7)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>FROZEN</div>}
                </div>

                <div className="counters-row">
                    <div className="counter good">
                        <div>{goodCount}</div>
                        <div style={{ fontSize: '1rem' }}>Good</div>
                    </div>
                    <div className="counter bs">
                        <div>{bsCount}</div>
                        <div style={{ fontSize: '1rem' }}>BS</div>
                    </div>
                </div>

                <div className={`big-result ${getBigResultClass()}`}>
                    <div style={{ fontSize: '32px' }}>{selectedSize !== "---" ? selectedSize : "-"}</div>
                    <div>{getBigResultText()}</div>
                </div>

                <div className="details-table">
                    <div className="dt-label">SKU/Size :</div>
                    <div className="dt-value">{selectedSku}/{selectedSize}</div>

                    <div className="dt-label">Length :</div>
                    <div className="dt-value">{data.real_length_mm ? data.real_length_mm.toFixed(2) : "-"} mm</div>

                    <div className="dt-label">Width :</div>
                    <div className="dt-value">{data.real_width_mm ? data.real_width_mm.toFixed(2) : "-"} mm</div>

                    <div className="dt-label">Result :</div>
                    <div className="dt-value">{data.pass_fail || "-"}</div>
                </div>
            </div>
        </div>
    );
};

export default LiveScreen;
