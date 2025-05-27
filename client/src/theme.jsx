import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#1877f2', // Facebook blue
        },
        secondary: {
            main: '#42b72a', // Facebook green
        },
        background: {
            default: '#f0f2f5', // Facebook background
            paper: '#fff',
        },
        text: {
            primary: '#050505',
            secondary: '#65676b',
        },
    },
    typography: {
        fontFamily: ['Segoe UI', 'Arial', 'sans-serif'].join(','),
        fontWeightBold: 600,
        fontWeightMedium: 500,
    },
    shape: {
        borderRadius: 10, // Facebook-like rounded corners
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: 'none', // Facebook buttons use normal case
                    fontWeight: 600,
                    boxShadow: 'none',
                    borderRadius: 8,
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    borderRadius: 10,
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    boxShadow: '0 1px 2px rgba(0,0,0,0.07), 0 0.5px 1.5px rgba(0,0,0,0.13)',
                    borderRadius: 10,
                },
            },
        },
    },
});

export default theme;