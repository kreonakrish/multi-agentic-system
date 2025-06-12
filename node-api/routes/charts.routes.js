const express = require('express');
const router = express.Router();
const axios = require('axios');
const logger = require('../utils/logger');

module.exports = (pool) => {
    // Chart endpoint: orchestrates call to Python microservice
    router.get('/', async (req, res) => {
        try {
            // Call Python microservice for chart data
            const { data } = await axios.get('http://localhost:5000/api/charts');
            res.json(data);
        } catch (err) {
            logger.warn('Python service unavailable, returning fallback data:', err);
            // Fallback dummy data if Python service unavailable
            res.json([
                {
                    id: 1,
                    type: 'bar',
                    title: 'Monthly Data Overview',
                    data: [
                        { name: 'Jan', uv: 400, pv: 240, amt: 240 },
                        { name: 'Feb', uv: 300, pv: 139, amt: 221 },
                        { name: 'Mar', uv: 200, pv: 980, amt: 229 },
                        { name: 'Apr', uv: 278, pv: 390, amt: 200 },
                        { name: 'May', uv: 189, pv: 480, amt: 218 },
                        { name: 'Jun', uv: 239, pv: 380, amt: 250 },
                        { name: 'Jul', uv: 349, pv: 430, amt: 210 },
                        { name: 'Aug', uv: 400, pv: 240, amt: 240 },
                        { name: 'Sep', uv: 300, pv: 139, amt: 221 },
                        { name: 'Oct', uv: 200, pv: 980, amt: 229 },
                        { name: 'Nov', uv: 278, pv: 390, amt: 200 },
                        { name: 'Dec', uv: 189, pv: 480, amt: 218 }
                    ]
                },
                {
                    id: 2,
                    type: 'line',
                    title: 'Email Traffic by Month',
                    data: [
                        { name: 'Jan', sent: 400, received: 240 },
                        { name: 'Feb', sent: 300, received: 139 },
                        { name: 'Mar', sent: 200, received: 980 },
                        { name: 'Apr', sent: 278, received: 390 },
                        { name: 'May', sent: 189, received: 480 },
                        { name: 'Jun', sent: 239, received: 380 },
                        { name: 'Jul', sent: 349, received: 430 },
                        { name: 'Aug', sent: 400, received: 240 },
                        { name: 'Sep', sent: 300, received: 139 },
                        { name: 'Oct', sent: 200, received: 980 },
                        { name: 'Nov', sent: 278, received: 390 },
                        { name: 'Dec', sent: 189, received: 480 }
                    ]
                }
            ]);
        }
    });

    return router;
}; 