const request = require('supertest');
const app = require('../app');
const db = require('../database/db');

describe('Agent API Endpoints', () => {
    let testAgentId;

    beforeAll(async () => {
        // Create a test agent to use in tests
        const [result] = await db.query(
            'INSERT INTO agents (name, memory_type, foundation_model, status) VALUES (?, ?, ?, ?)',
            ['Test Agent', 'short-term', 'gpt-4', 'inactive']
        );
        testAgentId = result.insertId;
    });

    afterAll(async () => {
        // Clean up test data
        await db.query('DELETE FROM agents WHERE id = ?', [testAgentId]);
        await db.end();
    });

    describe('GET /api/agents', () => {
        it('should return all agents', async () => {
            const res = await request(app)
                .get('/api/agents')
                .expect('Content-Type', /json/)
                .expect(200);

            expect(Array.isArray(res.body)).toBeTruthy();
            expect(res.body.length).toBeGreaterThan(0);
            expect(res.body[0]).toHaveProperty('id');
            expect(res.body[0]).toHaveProperty('name');
        });
    });

    describe('POST /api/agents', () => {
        it('should create a new agent', async () => {
            const newAgent = {
                name: 'New Test Agent',
                memory_type: 'long-term',
                foundation_model: 'gpt-3.5-turbo',
                status: 'active'
            };

            const res = await request(app)
                .post('/api/agents')
                .send(newAgent)
                .expect('Content-Type', /json/)
                .expect(201);

            expect(res.body).toHaveProperty('id');
            expect(res.body.name).toBe(newAgent.name);
            expect(res.body.memory_type).toBe(newAgent.memory_type);

            // Clean up
            await db.query('DELETE FROM agents WHERE id = ?', [res.body.id]);
        });

        it('should return 500 for invalid agent data', async () => {
            const invalidAgent = {
                // Missing required name field
                memory_type: 'long-term'
            };

            await request(app)
                .post('/api/agents')
                .send(invalidAgent)
                .expect('Content-Type', /json/)
                .expect(500);
        });
    });

    describe('GET /api/agents/:id', () => {
        it('should return a specific agent', async () => {
            const res = await request(app)
                .get(`/api/agents/${testAgentId}`)
                .expect('Content-Type', /json/)
                .expect(200);

            expect(res.body).toHaveProperty('id', testAgentId);
            expect(res.body).toHaveProperty('name', 'Test Agent');
            expect(res.body).toHaveProperty('tools');
            expect(res.body).toHaveProperty('teams');
        });

        it('should return 404 for non-existent agent', async () => {
            await request(app)
                .get('/api/agents/99999')
                .expect('Content-Type', /json/)
                .expect(404);
        });
    });

    describe('PUT /api/agents/:id', () => {
        it('should update an agent', async () => {
            const updateData = {
                name: 'Updated Test Agent',
                memory_type: 'updated-memory',
                foundation_model: 'gpt-4-turbo',
                status: 'active'
            };

            const res = await request(app)
                .put(`/api/agents/${testAgentId}`)
                .send(updateData)
                .expect('Content-Type', /json/)
                .expect(200);

            expect(res.body).toHaveProperty('id', testAgentId);
            expect(res.body.name).toBe(updateData.name);
            expect(res.body.memory_type).toBe(updateData.memory_type);
        });
    });

    describe('POST /api/agents/:id/tools', () => {
        it('should add a tool to an agent', async () => {
            // First create a test tool
            const [toolResult] = await db.query(
                'INSERT INTO tools (name, description) VALUES (?, ?)',
                ['Test Tool', 'A test tool']
            );
            const testToolId = toolResult.insertId;

            const res = await request(app)
                .post(`/api/agents/${testAgentId}/tools`)
                .send({ tool_id: testToolId })
                .expect('Content-Type', /json/)
                .expect(200);

            expect(res.body).toHaveProperty('message', 'Tool added to agent successfully');

            // Clean up
            await db.query('DELETE FROM tools WHERE id = ?', [testToolId]);
        });
    });
}); 