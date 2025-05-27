import Button from '@mui/material/Button';

type ChatSessionButtonProps = {
    label: string;
};

export default function ChatSessionButton({ label }: ChatSessionButtonProps) {
    return (
        <Button
            variant="contained"
    sx={{
        bgcolor: '#e7f3ff',
            color: '#1877f2',
            fontWeight: 600,
            borderRadius: 50,
            px: 3,
            my: 1,
            boxShadow: 'none',
            '&:hover': {
            bgcolor: '#d0e6fa',
        },
    }}
    disableElevation
    size="small"
        >
        {label}
        </Button>
);
}