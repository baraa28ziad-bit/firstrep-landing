const SUPABASE_FUNCTION_URL =
  "https://bcvjhjkieyffqkurfivj.supabase.co/functions/v1/render-trainer-website";
const SUPABASE_ARTICLES_URL =
  "https://bcvjhjkieyffqkurfivj.supabase.co/functions/v1/get-published-articles";
const SUPABASE_ARTICLE_URL =
  "https://bcvjhjkieyffqkurfivj.supabase.co/functions/v1/get-article-by-slug";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. /trainer/* → Supabase proxy (unchanged)
    if (url.pathname.startsWith("/trainer/")) {
      return handleTrainer(request, url);
    }

    // 2. /blog or /blog/ or /blog/index.html → blog index with trainer articles appended
    const blogPath = url.pathname.replace(/\/$/, "");
    if (blogPath === "/blog" || url.pathname === "/blog/index.html") {
      return handleBlogIndex(request, env);
    }

    // 3. /blog/{slug} (no .html extension) → try trainer article
    if (blogPath.startsWith("/blog/") && !blogPath.endsWith(".html")) {
      const slug = blogPath.replace("/blog/", "");
      if (slug && !slug.includes("/")) {
        return handleBlogArticle(request, env, slug);
      }
    }

    // 4. Everything else → static assets
    return env.ASSETS.fetch(request);
  },
};

// ─── Trainer pages proxy ───────────────────────────────────────

async function handleTrainer(request, url) {
  const parts = url.pathname.replace(/^\/trainer\//, "").split("/").filter(Boolean);
  const handle = parts[0] || "";
  const page = parts[1] || "home";
  const slug = parts[2] || "";

  if (!handle) {
    return new Response("Not Found", { status: 404 });
  }

  const target = new URL(SUPABASE_FUNCTION_URL);
  target.searchParams.set("handle", handle);
  target.searchParams.set("page", page);
  if (slug) target.searchParams.set("slug", slug);

  const headers = { Accept: "text/html" };
  const ct = request.headers.get("Content-Type");
  if (ct) headers["Content-Type"] = ct;

  const init = { method: request.method, headers };
  if (request.method === "POST") {
    init.body = await request.text();
  }

  const res = await fetch(target.toString(), init);

  return new Response(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": res.headers.get("Cache-Control") || "public, max-age=300, s-maxage=600",
    },
  });
}

// ─── Blog index: append trainer articles via HTMLRewriter ──────

async function handleBlogIndex(request, env) {
  // Fetch the static blog index + trainer articles in parallel
  const staticReq = new Request(new URL("/blog/index.html", request.url), request);
  let [staticRes, articlesRes] = await Promise.all([
    env.ASSETS.fetch(staticReq),
    fetch(SUPABASE_ARTICLES_URL).catch(() => null),
  ]);

  // CF Pages may 308 redirect /blog/index.html → /blog/ — follow it internally
  if (!staticRes.ok && (staticRes.status === 308 || staticRes.status === 301)) {
    const loc = staticRes.headers.get("location");
    if (loc) {
      staticRes = await env.ASSETS.fetch(new Request(new URL(loc, request.url), request));
    }
  }

  if (!staticRes.ok) {
    return staticRes;
  }

  let articles = [];
  try {
    if (articlesRes && articlesRes.ok) {
      articles = await articlesRes.json();
    }
  } catch { /* ignore parse errors */ }

  if (!articles.length) {
    return staticRes;
  }

  // Build HTML for trainer article cards
  const cardsHtml = articles.map((a) => {
    const dateStr = a.published_at
      ? new Date(a.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
      : "";
    const avatarHtml = a.trainer_avatar_url
      ? `<img src="${escHtml(a.trainer_avatar_url)}" alt="" style="width:20px;height:20px;border-radius:50%;object-fit:cover;">`
      : "";
    const imgHtml = a.cover_image_url
      ? `<img class="blog-card__img" src="${escHtml(a.cover_image_url)}" alt="${escHtml(a.title)}">`
      : `<div class="blog-card__img" style="background:#F5F5F7;"></div>`;

    return `
      <a href="/blog/${escHtml(a.slug)}" class="blog-card">
        ${imgHtml}
        <div class="blog-card__body">
          <span class="blog-card__tag" style="background:#EEF0FF;color:#5E59FE;">Coach Article</span>
          <h2 class="blog-card__title">${escHtml(a.title)}</h2>
          ${a.excerpt ? `<p class="blog-card__excerpt">${escHtml(a.excerpt)}</p>` : ""}
          <div class="blog-card__meta">
            <span style="display:flex;align-items:center;gap:6px;">
              ${avatarHtml}
              ${escHtml(a.trainer_name)}
            </span>
            ${dateStr ? `<span><i data-lucide="calendar" style="width:14px;height:14px"></i> ${dateStr}</span>` : ""}
          </div>
        </div>
      </a>`;
  }).join("\n");

  // Use HTMLRewriter to append trainer cards into .blog-grid
  const rewriter = new HTMLRewriter()
    .on(".blog-grid", {
      element(el) {
        el.append(cardsHtml, { html: true });
      },
    });

  const newRes = new Response(staticRes.body, {
    status: staticRes.status,
    headers: staticRes.headers,
  });

  return rewriter.transform(newRes);
}

