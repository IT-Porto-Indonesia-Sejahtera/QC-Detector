import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import MenuScreen from './screens/MenuScreen';
import LiveScreen from './screens/LiveScreen';
import PhotoScreen from './screens/PhotoScreen';
import DatasetScreen from './screens/DatasetScreen';
import './App.css';

// Placeholder
const VideoScreen = () => (
  <div className="screen-container">
    <h2 style={{ textAlign: 'center', marginTop: 100, color: '#888' }}>
      Video Measurement Coming Soon
    </h2>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<MenuScreen />} />
          <Route path="live" element={<LiveScreen />} />
          <Route path="photo" element={<PhotoScreen />} />
          <Route path="video" element={<VideoScreen />} />
          <Route path="dataset" element={<DatasetScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
