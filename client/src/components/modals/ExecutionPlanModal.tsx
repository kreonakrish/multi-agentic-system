import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box } from '@mui/material';

interface ExecutionPlanModalProps {
  open: boolean;
  onClose: () => void;
  mermaidDefinition: string;
}

const ExecutionPlanModal: React.FC<ExecutionPlanModalProps> = ({
  open,
  onClose,
  mermaidDefinition,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mermaidModule, setMermaidModule] = useState<any>(null);
  const [diagramId, setDiagramId] = useState<string>('');

  // Load Mermaid once
  useEffect(() => {
    import('mermaid')
      .then((mod) => {
        mod.default.initialize({ startOnLoad: false, securityLevel: 'loose' });
        setMermaidModule(mod.default);
        if (typeof window !== 'undefined') {
          // @ts-ignore
          window.mermaid = mod.default;
        }
      })
      .catch((err) => console.error('Mermaid load error:', err));
  }, []);

  // Reset diagramId on every open
  useEffect(() => {
    if (open) {
      setDiagramId(`mermaid-${Date.now()}`);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !mermaidModule || !containerRef.current || !diagramId) return;

    const def = mermaidDefinition.replace(/\\n/g, '\n');
    const el = containerRef.current;
    el.innerHTML = '';

    const renderTimer = setTimeout(() => {
      try {
        mermaidModule.render(diagramId, def).then(({ svg }: { svg: string }) => {
          if (el) el.innerHTML = svg;
        }).catch((err: any) => {
          el.innerHTML = `<pre style='color:red'>Render error: ${err?.message || err}</pre>`;
        });
      } catch (err) {
        el.innerHTML = `<pre style='color:red'>Render error: ${String(err)}</pre>`;
      }
    }, 300); // Let DOM settle (MUI Dialog open)

    return () => {
      clearTimeout(renderTimer);
      el.innerHTML = '';
    };
  }, [open, diagramId, mermaidDefinition, mermaidModule]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="execution-plan-title"
      aria-describedby="execution-plan-content"
    >
      <DialogTitle id="execution-plan-title">Execution Plan (SOP)</DialogTitle>
      <DialogContent id="execution-plan-content">
        <Box sx={{ minHeight: 300, overflow: 'auto' }}>
          <div ref={containerRef} />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExecutionPlanModal; 