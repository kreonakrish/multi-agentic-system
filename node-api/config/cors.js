const corsOptions = {
    origin: process.env.FRONTEND_URL || 'http://localhost:4000',
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true
};

module.exports = corsOptions; 