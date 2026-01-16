"use client"

interface OntologyBuildConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onReupload: () => void
  onConfirmBuild: () => void
  dataSize: string
  estimatedTokens: number
  estimatedTime: string
}

export function OntologyBuildConfirmationModal({
  isOpen,
  onClose,
  onReupload,
  onConfirmBuild,
  dataSize,
  estimatedTokens,
  estimatedTime,
}: OntologyBuildConfirmationModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm cursor-pointer" onClick={onClose} />
      <div className="relative z-10 w-[90%] max-w-[500px] bg-white border border-slate-200 rounded-xl shadow-2xl animate-scale-in">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-base font-semibold text-slate-800 m-0">Ontology Build Estimate</h3>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded bg-transparent text-slate-500 text-xl cursor-pointer flex items-center justify-center transition-all hover:bg-slate-100 hover:text-slate-800"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <p className="text-sm text-slate-600 mb-6">
            Based on your data and responses, here's what you can expect for the ontology construction process:
          </p>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-4 mb-6">
            {/* Data Size */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-xl">📊</div>
                <div>
                  <div className="text-xs text-slate-500 font-medium">Data Size</div>
                  <div className="text-lg font-semibold text-slate-800">{dataSize}</div>
                </div>
              </div>
            </div>

            {/* Token Consumption */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center text-xl">🪙</div>
                <div>
                  <div className="text-xs text-slate-500 font-medium">Estimated Token Usage</div>
                  <div className="text-lg font-semibold text-slate-800">{estimatedTokens.toLocaleString()} tokens</div>
                </div>
              </div>
            </div>

            {/* Processing Time */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center text-xl">⏱️</div>
                <div>
                  <div className="text-xs text-slate-500 font-medium">Estimated Time</div>
                  <div className="text-lg font-semibold text-slate-800">{estimatedTime}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-800">
              💡 <strong>Tip:</strong> The quality of your ontology depends on data completeness. Consider uploading
              additional data sources if available.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex gap-3">
          <button
            onClick={onReupload}
            className="flex-1 px-4 py-2.5 bg-white border border-slate-300 text-slate-600 rounded-lg font-medium transition-all hover:bg-slate-50"
          >
            Re-upload Data
          </button>
          <button
            onClick={onConfirmBuild}
            className="flex-1 px-4 py-2.5 bg-[#5A95A8] text-white rounded-lg font-medium transition-all hover:bg-[#7AB8CC]"
          >
            Confirm & Build
          </button>
        </div>
      </div>
    </div>
  )
}
