import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import useResizeObserver from 'use-resize-observer';
import type { RefObject } from 'react';

export interface AgentNode {
  id: string | number;
  name: string;
}

export interface AgentHierarchyGraphProps {
  agents: AgentNode[];
}

const AgentHierarchyGraph: React.FC<AgentHierarchyGraphProps> = ({ agents }) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { width = 400, height = 300 } = useResizeObserver({ ref: containerRef as RefObject<Element> });

  useEffect(() => {
    if (!svgRef.current || agents.length === 0 || !width || !height) return;

    const nodeRadius = 28;

    // Clear previous SVG
    d3.select(svgRef.current).selectAll('*').remove();

    type NodeType = {
      id: string | number;
      name: string;
      index: number;
      x?: number;
      y?: number;
      fx?: number | null;
      fy?: number | null;
    };

    type LinkType = { source: string | number; target: string | number };

    const nodes: NodeType[] = agents.map((a, i) => ({ ...a, index: i }));
    const links: LinkType[] = agents.slice(0, -1).map((_, i) => ({
      source: agents[i].id,
      target: agents[i + 1].id,
    }));

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id((d: any) => d.id).distance(90))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const svg = d3.select(svgRef.current)
        .attr('width', width)
        .attr('height', height);

    // Arrow marker
    svg.append('defs').append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 18)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#1976d2');

    // Draw links
    const link = svg.append('g')
        .attr('stroke', '#1976d2')
        .attr('stroke-width', 2)
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('marker-end', 'url(#arrow)');

    // Draw nodes
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

    node.append('circle')
        .attr('r', nodeRadius)
        .attr('fill', '#fff')
        .attr('stroke', '#1976d2')
        .attr('stroke-width', 3);

    node.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', 14)
        .attr('fill', '#1976d2')
        .attr('dy', 5)
        .text(d => d.name);

    simulation.on('tick', () => {
      link
          .attr('x1', d => typeof d.source === 'object' ? (d.source as NodeType).x! : nodes.find(n => n.id === d.source)!.x!)
          .attr('y1', d => typeof d.source === 'object' ? (d.source as NodeType).y! : nodes.find(n => n.id === d.source)!.y!)
          .attr('x2', d => typeof d.target === 'object' ? (d.target as NodeType).x! : nodes.find(n => n.id === d.target)!.x!)
          .attr('y2', d => typeof d.target === 'object' ? (d.target as NodeType).y! : nodes.find(n => n.id === d.target)!.y!);

      node
          .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [agents, width, height]);

  return (
      <div ref={containerRef} style={{ width: '100%', height: 320 }}>
        <svg ref={svgRef} style={{ display: 'block', width: '100%', height: '100%' }} />
      </div>
  );
};

export default AgentHierarchyGraph;
