import { createTheme } from '@mui/material/styles';

// Common theme settings
const getTheme = (mode) => createTheme({
    palette: {
        mode,
        primary: {
            main: mode === 'light' ? '#1877f2' : '#90caf9',
        },
        secondary: {
            main: mode === 'light' ? '#42b72a' : '#66bb6a',
        },
        background: {
            default: mode === 'light' ? '#f0f2f5' : '#121212',
            paper: mode === 'light' ? '#fff' : '#1e1e1e',
        },
        text: {
            primary: mode === 'light' ? '#050505' : '#fff',
            secondary: mode === 'light' ? '#65676b' : '#b0b3b8',
        },
    },
    typography: {
        fontFamily: ['Segoe UI', 'Arial', 'sans-serif'].join(','),
        fontWeightBold: 600,
        fontWeightMedium: 500,
    },
    shape: {
        borderRadius: 10,
    },
    components: {
        MuiCssBaseline: {
            styleOverrides: {
                body: {
                    backgroundColor: mode === 'light' ? '#f0f2f5' : '#121212',
                    color: mode === 'light' ? '#050505' : '#fff',
                },
            },
        },
        MuiAppBar: {
            styleOverrides: {
                root: {
                    backgroundColor: mode === 'light' ? '#8C7B53' : '#1e1e1e',
                    color: mode === 'light' ? '#fff' : '#fff',
                },
            },
        },
        MuiDrawer: {
            styleOverrides: {
                paper: {
                    backgroundColor: mode === 'light' ? '#fff' : '#1e1e1e',
                    color: mode === 'light' ? '#050505' : '#fff',
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: 'none',
                    fontWeight: 600,
                    boxShadow: 'none',
                    borderRadius: 8,
                    '&.Mui-disabled': {
                        backgroundColor: mode === 'light' ? '#e4e6eb' : '#2d2d2d',
                        color: mode === 'light' ? '#bcc0c4' : '#666',
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundColor: mode === 'light' ? '#fff' : '#1e1e1e',
                    color: mode === 'light' ? '#050505' : '#fff',
                    borderRadius: 10,
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    backgroundColor: mode === 'light' ? '#fff' : '#1e1e1e',
                    boxShadow: mode === 'light' 
                        ? '0 1px 2px rgba(0,0,0,0.07), 0 0.5px 1.5px rgba(0,0,0,0.13)'
                        : '0 1px 2px rgba(255,255,255,0.07), 0 0.5px 1.5px rgba(255,255,255,0.13)',
                    borderRadius: 10,
                },
            },
        },
        MuiList: {
            styleOverrides: {
                root: {
                    backgroundColor: 'transparent',
                },
            },
        },
        MuiListItem: {
            styleOverrides: {
                root: {
                    '&:hover': {
                        backgroundColor: mode === 'light' ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.08)',
                    },
                },
            },
        },
        MuiIconButton: {
            styleOverrides: {
                root: {
                    color: mode === 'light' ? '#050505' : '#fff',
                },
            },
        },
        MuiDivider: {
            styleOverrides: {
                root: {
                    borderColor: mode === 'light' ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)',
                },
            },
        },
    },
});

export { getTheme };