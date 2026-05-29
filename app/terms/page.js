export const metadata = {
  title: 'Terms of Service – Tipoff Lab',
};

export default function Terms() {
  return (
    <div className="min-h-screen text-white" style={{ backgroundColor: '#0d1117' }}>
      <div className="max-w-xl mx-auto px-5 py-14">
        <h1 className="text-2xl font-semibold tracking-tight text-white mb-2">Terms of Service</h1>
        <p className="text-slate-500 text-xs font-mono mb-10">Last updated: May 27, 2026</p>

        <div className="text-slate-300 text-sm leading-relaxed space-y-6">
          <section>
            <h2 className="text-white font-semibold mb-2">1. Acceptance</h2>
            <p>By using Tipoff Lab, you agree to these Terms. If you don't agree, don't use the site.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">2. What We Provide</h2>
            <p>Tipoff Lab provides predictions, statistics, and commentary about NBA games. Data is sourced from third-party APIs and may be inaccurate, delayed, or incomplete. We provide everything "as-is" with no warranties.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">3. Not For Gambling</h2>
            <p>This site is for entertainment and informational purposes only. We do not provide betting advice. Watchability scores, spreads, and predictions shown on this site are not recommendations to place wagers. Any use of this information for gambling is at your own risk. We are not responsible for any losses incurred.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">4. Not Affiliated</h2>
            <p>Tipoff Lab is not affiliated with, endorsed by, or sponsored by the NBA, ESPN, any NBA team, or any data provider. All team names, logos, and trademarks belong to their respective owners.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">5. Limitation of Liability</h2>
            <p>To the maximum extent allowed by law, Tipoff Lab and its operators are not liable for any direct, indirect, incidental, or consequential damages arising from your use of the site, including decisions made based on information shown here.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">6. Changes</h2>
            <p>We may update these Terms at any time. Continued use of the site after changes means you accept them.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">7. Contact</h2>
            <p>Questions about these Terms? Open an issue on our GitHub repository.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
