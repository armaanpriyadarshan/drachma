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
        <nav className="flex items-center gap-7">
          <span className="label">v0 · demo</span>
          <a
            href="https://github.com/"
            className="label hover:text-foreground transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            Source
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
        Drachma replaces that with a structured recommendation layer scored by
        verified human testers and validated by post-purchase outcomes.
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
        "Agents call one endpoint with the user's preference profile and receive ranked candidates scored across attestation, outcome, niche-fit, and value dimensions.",
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
