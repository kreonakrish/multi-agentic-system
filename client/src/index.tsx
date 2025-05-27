import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import {ThemeProvider, CssBaseline, containerClasses} from '@mui/material';
import theme from './theme';

const container = document.getElementById('root');
if (container) {
    const root = ReactDOM.createRoot(container);
    root.render(
        <React.StrictMode>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <App />
            </ThemeProvider>
        </React.StrictMode>
    );
}
