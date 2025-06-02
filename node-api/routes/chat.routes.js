const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller');

// Process chat message
router.post('/message', chatController.processMessage);

// Get chat history
router.get('/history/:sessionId', chatController.getHistory);

module.exports = router; 