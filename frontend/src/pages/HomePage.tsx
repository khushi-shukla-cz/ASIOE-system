import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import * as d3 from 'd3'
import { ArrowRight, Brain, GitBranch, Target, Zap } from 'lucide-react'

const DEMO_NODES = [
  { id: 'python', label: 'Python', x: 0, y: 0, r: 28, color: '#38A0F5' },
  { id: 'ml', label: 'ML', x: 160, y: -60, r: 24, color: '#4A8A4A' },
  { id: 'sql', label: 'SQL', x: -140, y: -80, r: 22, color: '#F5A623' },
  { id: 'stats', label: 'Statistics', x: 80, y: 120, r: 20, color: '#7AAD7A' },
  { id: 'dl', label: 'Deep Learning', x: 260, y: 60, r: 22, color: '#4A8A4A' },
  { id: 'aws', label: 'AWS', x: -60, y: 140, r: 18, color: '#38A0F5' },
  { id: 'docker', label: 'Docker', x: -200, y: 40, r: 18, color: '#8892A8' },
  { id: 'git', label: 'Git', x: 180, y: -160, r: 16, color: '#F87171' },
  { id: 'finance', label: 'Finance', x: -160, y: 160, r: 18, color: '#F5A623' },
]

const DEMO_LINKS = [
  { source: 'python', target: 'ml' },
  { source: 'python', target: 'stats' },
  { source: 'sql', target: 'python' },
  { source: 'ml', target: 'dl' },
  { source: 'stats', target: 'ml' },
  { source: 'docker', target: 'aws' },
  { source: 'git', target: 'python' },
  { source: 'stats', target: 'finance' },
  { source: 'aws', target: 'dl' },
]

function FloatingGraph() {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const W = 600, H = 400
    const cx = W / 2, cy = H / 2

    svg.selectAll('*').remove()

    const g = svg.append('g').attr('transform', `translate(${cx},${cy})`)

    // Draw links
    g.selectAll('.demo-link')
      .data(DEMO_LINKS)
      .enter()
      .append('line')
      .attr('class', 'demo-link')
      .attr('x1', d => DEMO_NODES.find(n => n.id === d.source)!.x)
      .attr('y1', d => DEMO_NODES.find(n => n.id === d.source)!.y)
      .attr('x2', d => DEMO_NODES.find(n => n.id === d.target)!.x)
      .attr('y2', d => DEMO_NODES.find(n => n.id === d.target)!.y)
      .attr('stroke', '#D8DCE8')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.6)

    // Draw nodes
    const nodeG = g.selectAll('.demo-node')
      .data(DEMO_NODES)
      .enter()
      .append('g')
      .attr('class', 'demo-node')
      .attr('transform', d => `translate(${d.x},${d.y})`)

    nodeG.append('circle')
      .attr('r', d => d.r)
      .attr('fill', d => d.color)
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => d.color)
      .attr('stroke-width', 1.5)

    nodeG.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', d => d.r > 22 ? '10px' : '9px')
      .attr('font-family', 'DM Sans, sans-serif')
      .attr('font-weight', '500')
      .attr('fill', '#4A5568')
      .text(d => d.label)

    // Gentle float animation
    function animateNodes() {
      nodeG.transition()
        .duration(3000 + Math.random() * 2000)
        .ease(d3.easeSinInOut)
        .attr('transform', d => {
          const dx = (Math.random() - 0.5) * 16
          const dy = (Math.random() - 0.5) * 16
          return `translate(${d.x + dx},${d.y + dy})`
        })
        .on('end', animateNodes)
    }
    animateNodes()
  }, [])

  return (
    <svg
      ref={svgRef}
      width="600"
      height="400"
      className="w-full h-auto opacity-90"
    />
  )
}

