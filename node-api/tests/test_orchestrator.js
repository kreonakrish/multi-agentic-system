const orchestrator = require('../services/orchestrator.service');
const logger = require('../utils/logger');

async function testOrchestratorService() {
    try {
        logger.info('Starting orchestrator service test');

        // Test standard workflow
        await testStandardWorkflow();

        // Test smart workflow
        await testSmartWorkflow();

        logger.info('All tests completed successfully');
        return { success: true };
    } catch (error) {
        logger.error('Test failed:', {
            error: error.message,
            stack: error.stack
        });
        return {
            success: false,
            error: error.message
        };
    }
}

async function testStandardWorkflow() {
    logger.info('Testing standard workflow...');

    const messageData = {
        content: "Hello, can you help me with data analysis?",
        userId: "test-user-1",
        sessionId: "test-session-1",
        context: {
            team_id: "data-analysis-team",
            team_config: {
                name: "Data Analysis Team",
                description: "Team specialized in data analysis tasks",
                members: [
                    {
                        agent_id: 10,
                        priority: 3,
                        accuracy_threshold: 0.9,
                        success_rate: 0.95,
                        role: "context_analyzer"
                    },
                    {
                        agent_id: 11,
                        priority: 2,
                        accuracy_threshold: 0.8,
                        success_rate: 0.9,
                        role: "response_generator"
                    }
                ]
            },
            conversation_history: []
        }
    };

    const response = await orchestrator.processChatMessage(messageData);
    validateResponse(response, 'standard');
}

async function testSmartWorkflow() {
    logger.info('Testing smart workflow...');

    const messageData = {
        content: "Create a data pipeline that processes customer feedback and generates sentiment analysis reports.",
        userId: "test-user-2",
        sessionId: "test-session-2",
        context: {
            team_id: "data-pipeline-team",
            use_smart_workflow: true,
            team_config: {
                name: "Data Pipeline Team",
                description: "Team specialized in data pipeline creation",
                members: [
                    {
                        agent_id: 20,
                        priority: 3,
                        accuracy_threshold: 0.95,
                        success_rate: 0.98,
                        role: "architect"
                    },
                    {
                        agent_id: 21,
                        priority: 2,
                        accuracy_threshold: 0.9,
                        success_rate: 0.95,
                        role: "developer"
                    },
                    {
                        agent_id: 22,
                        priority: 2,
                        accuracy_threshold: 0.9,
                        success_rate: 0.95,
                        role: "tester"
                    }
                ]
            },
            conversation_history: []
        }
    };

    const response = await orchestrator.processChatMessage(messageData);
    validateResponse(response, 'smart');
}

function validateResponse(response, type) {
    // Basic validation
    if (!response || typeof response !== 'object') {
        throw new Error('Invalid response format: response should be an object');
    }

    if (!response.content) {
        throw new Error('Invalid response format: missing content');
    }

    if (!response.status) {
        throw new Error('Invalid response format: missing status');
    }

    if (!response.metadata) {
        throw new Error('Invalid response format: missing metadata');
    }

    // Smart workflow specific validation
    if (type === 'smart') {
        if (!response.metadata.workflow_type || response.metadata.workflow_type !== 'smart') {
            throw new Error('Invalid smart workflow response: incorrect workflow type');
        }

        if (!response.smart_workflow_data) {
            throw new Error('Invalid smart workflow response: missing smart workflow data');
        }

        const { smart_workflow_data } = response;

        // Validate context analysis
        if (!smart_workflow_data.context_analysis) {
            throw new Error('Invalid smart workflow response: missing context analysis');
        }

        // Validate task decomposition
        if (!smart_workflow_data.task_decomposition || !Array.isArray(smart_workflow_data.task_decomposition.subtasks)) {
            throw new Error('Invalid smart workflow response: invalid task decomposition');
        }

        // Validate execution metrics
        if (!smart_workflow_data.execution_metrics) {
            throw new Error('Invalid smart workflow response: missing execution metrics');
        }
    }

    logger.info(`${type} workflow test passed`);
    logger.info('Response content:', response.content);
    logger.info('Response metadata:', response.metadata);
    if (type === 'smart') {
        logger.info('Smart workflow data:', response.smart_workflow_data);
    }
}

// Run the test
testOrchestratorService()
    .then(result => {
        if (result.success) {
            logger.info('✅ All tests passed');
        } else {
            logger.error('❌ Tests failed:', result.error);
        }
        process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
        logger.error('❌ Test execution failed:', error);
        process.exit(1);
    }); 