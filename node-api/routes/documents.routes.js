const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const db = require('../database/db');
const logger = require('../utils/logger');

// Configure multer for file upload
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const uploadDir = path.join(__dirname, '../uploads');
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        cb(null, Date.now() + '-' + file.originalname);
    }
});

const upload = multer({ storage: storage });

// Upload document
router.post('/upload', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const { team_id } = req.body;
        if (!team_id) {
            return res.status(400).json({ error: 'Team ID is required' });
        }

        const [result] = await db.query(
            'INSERT INTO documents (name, file_path, team_id, created_at) VALUES (?, ?, ?, NOW())',
            [req.file.originalname, req.file.path, team_id]
        );

        const [document] = await db.query(
            'SELECT * FROM documents WHERE id = ?',
            [result.insertId]
        );

        res.status(201).json({
            id: document[0].id,
            name: document[0].name,
            url: `/api/documents/download/${document[0].id}`,
            created_at: document[0].created_at
        });
    } catch (error) {
        logger.error('Error uploading document:', error);
        res.status(500).json({ error: 'Failed to upload document' });
    }
});

// Get documents for a team
router.get('/', async (req, res) => {
    try {
        const { team_id } = req.query;
        if (!team_id) {
            return res.status(400).json({ error: 'Team ID is required' });
        }

        const [documents] = await db.query(
            'SELECT * FROM documents WHERE team_id = ? ORDER BY created_at DESC',
            [team_id]
        );

        res.json(documents.map(doc => ({
            id: doc.id,
            name: doc.name,
            url: `/api/documents/download/${doc.id}`,
            created_at: doc.created_at
        })));
    } catch (error) {
        logger.error('Error fetching documents:', error);
        res.status(500).json({ error: 'Failed to fetch documents' });
    }
});

// Download document
router.get('/download/:id', async (req, res) => {
    try {
        const [document] = await db.query(
            'SELECT * FROM documents WHERE id = ?',
            [req.params.id]
        );

        if (!document.length) {
            return res.status(404).json({ error: 'Document not found' });
        }

        res.download(document[0].file_path);
    } catch (error) {
        logger.error('Error downloading document:', error);
        res.status(500).json({ error: 'Failed to download document' });
    }
});

// Delete document
router.delete('/:id', async (req, res) => {
    try {
        const [document] = await db.query(
            'SELECT * FROM documents WHERE id = ?',
            [req.params.id]
        );

        if (!document.length) {
            return res.status(404).json({ error: 'Document not found' });
        }

        // Delete file from filesystem
        if (fs.existsSync(document[0].file_path)) {
            fs.unlinkSync(document[0].file_path);
        }

        // Delete from database
        await db.query('DELETE FROM documents WHERE id = ?', [req.params.id]);

        res.json({ message: 'Document deleted successfully' });
    } catch (error) {
        logger.error('Error deleting document:', error);
        res.status(500).json({ error: 'Failed to delete document' });
    }
});

module.exports = router; 