const features = [
  {
    icon: Brain,
    title: 'AI-Powered Parsing',
    desc: 'Llama-3.3-70B extracts skills from resumes with enterprise-grade precision.',
    color: 'text-sky-500',
    bg: 'bg-sky-50',
  },
  {
    icon: GitBranch,
    title: 'Graph-Based Pathing',
    desc: 'Topological DAG algorithm sequences learning for maximum efficiency.',
    color: 'text-sage-600',
    bg: 'bg-sage-50',
  },
  {
    icon: Target,
    title: 'Precision Gap Analysis',
    desc: 'Cosine similarity vectors quantify exact competency deficits.',
    color: 'text-amber-600',
    bg: 'bg-amber-50',
  },
  {
    icon: Zap,
    title: 'Full Explainability',
    desc: 'Every recommendation has a traceable reasoning chain. Zero black boxes.',
    color: 'text-rose-500',
    bg: 'bg-rose-50',
  },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-cream">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-cream/80 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <span className="font-display text-xl text-slate-800">ASIOE</span>
          </div>
          <button
            onClick={() => navigate('/analyze')}
            className="btn-primary text-sm"
          >
            Start Analysis
            <ArrowRight size={15} />
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-24 px-6">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-sage-100 rounded-full text-sage-700 text-xs font-medium mb-6">
              <div className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
              Production-Grade AI System
            </div>
            <h1 className="font-display text-5xl lg:text-6xl text-slate-900 mb-6 leading-tight">
              Adaptive Skill
              <br />
              <span className="text-sage-600 italic">Intelligence</span>
              <br />
              Engine
            </h1>
            <p className="text-lg text-slate-500 mb-8 leading-relaxed max-w-lg">
              Upload a resume. Paste a job description. Receive a scientifically computed,
              graph-based learning path that eliminates redundancy and targets exact competency gaps.
            </p>
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/analyze')}
                className="btn-accent text-base px-8 py-4"
              >
                Analyze Now
                <ArrowRight size={18} />
              </button>
              <div className="text-sm text-slate-400">
                <span className="font-medium text-slate-600">42</span> skills ·{' '}
                <span className="font-medium text-slate-600">7</span> engines ·{' '}
                <span className="font-medium text-slate-600">17</span> courses
              </div>
            </div>
          </motion.div>

          {/* Right — Graph */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2, ease: 'easeOut' }}
            className="relative"
          >
            <div className="card p-6 rounded-3xl">
              <div className="text-xs text-slate-400 font-mono mb-3 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-sage-400 animate-pulse" />
                Skill Knowledge Graph — Live Preview
              </div>
              <FloatingGraph />
            </div>
            {/* Floating badge */}
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute -right-4 top-12 card px-4 py-3 shadow-card-hover"
            >
              <div className="text-xs text-slate-400 mb-0.5">Readiness Score</div>
              <div className="text-2xl font-display text-sage-600">87%</div>
            </motion.div>
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
              className="absolute -left-4 bottom-16 card px-4 py-3 shadow-card-hover"
            >
              <div className="text-xs text-slate-400 mb-0.5">Critical Gaps</div>
              <div className="text-2xl font-display text-rose-500">3</div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-14"
          >
            <h2 className="font-display text-4xl text-slate-800 mb-3">
              7 Engines. Zero Black Boxes.
            </h2>
            <p className="text-slate-400 text-lg">
              Every decision traceable. Every recommendation grounded.
            </p>
          </motion.div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="card card-hover p-6"
              >
                <div className={`w-10 h-10 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
                  <f.icon size={20} className={f.color} />
                </div>
                <h3 className="font-semibold text-slate-800 mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xs text-slate-400 font-mono mb-6 uppercase tracking-widest">
            Powered by
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              'Llama-3.3-70B', 'FastAPI', 'Neo4j', 'FAISS', 'sentence-transformers',
              'NetworkX', 'PostgreSQL', 'Redis', 'React', 'Docker',
            ].map(tech => (
              <span
                key={tech}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-mono text-slate-500 shadow-sm"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 py-8 px-6 text-center">
        <p className="text-xs text-slate-400 font-mono">
          ASIOE v1.0.0 · Adaptive Skill Intelligence & Optimization Engine · Production Release
        </p>
      </footer>
    </div>
  )
}
