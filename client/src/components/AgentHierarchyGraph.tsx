import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import useResizeObserver from 'use-resize-observer';

export interface AgentNode {
  id: string | number;
  name: string;
  priority?: number;
  accuracy?: number;
  success?: number;
}

export interface AgentHierarchyGraphProps {
  agents: AgentNode[];
  onEdgeClick?: (sourceId: number, targetId: number) => void;
  onBackgroundClick?: () => void;
  selectedAgents: string[];
}

const AgentHierarchyGraph: React.FC<AgentHierarchyGraphProps> = ({ agents, onEdgeClick, onBackgroundClick, selectedAgents }) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null!);
  const { width = 400, height = 300 } = useResizeObserver<HTMLDivElement>({ ref: containerRef });

  useEffect(() => {
    if (!svgRef.current || agents.length === 0 || !width || !height) return;

    const nodeRadius = 28;
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
        .attr('width', width)
        .attr('height', height)
        .on('click', (event) => {
          // Only trigger if clicking directly on the SVG background
          if (event.target === svgRef.current && onBackgroundClick) {
            onBackgroundClick();
          }
        });

    // Add VIBGYOR color scale
    const getVIBGYORColor = (value: number) => {
      // VIBGYOR colors from highest (100) to lowest (0)
      const colors = [
        '#8F00FF', // Violet (100)
        '#4B0082', // Indigo (85)
        '#0000FF', // Blue (70)
        '#00FF00', // Green (55)
        '#FFFF00', // Yellow (40)
        '#FF7F00', // Orange (25)
        '#FF0000'  // Red (0)
      ];
      
      const index = Math.floor((1 - value / 100) * (colors.length - 1));
      return colors[Math.min(Math.max(index, 0), colors.length - 1)];
    };

    type NodeType = {
      id: string | number;
      name: string;
      priority?: number;
      accuracy?: number;
      success?: number;
      index?: number;
      x?: number;
      y?: number;
      fx?: number | null;
      fy?: number | null;
      level?: number;
    };
    
    type LinkType = { 
      source: NodeType | string | number; 
      target: NodeType | string | number; 
      priority?: number;
      sourceLevel?: number;
      targetLevel?: number;
    };

    // Group agents by priority
    const agentsByPriority = agents.reduce((acc, agent) => {
      const priority = agent.priority || 1;
      if (!acc[priority]) acc[priority] = [];
      acc[priority].push(agent);
      return acc;
    }, {} as Record<number, AgentNode[]>);

    // Sort priorities in ascending order (lower number = higher priority)
    const priorityLevels = Object.keys(agentsByPriority)
      .map(Number)
      .sort((a, b) => a - b);

    // Create nodes with level information
    const nodes: NodeType[] = agents.map((agent, i) => ({
      ...agent,
      index: i,
      level: agent.priority || 1
    }));

    // Create links between priority levels
    const links: LinkType[] = [];
    priorityLevels.forEach((currentPriority, idx) => {
      if (idx === priorityLevels.length - 1) return; // Skip last level
      
      const currentLevelAgents = agentsByPriority[currentPriority];
      
      // Find all agents with higher priority levels (next levels)
      const higherPriorityLevels = priorityLevels.slice(idx + 1);
      
      // Connect current level agents to all agents in next immediate level
      currentLevelAgents.forEach(sourceAgent => {
        // Find the next immediate priority level that has agents
        const nextPriorityLevel = higherPriorityLevels.find(level => 
          agentsByPriority[level] && agentsByPriority[level].length > 0
        );
        
        if (nextPriorityLevel) {
          // Connect to all agents in the next priority level
          agentsByPriority[nextPriorityLevel].forEach(targetAgent => {
            links.push({
              source: sourceAgent.id,
              target: targetAgent.id,
              priority: targetAgent.priority,
              sourceLevel: currentPriority,
              targetLevel: nextPriorityLevel
            });
          });
        }
      });
    });

    // Log the created links for debugging
    console.log('Created links:', links);
    console.log('Agents by priority:', agentsByPriority);
    console.log('Priority levels:', priorityLevels);

    // Create force simulation with custom forces
    const simulation = d3.forceSimulation<NodeType>(nodes)
        .force('link', d3.forceLink<NodeType, LinkType>(links).id((d) => d.id).distance(180))
        .force('charge', d3.forceManyBody<NodeType>().strength(-500))
        .force('center', d3.forceCenter<NodeType>(width / 2, height / 2))
        .force('y', d3.forceY<NodeType>().strength(0.3).y((d) => {
          const level = d.level || 1;
          const levelCount = priorityLevels.length;
          return (level / (levelCount + 1)) * height;
        }))
        .force('x', d3.forceX<NodeType>().strength(0.2).x((d) => {
          const sameLevel = nodes.filter(n => n.level === d.level);
          const idx = sameLevel.findIndex(n => n.id === d.id);
          const count = sameLevel.length;
          return width * (0.2 + (idx + 0.5) / (count + 1) * 0.6);
        }));

    // Add arrow marker for directed edges
    svg.append('defs').selectAll('marker')
        .data(['end'])
        .enter()
        .append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -2.5 5 5')
        .attr('refX', 28)
        .attr('refY', 0)
        .attr('markerWidth', 3)
        .attr('markerHeight', 3)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-2.5L5,0L0,2.5')
        .attr('fill', '#666');

    // Create tooltip
    let tooltip: d3.Selection<HTMLDivElement, unknown, null, undefined> | null = null;
    if (containerRef.current) {
      d3.select(containerRef.current).selectAll('.d3-tooltip').remove();
      tooltip = d3.select(containerRef.current)
          .append('div')
          .attr('class', 'd3-tooltip')
          .style('position', 'absolute')
          .style('background', '#fff')
          .style('border', '1px solid #1976d2')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('pointer-events', 'none')
          .style('font-size', '12px')
          .style('color', '#1976d2')
          .style('display', 'none')
          .style('z-index', '999')
          .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)');
    }

    // Create links with updated styling
    const link = svg.append('g')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('marker-end', 'url(#arrow)')
        .attr('stroke-opacity', 0.8)
        .attr('stroke', (d: LinkType) => {
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const sourceNode = nodes.find(n => n.id === sourceId);
          if (!sourceNode) return '#1976d2';
          const accuracy = sourceNode.accuracy || 100;
          const success = sourceNode.success || 100;
          const combinedValue = (accuracy + success) / 2;
          console.log(`Edge color for ${sourceNode.name}: Combined value = ${combinedValue}, Color = ${getVIBGYORColor(combinedValue)}`);
          return getVIBGYORColor(combinedValue);
        })
        .attr('stroke-width', (d: LinkType) => {
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          const isSelected = selectedAgents.includes(sourceId.toString()) && selectedAgents.includes(targetId.toString());
          return isSelected ? 3 : 1.5;
        })
        .style('cursor', 'pointer')
        .on('click', (event: MouseEvent, d: LinkType) => {
          event.stopPropagation();
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          if (onEdgeClick) {
            onEdgeClick(Number(sourceId), Number(targetId));
          }
        })
        .on('mouseover', (event: MouseEvent, d: LinkType) => {
          if (!tooltip) return;
          tooltip.style('display', 'block');
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          const sourceNode = nodes.find(n => n.id === sourceId);
          const targetNode = nodes.find(n => n.id === targetId);
          tooltip.html(`
            <div>From: ${sourceNode?.name}</div>
            <div>To: ${targetNode?.name}</div>
            <div style="font-size: 10px; margin-top: 4px;">Click to view interactions</div>
          `);
          tooltip
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', () => {
          if (!tooltip) return;
          tooltip.style('display', 'none');
        });

    // Create nodes
    const node = svg.append('g')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .call(d3.drag<any, NodeType>()
            .on('start', (event, d) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on('drag', (event, d) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on('end', (event, d) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            })
        );

    // Add circles for nodes
    node.append('circle')
        .attr('r', nodeRadius)
        .attr('fill', d => selectedAgents.includes(d.name) ? '#4CAF50' : '#fff')
        .attr('stroke', '#1976d2')
        .attr('stroke-width', 3);

    // Add text labels
    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', 12)
        .attr('fill', '#1976d2')
        .attr('dy', -18)
        .text(d => d.name);

    // Add priority labels
    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', 10)
        .attr('fill', '#666')
        .attr('dy', 18)
        .text(d => `P: ${d.priority || 1}`);

    // Update positions on each tick
    simulation.on('tick', () => {
      link
          .attr('x1', d => {
            const sourceNode = typeof d.source === 'object' ? d.source : nodes.find(n => n.id === d.source);
            return sourceNode && sourceNode.x != null ? sourceNode.x : 0;
          })
          .attr('y1', d => {
            const sourceNode = typeof d.source === 'object' ? d.source : nodes.find(n => n.id === d.source);
            return sourceNode && sourceNode.y != null ? sourceNode.y : 0;
          })
          .attr('x2', d => {
            const targetNode = typeof d.target === 'object' ? d.target : nodes.find(n => n.id === d.target);
            return targetNode && targetNode.x != null ? targetNode.x : 0;
          })
          .attr('y2', d => {
            const targetNode = typeof d.target === 'object' ? d.target : nodes.find(n => n.id === d.target);
            return targetNode && targetNode.y != null ? targetNode.y : 0;
          });

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
      if (tooltip) tooltip.remove();
    };
  }, [agents, width, height, onEdgeClick, onBackgroundClick, selectedAgents]);

  return (
      <div ref={containerRef} style={{ width: '100%', height: 400, position: 'relative' }}>
        <svg ref={svgRef} style={{ display: 'block', width: '100%', height: '100%' }} />
      </div>
  );
};

export default AgentHierarchyGraph;
