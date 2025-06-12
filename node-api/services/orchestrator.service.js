const axios = require('axios');
const logger = require('../utils/logger');
const OpenAI = require('openai');

// Configuration for Python ML service
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000/api/ml';
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

class OrchestratorService {
    constructor() {
        this.defaultTeamConfig = {
            name: "Chat Response Team",
            description: "Team for processing chat messages and generating responses",
            use_smart_workflow: false,
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
        };
        
        // Initialize conversation contexts
        this.conversationContexts = new Map();
        
        // Common greetings patterns
        this.greetingPatterns = [
            /^hi\b/i,
            /^hello\b/i,
            /^hey\b/i,
            /^greetings\b/i,
            /^good\s*(morning|afternoon|evening|day)\b/i,
            /^howdy\b/i,
            /^hola\b/i
        ];

        // System question patterns
        this.systemQuestionPatterns = {
            tools: [
                /what\s+tools?\s+(?:do\s+)?(?:you|we|i)\s+have/i,
                /what\s+(?:can|could)\s+(?:you|we|i)\s+(?:do|use)/i,
                /(?:show|list|tell)\s+(?:me\s+)?(?:the\s+)?(?:available\s+)?tools/i,
                /what\s+(?:are|is)\s+(?:the|your)\s+capabilities/i,
                /how\s+(?:many)\s+(?:tools)\s+(?:do\s+)?(?:you|we|i)\s+have/i,
                /^how\s+many\s+tools?\b/i
            ],
            capabilities: [
                /what\s+can\s+you\s+do/i,
                /what\s+(?:are|is)\s+(?:the|your)\s+capabilities/i,
                /what\s+(?:are|is)\s+(?:the|your)\s+functions?/i
            ],
            agents: [
                /what\s+agents?\s+(?:do\s+)?(?:you|we|i)\s+have/i,
                /(?:show|list|tell)\s+(?:me\s+)?(?:the\s+)?(?:available\s+)?agents/i,
                /who\s+(?:are|is)\s+(?:the|your)\s+agents/i,
                /how\s+(?:many)\s+agents?\s+(?:do\s+)?(?:you|we|i)\s+have/i,
                /^how\s+many\s+agents?\b/i
            ],
            team_members: [
                /what\s+(?:team\s+)?members?\s+(?:do\s+)?(?:you|we|i)\s+have/i,
                /(?:show|list|tell)\s+(?:me\s+)?(?:the\s+)?(?:team\s+)?members/i,
                /who\s+(?:are|is)\s+(?:in|on)\s+(?:the\s+)?team/i
            ]
        };
    }

    /**
     * Check if a message is a simple greeting
     * @param {string} message - The message to check
     * @returns {boolean} True if the message is a simple greeting
     */
    _isSimpleGreeting(message) {
        return this.greetingPatterns.some(pattern => pattern.test(message.trim().toLowerCase()));
    }

    /**
     * Handle simple greetings directly with OpenAI
     * @param {Object} messageData - The message data
     * @returns {Promise<Object>} Formatted response
     */
    async _handleSimpleGreeting(messageData) {
        try {
            const parsedContext = typeof messageData.context === 'string' 
                ? JSON.parse(messageData.context) 
                : messageData.context;

            const startPrompt = parsedContext?.team_config?.start_prompt || '';
            
            const completion = await openai.chat.completions.create({
                model: parsedContext?.conversation_settings?.model || 'gpt-4',
                temperature: parsedContext?.conversation_settings?.temperature || 0.7,
                messages: [
                    {
                        role: 'system',
                        content: `${startPrompt} Please provide a friendly greeting response.`
                    },
                    {
                        role: 'user',
                        content: messageData.content
                    }
                ]
            });

            const response = completion.choices[0]?.message?.content || "Hello! How can I help you today?";

            return {
                content: response,
                status: 'completed',
                metadata: {
                    team_id: parsedContext?.team_id || 'default',
                    processing_time: 0,
                    confidence_score: 1,
                    agent_contributions: [],
                    has_tool_data: false,
                    has_visualization: false
                },
                conversation_id: messageData.sessionId,
                timestamp: new Date().toISOString(),
                tool_data: null,
                visualization_data: null
            };
        } catch (error) {
            logger.error('Error handling simple greeting', error);
            throw error;
        }
    }