// ─── Individual trainer article at /blog/{slug} ─────────────────

async function handleBlogArticle(request, env, slug) {
  // First try static file: /blog/{slug}.html
  const staticReq = new Request(new URL(`/blog/${slug}.html`, request.url), request);
  let staticRes = await env.ASSETS.fetch(staticReq);
  // CF Pages may 308 redirect to strip .html — follow it internally
  if (!staticRes.ok && (staticRes.status === 308 || staticRes.status === 301)) {
    const loc = staticRes.headers.get("location");
    if (loc) {
      staticRes = await env.ASSETS.fetch(new Request(new URL(loc, request.url), request));
    }
  }
  if (staticRes.ok) {
    return staticRes;
  }

  // Not a static article — try trainer article from DB
  const articleRes = await fetch(`${SUPABASE_ARTICLE_URL}?slug=${encodeURIComponent(slug)}`);
  if (!articleRes.ok) {
    // Fall through to 404
    return env.ASSETS.fetch(request);
  }

  let article;
  try {
    article = await articleRes.json();
  } catch {
    return env.ASSETS.fetch(request);
  }

  if (article.error) {
    return env.ASSETS.fetch(request);
  }

  const html = renderTrainerArticlePage(article);
  return new Response(html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300, s-maxage=600",
    },
  });
}

// ─── Helpers ────────────────────────────────────────────────────

function escHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function markdownToHtml(md) {
  if (!md) return "";
  let html = md;
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/^> (.+)$/gm, "<blockquote><p>$1</p></blockquote>");
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");
  html = html.replace(/^---$/gm, "<hr>");
  html = html.replace(/^(?!<[hublao])(.*\S.*)$/gm, "<p>$1</p>");
  return html;
}

