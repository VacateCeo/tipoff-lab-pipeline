import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="max-w-xl mx-auto px-5 py-10 border-t border-slate-800 mt-8">
      <p className="text-slate-500 text-xs font-mono text-center mb-4">
        Not affiliated with the NBA or ESPN. Data may be inaccurate or delayed. Not for gambling purposes.
      </p>
      <div className="flex justify-center gap-6 text-xs font-mono">
        <Link href="/terms" className="text-slate-500 hover:text-white transition-colors">Terms</Link>
        <Link href="/privacy" className="text-slate-500 hover:text-white transition-colors">Privacy</Link>
        <a href="https://github.com/VacateCeo/tipoff-lab-frontend" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-white transition-colors">GitHub</a>
      </div>
    </footer>
  );
}
