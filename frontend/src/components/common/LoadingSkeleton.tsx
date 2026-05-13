import { ReactNode } from 'react'

interface SkeletonProps {
  className?: string
}

export function TextSkeleton({ className = '' }: SkeletonProps) {
  return <div className={`skeleton h-4 w-full ${className}`} />
}

export function TextSkeletonSm({ className = '' }: SkeletonProps) {
  return <div className={`skeleton h-3 w-3/4 ${className}`} />
}

export function CircleSkeleton({ size = 40 }: { size?: number }) {
  return (
    <div
      className="skeleton rounded-full animate-pulse"
      style={{ width: size, height: size }}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="skeleton-card">
      <div className="skeleton h-6 w-1/3" />
      <div className="skeleton h-4 w-full" />
      <div className="skeleton h-4 w-5/6" />
      <div className="skeleton h-8 w-1/2 mt-4" />
    </div>
  )
}

export function ListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="skeleton rounded-full w-10 h-10 flex-shrink-0" />
          <div className="flex-1">
            <div className="skeleton h-4 w-full mb-2" />
            <div className="skeleton h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function GridSkeleton({ columns = 3, count = 6 }: { columns?: number; count?: number }) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-${columns} gap-6`}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton h-6 w-2/3" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-5/6" />
        </div>
      ))}
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="skeleton-card p-4">
      <div className="skeleton h-5 w-1/3 mb-4" />
      <div className="flex items-end gap-3 justify-center h-48">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="flex flex-col items-center flex-1 gap-2">
            <div
              className="skeleton w-full rounded-t"
              style={{ height: `${Math.random() * 60 + 60}px` }}
            />
            <div className="skeleton h-3 w-full rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function GraphSkeleton() {
  return (
    <div className="skeleton-card p-4 aspect-video">
      <div className="skeleton h-5 w-1/4 mb-4" />
      <div className="w-full h-full flex items-center justify-center">
        <div className="grid grid-cols-5 gap-4 w-2/3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex flex-col items-center gap-2">
              <div className="skeleton rounded-full w-12 h-12" />
              <div className="skeleton h-3 w-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function LoadingSkeleton({ children }: { children?: ReactNode }) {
  return children || <CardSkeleton />
}
