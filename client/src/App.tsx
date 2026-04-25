import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import AgentInsights from './pages/AgentInsights';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<Dashboard />} />
                    <Route path="alerts" element={<Alerts />} />
                    <Route path="insights" element={<AgentInsights />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

export default App;
