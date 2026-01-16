export function CanvasLoadingState() {
  return (
    <div className="absolute inset-0 bg-[#F8F9FB]/80 backdrop-blur-sm z-30 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-16 h-16">
          {/* 外圈旋转 */}
          <div className="absolute inset-0 rounded-full border-4 border-[#E9EEF3]"></div>
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-[#5A95A8] animate-spin"></div>
          
          {/* 内圈脉冲 */}
          <div className="absolute inset-2 rounded-full bg-[#5A95A8]/20 animate-pulse"></div>
        </div>
        <p className="text-sm font-medium text-slate-600">Updating canvas...</p>
      </div>
    </div>
  )
}
