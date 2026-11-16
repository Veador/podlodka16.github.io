// Terminal theme runtime: types the slide headline character by character when
// moving forward; the rest of the slide appears as soon as typing ends.
// Only observes the deck's own show()/next(); going back shows headlines at once.
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const stage = document.getElementById('stage');
  const S = [...stage.querySelectorAll(':scope > section')];
  const FORWARD_KEYS = ['ArrowRight', 'PageDown', ' '];
  const MS_PER_CHAR = 26, MAX_MS = 850;
  // Slides whose content is all click-builds: reveal the first build group as
  // soon as the headline is typed, so the slide is never empty after typing.
  const AUTO_FIRST_BUILD = new Set(['slide-03', 'slide-13', 'slide-14', 'slide-18']);
  let job = null;

  // Headline pieces in reading order: text nodes are typed letter by letter,
  // a <br> counts as one step and stays hidden until typing reaches it
  // (otherwise the cursor sits on the second line from the start).
  function pieces(heading) {
    const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: n => (n.nodeType === 3 || n.tagName === 'BR') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP,
    });
    const out = [];
    while (walker.nextNode()) {
      const n = walker.currentNode;
      if (n.nodeType === 3) {
        const full = n.textContent;
        out.push({ len: full.length, set: k => { n.textContent = full.slice(0, k); } });
      } else {
        out.push({ len: 1, set: k => { n.style.display = k ? '' : 'none'; } });
      }
    }
    return out;
  }

  function render(parts, count) {
    let left = count;
    parts.forEach(p => {
      const take = Math.max(0, Math.min(p.len, left));
      p.set(take);
      left -= take;
    });
  }

  function finish() {
    if (!job) return;
    cancelAnimationFrame(job.raf);
    render(job.parts, job.total);
    job.heading.classList.remove('typing');
    job.heading.style.minHeight = '';
    job.waiting.forEach(el => el.classList.remove('wait'));
    job = null;
  }

  // Typing ended on its own or was skipped: show content, then the first build
  // group on the slides listed in AUTO_FIRST_BUILD.
  function complete() {
    const sec = job && job.sec;
    finish();
    if (sec && sec.classList.contains('on') && AUTO_FIRST_BUILD.has(sec.dataset.notesId)
        && sec.querySelector('.build:not(.shown)')) next();
  }

  // Everything after the headline in reading order: following siblings of the
  // headline and of each of its ancestors up to the slide.
  function contentAfter(heading, sec) {
    const out = [];
    for (let el = heading; el && el !== sec; el = el.parentElement) {
      for (let sib = el.nextElementSibling; sib; sib = sib.nextElementSibling) if (!sib.classList.contains('quote')) out.push(sib);
    }
    return out;
  }

  function type(sec) {
    if (sec.classList.contains('cover')) return;
    const heading = sec.querySelector('h1,h2');
    if (!heading) return;
    const parts = pieces(heading);
    const total = parts.reduce((sum, p) => sum + p.len, 0);
    if (!total) return;

    // Reserve the final height so a centred layout does not jump when the
    // headline wraps to its second line mid-typing (slide 21).
    heading.style.minHeight = heading.offsetHeight + 'px';
    const waiting = contentAfter(heading, sec);
    // "reveal" carries the fade-in transition, so removing "wait" fades the content in.
    waiting.forEach(el => el.classList.add('wait', 'reveal'));
    // Content above the headline (slide 20's lead-in line) is shown at once, by the owner's choice.
    render(parts, 0);
    heading.classList.add('typing');

    const perChar = Math.min(MS_PER_CHAR, MAX_MS / total);
    const t0 = performance.now();
    job = { sec, heading, parts, total, waiting, raf: 0 };
    const step = now => {
      const shown = Math.min(total, Math.floor((now - t0) / perChar) + 1);
      render(parts, shown);
      if (shown >= total) { complete(); return; }
      job.raf = requestAnimationFrame(step);
    };
    job.raf = requestAnimationFrame(step);
  }

  // Slide changes: the observer runs before the next paint, so the full
  // headline never flashes.
  let cur = S.findIndex(s => s.classList.contains('on'));
  const observer = new MutationObserver(() => {
    const n = S.findIndex(s => s.classList.contains('on'));
    if (n < 0 || n === cur) return;
    const forward = n > cur;
    cur = n;
    finish();
    if (forward) type(S[n]);
  });
  S.forEach(s => observer.observe(s, { attributes: true, attributeFilter: ['class'] }));

  // A forward press while typing completes the headline instead of advancing.
  document.addEventListener('keydown', e => {
    if (!job || !FORWARD_KEYS.includes(e.key)) return;
    if (e.target instanceof Element && e.target.closest('textarea,input,select,audio,[contenteditable="true"]')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    complete();
  }, true);
  document.addEventListener('click', e => {
    if (!job || !(e.target instanceof Element) || !e.target.closest('#next')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    complete();
  }, true);
})();
