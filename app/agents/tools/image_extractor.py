"""Supplier logo and product image extraction via Browserbase + Playwright.

Navigates supplier websites to extract:
- Company logo (favicon, og:image, header/nav logo element)
- Product images from homepage hero/gallery sections

Stores as direct URLs — no S3/storage needed for MVP.
"""

import logging
from urllib.parse import urlparse, urljoin

from pydantic import BaseModel, Field

from app.agents.tools.browserbase_service import _with_page, _is_configured, _dismiss_cookie_banner, _scroll_page, PAGE_LOAD_TIMEOUT_MS

logger = logging.getLogger(__name__)


class SupplierImageSet(BaseModel):
    """Extracted images from a supplier's website."""
    logo_url: str | None = None
    favicon_url: str | None = None
    og_image_url: str | None = None
    product_images: list[str] = Field(default_factory=list)
    hero_image_url: str | None = None
    source: str = "browserbase_extraction"


# JavaScript to extract logo and image URLs from the current page
_EXTRACT_IMAGES_JS = """
() => {
    const results = {
        logo_url: null,
        favicon_url: null,
        og_image_url: null,
        hero_image_url: null,
        product_images: [],
    };

    // 1. og:image meta tag
    const ogImage = document.querySelector('meta[property="og:image"]');
    if (ogImage && ogImage.content) {
        results.og_image_url = ogImage.content;
    }

    // 2. Twitter card image
    const twitterImage = document.querySelector('meta[name="twitter:image"]');
    if (twitterImage && twitterImage.content && !results.og_image_url) {
        results.og_image_url = twitterImage.content;
    }

    // 3. Favicon / apple-touch-icon (prefer larger sizes)
    const icons = document.querySelectorAll(
        'link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"], link[rel="apple-touch-icon-precomposed"]'
    );
    let bestIcon = null;
    let bestIconSize = 0;
    icons.forEach(icon => {
        const size = icon.sizes ? parseInt(icon.sizes.toString().split('x')[0]) : 16;
        if (size > bestIconSize) {
            bestIconSize = size;
            bestIcon = icon.href;
        }
    });
    if (bestIcon) {
        results.favicon_url = bestIcon;
    }

    // 4. Header/nav logo — largest img in header, nav, or logo-classed elements
    const logoSelectors = [
        'header img[src]',
        'nav img[src]',
        '[class*="logo"] img[src]',
        '[id*="logo"] img[src]',
        '[class*="brand"] img[src]',
        '[class*="header"] img[src]',
        'a[href="/"] img[src]',
        'a[href="./"] img[src]',
    ];
    let bestLogo = null;
    let bestLogoArea = 0;
    for (const sel of logoSelectors) {
        const imgs = document.querySelectorAll(sel);
        imgs.forEach(img => {
            const w = img.naturalWidth || img.width || 0;
            const h = img.naturalHeight || img.height || 0;
            const area = w * h;
            // Logo should be reasonably sized (not a tiny icon, not a giant hero)
            if (area > bestLogoArea && w < 600 && h < 300 && w > 20 && h > 20) {
                bestLogoArea = area;
                bestLogo = img.src;
            }
        });
    }
    if (bestLogo) {
        results.logo_url = bestLogo;
    }

    // 5. Product / hero images — significant images on the page
    const allImgs = document.querySelectorAll('img[src]');
    const seen = new Set();
    const candidates = [];
    allImgs.forEach(img => {
        const src = img.src;
        if (!src || seen.has(src)) return;
        if (src.startsWith('data:')) return;
        seen.add(src);

        const w = img.naturalWidth || img.width || 0;
        const h = img.naturalHeight || img.height || 0;

        // Skip tiny images (icons, spacers)
        if (w < 100 || h < 100) return;
        // Skip the logo we already found
        if (src === bestLogo) return;

        candidates.push({
            src,
            area: w * h,
            isHero: w > 600 && h > 300,
        });
    });

    // Sort by area descending
    candidates.sort((a, b) => b.area - a.area);

    // First large image is the hero
    if (candidates.length > 0 && candidates[0].isHero) {
        results.hero_image_url = candidates[0].src;
    }

    // Top 5 product-sized images
    results.product_images = candidates
        .filter(c => !c.isHero || candidates.length <= 1)
        .slice(0, 5)
        .map(c => c.src);

    // If no dedicated product images but we have a hero, include it
    if (results.product_images.length === 0 && results.hero_image_url) {
        results.product_images = [results.hero_image_url];
    }

    return results;
}
"""


async def extract_supplier_images(
    website_url: str,
) -> SupplierImageSet:
    """Extract logo and product images from a supplier's website.

    Strategy:
    1. Navigate to homepage
    2. Dismiss cookie banners
    3. Scroll to load lazy images
    4. Extract via DOM evaluation:
       - Favicon / apple-touch-icon
       - og:image / twitter:image meta tags
       - Header/nav logo element
       - Product/hero images (large images on page)
    5. Resolve relative URLs to absolute

    Args:
        website_url: The supplier's website URL.

    Returns:
        SupplierImageSet with extracted URLs.
    """
    if not _is_configured():
        logger.debug("Browserbase not configured — skipping image extraction")
        return SupplierImageSet()

    logger.info("  [ImageExtractor] Extracting images from: %s", website_url)

    async def _extract(page):
        # Navigate to homepage
        await page.goto(
            website_url,
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )

        # Dismiss cookie banners
        await _dismiss_cookie_banner(page)

        # Scroll to trigger lazy-loaded images
        await _scroll_page(page, scroll_count=3)

        # Wait for images to load
        await page.wait_for_timeout(1000)

        # Extract images via JavaScript
        raw = await page.evaluate(_EXTRACT_IMAGES_JS)

        if not raw:
            logger.warning("  [ImageExtractor] No images extracted from %s", website_url)
            return SupplierImageSet()

        # Resolve relative URLs
        def resolve_url(u):
            if not u:
                return None
            if u.startswith("http"):
                return u
            return urljoin(website_url, u)

        return SupplierImageSet(
            logo_url=resolve_url(raw.get("logo_url")),
            favicon_url=resolve_url(raw.get("favicon_url")),
            og_image_url=resolve_url(raw.get("og_image_url")),
            product_images=[
                resolve_url(img) for img in raw.get("product_images", [])
                if resolve_url(img)
            ],
            hero_image_url=resolve_url(raw.get("hero_image_url")),
        )

    result = await _with_page(_extract)

    if result is None:
        logger.warning("  [ImageExtractor] Session failed for %s", website_url)
        return SupplierImageSet()

    # Pick the best available logo
    if not result.logo_url:
        result.logo_url = result.og_image_url or result.favicon_url

    logger.info(
        "  [ImageExtractor] Extracted from %s: logo=%s, products=%d, hero=%s",
        website_url,
        bool(result.logo_url),
        len(result.product_images),
        bool(result.hero_image_url),
    )
    return result
