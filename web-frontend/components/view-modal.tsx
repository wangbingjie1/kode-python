"use client"

interface ViewModalProps {
  onClose: () => void
}

export default function ViewModal({ onClose }: ViewModalProps) {
  const templates = [
    { icon: "✨", title: "Freeform", desc: "Create custom view from scratch" },
    { icon: "📊", title: "Analytics Dashboard", desc: "Standard metrics and KPI tracking" },
    { icon: "📈", title: "Monitoring Dashboard", desc: "Real-time data monitoring" },
    { icon: "📝", title: "Report Generator", desc: "Generate custom reports" },
    { icon: "🎯", title: "Goal Tracking", desc: "Monitor KPI progress" },
    { icon: "💰", title: "Sales Funnel", desc: "Track sales funnel and deals" },
  ]

  return (
    <div className="fixed top-0 left-0 w-full h-full z-[2000] flex items-center justify-center">
      <div
        className="absolute top-0 left-0 w-full h-full bg-black/30 backdrop-blur-sm cursor-pointer"
        onClick={onClose}
      />
      <div className="relative z-10 w-[90%] max-w-[700px] bg-white border border-[#E2E8F0] rounded-xl shadow-2xl animate-scale-in">
        <div className="px-6 py-5 border-b border-[#E2E8F0] flex justify-between items-center">
          <h3 className="text-base font-semibold text-[#1A202C] m-0">Create New View</h3>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded bg-transparent text-[#718096] text-xl cursor-pointer flex items-center justify-center transition-all hover:bg-[#F8F9FA] hover:text-[#2D3748]"
          >
            ×
          </button>
        </div>
        <div className="px-6 py-6 max-h-[500px] overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            {templates.map((template, idx) => (
              <div
                key={idx}
                className="px-4 py-5 bg-[#F7F8F9] border border-[#E2E8F0] rounded-lg cursor-pointer transition-all hover:bg-[#F8F9FA] hover:border-[#CBD5E0] hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="text-[32px] mb-3 opacity-80">{template.icon}</div>
                <div className="text-sm text-[#2D3748] font-semibold mb-1.5">{template.title}</div>
                <div className="text-xs text-[#718096] leading-normal">{template.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