    /**
     * Check if a message is asking about system capabilities
     * @param {string} message - The message to check
     * @returns {string|null} The type of system question or null
     */
    _getSystemQuestionType(message) {
        const trimmedMessage = message.trim().toLowerCase();
        
        for (const [type, patterns] of Object.entries(this.systemQuestionPatterns)) {
            if (patterns.some(pattern => pattern.test(trimmedMessage))) {
                return type;
            }
        }
        return null;
    }

    /**
     * Fetch all tools for a team
     * @param {number} teamId - The team ID
     * @returns {Promise<Array>} Array of tools with details
     */
    async _fetchTeamTools(teamId) {
        try {
            // Get team members
            const teamResponse = await axios.get(`${ML_SERVICE_URL}/team/${teamId}/members`);
            
            // If team doesn't exist or has no members, return empty array with message
            if (teamResponse.data.status === 'error' || !teamResponse.data.members || teamResponse.data.members.length === 0) {
                return [{
                    tool_name: 'No Tools Available',
                    tool_type: 'info',
                    description: `No tools found for team ${teamId}. ${teamResponse.data.message || 'The team may not exist or have no members.'}`,
                    agents: []
                }];
            }

            const members = teamResponse.data.members;

            // Get tools for each agent
            const toolsMap = new Map();
            for (const member of members) {
                try {
                    const agentTools = await axios.get(`${ML_SERVICE_URL}/agent/${member.agent_id}/tools`);
                    for (const tool of agentTools.data.tools || []) {
                        if (!toolsMap.has(tool.tool_id)) {
                            try {
                                // Get detailed tool info
                                const toolDetails = await axios.get(`${ML_SERVICE_URL}/tools/${tool.tool_id}`);
                                toolsMap.set(tool.tool_id, {
                                    ...toolDetails.data,
                                    agents: [member.agent_id]
                                });
                            } catch (toolError) {
                                logger.error(`Error fetching details for tool ${tool.tool_id}`, toolError);
                                // Continue with basic tool info if details fetch fails
                                toolsMap.set(tool.tool_id, {
                                    ...tool,
                                    agents: [member.agent_id]
                                });
                            }
                        } else {
                            toolsMap.get(tool.tool_id).agents.push(member.agent_id);
                        }
                    }
                } catch (agentError) {
                    logger.error(`Error fetching tools for agent ${member.agent_id}`, agentError);
                    // Continue with next agent if one fails
                    continue;
                }
            }

            const tools = Array.from(toolsMap.values());
            return tools.length > 0 ? tools : [{
                tool_name: 'No Tools Available',
                tool_type: 'info',
                description: 'No tools found for any team members.',
                agents: []
            }];
        } catch (error) {
            logger.error('Error fetching team tools', error);
            // Return informative message instead of throwing
            return [{
                tool_name: 'Error Fetching Tools',
                tool_type: 'error',
                description: `Failed to fetch tools: ${error.message}. Please try again later or contact support if the issue persists.`,
                agents: []
            }];
        }
    }

