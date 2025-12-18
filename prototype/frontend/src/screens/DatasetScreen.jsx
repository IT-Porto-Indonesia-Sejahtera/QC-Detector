import React, { useState, useEffect } from 'react';
import { Camera, Save } from 'lucide-react';
import '../App.css';

const DatasetScreen = () => {
    const [cameras, setCameras] = useState([]);
    const [selectedCam, setSelectedCam] = useState(0);
    const [lastCaptured, setLastCaptured] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchCameras();
    }, []);

    const fetchCameras = async () => {
        try {
            const res = await fetch('http://localhost:8000/cameras');
            const data = await res.json();
            setCameras(data);
        } catch (e) {
            setCameras([0]); // Fallback
        }
    };

    const handleCapture = async () => {
        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/dataset/capture?camera_index=${selectedCam}`, {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                setLastCaptured(data.filename);
                // Simple flash effect or notification could go here
                setTimeout(() => setLastCaptured(null), 3000);
            }
        } catch (e) {
            alert("Capture failed");
        }
        setLoading(false);
    };

    return (
        <div className="screen-container">
            <div className="dataset-header">
                <label>Select Camera: </label>
                <select
                    value={selectedCam}
                    onChange={(e) => setSelectedCam(parseInt(e.target.value))}
                    className="cam-select"
                >
                    {cameras.map(idx => (
                        <option key={idx} value={idx}>Camera {idx}</option>
                    ))}
                </select>
            </div>

            <div className="video-section large">
                <div className="video-wrapper">
                    {/* Key is used to force re-render when camera changes */}
                    <img
                        key={selectedCam}
                        src={`http://localhost:8000/video_feed?camera_index=${selectedCam}`}
                        alt="Live Feed"
                        className="live-video"
                    />
                </div>
            </div>

            <div className="dataset-controls">
                <button
                    className={`btn capture-btn ${lastCaptured ? 'success' : ''}`}
                    onClick={handleCapture}
                    disabled={loading}
                >
                    <Camera size={24} style={{ marginRight: 10 }} />
                    {lastCaptured ? "Saved!" : "Capture to Dataset"}
                </button>
                {lastCaptured && <div className="saved-msg">Saved: {lastCaptured}</div>}
            </div>
        </div>
    );
};

export default DatasetScreen;
