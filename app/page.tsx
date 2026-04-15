import Demo from "./components/Demo";

export default function Home() {
  return (
    <div className="flex-1 flex flex-col">
      <SiteHeader />
      <main className="flex-1 w-full max-w-[1240px] mx-auto px-8 lg:px-12 py-12 lg:py-16">
        <Hero />
        <div className="mt-16">
          <Demo />
        </div>
        <Thesis />
      </main>
      <SiteFooter />
    </div>
  );
}

function SiteHeader() {
  return (
    <header className="border-b border-hairline">
      <div className="w-full max-w-[1240px] mx-auto px-8 lg:px-12 py-5 flex items-center justify-between">
        <span className="display text-[22px] tracking-tight font-medium">drachma</span>
        <nav className="flex items-center gap-6">
          <span className="label">v0 · demo</span>
          <a
            href="https://github.com/armaanpriyadarshan/drachma"
            aria-label="Source on GitHub"
            className="text-muted hover:text-foreground transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              viewBox="0 0 16 16"
              width="18"
              height="18"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 005.47 7.59c.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.42 7.42 0 014 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
          </a>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="flex flex-col gap-6">
      <span className="label">Attention economics for agents</span>
      <h1 className="display text-[46px] md:text-[64px] leading-[1.02] tracking-[-0.025em] font-medium max-w-[17ch]">
        Ranked by humans with skin in the game. Not by ad spend.
      </h1>
      <p className="text-[17px] leading-[1.6] text-muted max-w-[58ch]">
        When AI agents mediate purchases, the products that win today are the ones
        with the best SEO and the biggest budgets — not the best products.
        Drachma replaces that with a structured recommendation layer scored across
        four dimensions: creator-verified quality, expert coverage of the user&apos;s
        niche, similarity-weighted post-purchase outcomes, and value.
      </p>
    </section>
  );
}

function Thesis() {
  const items = [
    {
      label: "Creators",
      title: "Not influencers. Evaluators.",
      body:
        "A verified network of product testers publishes signed attestations against a category-specific rubric. Reputation is earned by predictive accuracy against real outcome data.",
    },
    {
      label: "Agents",
      title: "Query structured signal, not prose.",
      body:
        "Agents call one endpoint with the user's preference profile and receive ranked candidates scored across quality, expert coverage, outcome alignment, and value. Different profiles get different winners.",
    },
    {
      label: "Brands",
      title: "Pay to be evaluated, not promoted.",
      body:
        "Access to the feed is paid. Ranking inside it is earned. The fee buys distribution into the signal network — never influence over the algorithm.",
    },
  ];
  return (
    <section className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-px bg-hairline border border-hairline">
      {items.map((it) => (
        <div key={it.label} className="bg-panel px-7 py-8 flex flex-col gap-3">
          <span className="label">{it.label}</span>
          <h3 className="display text-xl tracking-tight">{it.title}</h3>
          <p className="text-[15px] leading-[1.6] text-muted">{it.body}</p>
        </div>
      ))}
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-hairline">
      <div className="w-full max-w-[1240px] mx-auto px-8 lg:px-12 py-8 flex items-center justify-between">
        <span className="label">drachma · 2026</span>
        <span className="label">demo · mock data · local backend</span>
      </div>
    </footer>
  );
}
