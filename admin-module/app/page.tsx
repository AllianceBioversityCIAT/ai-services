import Link from "next/link";
import Image from "next/image";
import { listProducts } from "@/lib/database/products";
import { getActiveProjects } from "@/lib/database/projects";

export default async function HomePage() {
  const [products, activeProjects] = await Promise.all([
    listProducts(),
    getActiveProjects(),
  ]);

  const byProduct: Record<string, any[]> = {};
  for (const p of activeProjects) {
    const pid = p.product_id;
    if (!byProduct[pid]) byProduct[pid] = [];
    byProduct[pid].push(p);
  }

  const visibleProducts = products
    .filter((prod: any) => byProduct[prod.id]?.length)
    .sort((a: any, b: any) => (a.name > b.name ? 1 : -1));
  Object.keys(byProduct).forEach((k) => {
    byProduct[k] = byProduct[k].sort((a: any, b: any) => (a.name > b.name ? 1 : -1));
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent" />
        <header className="relative border-b border-border/50 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-primary" />
              <span className="text-base font-semibold text-foreground">AI Services</span>
            </div>
            <nav className="text-sm text-muted-foreground">
              <Link href="/login" className="hover:text-foreground">Sign in</Link>
            </nav>
          </div>
        </header>

        <section className="relative max-w-6xl mx-auto px-6 pt-10 pb-8">
          <h1 className="text-4xl font-semibold tracking-tight text-foreground">AI Services</h1>
          <p className="text-base text-muted-foreground mt-3 max-w-2xl">
            Explore our products and active projects. Access each service's Swagger documentation.
          </p>
        </section>
      </div>

      {/* Product grid */}
      <main className="max-w-6xl mx-auto px-6 pb-14">
        {visibleProducts.length === 0 ? (
          <div className="text-muted-foreground">No hay proyectos activos por el momento.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {visibleProducts.map((prod: any) => (
              <div key={prod.id} className="rounded-xl border border-border bg-card shadow-sm hover:shadow transition-shadow">
                <div className="p-5 flex items-start gap-4">
                  {prod.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={prod.image_url} alt={prod.name} className="h-12 w-12 rounded object-cover ring-1 ring-border" />
                  )}
                  <div>
                    <h2 className="text-lg font-medium text-foreground">{prod.name}</h2>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{prod.description}</p>
                  </div>
                </div>
                <div className="px-5 pb-4 text-xs text-muted-foreground">
                  {(() => {
                    const c = (byProduct[prod.id] || []).length;
                    return `${c} active project${c === 1 ? "" : "s"}`;
                  })()}
                </div>
                <div className="px-5 pb-5 space-y-3">
                  {(byProduct[prod.id] || []).map((project: any) => (
                    <div key={project.id || project.PK} className="rounded-lg border border-border/80 bg-background p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-foreground">{project.name}</div>
                          <div className="text-xs text-muted-foreground line-clamp-1">{project.description}</div>
                        </div>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-[10px] font-medium bg-emerald-100 text-emerald-700">
                          Active
                        </span>
                      </div>
                      <div className="mt-3">
                        {project.swaggerURL ? (
                          <a
                            href={project.swaggerURL}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4"><path d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-6 6L21 3m0 0h-5.25M21 3v5.25"/></svg>
                            Open Swagger
                          </a>
                        ) : (
                          <span className="text-sm text-muted-foreground">No Swagger</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="border-t border-border mt-6">
        <div className="max-w-6xl mx-auto px-6 py-4 text-xs text-muted-foreground">
          © {new Date().getFullYear()} AI Unit · All rights reserved
        </div>
      </footer>
    </div>
  );
}