function renderTrainerArticlePage(article) {
  const title = escHtml(article.seo_title || article.title);
  const desc = escHtml(article.seo_description || article.excerpt || "");
  const trainerName = escHtml(article.trainer_name);
  const trainerHandle = escHtml(article.trainer_handle);
  const coverImg = article.cover_image_url ? escHtml(article.cover_image_url) : "";
  const dateStr = article.published_at
    ? new Date(article.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "";
  const bodyHtml = markdownToHtml(article.body || "");
  const avatarHtml = article.trainer_avatar_url
    ? `<img src="${escHtml(article.trainer_avatar_url)}" alt="${trainerName}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid var(--border);">`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} — FirstRep</title>
  <meta name="description" content="${desc}">
  <link rel="canonical" href="https://firstrep.fit/blog/${escHtml(article.slug)}">
  <meta property="og:title" content="${title}">
  <meta property="og:description" content="${desc}">
  ${coverImg ? `<meta property="og:image" content="${coverImg}">` : ""}
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://firstrep.fit/blog/${escHtml(article.slug)}">
  <meta property="og:site_name" content="FirstRep">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${title}">
  <meta name="twitter:description" content="${desc}">
  ${coverImg ? `<meta name="twitter:image" content="${coverImg}">` : ""}
  <link rel="apple-touch-icon" sizes="180x180" href="/images/icons/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="32x32" href="/images/icons/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/images/icons/favicon-16x16.png">
  <meta name="theme-color" content="#5E59FE">
  <script type="application/ld+json">
  ${JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.excerpt || "",
    image: article.cover_image_url || "",
    datePublished: article.published_at || "",
    author: {
      "@type": "Person",
      name: article.trainer_name,
      url: `https://firstrep.fit/trainer/${article.trainer_handle}`,
    },
    publisher: {
      "@type": "Organization",
      name: "FirstRep",
      logo: { "@type": "ImageObject", url: "https://firstrep.fit/images/brand/firstrep-black.png" },
    },
    mainEntityOfPage: { "@type": "WebPage", "@id": `https://firstrep.fit/blog/${article.slug}` },
  })}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lucide@0.344.0/dist/umd/lucide.min.js"></script>
  <style>
    :root {
      --brand: #5E59FE;
      --brand-hover: #4B46E5;
      --brand-light: #EEF0FF;
      --dark: #0F1117;
      --text: #111827;
      --text-2: #374151;
      --text-3: #6B7280;
      --text-muted: #9CA3AF;
      --bg: #FFFFFF;
      --bg-2: #F5F5F7;
      --border: #E5E7EB;
      --success: #10B981;
      --radius: 16px;
      --radius-lg: 20px;
      --shadow: 0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
      --shadow-lg: 0 4px 12px rgba(0,0,0,0.04), 0 20px 48px rgba(0,0,0,0.06);
      --container: 1240px;
      --nav-h: 80px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; -webkit-font-smoothing: antialiased; }
    body { font-family: 'Inter', sans-serif; color: var(--text); background: var(--bg); line-height: 1.6; }
    img { max-width: 100%; display: block; }
    a { text-decoration: none; color: inherit; }
    ul { list-style: none; }
    .container { max-width: var(--container); margin: 0 auto; padding: 0 24px; }

    /* NAV (scrolled state) */
    .nav { position: fixed; top: 0; left: 0; right: 0; height: var(--nav-h); background: rgba(255,255,255,0.98); backdrop-filter: blur(12px); z-index: 1000; border-bottom: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .nav__inner { display: flex; align-items: center; justify-content: space-between; height: 100%; max-width: var(--container); margin: 0 auto; padding: 0 24px; }
    .nav__logo-img { height: 28px; width: auto; }
    .nav__links { display: flex; gap: 32px; }
    .nav__link { font-size: 14px; font-weight: 500; color: var(--text-2); letter-spacing: -0.01em; transition: color 0.2s; cursor: pointer; }
    .nav__link:hover { color: var(--text); }
    .nav__link--active { color: var(--brand); font-weight: 600; }
    .nav__actions { display: flex; align-items: center; gap: 12px; }
    .nav__cta { display: inline-flex; align-items: center; font-family: inherit; font-weight: 600; font-size: 14px; padding: 11px 28px; border-radius: 12px; background: var(--brand); color: #fff; border: none; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
    .nav__cta:hover { background: var(--brand-hover); }
    .nav__hamburger { display: none; flex-direction: column; gap: 5px; cursor: pointer; padding: 8px; }
    .nav__hamburger span { width: 22px; height: 2px; background: var(--text); border-radius: 2px; display: block; }
    .nav__mobile { display: none; position: fixed; top: var(--nav-h); left: 0; right: 0; bottom: 0; background: #fff; padding: 32px 24px; flex-direction: column; gap: 8px; z-index: 999; }
    .nav__mobile.open { display: flex; }
    .nav__mobile a, .nav__mobile span { font-size: 17px; font-weight: 500; color: var(--text); padding: 16px 0; border-bottom: 1px solid var(--bg-2); cursor: pointer; }

    /* MEGA MENU */
    .nav__link--features { position: relative; display: inline-flex; align-items: center; gap: 4px; padding-bottom: 20px; margin-bottom: -20px; }
    .nav__link--features::after { content: ''; display: inline-block; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid currentColor; margin-left: 2px; transition: transform 0.25s; }
    .nav__link--features:hover::after, .nav__link--features.open::after { transform: rotate(180deg); }
    .mega-menu { position: fixed; top: var(--nav-h); left: 50%; transform: translateX(-50%); width: 100%; max-width: 1120px; background: #fff; border-radius: 0 0 16px 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.12); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 0.25s; z-index: 998; padding: 36px 40px 40px; }
    .mega-menu.visible { opacity: 1; visibility: visible; pointer-events: auto; }
    .mega-menu__grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; }
    .mega-menu__col { padding: 0 28px; border-right: 1px solid var(--border); }
    .mega-menu__col:first-child { padding-left: 0; }
    .mega-menu__col:last-child { padding-right: 0; border-right: none; }
    .mega-menu__col-title { font-size: 18px; font-weight: 800; color: var(--text); margin-bottom: 16px; letter-spacing: -0.03em; }
    .mega-menu__col-img { width: 100%; height: 140px; object-fit: cover; border-radius: 12px; margin-bottom: 20px; }
    .mega-menu__links { display: flex; flex-direction: column; }
    .mega-menu__link { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; font-size: 15px; font-weight: 500; color: var(--text-2); transition: color 0.2s; }
    .mega-menu__link:hover { color: var(--text); }
    .mega-menu__link-arrow { font-size: 16px; color: var(--text-muted); transition: transform 0.2s, color 0.2s; }
    .mega-menu__link:hover .mega-menu__link-arrow { transform: translateX(3px); color: var(--text); }
    .mega-overlay { position: fixed; inset: 0; top: var(--nav-h); background: rgba(0,0,0,0.15); z-index: 997; opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 0.25s; }
    .mega-overlay.visible { opacity: 1; visibility: visible; pointer-events: auto; }
    .nav__mobile-features { display: none; padding-left: 16px; }
    .nav__mobile-features.open { display: flex; flex-direction: column; }
    .nav__mobile-features a { font-size: 15px; padding: 12px 0; color: var(--text-3); }

    /* ARTICLE */
    .article-hero { padding: 140px 0 0; }
    .article-hero .container { max-width: 768px; }
    .article-hero__back { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 500; color: var(--text-3); margin-bottom: 24px; transition: color 0.2s; }
    .article-hero__back:hover { color: var(--brand); }
    .article-hero__tag { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--brand); background: var(--brand-light); padding: 4px 10px; border-radius: 6px; margin-bottom: 16px; }
    .article-hero__title { font-size: 42px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.15; margin-bottom: 16px; max-width: 720px; }
    .article-hero__meta { display: flex; align-items: center; gap: 16px; font-size: 14px; color: var(--text-muted); margin-bottom: 32px; flex-wrap: wrap; }
    .article-hero__meta span { display: flex; align-items: center; gap: 5px; }
    .article-hero__author { display: flex; align-items: center; gap: 10px; }
    .article-hero__author-info { display: flex; flex-direction: column; }
    .article-hero__author-name { font-size: 14px; font-weight: 600; color: var(--text); }
    .article-hero__author-role { font-size: 12px; color: var(--text-muted); }
    .article-hero__img { width: 100%; max-width: 720px; height: 400px; object-fit: cover; border-radius: var(--radius); }
    .article { max-width: 720px; margin: 0 auto; padding: 48px 24px 80px; }
    .article h2 { font-size: 28px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; margin: 48px 0 16px; color: var(--text); }
    .article h3 { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.3; margin: 36px 0 12px; color: var(--text); }
    .article p { font-size: 17px; line-height: 1.8; color: var(--text-2); margin-bottom: 20px; }
    .article ul, .article ol { margin: 0 0 20px 24px; }
    .article ul { list-style: disc; }
    .article ol { list-style: decimal; }
    .article li { font-size: 17px; line-height: 1.8; color: var(--text-2); margin-bottom: 8px; }
    .article strong { color: var(--text); font-weight: 600; }
    .article blockquote { border-left: 3px solid var(--brand); padding: 16px 24px; margin: 28px 0; background: var(--brand-light); border-radius: 0 12px 12px 0; }
    .article blockquote p { color: var(--text-2); font-style: italic; margin-bottom: 0; }
    .article a { color: var(--brand); font-weight: 500; transition: color 0.2s; }
    .article a:hover { color: var(--brand-hover); }
    .article img { border-radius: var(--radius); margin: 32px 0; }
    .article hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }

    /* CTA */
    .blog-cta { background: linear-gradient(135deg, var(--brand) 0%, var(--dark) 100%); padding: 80px 0; text-align: center; }
    .blog-cta__title { font-size: 36px; font-weight: 800; color: #fff; letter-spacing: -0.04em; line-height: 1.15; margin-bottom: 12px; }
    .blog-cta__desc { font-size: 17px; color: rgba(255,255,255,0.7); margin-bottom: 32px; line-height: 1.7; max-width: 520px; margin-left: auto; margin-right: auto; }
    .blog-cta__badges { display: flex; justify-content: center; gap: 14px; flex-wrap: wrap; }
    .app-badge { display: inline-flex; align-items: center; gap: 10px; padding: 12px 24px; border-radius: 12px; transition: all 0.2s; background: #fff; color: #111; }
    .app-badge:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(255,255,255,0.2); }
    .app-badge__icon { display: flex; align-items: center; }
    .app-badge__icon svg { width: 28px; height: 28px; }
    .app-badge__text { display: flex; flex-direction: column; }
    .app-badge__label { font-size: 10px; font-weight: 500; color: #6B7280; line-height: 1; }
    .app-badge__store { font-size: 17px; font-weight: 700; line-height: 1.2; letter-spacing: -0.02em; }

    /* FOOTER */
    .footer { background: var(--dark); border-top: 1px solid rgba(255,255,255,0.06); padding: 80px 0 40px; }
    .footer__grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 48px; margin-bottom: 60px; max-width: var(--container); margin-left: auto; margin-right: auto; padding: 0 24px; }
    .footer__logo-img { height: 28px; width: auto; margin-bottom: 16px; }
    .footer__desc { font-size: 15px; color: rgba(255,255,255,0.45); line-height: 1.7; max-width: 300px; margin-bottom: 24px; }
    .footer__apps { display: flex; flex-direction: column; gap: 8px; }
    .footer__apps .app-badge { padding: 8px 16px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); color: #fff; }
    .footer__apps .app-badge:hover { background: rgba(255,255,255,0.12); box-shadow: none; }
    .footer__apps .app-badge__icon svg { width: 22px; height: 22px; }
    .footer__apps .app-badge__store { font-size: 14px; }
    .footer__apps .app-badge__label { font-size: 9px; color: rgba(255,255,255,0.6); }
    .footer__col-title { font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.35); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
    .footer__col a { display: block; font-size: 14px; color: rgba(255,255,255,0.55); padding: 5px 0; transition: color 0.2s; }
    .footer__col a:hover { color: #fff; }
    .footer__bottom { display: flex; justify-content: space-between; align-items: center; padding-top: 32px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 13px; color: rgba(255,255,255,0.25); max-width: var(--container); margin: 0 auto; padding-left: 24px; padding-right: 24px; }
    .footer__legal { display: flex; gap: 24px; }
    .footer__legal a { color: rgba(255,255,255,0.25); transition: color 0.2s; }
    .footer__legal a:hover { color: rgba(255,255,255,0.5); }

    @media (max-width: 1024px) {
      .footer__grid { grid-template-columns: 2fr 1fr 1fr; }
    }
    @media (max-width: 768px) {
      .nav__links, .nav__actions { display: none; }
      .nav__hamburger { display: flex; }
      .mega-menu { display: none !important; }
      .mega-overlay { display: none !important; }
      .article-hero__title { font-size: 28px; }
      .article-hero { padding: 120px 0 0; }
      .article-hero__img { height: 260px; }
      .blog-cta__title { font-size: 28px; }
      .footer__grid { grid-template-columns: 1fr 1fr; gap: 32px; }
    }
    @media (max-width: 480px) {
      .footer__grid { grid-template-columns: 1fr; gap: 28px; }
      .blog-cta__badges { flex-direction: column; align-items: center; }
    }
  </style>
</head>
<body>
  <nav class="nav" id="nav">
    <div class="nav__inner">
      <a href="/"><img src="/images/brand/firstrep-black.png" alt="FirstRep" class="nav__logo-img"></a>
      <div class="nav__links">
        <span class="nav__link nav__link--features" id="featuresToggle">Features</span>
        <a href="/#how-it-works" class="nav__link">How It Works</a>
        <a href="/#pricing" class="nav__link">Pricing</a>
        <a href="/blog/index.html" class="nav__link nav__link--active">Blog</a>
      </div>
      <div class="nav__actions">
        <a href="#" class="nav__cta">Download the App &rarr;</a>
      </div>
      <div class="nav__hamburger" id="hamburger">
        <span></span><span></span><span></span>
      </div>
    </div>
    <div class="mega-menu" id="megaMenu">
      <div class="mega-menu__grid">
        <div class="mega-menu__col">
          <div class="mega-menu__col-title">Coach</div>
          <img class="mega-menu__col-img" src="https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=400&h=220&fit=crop&q=80" alt="Trainer coaching client">
          <div class="mega-menu__links">
            <a href="/features/programming.html" class="mega-menu__link">AI Workout Builder <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/nutrition.html" class="mega-menu__link">Nutrition &amp; Meal Plans <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/habits.html" class="mega-menu__link">Habit Tracking <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/coaching.html" class="mega-menu__link">Coaching Dashboard <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/progress.html" class="mega-menu__link">Progress Tracking <span class="mega-menu__link-arrow">&rarr;</span></a>
          </div>
        </div>
        <div class="mega-menu__col">
          <div class="mega-menu__col-title">Engage</div>
          <img class="mega-menu__col-img" src="https://images.unsplash.com/photo-1556740758-90de374c12ad?w=400&h=220&fit=crop&q=80" alt="People connecting">
          <div class="mega-menu__links">
            <a href="/features/communication.html" class="mega-menu__link">1-on-1 Messaging <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/communication.html" class="mega-menu__link">Group Messaging <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/business.html" class="mega-menu__link">Forms &amp; Questionnaires <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/coaching.html" class="mega-menu__link">Weekly Check-ins <span class="mega-menu__link-arrow">&rarr;</span></a>
          </div>
        </div>
        <div class="mega-menu__col">
          <div class="mega-menu__col-title">Manage</div>
          <img class="mega-menu__col-img" src="https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=400&h=220&fit=crop&q=80" alt="Gym management">
          <div class="mega-menu__links">
            <a href="/features/coaching.html" class="mega-menu__link">Client Dashboard <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/scheduling.html" class="mega-menu__link">Scheduling &amp; Booking <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/progress.html" class="mega-menu__link">Analytics &amp; Reports <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/business.html" class="mega-menu__link">Business Tools <span class="mega-menu__link-arrow">&rarr;</span></a>
          </div>
        </div>
        <div class="mega-menu__col">
          <div class="mega-menu__col-title">Scale</div>
          <img class="mega-menu__col-img" src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&h=220&fit=crop&q=80" alt="Group fitness class">
          <div class="mega-menu__links">
            <a href="/features/marketplace.html" class="mega-menu__link">Trainer Marketplace <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/payments.html" class="mega-menu__link">Integrated Payments <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features/business.html" class="mega-menu__link">Automation Rules <span class="mega-menu__link-arrow">&rarr;</span></a>
            <a href="/features.html" class="mega-menu__link">All Features <span class="mega-menu__link-arrow">&rarr;</span></a>
          </div>
        </div>
      </div>
    </div>
  </nav>
  <div class="mega-overlay" id="megaOverlay"></div>
  <div class="nav__mobile" id="mobileMenu">
    <span id="mobileFeatures" style="display:flex;align-items:center;justify-content:space-between;">Features <span style="font-size:20px;">+</span></span>
    <div class="nav__mobile-features" id="mobileFeaturesList">
      <a href="/features/programming.html">AI Workout Builder</a>
      <a href="/features/nutrition.html">Nutrition & Meal Plans</a>
      <a href="/features/coaching.html">Coaching Dashboard</a>
      <a href="/features/scheduling.html">Scheduling & Booking</a>
      <a href="/features/marketplace.html">Trainer Marketplace</a>
      <a href="/features.html">All Features</a>
    </div>
    <a href="/#how-it-works">How It Works</a>
    <a href="/#pricing">Pricing</a>
    <a href="/blog/index.html">Blog</a>
    <a href="#" style="background:var(--brand);color:#fff;text-align:center;border-radius:12px;padding:14px 0;border:none;margin-top:16px;">Download the App &rarr;</a>
  </div>

  <section class="article-hero">
    <div class="container">
      <a href="/blog/index.html" class="article-hero__back"><i data-lucide="arrow-left" style="width:16px;height:16px"></i> Back to Blog</a>
      <span class="article-hero__tag">Coach Article</span>
      <h1 class="article-hero__title">${escHtml(article.title)}</h1>
      <div class="article-hero__meta">
        <div class="article-hero__author">
          ${avatarHtml}
          <div class="article-hero__author-info">
            <span class="article-hero__author-name">${trainerName}</span>
            <span class="article-hero__author-role">Personal Trainer on <a href="/trainer/${trainerHandle}" style="color:var(--brand);font-weight:500;">FirstRep</a></span>
          </div>
        </div>
        ${dateStr ? `<span><i data-lucide="calendar" style="width:14px;height:14px"></i> ${dateStr}</span>` : ""}
      </div>
      ${coverImg ? `<img class="article-hero__img" src="${coverImg}" alt="${escHtml(article.title)}">` : ""}
    </div>
  </section>

  <div class="article">
    ${bodyHtml}
    ${article.ai_generated ? '<p style="font-size:12px;color:var(--text-muted);text-align:center;margin-top:40px;">AI-assisted content, reviewed by the trainer.</p>' : ""}
  </div>

  <section class="blog-cta">
    <div class="container">
      <h2 class="blog-cta__title">Start coaching smarter today</h2>
      <p class="blog-cta__desc">FirstRep helps personal trainers find clients, build programs with AI, and scale their business. Free for up to 3 clients.</p>
      <div class="blog-cta__badges">
        <a href="#" class="app-badge">
          <span class="app-badge__icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg></span>
          <span class="app-badge__text">
            <span class="app-badge__label">Download on the</span>
            <span class="app-badge__store">App Store</span>
          </span>
        </a>
        <a href="#" class="app-badge">
          <span class="app-badge__icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 0 1-.61-.92V2.734a1 1 0 0 1 .609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.302 2.302a1 1 0 0 1 0 1.38l-2.302 2.302L15.396 13l2.302-2.492zM5.864 2.658L16.8 8.99l-2.302 2.302L5.864 2.658z"/></svg></span>
          <span class="app-badge__text">
            <span class="app-badge__label">Get it on</span>
            <span class="app-badge__store">Google Play</span>
          </span>
        </a>
      </div>
    </div>
  </section>

  <footer class="footer">
    <div class="footer__grid">
      <div>
        <div><img src="/images/brand/firstrep-white.png" alt="FirstRep" class="footer__logo-img"></div>
        <p class="footer__desc">The only platform that finds you clients AND gives you AI tools to coach them. A business-in-a-box for personal trainers.</p>
        <div class="footer__apps">
          <a href="#" class="app-badge">
            <span class="app-badge__icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg></span>
            <span class="app-badge__text">
              <span class="app-badge__label">Download on the</span>
              <span class="app-badge__store">App Store</span>
            </span>
          </a>
          <a href="#" class="app-badge">
            <span class="app-badge__icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 0 1-.61-.92V2.734a1 1 0 0 1 .609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.302 2.302a1 1 0 0 1 0 1.38l-2.302 2.302L15.396 13l2.302-2.492zM5.864 2.658L16.8 8.99l-2.302 2.302L5.864 2.658z"/></svg></span>
            <span class="app-badge__text">
              <span class="app-badge__label">Get it on</span>
              <span class="app-badge__store">Google Play</span>
            </span>
          </a>
        </div>
      </div>
      <div class="footer__col">
        <h4 class="footer__col-title">Features</h4>
        <a href="/features/programming.html">Programming</a>
        <a href="/features/coaching.html">Coaching</a>
        <a href="/features/nutrition.html">Nutrition</a>
        <a href="/features/marketplace.html">Marketplace</a>
        <a href="/features/payments.html">Payments</a>
      </div>
      <div class="footer__col">
        <h4 class="footer__col-title">More Features</h4>
        <a href="/features/communication.html">Communication</a>
        <a href="/features/scheduling.html">Scheduling</a>
        <a href="/features/progress.html">Progress</a>
        <a href="/features/habits.html">Habits</a>
        <a href="/features/business.html">Business Tools</a>
      </div>
      <div class="footer__col">
        <h4 class="footer__col-title">Resources</h4>
        <a href="/blog/index.html">Blog</a>
        <a href="/contact.html">Contact</a>
        <a href="/features.html">All Features</a>
      </div>
      <div class="footer__col">
        <h4 class="footer__col-title">Legal</h4>
        <a href="/privacy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
      </div>
    </div>
    <div class="footer__bottom">
      <div>&copy; 2026 FirstRep. All rights reserved.</div>
      <div class="footer__legal">
        <a href="/privacy.html">Privacy</a>
        <a href="/terms.html">Terms</a>
      </div>
    </div>
  </footer>

  <script>
    if (typeof lucide !== 'undefined') lucide.createIcons();

    var hamburger = document.getElementById('hamburger');
    var mobileMenu = document.getElementById('mobileMenu');
    if (hamburger && mobileMenu) {
      hamburger.addEventListener('click', function() { mobileMenu.classList.toggle('open'); });
    }

    var mobileFeatures = document.getElementById('mobileFeatures');
    var mobileFeaturesList = document.getElementById('mobileFeaturesList');
    if (mobileFeatures && mobileFeaturesList) {
      mobileFeatures.addEventListener('click', function() {
        mobileFeaturesList.classList.toggle('open');
        var icon = mobileFeatures.querySelector('span:last-child');
        if (icon) icon.textContent = mobileFeaturesList.classList.contains('open') ? '−' : '+';
      });
    }

    var featuresToggle = document.getElementById('featuresToggle');
    var megaMenu = document.getElementById('megaMenu');
    var megaOverlay = document.getElementById('megaOverlay');
    var megaTimeout;
    function showMega() { clearTimeout(megaTimeout); megaMenu.classList.add('visible'); megaOverlay.classList.add('visible'); featuresToggle.classList.add('open'); }
    function hideMega() { megaTimeout = setTimeout(function() { megaMenu.classList.remove('visible'); megaOverlay.classList.remove('visible'); featuresToggle.classList.remove('open'); }, 150); }
    if (featuresToggle && megaMenu && megaOverlay) {
      featuresToggle.addEventListener('mouseenter', showMega);
      featuresToggle.addEventListener('mouseleave', hideMega);
      megaMenu.addEventListener('mouseenter', showMega);
      megaMenu.addEventListener('mouseleave', hideMega);
      megaOverlay.addEventListener('click', function() { clearTimeout(megaTimeout); megaMenu.classList.remove('visible'); megaOverlay.classList.remove('visible'); featuresToggle.classList.remove('open'); });
    }
  </script>
</body>
</html>`;
}
