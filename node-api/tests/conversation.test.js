const request = require('supertest');
const app = require('../app');
const db = require('../database/db');

describe('Conversation API Endpoints', () => {
    let testConversationId;
    let testTeamId;

    beforeAll(async () => {
        // Create a test team
        const [teamResult] = await db.query(
            'INSERT INTO teams (name, description) VALUES (?, ?)',
            ['Test Team', 'A test team']
        );
        testTeamId = teamResult.insertId;

        // Create a test conversation
        const [convResult] = await db.query(
            `INSERT INTO conversations 
             (team_id, title, temperature, token_limit, start_prompt, end_prompt, style, started_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, NOW())`,
            [testTeamId, 'Test Conversation', 0.7, 1000, 'Start', 'End', 'casual']
        );
        testConversationId = convResult.insertId;
    });

    afterAll(async () => {
        // Clean up test data
        await db.query('DELETE FROM conversations WHERE id = ?', [testConversationId]);
        await db.query('DELETE FROM teams WHERE id = ?', [testTeamId]);
        await db.end();
    });

    describe('GET /api/conversations', () => {
        it('should return all conversations', async () => {
            const res = await request(app)
                .get('/api/conversations')
                .expect('Content-Type', /json/)
                .expect(200);

            expect(Array.isArray(res.body)).toBeTruthy();
            expect(res.body.length).toBeGreaterThan(0);
            expect(res.body[0]).toHaveProperty('id');
            expect(res.body[0]).toHaveProperty('title');
            expect(res.body[0]).toHaveProperty('team_name');
        });
    });

    describe('POST /api/conversations', () => {
        it('should create a new conversation', async () => {
            const newConversation = {
                team_id: testTeamId,
                title: 'New Test Conversation',
                settings: {
                    temperature: 0.8,
                    token_limit: 2000,
                    start_prompt: 'New Start',
                    end_prompt: 'New End',
                    style: 'formal'
                }
            };

            const res = await request(app)
                .post('/api/conversations')
                .send(newConversation)
                .expect('Content-Type', /json/)
                .expect(201);

            expect(res.body).toHaveProperty('id');
            expect(res.body.title).toBe(newConversation.title);
            expect(res.body.temperature).toBe(newConversation.settings.temperature);

            // Clean up
            await db.query('DELETE FROM conversations WHERE id = ?', [res.body.id]);
        });
    });

    describe('GET /api/conversations/:id', () => {
        it('should return a specific conversation with steps', async () => {
            const res = await request(app)
                .get(`/api/conversations/${testConversationId}`)
                .expect('Content-Type', /json/)
                .expect(200);

            expect(res.body).toHaveProperty('id', testConversationId);
            expect(res.body).toHaveProperty('title', 'Test Conversation');
            expect(res.body).toHaveProperty('steps');
            expect(Array.isArray(res.body.steps)).toBeTruthy();
        });

        it('should return 404 for non-existent conversation', async () => {
            await request(app)
                .get('/api/conversations/99999')
                .expect('Content-Type', /json/)
                .expect(404);
        });
    });

    describe('POST /api/conversations/:id/steps', () => {
        it('should add a step to a conversation', async () => {
            const newStep = {
                role: 'user',
                content: 'Test message',
                agent_id: null,
                tool_id: null,
                parent_idx: null
            };

            const res = await request(app)
                .post(`/api/conversations/${testConversationId}/steps`)
                .send(newStep)
                .expect('Content-Type', /json/)
                .expect(201);

            expect(res.body).toHaveProperty('id');
            expect(res.body.role).toBe(newStep.role);
            expect(res.body.content).toBe(newStep.content);
        });
    });

    describe('PUT /api/conversations/:id/end', () => {
        it('should end a conversation', async () => {
            const res = await request(app)
                .put(`/api/conversations/${testConversationId}/end`)
                .expect('Content-Type', /json/)
                .expect(200);

            expect(res.body).toHaveProperty('id', testConversationId);
            expect(res.body).toHaveProperty('ended_at');
            expect(res.body.ended_at).not.toBeNull();
        });
    });
}); 