    /**
     * Handle system-related questions
     * @param {Object} messageData - The message data
     * @param {string} questionType - The type of system question
     * @returns {Promise<Object>} Formatted response
     */
    async _handleSystemQuestion(messageData, questionType) {
        try {
            const parsedContext = typeof messageData.context === 'string' 
                ? JSON.parse(messageData.context || '{}') 
                : (messageData.context || {});

            const teamId = parsedContext?.team_id;
            let systemInfo = '';
            let toolData = null;

            // Helper function to create response when team context is missing
            const createTeamContextRequiredResponse = (message) => ({
                content: message,
                status: 'completed',
                metadata: {
                    team_id: 'default',
                    processing_time: 0,
                    confidence_score: 1,
                    agent_contributions: [],
                    has_tool_data: false,
                    has_visualization: false
                },
                conversation_id: messageData.sessionId,
                timestamp: new Date().toISOString(),
                tool_data: null,
                visualization_data: null
            });

            // Check if it's a count question
            const isCountQuestion = messageData.content.toLowerCase().startsWith('how many');
            
            if (isCountQuestion) {
                if (questionType === 'tools') {
                    // Hardcoded list of available tools
                    const availableTools = [
                        "GitHub Data Analysis",
                        "Data Visualization",
                        "Dataset Query",
                        "Statistical Analysis",
                        "Data Export"
                    ];
                    systemInfo = `I have ${availableTools.length} main tools available:\n\n` + 
                        availableTools.map(tool => `- ${tool}`).join('\n');
                    return {
                        content: systemInfo,
                        status: 'completed',
                        metadata: {
                            team_id: teamId || 'default',
                            processing_time: 0,
                            confidence_score: 1,
                            agent_contributions: [],
                            has_tool_data: false,
                            has_visualization: false
                        },
                        conversation_id: messageData.sessionId,
                        timestamp: new Date().toISOString(),
                        tool_data: null,
                        visualization_data: null
                    };
                } else if (questionType === 'agents') {
                    const agents = parsedContext?.team_config?.agents || [];
                    systemInfo = `I have ${agents.length} agents in the current team.`;
                    if (agents.length > 0) {
                        systemInfo += '\n\nThey have the following roles:\n' +
                            agents.map(agent => `- Agent ${agent.agent_id}: ${agent.role} (Priority: ${agent.priority})`).join('\n');
                    }
                    return {
                        content: systemInfo,
                        status: 'completed',
                        metadata: {
                            team_id: teamId || 'default',
                            processing_time: 0,
                            confidence_score: 1,
                            agent_contributions: [],
                            has_tool_data: false,
                            has_visualization: false
                        },
                        conversation_id: messageData.sessionId,
                        timestamp: new Date().toISOString(),
                        tool_data: null,
                        visualization_data: null
                    };
                }
            }

            // If not a count question, proceed with existing logic
            if (!teamId && ['tools', 'agents', 'team_members'].includes(questionType)) {
                return createTeamContextRequiredResponse(
                    "I notice you haven't selected a team yet. Please select a team first to see the requested information."
                );
            }

            switch (questionType) {
                case 'tools': {
                    const tools = await this._fetchTeamTools(teamId);
                    toolData = { tools };

                    // Get OpenAI to format the response
                    const completion = await openai.chat.completions.create({
                        model: parsedContext?.conversation_settings?.model || 'gpt-4',
                        temperature: 0.7,
                        messages: [
                            {
                                role: 'system',
                                content: `You are a helpful assistant explaining the available tools. Format the response in markdown with clear sections and code blocks where appropriate. Include a summary visualization of tool types if possible.`
                            },
                            {
                                role: 'user',
                                content: `Please describe these tools and their capabilities: ${JSON.stringify(tools, null, 2)}`
                            }
                        ]
                    });

                    systemInfo = completion.choices[0]?.message?.content || 
                        "I apologize, but I couldn't format the tools information properly.";
                    break;
                }

                case 'capabilities': {
                    // Get OpenAI to format the system capabilities response
                    const completion = await openai.chat.completions.create({
                        model: parsedContext?.conversation_settings?.model || 'gpt-4',
                        temperature: 0.7,
                        messages: [
                            {
                                role: 'system',
                                content: `You are a helpful assistant explaining your capabilities. Format the response in markdown.`
                            },
                            {
                                role: 'user',
                                content: `Please explain what you can do, including: processing chat messages, working with teams of AI agents, using tools, and handling system questions.`
                            }
                        ]
                    });

                    systemInfo = completion.choices[0]?.message?.content || 
                        "I can help you with chat processing, team management, and various tools. Please select a team to see specific capabilities.";
                    break;
                }

                case 'agents': {
                    try {
                        const response = await axios.get(`${ML_SERVICE_URL}/team/${teamId}/members`);
                        const agents = response.data.members || [];

                        // Get OpenAI to format the agents response
                        const completion = await openai.chat.completions.create({
                            model: parsedContext?.conversation_settings?.model || 'gpt-4',
                            temperature: 0.7,
                            messages: [
                                {
                                    role: 'system',
                                    content: `You are a helpful assistant explaining the available agents. Format the response in markdown with clear sections.`
                                },
                                {
                                    role: 'user',
                                    content: `Please describe these agents and their roles: ${JSON.stringify(agents, null, 2)}`
                                }
                            ]
                        });

                        systemInfo = completion.choices[0]?.message?.content || 
                            "I apologize, but I couldn't format the agents information properly.";
                    } catch (error) {
                        systemInfo = "I encountered an error while fetching the agents information. Please try again later.";
                    }
                    break;
                }

                case 'team_members': {
                    try {
                        const response = await axios.get(`${ML_SERVICE_URL}/team/${teamId}/members`);
                        const members = response.data.members || [];

                        // Get OpenAI to format the team members response
                        const completion = await openai.chat.completions.create({
                            model: parsedContext?.conversation_settings?.model || 'gpt-4',
                            temperature: 0.7,
                            messages: [
                                {
                                    role: 'system',
                                    content: `You are a helpful assistant explaining the team members. Format the response in markdown with clear sections.`
                                },
                                {
                                    role: 'user',
                                    content: `Please describe the team members and their roles: ${JSON.stringify(members, null, 2)}`
                                }
                            ]
                        });

                        systemInfo = completion.choices[0]?.message?.content || 
                            "I apologize, but I couldn't format the team members information properly.";
                    } catch (error) {
                        systemInfo = "I encountered an error while fetching the team members information. Please try again later.";
                    }
                    break;
                }

                default: {
                    systemInfo = "I'm not sure how to handle that system question. Please try asking about tools, capabilities, agents, or team members.";
                }
            }

            return {
                content: systemInfo,
                status: 'completed',
                metadata: {
                    team_id: teamId || 'default',
                    processing_time: 0,
                    confidence_score: 1,
                    agent_contributions: [],
                    has_tool_data: !!toolData,
                    has_visualization: toolData?.tools?.some(t => t.tool_type !== 'info')
                },
                conversation_id: messageData.sessionId,
                timestamp: new Date().toISOString(),
                tool_data: toolData,
                visualization_data: toolData?.tools?.some(t => t.tool_type !== 'info') ? {
                    tools: toolData.tools.map(tool => ({
                        name: tool.tool_name,
                        type: tool.tool_type,
                        description: tool.description,
                        agents: tool.agents
                    }))
                } : null
            };
        } catch (error) {
            logger.error('Error handling system question', error);
            // Return a user-friendly error response instead of throwing
            return {
                content: "I apologize, but I encountered an error while processing your request. Please try again later or contact support if the issue persists.",
                status: 'error',
                metadata: {
                    error: error.message,
                    team_id: 'default',
                    processing_time: 0,
                    confidence_score: 0,
                    agent_contributions: [],
                    has_tool_data: false,
                    has_visualization: false
                },
                conversation_id: messageData.sessionId,
                timestamp: new Date().toISOString(),
                tool_data: null,
                visualization_data: null
            };
        }
    }

