const express = require('express');
const router = express.Router();
const createChatController = require('../controllers/chat.controller');

module.exports = (pool) => {
    const chatController = createChatController(pool);

    // Process chat message
    router.post('/message', chatController.processMessage.bind(chatController));

    // Get chat history
    router.get('/history/:sessionId', chatController.getHistory.bind(chatController));

    return router;
}; 