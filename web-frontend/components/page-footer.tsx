import { Twitter, Github, Linkedin, Youtube, Globe } from "lucide-react"

export function PageFooter() {
  return (
    <footer className="border-t border-[#E5E7EB] bg-white">
      <div className="mx-auto max-w-[1400px] px-10 pb-8 pt-16">
        {/* Footer Top */}
        <div className="mb-12 grid gap-12 md:grid-cols-2 lg:grid-cols-5">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                  <rect width="32" height="32" rx="8" fill="#5A95A8" />
                  <path d="M16 8L24 16L16 24L8 16L16 8Z" fill="white" opacity="0.9" />
                  <circle cx="16" cy="16" r="3" fill="white" />
                </svg>
              </div>
              <span className="text-lg font-bold text-[#1A202C]">Trantor</span>
            </div>
            <p className="mb-6 max-w-[320px] text-sm leading-relaxed text-[#6B7280]">
              Transform your data into actionable insights with AI-powered analysis. Connect any data source and get
              intelligent recommendations in seconds.
            </p>
            <div className="flex gap-3">
              <a
                href="#"
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F8F9FA] text-[#6B7280] transition-all hover:-translate-y-0.5 hover:bg-[#5A95A8] hover:text-white"
                aria-label="Twitter"
              >
                <Twitter size={18} />
              </a>
              <a
                href="#"
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F8F9FA] text-[#6B7280] transition-all hover:-translate-y-0.5 hover:bg-[#5A95A8] hover:text-white"
                aria-label="GitHub"
              >
                <Github size={18} />
              </a>
              <a
                href="#"
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F8F9FA] text-[#6B7280] transition-all hover:-translate-y-0.5 hover:bg-[#5A95A8] hover:text-white"
                aria-label="LinkedIn"
              >
                <Linkedin size={18} />
              </a>
              <a
                href="#"
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F8F9FA] text-[#6B7280] transition-all hover:-translate-y-0.5 hover:bg-[#5A95A8] hover:text-white"
                aria-label="YouTube"
              >
                <Youtube size={18} />
              </a>
            </div>
          </div>

          {/* Product Column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#2D3748]">Product</h3>
            <ul className="space-y-3">
              <li>
                <a href="#features" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Features
                </a>
              </li>
              <li>
                <a href="#integrations" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Integrations
                </a>
              </li>
              <li>
                <a href="#pricing" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Pricing
                </a>
              </li>
              <li>
                <a href="#changelog" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Changelog
                </a>
              </li>
              <li>
                <a href="#roadmap" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Roadmap
                </a>
              </li>
            </ul>
          </div>

          {/* Resources Column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#2D3748]">Resources</h3>
            <ul className="space-y-3">
              <li>
                <a href="#docs" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Documentation
                </a>
              </li>
              <li>
                <a href="#api" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  API Reference
                </a>
              </li>
              <li>
                <a href="#tutorials" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Tutorials
                </a>
              </li>
              <li>
                <a href="#blog" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Blog
                </a>
              </li>
              <li>
                <a href="#community" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Community
                </a>
              </li>
            </ul>
          </div>

          {/* Company Column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[#2D3748]">Company</h3>
            <ul className="space-y-3">
              <li>
                <a href="#about" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  About Us
                </a>
              </li>
              <li>
                <a href="#careers" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Careers
                </a>
              </li>
              <li>
                <a href="#contact" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Contact
                </a>
              </li>
              <li>
                <a href="#partners" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Partners
                </a>
              </li>
              <li>
                <a href="#press" className="text-sm text-[#6B7280] transition-colors hover:text-[#5A95A8]">
                  Press Kit
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="flex flex-col items-start justify-between gap-4 border-t border-[#E5E7EB] pt-8 sm:flex-row sm:items-center">
          <p className="text-sm text-[#9CA3AF]">© 2025 Trantor. All rights reserved.</p>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <a href="#status" className="text-[#6B7280] transition-colors hover:text-[#5A95A8]">
              System Status
            </a>
            <span className="text-[#E5E7EB]">•</span>
            <a href="#sitemap" className="text-[#6B7280] transition-colors hover:text-[#5A95A8]">
              Sitemap
            </a>
            <span className="text-[#E5E7EB]">•</span>
            <button className="flex items-center gap-1.5 text-[#6B7280] transition-colors hover:text-[#5A95A8]">
              <Globe size={16} />
              <span>English</span>
            </button>
          </div>
        </div>
      </div>
    </footer>
  )
}
