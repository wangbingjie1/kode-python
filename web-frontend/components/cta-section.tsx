import { Button } from "@/components/ui/button"

export function CTASection() {
  return (
    <section className="mt-20 bg-gradient-to-br from-[#5A95A8] to-[#7AB8CC] px-10 py-20">
      <div className="mx-auto max-w-[800px] text-center text-white">
        <h2 className="mb-4 text-4xl font-bold">Ready to transform your data?</h2>
        <p className="mb-8 text-lg leading-relaxed opacity-95">
          Join thousands of teams already using Trantor to unlock insights from their data.
        </p>
        <div className="mb-4 flex flex-col justify-center gap-4 sm:flex-row">
          <Button
            size="lg"
            className="bg-white text-[#5A95A8] transition-all hover:-translate-y-0.5 hover:bg-white hover:shadow-2xl"
          >
            Get Started Free
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="border-2 border-white bg-transparent text-white transition-all hover:-translate-y-0.5 hover:bg-white/10"
          >
            Schedule Demo
          </Button>
        </div>
        <p className="text-sm opacity-85">No credit card required • Free 14-day trial</p>
      </div>
    </section>
  )
}
