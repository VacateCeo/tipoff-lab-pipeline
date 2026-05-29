export const metadata = {
  title: 'Privacy Policy – Tipoff Lab',
};

export default function Privacy() {
  return (
    <div className="min-h-screen text-white" style={{ backgroundColor: '#0d1117' }}>
      <div className="max-w-xl mx-auto px-5 py-14">
        <h1 className="text-2xl font-semibold tracking-tight text-white mb-2">Privacy Policy</h1>
        <p className="text-slate-500 text-xs font-mono mb-10">Last updated: May 27, 2026</p>

        <div className="text-slate-300 text-sm leading-relaxed space-y-6">
          <section>
            <h2 className="text-white font-semibold mb-2">What We Collect</h2>
            <p>Tipoff Lab does not require accounts and does not collect personal information from visitors. We use standard hosting and analytics provided by Vercel, which may collect anonymized request data (IP, browser type, referrer) for performance monitoring. We do not sell or share this data.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">Cookies</h2>
            <p>We do not use tracking cookies. Vercel may set technical cookies necessary for the site to function.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">Third-Party Services</h2>
            <p>This site uses data from ESPN, NBA.com, and The Odds API. These providers have their own privacy policies that govern data they collect from you when their APIs are called by our backend.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">Your Rights</h2>
            <p>If you are located in the EU or California, you may have rights regarding your personal information. Since we don't collect personal information directly, most of these rights do not apply, but you can contact us via GitHub with any questions.</p>
          </section>

          <section>
            <h2 className="text-white font-semibold mb-2">Changes</h2>
            <p>We may update this policy. Material changes will be noted at the top of this page.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