    /**
     * Process incoming chat message and orchestrate response
     * @param {Object} messageData - The chat message data
     * @param {string} messageData.content - The actual message content
     * @param {string} messageData.userId - ID of the user sending the message
     * @param {string} messageData.sessionId - Chat session ID
     * @param {Object} messageData.context - Additional context (optional)
     */
    async processChatMessage(messageData) {
        try {
            const parsedContext = typeof messageData.context === 'string' 
                ? JSON.parse(messageData.context) 
                : messageData.context;

            logger.info('Processing chat message', {
                userId: messageData.userId,
                sessionId: messageData.sessionId,
                contentLength: messageData.content.length,
                hasContext: !!parsedContext,
                team_id: parsedContext?.team_id,
                use_smart_workflow: parsedContext?.team_config?.use_smart_workflow,
                content: messageData.content
            });

            // Check for simple greeting
            if (this.greetingPatterns.some(pattern => pattern.test(messageData.content))) {
                return this._handleSimpleGreeting(messageData);
            }

            // Check for system questions
            const systemQuestionType = this._getSystemQuestionType(messageData.content);
            if (systemQuestionType) {
                return this._handleSystemQuestion(messageData, systemQuestionType);
            }
            
            // Prepare ML service request
            const mlRequest = {
                content: messageData.content,
                userId: messageData.userId,
                sessionId: messageData.sessionId,
                task_type: parsedContext.task_type || 'general',
                complexity: parsedContext.complexity || 'medium',
                context: {
                    team_id: parsedContext.team_id,
                    team_config: {
                        team_id: parsedContext.team_config.team_id,
                        name: parsedContext.team_config.name,
                        description: parsedContext.team_config.description,
                        members: parsedContext.team_config.members,
                        use_smart_workflow: parsedContext.team_config.use_smart_workflow || false,
                        temperature: parsedContext.team_config.temperature,
                        token_limit: parsedContext.team_config.token_limit,
                        start_prompt: parsedContext.team_config.start_prompt,
                        end_prompt: parsedContext.team_config.end_prompt,
                        style: parsedContext.team_config.style || ''
                    },
                    conversation_settings: parsedContext.conversation_settings || {},
                    conversation_history: parsedContext.conversation_history || [],
                    documents: parsedContext.documents || []
                }
            };

            logger.info('Prepared ML service request', {
                team_id: mlRequest.context.team_id,
                use_smart_workflow: mlRequest.context.team_config.use_smart_workflow,
                content_length: mlRequest.content.length,
                content: mlRequest.content,
                conversation_history_length: mlRequest.context.conversation_history.length,
                has_documents: mlRequest.context.documents.length > 0
            });

            // Send to ML service
            const mlResponse = await this._sendToMLService(mlRequest);
            
            // Process the response based on workflow type
            const processedResponse = await this._processTeamResponse(
                mlResponse, 
                messageData.sessionId,
                mlRequest.context.team_config.use_smart_workflow
            );

            // Log the processed response
            logger.info('Chat message processed successfully', {
                userId: messageData.userId,
                sessionId: messageData.sessionId,
                responseStatus: processedResponse.status,
                workflow_type: mlRequest.context.team_config.use_smart_workflow ? 'smart' : 'standard',
                processing_time: processedResponse.metadata.processing_time,
                response_length: processedResponse.content.length,
                has_tool_data: processedResponse.metadata.has_tool_data,
                has_visualization: processedResponse.metadata.has_visualization,
                agent_contributions: processedResponse.metadata.agent_contributions
            });

            return processedResponse;
        } catch (error) {
            logger.error('Error processing chat message', {
                error: error.message,
                stack: error.stack,
                userId: messageData?.userId,
                sessionId: messageData?.sessionId,
                response: error.response?.data
            });
            throw error;
        }
    }

