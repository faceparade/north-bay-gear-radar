from __future__ import annotations


_FACEBOOK = r'''(()=>{
  const links=[...document.querySelectorAll('a[href*="/marketplace/item/"]')];
  const seen=new Set(), listings=[];
  for(const a of links){
    const m=a.href.match(/\/marketplace\/item\/(\d+)/);
    if(!m||seen.has(m[1])) continue;
    const text=(a.innerText||a.getAttribute('aria-label')||'').trim();
    if(!text) continue;
    seen.add(m[1]);
    const lines=text.split('\n').map(x=>x.trim()).filter(Boolean);
    const price=(text.match(/\$[\d,.]+/)||[])[0]||'';
    const title=lines.filter(x=>x!==price)[0]||text;
    const location=lines.find(x=>/\b(mi|miles|Novato|San Rafael|Petaluma|Sonoma|Marin)\b/i.test(x))||'';
    listings.push({id:m[1],url:a.href,title,price,location});
  }
  return {listings,listing_ids:[...seen],has_next:false,next_url:null,
    has_numbered_pages:false,
    has_load_more:[...document.querySelectorAll('button,a')].some(x=>/load more|see more results/i.test(x.innerText||'')),
    scroll_height:document.documentElement.scrollHeight};
})()'''

_EBAY = r'''(()=>{
  const anchors=[...document.querySelectorAll('a[href*="/itm/"]')];
  const seen=new Set(), listings=[];
  for(const a of anchors){
    const m=a.href.match(/\/itm\/(?:[^/?]+\/)?(\d{9,15})/);
    if(!m||m[1]==='123456'||seen.has(m[1])) continue;
    const scope=a.closest('.su-card-container,.s-item,li,article')||a.parentElement;
    const text=(scope?.innerText||'').trim();
    const titleNode=scope?.querySelector('.s-card__title,.s-item__title,[role="heading"]');
    const imageAlt=scope?.querySelector('img[alt]')?.getAttribute('alt')||'';
    const title=(titleNode?.innerText||imageAlt||a.getAttribute('aria-label')||a.innerText||'')
      .replace(/Opens in a new window or tab/g,'').trim();
    if(!title||title==='Shop on eBay'||/^Sold\s+/i.test(title)) continue;
    seen.add(m[1]);
    const price=(text.match(/\$[\d,]+(?:\.\d{2})?(?:\s+to\s+\$[\d,]+(?:\.\d{2})?)?/)||[])[0]||'';
    const location=(text.match(/Located in[^\n]*/i)||[])[0]||'';
    listings.push({id:m[1],url:a.href,title,price,location});
  }
  const next=document.querySelector('a.pagination__next');
  return {listings,listing_ids:[...seen],
    has_next:!!next && next.getAttribute('aria-disabled')!=='true',next_url:next?.href||null,
    has_numbered_pages:document.querySelectorAll('.pagination__items a').length>0,
    has_load_more:[...document.querySelectorAll('button,a')].some(x=>/load more|show more results/i.test(x.innerText||'')),
    scroll_height:document.documentElement?.scrollHeight||0};
})()'''


def extractor_script(source: str) -> str:
    if source == "facebook":
        return _FACEBOOK
    if source == "ebay":
        return _EBAY
    raise ValueError(f"unsupported browser source: {source}")
