import React from "react"
import { ArrowRight } from "lucide-react"
import { cn } from "../../lib/utils"

export const BentoGrid = ({ children, className, ...props }) => {
  return (
    <div
      className={cn(
        "grid w-full auto-rows-[20rem] grid-cols-1 md:grid-cols-3 gap-5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export const BentoCard = ({
  name,
  className,
  background,
  Icon,
  description,
  href,
  cta,
  ...props
}) => (
  <div
    key={name}
    className={cn(
      "group relative col-span-3 md:col-span-1 flex flex-col justify-between overflow-hidden rounded-2xl p-6 border border-gray-200/80 bg-white/90 shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1 backdrop-blur-sm",
      className
    )}
    {...props}
  >
    <div>{background}</div>
    <div className="pointer-events-none z-10 flex transform-gpu flex-col gap-2 transition-all duration-300">
      {Icon && (
        <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-2 shadow-xs group-hover:scale-110 transition-transform">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-gray-900 tracking-tight">
        {name}
      </h3>
      <p className="max-w-lg text-sm text-gray-600 leading-relaxed">{description}</p>
    </div>

    {cta && (
      <div className="z-10 mt-4 flex items-center text-sm font-medium text-blue-600 group-hover:text-blue-700">
        <span>{cta}</span>
        <ArrowRight className="ml-1.5 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
      </div>
    )}
    <div className="pointer-events-none absolute inset-0 transform-gpu transition-all duration-300 group-hover:bg-blue-500/[0.02]" />
  </div>
)
