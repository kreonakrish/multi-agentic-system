import React, { useEffect, useRef } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

// @ts-ignore
import mermaid from 'mermaid';

interface ExecutionPlanModalProps {
  open: boolean;
  onClose: () => void;
  mermaidDefinition: string;
}

const ExecutionPlanModal: React.FC<ExecutionPlanModalProps> = ({ open, onClose, mermaidDefinition }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && ref.current) {
      mermaid.initialize({ startOnLoad: false });
      mermaid.render('mermaid-sop', mermaidDefinition).then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      });
    }
  }, [open, mermaidDefinition]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Execution Plan (SOP)</DialogTitle>
      <DialogContent>
        <Box sx={{ minHeight: 300 }}>
          <div ref={ref} />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExecutionPlanModal;

