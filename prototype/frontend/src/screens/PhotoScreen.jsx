import React, { useState, useEffect } from 'react';
import { Ruler, CheckCircle, AlertCircle } from 'lucide-react';
import '../App.css';

const PhotoScreen = () => {
    const [images, setImages] = useState([]);
    const [selectedImage, setSelectedImage] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchImages();
    }, []);

    const fetchImages = async () => {
        try {
            const res = await fetch('http://localhost:8000/gallery');
            const data = await res.json();
            setImages(data);
        } catch (e) {
            console.error("Failed to fetch gallery", e);
        }
    };

    const handleSelect = (img) => {
        setSelectedImage(img);
        setResult(null); // Reset result on new selection
    };

    const handleMeasure = async () => {
        if (!selectedImage) return;
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/measure/photo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: selectedImage.name })
            });
            const data = await res.json();
            if (data.success) {
                setResult(data);
            } else {
                alert("Measurement failed: " + data.error);
            }
        } catch (e) {
            alert("Error measuring image");
        }
        setLoading(false);
    };

    // Determine what image to show (Original or Processed)
    const displayImage = result && result.output_url
        ? `http://localhost:8000${result.output_url}`
        : selectedImage
            ? `http://localhost:8000${selectedImage.url}`
            : null;

    return (
        <div className="screen-container">
            <div className="photo-layout">
                {/* Left: Preview & Action */}
                <div className="preview-panel">
                    <div className="image-viewer">
                        {displayImage ? (
                            <img src={displayImage} alt="Preview" className="main-preview" />
                        ) : (
                            <div className="placeholder">Select an image from the gallery</div>
                        )}
                    </div>

                    <div className="action-bar">
                        <button
                            className="btn primary"
                            disabled={!selectedImage || loading}
                            onClick={handleMeasure}
                        >
                            {loading ? "Processing..." : "Measure Selected"}
                        </button>
                    </div>

                    {/* Simple Result Display */}
                    {result && result.results && result.results[0] && (
                        <div className="result-overlay-box">
                            <h3>Measurement Result</h3>
                            <div className="row">
                                <span>Length:</span>
                                <strong>{result.results[0].px_length.toFixed(1)} px</strong>
                            </div>
                            <div className="row">
                                <span>Width:</span>
                                <strong>{result.results[0].px_width.toFixed(1)} px</strong>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right: Gallery Grid */}
                <div className="gallery-panel">
                    <h3>Gallery</h3>
                    <div className="gallery-grid">
                        {images.map(img => (
                            <div
                                key={img.name}
                                className={`gallery-item ${selectedImage?.name === img.name ? 'selected' : ''}`}
                                onClick={() => handleSelect(img)}
                            >
                                <img src={`http://localhost:8000${img.url}`} alt={img.name} />
                                <span className="filename">{img.name}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PhotoScreen;
