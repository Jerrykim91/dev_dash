'use strict';

const ReadingShelf = (() => {
  const $ = (id) => document.getElementById(id);
  const storageKey = 'devnest.readingShelf.v1';
  const colors = Object.freeze(['rose','peach','lemon','mint','sky','violet','cream']);
  let books = [];
  let selectedId = null;

  const text = (value, max = 80) => typeof value === 'string' ? value.trim().slice(0, max) : '';
  const year = (value, fallback = new Date().getFullYear()) => {
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed >= 1900 && parsed <= 2100 ? parsed : fallback;
  };
  function normalizeBook(value) {
    if (!value || typeof value !== 'object') return null;
    const title = text(value.title, 80);
    if (!title) return null;
    const finishedAt = /^\d{4}-\d{2}-\d{2}$/.test(value.finishedAt || '') ? value.finishedAt : '';
    return {
      id: text(value.id, 80) || `book-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
      title,
      author: text(value.author, 60),
      finishedAt,
      year: year(value.year || finishedAt.slice(0,4)),
      rating: Math.min(5, Math.max(0, Number(value.rating) || 0)),
      note: text(value.note, 240),
      color: colors.includes(value.color) ? value.color : 'cream'
    };
  }
  function read() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) || '[]');
      return Array.isArray(parsed) ? parsed.map(normalizeBook).filter(Boolean).slice(0, 240) : [];
    } catch { return []; }
  }
  function write() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(books));
      $('reading-storage-status').textContent = '독서 기록 저장됨';
    } catch {
      $('reading-storage-status').textContent = '브라우저 저장 공간에 기록하지 못했습니다.';
    }
  }
  function activeYear() { return year($('reading-year').value); }
  function booksForYear(targetYear = activeYear()) {
    return books.filter((book) => book.year === targetYear).sort((a,b) => (a.finishedAt || '9999').localeCompare(b.finishedAt || '9999') || a.title.localeCompare(b.title, 'ko'));
  }
  function spine(book, index, miniature = false) {
    const node = document.createElement(miniature ? 'i' : 'button');
    node.className = miniature ? `scene-book book-${book.color}` : `reading-book book-${book.color}`;
    node.style.setProperty('--book-height', `${82 + (index % 5) * 4}%`);
    if (!miniature) {
      node.type = 'button';
      node.dataset.bookId = book.id;
      node.setAttribute('aria-label', `${book.title}${book.author ? ` · ${book.author}` : ''} 편집`);
      const label = document.createElement('span');
      label.textContent = book.title;
      node.append(label);
      node.addEventListener('click', () => edit(book.id));
    }
    return node;
  }
  function render() {
    const current = booksForYear();
    const shelf = $('reading-bookshelf');
    shelf.replaceChildren();
    const capacity = Math.max(48, Math.ceil(current.length / 12) * 12);
    for (let index = 0; index < capacity; index += 1) {
      if (current[index]) shelf.append(spine(current[index], index));
      else {
        const empty = document.createElement('button');
        empty.type = 'button';
        empty.className = 'reading-book is-empty';
        empty.setAttribute('aria-label', `${index + 1}번 빈 책등에 완독 책 추가`);
        empty.addEventListener('click', newBook);
        shelf.append(empty);
      }
    }
    $('reading-count').textContent = `${current.length}권 완독`;
    $('scene-reading-count').textContent = String(booksForYear(new Date().getFullYear()).length);
    const preview = $('scene-reading-preview');
    preview.replaceChildren(...booksForYear(new Date().getFullYear()).slice(-14).map((book,index) => spine(book,index,true)));
    if (!preview.childElementCount) preview.append(Object.assign(document.createElement('i'), { className:'scene-book is-empty' }));
  }
  function setForm(book) {
    selectedId = book?.id || null;
    $('reading-book-id').value = selectedId || '';
    $('reading-title').value = book?.title || '';
    $('reading-author').value = book?.author || '';
    $('reading-finished-at').value = book?.finishedAt || `${activeYear()}-01-01`;
    $('reading-rating').value = String(book?.rating || 0);
    $('reading-color').value = book?.color || colors[booksForYear().length % colors.length];
    $('reading-note').value = book?.note || '';
    $('reading-form-heading').textContent = book ? '책 정보 수정' : '완독 책 추가';
    $('delete-reading-book').disabled = !book;
  }
  function newBook() { setForm(null); $('reading-title').focus({ preventScroll:true }); }
  function edit(id) {
    const book = books.find((item) => item.id === id);
    if (book) setForm(book);
  }
  function save(event) {
    event.preventDefault();
    const finishedAt = $('reading-finished-at').value;
    const book = normalizeBook({
      id: selectedId || undefined,
      title: $('reading-title').value,
      author: $('reading-author').value,
      finishedAt,
      year: finishedAt ? finishedAt.slice(0,4) : activeYear(),
      rating: $('reading-rating').value,
      color: $('reading-color').value,
      note: $('reading-note').value
    });
    if (!book) return;
    const index = books.findIndex((item) => item.id === selectedId);
    if (index >= 0) books[index] = book; else books.push(book);
    $('reading-year').value = String(book.year);
    selectedId = book.id;
    write(); render(); setForm(book);
  }
  function remove(id = selectedId) {
    const before = books.length;
    books = books.filter((book) => book.id !== id);
    if (books.length === before) return false;
    selectedId = null; write(); render(); setForm(null); return true;
  }
  function add(value) {
    const book = normalizeBook(value);
    if (!book) return null;
    books.push(book); write(); render(); return book;
  }
  function open() {
    if (!$('reading-shelf-dialog').open) $('reading-shelf-dialog').showModal();
    render();
  }

  books = read();
  $('reading-year').value = String(new Date().getFullYear());
  $('reading-year').addEventListener('change', () => { render(); setForm(null); });
  $('reading-book-form').addEventListener('submit', save);
  $('new-reading-book').addEventListener('click', newBook);
  $('delete-reading-book').addEventListener('click', () => remove());
  $('close-reading-shelf').addEventListener('click', () => $('reading-shelf-dialog').close());
  $('reading-shelf-entry').addEventListener('click', open);
  render(); setForm(null);

  return Object.freeze({
    open, add, remove,
    get books() { return books.map((book) => ({ ...book })); },
    get storageKey() { return storageKey; }
  });
})();
