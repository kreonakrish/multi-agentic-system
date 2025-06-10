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
        const startTime = Date.now();
        try {
            // Log received message
            logger.orchestrator.messageReceived(
                messageData.userId,
                messageData.sessionId,
                messageData.content,
                messageData.context
            );

            // Check if it's a simple greeting
            if (this._isSimpleGreeting(messageData.content)) {
                logger.info('Detected simple greeting, handling directly with OpenAI');
                const response = await this._handleSimpleGreeting(messageData);
                
                // Store conversation history
                await this._storeConversationHistory(messageData, response);
                
                return response;
            }

            // Check if it's a system question
            const systemQuestionType = this._getSystemQuestionType(messageData.content);
            if (systemQuestionType) {
                logger.info(`Detected system question of type: ${systemQuestionType}`);
                const response = await this._handleSystemQuestion(messageData, systemQuestionType);
                await this._storeConversationHistory(messageData, response);
                return response;
            }

            // Validate input
            logger.debug('Validating input data', {
                hasContent: !!messageData.content,
                hasUserId: !!messageData.userId,
                hasSessionId: !!messageData.sessionId,
                hasContext: !!messageData.context
            });

            // Parse context if it's a string
            let parsedContext = typeof messageData.context === 'string' 
                ? JSON.parse(messageData.context) 
                : messageData.context;

            // Prepare ML request
            logger.info('Preparing ML service request');
            const mlRequest = {
                content: messageData.content,
                userId: messageData.userId,
                sessionId: messageData.sessionId,
                context: {
                    team_id: parsedContext.team_id,
                    team_config: {
                        team_id: parsedContext.team_config.team_id,
                        name: parsedContext.team_config.name,
                        description: parsedContext.team_config.description,
                        members: parsedContext.team_config.members,
                        temperature: parsedContext.team_config.temperature,
                        token_limit: parsedContext.team_config.token_limit,
                        start_prompt: parsedContext.team_config.start_prompt,
                        end_prompt: parsedContext.team_config.end_prompt,
                        style: parsedContext.team_config.style || ''
                    },
                    conversation_settings: {
                        temperature: parsedContext.conversation_settings.temperature,
                        tokenLimit: parsedContext.conversation_settings.tokenLimit,
                        startPrompt: parsedContext.conversation_settings.startPrompt,
                        endPrompt: parsedContext.conversation_settings.endPrompt,
                        style: parsedContext.conversation_settings.style,
                        start_prompt: parsedContext.conversation_settings.start_prompt || '',
                        system_prompt: parsedContext.conversation_settings.system_prompt || '',
                        max_tokens: parsedContext.conversation_settings.max_tokens || 2000,
                        model: parsedContext.conversation_settings.model || 'gpt-4'
                    },
                    conversation_history: parsedContext.conversation_history || [],
                    documents: parsedContext.documents || []
                }
            };

            // Send to ML service
            const mlResponse = await this._sendToMLService(mlRequest);
            
            // Process the response
            const processedResponse = await this._processTeamResponse(mlResponse, messageData.sessionId);

            // Log the processed response
            logger.orchestrator.messageSent(
                messageData.userId,
                messageData.sessionId,
                processedResponse
            );

            // Store conversation history
            try {
                const historyStartTime = Date.now();
                await this._storeConversationHistory(messageData, processedResponse);
                logger.info('Conversation history stored', {
                    storageTimeMs: Date.now() - historyStartTime
                });
            } catch (storeError) {
                logger.orchestrator.error('Error storing conversation history', storeError, {
                    sessionId: messageData.sessionId
                });
            }

            logger.info('Processing completed successfully', {
                totalProcessingTimeMs: Date.now() - startTime
            });

            return processedResponse;
        } catch (error) {
            logger.orchestrator.error('Error processing chat message', error, {
                userId: messageData?.userId,
                sessionId: messageData?.sessionId
            });
            throw error;
        }
    }

    /**
     * Process and format team response for chat
     * @param {Object} teamResponse - Raw response from team service
     * @param {string} sessionId - Chat session ID
     * @returns {Object} Formatted chat response
     */
    _processTeamResponse(teamResponse, sessionId) {
        const startTime = Date.now();
        try {
            logger.info('[Orchestrator:processTeamResponse] Starting response processing', {
                sessionId,
                hasTeamResponse: !!teamResponse
            });

            // Validate input
            if (!teamResponse) {
                logger.error('[Orchestrator:processTeamResponse] Team response is null or undefined');
                throw new Error('Team response is null or undefined');
            }

            // Extract result and processing time
            logger.debug('[Orchestrator:processTeamResponse] Extracting base response data');
            const result = teamResponse.result || teamResponse;
            const processing_time_seconds = teamResponse.processing_time_seconds || 0;
            
            if (!result) {
                logger.error('[Orchestrator:processTeamResponse] Invalid team response structure');
                throw new Error('Invalid team response structure');
            }

            logger.debug('[Orchestrator:processTeamResponse] Base response data extracted', {
                hasResult: !!result,
                processingTime: processing_time_seconds
            });

            // Initialize response variables
            let finalResponse = '';
            let toolData = null;
            let visualizationData = null;

            // Process results array
            logger.info('[Orchestrator:processTeamResponse] Processing agent results');
            if (result.results && Array.isArray(result.results)) {
                logger.debug('[Orchestrator:processTeamResponse] Found results array', {
                    resultsCount: result.results.length
                });

                for (const agentResult of result.results) {
                    logger.debug('[Orchestrator:processTeamResponse] Processing agent result', {
                        agentId: agentResult?.agent_id,
                        hasResponse: !!agentResult?.response?.message,
                        hasToolResults: !!agentResult?.response?.tool_results
                    });

                    if (agentResult?.response?.message) {
                        finalResponse = agentResult.response.message;
                        
                        // Process tool results
                        if (agentResult.response.tool_results?.length > 0) {
                            logger.info('[Orchestrator:processTeamResponse] Processing tool results');
                            const toolResult = agentResult.response.tool_results[0];
                            
                            if (toolResult?.result?.aggregation_data) {
                                logger.debug('[Orchestrator:processTeamResponse] Processing aggregation data');
                                const aggregationData = toolResult.result.aggregation_data;
                                
                                // Handle raw data
                                if (aggregationData.raw_data) {
                                    logger.debug('[Orchestrator:processTeamResponse] Processing raw data');
                                    const rawData = aggregationData.raw_data;
                                    toolData = {
                                        sample: rawData.sample || [],
                                        total_records: rawData.total_records || 0,
                                        schema: rawData.schema || []
                                    };
                                }

                                // Handle visualization data
                                if (aggregationData.visualization) {
                                    logger.debug('[Orchestrator:processTeamResponse] Processing visualization data');
                                    visualizationData = aggregationData.visualization.data;
                                    finalResponse = this._appendVisualizationToResponse(finalResponse, visualizationData);
                                }
                                // Create visualization from raw data if needed
                                else if (toolData?.sample && toolData.sample.length > 0) {
                                    logger.debug('[Orchestrator:processTeamResponse] Creating visualization from raw data');
                                    visualizationData = this._createVisualizationFromRawData(toolData.sample);
                                    if (visualizationData) {
                                        finalResponse = this._appendVisualizationToResponse(finalResponse, visualizationData);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Process aggregated data if needed
            if (!finalResponse && result.aggregated_data) {
                logger.info('[Orchestrator:processTeamResponse] Processing aggregated data');
                finalResponse = this._processAggregatedData(result.aggregated_data);
            }

            // Use default message if no response found
            if (!finalResponse) {
                logger.warn('[Orchestrator:processTeamResponse] No response generated, using default message');
                finalResponse = "I apologize, but I couldn't process your request properly.";
            }

            // Append tool data if needed
            if (toolData && !visualizationData) {
                logger.debug('[Orchestrator:processTeamResponse] Appending raw tool data to response');
                finalResponse = this._appendToolDataToResponse(finalResponse, toolData);
            }

            // Create metadata
            logger.info('[Orchestrator:processTeamResponse] Creating response metadata');
            const metadata = {
                team_id: result.team_id || 'unknown',
                processing_time: processing_time_seconds,
                confidence_score: 1,
                agent_contributions: (result.results || []).map(r => ({
                    agent_id: r?.agent_id || 'unknown',
                    confidence: r?.result?.validation_results?.confidence || 0
                })),
                has_tool_data: !!toolData,
                has_visualization: !!visualizationData
            };

            const totalProcessingTime = Date.now() - startTime;
            logger.info('[Orchestrator:processTeamResponse] Response processing completed', {
                processingTimeMs: totalProcessingTime,
                responseLength: finalResponse.length,
                hasToolData: !!toolData,
                hasVisualization: !!visualizationData
            });

            return {
                content: finalResponse,
                status: result.final_status || 'completed',
                metadata,
                conversation_id: sessionId,
                timestamp: new Date().toISOString(),
                tool_data: toolData,
                visualization_data: visualizationData
            };

        } catch (error) {
            const processingTime = Date.now() - startTime;
            logger.error('[Orchestrator:processTeamResponse] Error processing team response', {
                error: error.message,
                stack: error.stack,
                processingTimeMs: processingTime,
                sessionId
            });
            logger.error('[Orchestrator:processTeamResponse] Team response was:', 
                JSON.stringify(teamResponse, null, 2)
            );
            throw new Error('Failed to process team response: ' + error.message);
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
            logger.info('Sending request to ML service');
            const startTime = Date.now();
            
            const response = await axios.post(`${ML_SERVICE_URL}/team/execute`, mlRequest);
            
            logger.info('Received response from ML service', {
                processingTimeMs: Date.now() - startTime,
                responseStatus: response.status,
                hasData: !!response.data
            });

            return response.data;
        } catch (error) {
            logger.orchestrator.error('Error communicating with ML service', error, {
                requestContent: mlRequest.content,
                sessionId: mlRequest.session_id
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