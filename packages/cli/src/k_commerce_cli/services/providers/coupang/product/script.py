from typing import Final

PRODUCT_BODY_LOAD_SCRIPT: Final = """
(() => {
  const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
  const compactText = (node) => normalizeText(node?.textContent || '');
  const moreButton = Array.from(document.querySelectorAll('button, a, div'))
    .find((node) => compactText(node).includes('상품정보 더보기'));
  if (moreButton) {
    moreButton.click();
  }
  const target =
    document.querySelector('#productDetail') ||
    document.querySelector('.product-detail-content') ||
    document.querySelector('[class*="product-detail"]') ||
    document.querySelector('[class*="subType-IMAGE"]') ||
    document.querySelector('#itemBrief') ||
    document.querySelector('[class*="itemBrief"]');
  if (target) {
    target.scrollIntoView({block: 'start', inline: 'nearest'});
    window.scrollBy(0, Math.floor(window.innerHeight * 0.8));
  } else {
    window.scrollTo(0, Math.max(window.scrollY, Math.floor(window.innerHeight * 2)));
  }
  window.dispatchEvent(new Event('scroll'));
  return true;
})()
"""

PRODUCT_DETAIL_SCRIPT: Final = """
(() => {
  const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
  const compactText = (node) => normalizeText(node?.textContent || '');
  const unique = (items) => Array.from(new Set(items.filter(Boolean)));
  const currentUrl = new URL(window.location.href);
  if (currentUrl.hostname.includes('login.coupang.com')) {
    return {state: 'not_logged_in', message: '쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.'};
  }
  const bodyText = document.body?.innerText || '';
  if (bodyText.includes('자동입력') || bodyText.includes('보안문자') || bodyText.includes('captcha')) {
    return {state: 'access_blocked', message: '쿠팡 접근 확인 페이지가 표시되었습니다.'};
  }
  const productMatch = currentUrl.pathname.match(/\\/vp\\/products\\/(\\d+)/);
  if (!productMatch) {
    return {state: 'product_not_found', message: '상품 페이지가 아닙니다.'};
  }
  const readJsonLd = () => {
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const data = JSON.parse(script.textContent || '');
        if (data && (data['@type'] === 'Product' || data.name || data.offers)) {
          return data;
        }
      } catch (error) {
      }
    }
    return {};
  };
  const jsonLd = readJsonLd();
  const offer = Array.isArray(jsonLd.offers) ? jsonLd.offers[0] || {} : jsonLd.offers || {};
  const rating = jsonLd.aggregateRating || {};
  const brand = typeof jsonLd.brand === 'string' ? jsonLd.brand : jsonLd.brand?.name || '';
  const image = Array.isArray(jsonLd.image) ? jsonLd.image[0] || '' : jsonLd.image || '';
  const canonicalUrl =
    document.querySelector('link[rel="canonical"]')?.href ||
    document.querySelector('meta[property="og:url"]')?.content ||
    window.location.href;
  const mainImageUrl =
    image ||
    document.querySelector('meta[property="og:image"]')?.content ||
    document.querySelector('.prod-image img, [class*="prod-image"] img')?.src ||
    '';
  const moreButton = Array.from(document.querySelectorAll('button, a, div'))
    .find((node) => compactText(node).includes('상품정보 더보기'));
  if (moreButton) {
    moreButton.click();
  }
  const requiredInfo = [];
  const infoRoot = document.querySelector('#itemBrief') || document.querySelector('[class*="itemBrief"]');
  if (infoRoot) {
    for (const row of infoRoot.querySelectorAll('tr, li, dl, div')) {
      const cells = Array.from(row.querySelectorAll('th, td, dt, dd, strong, span'))
        .map(compactText)
        .filter(Boolean);
      if (cells.length >= 2) {
        requiredInfo.push({label: cells[0], value: cells.slice(1).join(' ')});
      }
    }
  }
  const detailRoot =
    document.querySelector('.product-detail-content') ||
    document.querySelector('#productDetail') ||
    document.querySelector('[class*="product-detail"]') ||
    document.querySelector('[class*="twc-scroll-mt"]') ||
    document.querySelector('#itemBrief')?.parentElement;
  const isDetailBodyImage = (img) => {
    const detailImageRoot = img.closest('[class*="subType-IMAGE"], .product-detail-content, #productDetail, [class*="product-detail"]');
    if (!detailImageRoot) return false;
    const excluded = img.closest('#wa-header, #wa-sidebar, [class*="prod-atf"], [class*="option-picker"], [class*="also-view-product"], [id*="ad"], [class*="ad-"]');
    return !excluded;
  };
  const detailImages = unique(
    Array.from(document.querySelectorAll('[class*="subType-IMAGE"] img, .product-detail-content img, #productDetail img, [class*="product-detail"] img'))
      .filter(isDetailBodyImage)
      .map((img) => img.currentSrc || img.src || img.dataset?.src || img.getAttribute('data-src') || '')
      .map((src) => src.startsWith('//') ? `https:${src}` : src)
      .filter((src) => src.includes('coupangcdn.com') || src.includes('image/'))
  );
  const headings = Array.from(detailRoot?.querySelectorAll('h2, h3, h4, strong, b') || [])
    .map(compactText)
    .filter((text) => text.length >= 2 && text.length <= 80);
  const sections = unique(headings).slice(0, 12).map((title) => ({title, text: ''}));
  const tables = Array.from(detailRoot?.querySelectorAll('table') || []).slice(0, 5).map((table) => {
    const rows = Array.from(table.querySelectorAll('tr')).map((row) =>
      Array.from(row.querySelectorAll('th, td')).map(compactText).filter(Boolean)
    ).filter((row) => row.length);
    const headers = rows.length ? rows[0] : [];
    return {title: '', headers, rows: rows.slice(1)};
  }).filter((table) => table.headers.length || table.rows.length);
  return {
    state: 'success',
    productId: productMatch[1],
    itemId: currentUrl.searchParams.get('itemId') || '',
    vendorItemId: currentUrl.searchParams.get('vendorItemId') || '',
    canonicalUrl,
    name: jsonLd.name || document.querySelector('meta[property="og:title"]')?.content || compactText(document.querySelector('.prod-buy-header__title')),
    brand,
    description: jsonLd.description || document.querySelector('meta[name="description"]')?.content || '',
    price: offer.price || '',
    currency: offer.priceCurrency || '',
    availability: offer.availability || '',
    ratingValue: rating.ratingValue || '',
    ratingCount: rating.reviewCount || rating.ratingCount || '',
    breadcrumbs: Array.from(document.querySelectorAll('[class*="breadcrumb"] a, .breadcrumb a')).map(compactText).filter(Boolean),
    mainImageUrl,
    requiredInfo,
    detailImages,
    sections,
    tables,
  };
})()
"""
