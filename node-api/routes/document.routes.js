const express = require('express');
const router = express.Router();
const db = require('../database/db');
const logger = require('../utils/logger');

// Get documents by team ID
router.get('/', async (req, res) => {
    try {
        const teamId = req.query.team_id;
        if (!teamId) {
            return res.status(400).json({ error: 'team_id query parameter is required' });
        }

        const [documents] = await db.query(`
            SELECT 
                d.*,
                t.name as team_name
            FROM documents d
            JOIN teams t ON d.team_id = t.id
            WHERE d.team_id = ?
            ORDER BY d.uploaded_at DESC
        `, [teamId]);

        // Format response
        const formattedDocuments = documents.map(doc => ({
            ...doc,
            uploaded_at: doc.uploaded_at ? new Date(doc.uploaded_at).toISOString() : null
        }));

        res.json(formattedDocuments);
    } catch (error) {
        logger.error('Error fetching team documents:', error);
        res.status(500).json({ error: 'Failed to fetch team documents' });
    }
});

// Upload new document
router.post('/', async (req, res) => {
    try {
        const { 
            team_id,
            name,
            type,
            url
        } = req.body;

        // Insert document
        const [result] = await db.query(`
            INSERT INTO documents 
                (team_id, name, type, url)
            VALUES 
                (?, ?, ?, ?)
        `, [team_id, name, type, url]);

        // Get the created document
        const [document] = await db.query(`
            SELECT 
                d.*,
                t.name as team_name
            FROM documents d
            JOIN teams t ON d.team_id = t.id
            WHERE d.id = ?
        `, [result.insertId]);

        res.status(201).json(document[0]);
    } catch (error) {
        logger.error('Error creating document:', error);
        res.status(500).json({ error: 'Failed to create document' });
    }
});

module.exports = router; 