import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import { ZoomIn, ZoomOut, Maximize2, Info } from 'lucide-react'
import type { PathGraph, GraphNode, GraphEdge } from '@/types'
import { domainGraphColors } from '@/utils/helpers'
import { useStore } from '@/store/useStore'

interface Props {
  graph: PathGraph
  onNodeClick?: (node: GraphNode) => void
}

const SEVERITY_STROKE: Record<string, string> = {
  critical: '#F87171',
  major:    '#F5A623',
  minor:    '#38A0F5',
  none:     '#D8DCE8',
}

export default function SkillGraphD3({ graph, onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{ node: GraphNode; x: number; y: number } | null>(null)
  const { selectedModuleId } = useStore()

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return
    if (!graph.nodes.length) return

    const container = containerRef.current
    const W = container.clientWidth
    const H = container.clientHeight || 520

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', W).attr('height', H)

    // ── Defs: arrowhead marker ───────────────────────────────────────────────
    const defs = svg.append('defs')
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#D8DCE8')

    // ── Zoom behaviour ───────────────────────────────────────────────────────
    const zoomG = svg.append('g')
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        zoomG.attr('transform', event.transform)
      })
    svg.call(zoom)

    // Initial zoom to fit
    const initialScale = 0.85
    svg.call(
      zoom.transform,
      d3.zoomIdentity
        .translate(W / 2, H / 2)
        .scale(initialScale)
        .translate(-W / 2, -H / 2)
    )

    // ── Force simulation ─────────────────────────────────────────────────────
    const nodes: d3.SimulationNodeDatum[] = graph.nodes.map(n => ({
      ...n,
      x: W / 2 + (Math.random() - 0.5) * 300,
      y: H / 2 + (Math.random() - 0.5) * 300,
    }))

    const nodeById = new Map(nodes.map(n => [(n as any).id, n]))

    const links: d3.SimulationLinkDatum<d3.SimulationNodeDatum>[] = graph.edges
      .map(e => ({
        source: nodeById.get(e.source)!,
        target: nodeById.get(e.target)!,
      }))
      .filter(e => e.source && e.target)

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).distance(90).strength(0.6))
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(38))

    // ── Draw edges ───────────────────────────────────────────────────────────
    const link = zoomG.append('g')
      .selectAll('.edge')
      .data(links)
      .enter()
      .append('line')
      .attr('class', 'link prerequisite')
      .attr('stroke', '#C8DCC8')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')
      .attr('opacity', 0.6)

    // ── Draw nodes ───────────────────────────────────────────────────────────
    const nodeG = zoomG.append('g')
      .selectAll('.node')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(
        d3.drag<SVGGElement, d3.SimulationNodeDatum>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )

    // Outer severity ring
    nodeG.append('circle')
      .attr('r', 24)
      .attr('fill', 'none')
      .attr('stroke', d => SEVERITY_STROKE[(d as any).gap_severity || 'none'])
      .attr('stroke-width', 2)
      .attr('opacity', d => (d as any).gap_severity && (d as any).gap_severity !== 'none' ? 1 : 0.3)

    // Main fill circle
    nodeG.append('circle')
      .attr('r', 20)
      .attr('fill', d => {
        const domain = (d as GraphNode).domain
        return domainGraphColors[domain] || '#8892A8'
      })
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => {
        const domain = (d as GraphNode).domain
        return domainGraphColors[domain] || '#8892A8'
      })
      .attr('stroke-width', 1.5)
      .on('mouseover', function (event, d) {
        d3.select(this).attr('fill-opacity', 0.3).attr('r', 22)
        setTooltip({ node: d as any, x: event.offsetX, y: event.offsetY })
      })
      .on('mouseout', function () {
        d3.select(this).attr('fill-opacity', 0.15).attr('r', 20)
        setTooltip(null)
      })
      .on('click', (_, d) => onNodeClick?.(d as any))

    // Phase number badge
    nodeG.append('circle')
      .attr('r', 8)
      .attr('cx', 14)
      .attr('cy', -14)
      .attr('fill', '#FFFFFF')
      .attr('stroke', '#E8ECF0')
      .attr('stroke-width', 1)
      .attr('opacity', d => (d as any).phase ? 1 : 0)

    nodeG.append('text')
      .attr('x', 14).attr('y', -14)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', '8px')
      .attr('font-family', 'DM Sans, sans-serif')
      .attr('font-weight', '700')
      .attr('fill', '#4A5568')
      .text(d => (d as any).phase || '')

    // Label below node
    nodeG.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 34)
      .attr('font-size', '10px')
      .attr('font-family', 'DM Sans, sans-serif')
      .attr('font-weight', '500')
      .attr('fill', '#4A5568')
      .text(d => {
        const label = (d as any).label || ''
        return label.length > 14 ? label.substring(0, 12) + '…' : label
      })

    // ── Tick handler ─────────────────────────────────────────────────────────
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as any).x)
        .attr('y1', d => (d.source as any).y)
        .attr('x2', d => (d.target as any).x)
        .attr('y2', d => (d.target as any).y)

      nodeG.attr('transform', d => `translate(${(d as any).x},${(d as any).y})`)
    })

    return () => { simulation.stop() }
  }, [graph])

  const handleZoom = (factor: number) => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(
      (d3.zoom() as any).scaleBy,
      factor
    )
  }

  return (
    <div className="relative" ref={containerRef}>
      {/* Legend */}
      <div className="absolute top-3 left-3 z-10 card p-3 space-y-1.5">
        <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wide mb-2">Legend</p>
        {[
          { label: 'Critical Gap', color: '#F87171' },
          { label: 'Major Gap', color: '#F5A623' },
          { label: 'Minor Gap', color: '#38A0F5' },
          { label: 'No Gap', color: '#D8DCE8' },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full border-2 flex-shrink-0"
              style={{ borderColor: color }}
            />
            <span className="text-[10px] text-slate-500">{label}</span>
          </div>
        ))}
      </div>

      {/* Zoom controls */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        {[
          { icon: ZoomIn, action: () => handleZoom(1.3), label: 'Zoom in' },
          { icon: ZoomOut, action: () => handleZoom(0.77), label: 'Zoom out' },
        ].map(({ icon: Icon, action, label }) => (
          <button
            key={label}
            onClick={action}
            title={label}
            className="w-8 h-8 card flex items-center justify-center hover:bg-slate-50 transition-colors"
          >
            <Icon size={14} className="text-slate-500" />
          </button>
        ))}
      </div>

      {/* SVG */}
      <svg ref={svgRef} className="w-full rounded-xl bg-cream" style={{ height: 520 }} />

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-20 card p-3 pointer-events-none shadow-card-hover max-w-[200px]"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <p className="font-semibold text-slate-800 text-sm mb-1">{tooltip.node.label}</p>
          <p className="text-xs text-slate-400 capitalize mb-1">
            {tooltip.node.domain?.replace('_', ' ')} · {tooltip.node.difficulty}
          </p>
          <p className="text-xs text-slate-500">{tooltip.node.hours?.toFixed(0)}h estimated</p>
          {tooltip.node.gap_severity && tooltip.node.gap_severity !== 'none' && (
            <p className="text-xs mt-1 font-medium" style={{ color: SEVERITY_STROKE[tooltip.node.gap_severity] }}>
              {tooltip.node.gap_severity} gap
            </p>
          )}
        </div>
      )}

      {/* Empty state */}
      {!graph.nodes.length && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <Info size={24} className="text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-400">No graph data available</p>
          </div>
        </div>
      )}
    </div>
  )
}