    // Helper methods for _processTeamResponse
    _appendVisualizationToResponse(response, visualizationData) {
        return response + "\n\nNFL Team Statistics\nAverage scores across different metrics for each NFL team\n\n[VISUALIZATION_DATA]" + 
            JSON.stringify(visualizationData) +
            "[/VISUALIZATION_DATA]";
    }

    _createVisualizationFromRawData(sampleData) {
        const firstItem = sampleData[0];
        const numericKeys = Object.keys(firstItem).filter(key => 
            typeof firstItem[key] === 'number' && key !== 'id'
        );

        if (numericKeys.length > 0) {
            return sampleData.map(item => ({
                name: item.TEAM || item.name || item.id || 'Unknown',
                value: item[numericKeys[0]]
            })).sort((a, b) => b.value - a.value);
        }
        return null;
    }

    _appendToolDataToResponse(response, toolData) {
        let updatedResponse = response + "\n\nHere's a sample of the data from the dataset:\n";
        updatedResponse += JSON.stringify(toolData.sample, null, 2);
        updatedResponse += `\n\nTotal records in dataset: ${toolData.total_records}`;
        if (toolData.schema && toolData.schema.length > 0) {
            updatedResponse += "\nAvailable fields: " + toolData.schema.join(", ");
        }
        return updatedResponse;
    }

    _processAggregatedData(aggregatedData) {
        let response = '';
        if (aggregatedData.llm_responses?.length > 0) {
            response = aggregatedData.llm_responses[0].response || '';
        }
        return response;
    }

