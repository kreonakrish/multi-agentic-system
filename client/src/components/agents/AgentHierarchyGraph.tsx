import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Agent extends d3.SimulationNodeDatum {
  id: number;
  name: string;
  priority: number;
  accuracy: number;
  success: number;
}

interface AgentHierarchyGraphProps {
  agents: Agent[];
  onEdgeClick: (sourceId: number, targetId: number) => void;
  onBackgroundClick: () => void;
}

const AgentHierarchyGraph: React.FC<AgentHierarchyGraphProps> = ({
  agents,
  onEdgeClick,
  onBackgroundClick
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !agents.length) return;

    // Clear previous graph
    d3.select(svgRef.current).selectAll('*').remove();

    // Setup dimensions
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;
    const margin = { top: 40, right: 40, bottom: 40, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .on('click', onBackgroundClick);

    // Group agents by priority
    const agentsByPriority = d3.group(agents, d => d.priority);
    const priorities = Array.from(agentsByPriority.keys()).sort((a, b) => a - b);
    
    // Calculate vertical spacing
    const levelHeight = innerHeight / (priorities.length || 1);

    // Create links data based on agent priorities - only connect to next level
    const links = priorities.flatMap((currentPriority, index) => {
      if (index === priorities.length - 1) return []; // Skip last priority level

      const currentLevelAgents = agentsByPriority.get(currentPriority) || [];
      
      // Find the next non-empty priority level
      let nextPriorityIndex = index + 1;
      while (nextPriorityIndex < priorities.length) {
        const nextPriority = priorities[nextPriorityIndex];
        const nextLevelAgents = agentsByPriority.get(nextPriority) || [];
        
        if (nextLevelAgents.length > 0) {
          // Connect current level agents to next level agents
          return currentLevelAgents.flatMap(source =>
            nextLevelAgents.map(target => ({
              source: source.id,
              target: target.id,
              value: 1,
              sourceLevel: currentPriority,
              targetLevel: nextPriority
            }))
          );
        }
        nextPriorityIndex++;
      }
      return [];
    });

    // Create force simulation with adjusted parameters
    const simulation = d3.forceSimulation<Agent>(agents)
      .force('link', d3.forceLink<Agent, d3.SimulationLinkDatum<Agent>>(links)
        .id(d => d.id)
        .distance(100))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('x', d3.forceX<Agent>(d => {
        // Spread nodes horizontally within their priority level
        const priorityGroup = agents.filter(a => a.priority === d.priority);
        const index = priorityGroup.indexOf(d);
        const groupSize = priorityGroup.length;
        const section = innerWidth / (groupSize + 1);
        return margin.left + section * (index + 1);
      }).strength(0.5))
      .force('y', d3.forceY<Agent>(d => {
        // Position nodes vertically based on priority
        const priorityIndex = priorities.indexOf(d.priority);
        return margin.top + levelHeight * priorityIndex;
      }).strength(1))
      .force('collision', d3.forceCollide().radius(40))
      .alphaDecay(0.0005) // Decrease alphaDecay to slow cooling
      .velocityDecay(0.6); // Increase velocityDecay for more friction

    // Add links with curved paths
    const link = svg.append('g')
      .selectAll('path')
      .data(links)
      .join('path')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2)
      .attr('fill', 'none')
      .attr('marker-end', 'url(#arrow)')
      .style('cursor', 'pointer')
      .on('click', (event, d: any) => {
        event.stopPropagation();
        onEdgeClick(d.source.id, d.target.id);
      });

    // Add arrow marker definition
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('fill', '#999')
      .attr('d', 'M0,-5L10,0L0,5');

    // Add nodes
    const node = svg.append('g')
      .selectAll<SVGGElement, Agent>('g')
      .data(agents)
      .join('g')
      .call(d3.drag<SVGGElement, Agent>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add circles for nodes
    node.append('circle')
      .attr('r', 20)
      .attr('fill', (d) => {
        const hue = (d.accuracy * 120) / 100; // 0 = red, 120 = green
        return `hsl(${hue}, 70%, 50%)`;
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // Add labels
    node.append('text')
      .text(d => d.name)
      .attr('x', 0)
      .attr('y', -25)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('fill', '#333');

    // Add priority labels
    node.append('text')
      .text(d => `Priority: ${d.priority}`)
      .attr('x', 0)
      .attr('y', 25)
      .attr('text-anchor', 'middle')
      .style('font-size', '10px')
      .style('fill', '#666');

    // Update the tick function to use curved paths
    simulation.on('tick', () => {
      link.attr('d', (d: any) => {
        const sourceX = d.source.x;
        const sourceY = d.source.y;
        const targetX = d.target.x;
        const targetY = d.target.y;
        
        // Calculate control point for the curve
        const midY = (sourceY + targetY) / 2;
        
        return `M${sourceX},${sourceY}
                C${sourceX},${midY}
                 ${targetX},${midY}
                 ${targetX},${targetY}`;
      });

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event: d3.D3DragEvent<SVGGElement, Agent, Agent>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, Agent, Agent>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGGElement, Agent, Agent>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [agents, onEdgeClick, onBackgroundClick]);

  return (
    <svg
      ref={svgRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '400px',
        background: '#fafafa',
        borderRadius: '4px'
      }}
    />
  );
};

export default AgentHierarchyGraph; 