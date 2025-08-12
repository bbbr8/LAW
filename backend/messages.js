const store = {};

function encode(text) {
  if (typeof btoa === 'function') {
    return btoa(unescape(encodeURIComponent(text)));
  }
  return Buffer.from(text, 'utf8').toString('base64');
}

function decode(text) {
  if (typeof atob === 'function') {
    return decodeURIComponent(escape(atob(text)));
  }
  return Buffer.from(text, 'base64').toString('utf8');
}

export function addMessage(caseId, { text, author = 'unknown', internal = false }) {
  const encoded = encode(text);
  // Older Node runtimes don't expose `crypto.randomUUID` globally. Mirror the
  // fallback logic used in `tasks.js` so message IDs are still generated
  // without blowing up when `crypto` is missing.
  const id = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
  const msg = {
    id,
    text: encoded,
    author,
    internal: !!internal,
    createdAt: new Date().toISOString(),
  };
  store[caseId] = store[caseId] || [];
  store[caseId].push(msg);
  return msg.id;
}

export function getMessages(caseId, viewerRole = 'client') {
  const msgs = store[caseId] || [];
  return msgs
    .filter((m) => viewerRole === 'lawyer' || !m.internal)
    .map((m) => ({
      ...m,
      text: decode(m.text),
    }));
}