    _processTeamResponse(teamResponse, sessionId, isSmartWorkflow) {
        const startTime = Date.now();
        try {
            logger.info('[Orchestrator:processTeamResponse] Starting response processing', {
                sessionId,
                isSmartWorkflow,
                hasTeamResponse: !!teamResponse
            });

            // Validate input
            if (!teamResponse) {
                logger.error('[Orchestrator:processTeamResponse] Team response is null or undefined');
                throw new Error('Team response is null or undefined');
            }

            // Extract result and processing time
            const result = teamResponse.result || teamResponse;
            
            if (!result) {
                logger.error('[Orchestrator:processTeamResponse] Invalid team response structure');
                throw new Error('Invalid team response structure');
            }

            logger.debug('[Orchestrator:processTeamResponse] Processing response structure', {
                hasResults: !!result.results,
                hasAggregatedData: !!result.aggregated_data,
                resultCount: result.results?.length,
                responseStructure: Object.keys(result)
            });

            // Initialize response components
            let finalResponse = '';
            let toolData = null;
            let visualizationData = null;
            let smartWorkflowData = null;

            // Process aggregated data
            if (result.aggregated_data) {
                const aggregatedData = result.aggregated_data;
                
                // Process LLM responses first
                if (aggregatedData.llm_responses?.length > 0) {
                    // Get the most detailed response
                    const sortedResponses = aggregatedData.llm_responses
                        .filter(r => r.response)
                        .sort((a, b) => (b.response?.length || 0) - (a.response?.length || 0));
                    
                    if (sortedResponses.length > 0) {
                        finalResponse = sortedResponses[0].response;
                    }
                }
                
                // Process vector store results
                if (aggregatedData.vector_store) {
                    toolData = {
                        ...toolData,
                        vector_store: {
                            results: aggregatedData.vector_store.results,
                            queries: aggregatedData.vector_store.queries,
                            datasets: aggregatedData.vector_store.datasets
                        }
                    };
                }
                
                // Process raw data
                if (aggregatedData.raw_data) {
                    toolData = {
                        ...toolData,
                        raw_data: {
                            samples: aggregatedData.raw_data.samples,
                            total_records: aggregatedData.raw_data.total_records,
                            schemas: aggregatedData.raw_data.schemas
                        }
                    };
                }
                
                // Process tool results
                if (aggregatedData.tool_results?.length > 0) {
                    toolData = {
                        ...toolData,
                        tool_results: aggregatedData.tool_results
                    };

                    // If no LLM response, try to construct one from tool results
                    if (!finalResponse) {
                        const toolMessages = aggregatedData.tool_results
                            .filter(t => t.result?.message)
                            .map(t => t.result.message)
                            .join('\n');
                        
                        if (toolMessages) {
                            finalResponse = toolMessages;
                        }
                    }

                    // Process visualization from tool results
                    for (const toolResult of aggregatedData.tool_results) {
                        if (toolResult?.result?.aggregation_data?.visualization?.data) {
                            visualizationData = toolResult.result.aggregation_data.visualization.data;
                            finalResponse = this._appendVisualizationToResponse(finalResponse, visualizationData);
                        }
                    }
                }
            }

            // Process individual agent results if no aggregated response
            if (!finalResponse && result.results?.length > 0) {
                for (const agentResult of result.results) {
                    // Add agent response to final response if no aggregated response exists
                    if (agentResult.response?.message) {
                        finalResponse = agentResult.response.message;
                        break;
                    }

                    // Process tool results from individual agents
                    if (agentResult.response?.tool_results) {
                        logger.debug('[Orchestrator:processTeamResponse] Processing agent tool results', {
                            agentId: agentResult.agent_id,
                            toolResultCount: agentResult.response.tool_results.length,
                            hasToolResults: !!agentResult.response.tool_results
                        });

                        // Initialize tool data if not exists
                        if (!toolData) {
                            toolData = { tool_results: [] };
                        }

                        // Add each tool result
                        for (const toolResult of agentResult.response.tool_results) {
                            // Add to tool results array
                            toolData.tool_results.push(toolResult);

                            // If still no response, use tool result message
                            if (!finalResponse && toolResult.result?.message) {
                                finalResponse = toolResult.result.message;
                            }

                            // Process visualization data if present
                            if (toolResult?.result?.aggregation_data?.visualization?.data) {
                                visualizationData = toolResult.result.aggregation_data.visualization.data;
                                finalResponse = this._appendVisualizationToResponse(finalResponse, visualizationData);
                            }
                            // Handle raw data if no visualization
                            else if (toolResult?.result?.aggregation_data?.raw_data) {
                                const rawData = toolResult.result.aggregation_data.raw_data;
                                if (!toolData.raw_data) {
                                    toolData.raw_data = {
                                        samples: [],
                                        total_records: 0,
                                        schemas: []
                                    };
                                }
                                toolData.raw_data.samples.push(...(rawData.sample || []));
                                toolData.raw_data.total_records += (rawData.total_records || 0);
                                if (rawData.schema) {
                                    toolData.raw_data.schemas.push(rawData.schema);
                                }

                                // Try to create visualization from raw data
                                if (!visualizationData && rawData.sample?.length > 0) {
                                    visualizationData = this._createVisualizationFromRawData(rawData.sample);
                                    if (visualizationData) {
                                        finalResponse = this._appendVisualizationToResponse(finalResponse, visualizationData);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Use default message if no response found
            if (!finalResponse) {
                logger.warn('[Orchestrator:processTeamResponse] No response generated, using default message');
                finalResponse = "I apologize, but I couldn't process your request properly.";
            }

            // Append tool data if needed
            if (toolData?.raw_data && !visualizationData) {
                finalResponse = this._appendToolDataToResponse(finalResponse, toolData.raw_data);
            }

            // Create metadata
            const metadata = {
                team_id: result.team_id || 'unknown',
                processing_time: result.execution_summary?.execution_time || 0,
                confidence_score: 1,
                agent_contributions: result.results?.map(r => ({
                    agent_id: r.agent_id || 'unknown',
                    confidence: r.response?.validation_result?.confidence || 0
                })) || [],
                has_tool_data: !!toolData,
                has_visualization: !!visualizationData,
                workflow_type: isSmartWorkflow ? 'smart' : 'standard',
                validation_result: result.validation_result,
                validation_passed: result.validation_passed,
                successful_agents: result.execution_summary?.successful_agents || 0,
                total_agents: result.execution_summary?.total_agents || 0
            };

            const totalProcessingTime = Date.now() - startTime;
            logger.info('[Orchestrator:processTeamResponse] Response processing completed', {
                processingTimeMs: totalProcessingTime,
                responseLength: finalResponse.length,
                hasToolData: !!toolData,
                hasVisualization: !!visualizationData,
                hasSmartWorkflowData: !!smartWorkflowData,
                workflowType: isSmartWorkflow ? 'smart' : 'standard',
                toolResultsCount: toolData?.tool_results?.length || 0
            });

            return {
                content: finalResponse,
                status: result.final_status || 'completed',
                metadata,
                conversation_id: sessionId,
                timestamp: new Date().toISOString(),
                tool_data: toolData,
                visualization_data: visualizationData,
                smart_workflow_data: smartWorkflowData
            };

        } catch (error) {
            const processingTime = Date.now() - startTime;
            logger.error('[Orchestrator:processTeamResponse] Error processing team response', {
                error: error.message,
                stack: error.stack,
                processingTimeMs: processingTime,
                sessionId,
                isSmartWorkflow
            });
            throw new Error('Failed to process team response: ' + error.message);
        }
    }

    _appendSmartWorkflowDetails(response, smartWorkflowData) {
        if (!smartWorkflowData) return response;

        let details = '\n\nTask Execution Details:';
        
        if (smartWorkflowData.execution_metrics) {
            const metrics = smartWorkflowData.execution_metrics;
            details += `\n- Execution Time: ${metrics.execution_time.toFixed(2)}s`;
            details += `\n- Success Rate: ${metrics.success_rate.toFixed(1)}%`;
            details += `\n- Agents: ${metrics.successful_agents}/${metrics.total_agents} successful`;
        }

        if (smartWorkflowData.task_decomposition?.subtasks?.length > 0) {
            details += '\n\nTask was broken down into:';
            smartWorkflowData.task_decomposition.subtasks.forEach((subtask, index) => {
                details += `\n${index + 1}. ${subtask.description || subtask.type}`;
            });
        }

        return response + details;
    }

    /**
     * Get conversation history for a session
     * @param {string} sessionId - Chat session ID
     * @returns {Promise<Array>} Conversation history
     */
    async getConversationHistory(sessionId) {
        try {
            // Get team history from ML service
            const response = await axios.get(`${ML_SERVICE_URL}/conversation/history`, {
                params: { session_id: sessionId }
            });

            return response.data.history;
        } catch (error) {
            logger.error(`[Orchestrator] Error fetching conversation history: ${error.message}`);
            throw new Error(`Failed to fetch conversation history: ${error.message}`);
        }
    }

    /**
     * Send request to ML service
     * @param {Object} mlRequest - Request data for ML service
     * @returns {Promise<Object>} ML service response
     * @private
     */
    async _sendToMLService(mlRequest) {
        try {
            // Log full request details
            logger.info('Sending request to ML service - Full Details', {
                request: {
                    content: mlRequest.content,
                    userId: mlRequest.userId,
                    sessionId: mlRequest.sessionId,
                    task_type: mlRequest.task_type || 'general',
                    complexity: mlRequest.complexity || 'medium',
                    context: {
                        team_id: mlRequest.context.team_id,
                        team_config: {
                            team_id: mlRequest.context.team_config.team_id,
                            name: mlRequest.context.team_config.name,
                            description: mlRequest.context.team_config.description,
                            use_smart_workflow: mlRequest.context.team_config.use_smart_workflow,
                            temperature: mlRequest.context.team_config.temperature,
                            token_limit: mlRequest.context.team_config.token_limit,
                            start_prompt: mlRequest.context.team_config.start_prompt,
                            end_prompt: mlRequest.context.team_config.end_prompt,
                            style: mlRequest.context.team_config.style,
                            members: mlRequest.context.team_config.members
                        },
                        conversation_settings: mlRequest.context.conversation_settings,
                        conversation_history_length: mlRequest.context.conversation_history?.length || 0,
                        documents_count: mlRequest.context.documents?.length || 0
                    }
                }
            });
            
            const startTime = Date.now();
            const response = await axios.post(`${ML_SERVICE_URL}/team/execute`, {
                ...mlRequest,
                task_type: mlRequest.task_type || 'general',
                complexity: mlRequest.complexity || 'medium'
            });
            const processingTime = Date.now() - startTime;
            
            // Log full response details
            logger.info('Received response from ML service - Full Details', {
                response: {
                    processingTimeMs: processingTime,
                    status: response.status,
                    data: {
                        task_id: response.data?.task_id,
                        team_id: response.data?.team_id,
                        status: response.data?.status,
                        final_status: response.data?.final_status,
                        workflow_type: response.data?.workflow_type,
                        execution_summary: response.data?.execution_summary,
                        validation_result: response.data?.validation_result,
                        aggregated_data: response.data?.aggregated_data,
                        results: response.data?.results?.map(r => ({
                            agent_id: r.agent_id,
                            status: r.status,
                            response: {
                                content: r.response?.content,
                                tool_results: r.response?.tool_results,
                                validation_result: r.response?.validation_result,
                                metadata: r.response?.metadata
                            }
                        }))
                    }
                }
            });

            // Keep the original summary log for quick reference
            logger.info('ML Service Request Summary', {
                team_id: mlRequest.context.team_id,
                use_smart_workflow: mlRequest.context.team_config.use_smart_workflow,
                request_type: 'team_execute',
                content: mlRequest.content,
                userId: mlRequest.userId,
                sessionId: mlRequest.sessionId
            });

            logger.info('ML Service Response Summary', {
                processingTimeMs: processingTime,
                responseStatus: response.status,
                hasData: !!response.data,
                workflow_type: mlRequest.context.team_config.use_smart_workflow ? 'smart' : 'standard',
                response_type: response.data?.type || 'unknown',
                task_id: response.data?.task_id,
                team_id: response.data?.team_id,
                status: response.data?.status,
                final_status: response.data?.final_status
            });

            return response.data;
        } catch (error) {
            logger.error('Error communicating with ML service', {
                error: error.message,
                stack: error.stack,
                request: {
                    content: mlRequest.content,
                    sessionId: mlRequest.sessionId,
                    team_id: mlRequest.context.team_id,
                    use_smart_workflow: mlRequest.context.team_config.use_smart_workflow
                },
                response: error.response?.data
            });
            throw error;
        }
    }

    /**
     * Store conversation history
     * @param {Object} messageData - Original message data
     * @param {Object} processedResponse - Processed response data
     * @private
     */
    async _storeConversationHistory(messageData, processedResponse) {
        await axios.post(`${ML_SERVICE_URL}/conversation/store`, {
            conversation_id: messageData.sessionId,
            content: {
                user_message: messageData.content,
                bot_response: processedResponse.content,
                timestamp: new Date().toISOString()
            },
            metadata: {
                team_id: processedResponse.metadata.team_id,
                processing_time: processedResponse.metadata.processing_time,
                confidence_score: processedResponse.metadata.confidence_score,
                agent_contributions: processedResponse.metadata.agent_contributions
            }
        });
    }
}

module.exports = new OrchestratorService(); 