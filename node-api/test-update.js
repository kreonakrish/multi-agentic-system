const axios = require('axios');

const updateAgent = async () => {
    try {
        const response = await axios.put('http://localhost:4000/api/agents/13', {
            name: 'AWS Agents',
            memoryType: 'Graph',
            foundationModel: 'OpenAI',
            tools: [{ id: 1 }, { id: 2 }]
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });

        console.log('Response:', response.data);
    } catch (error) {
        console.error('Error:', error.response ? error.response.data : error.message);
    }
};

updateAgent(); 