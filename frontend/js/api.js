// api.js - fetch wrappers for the HasseQuest C++ server.
// Requests are form-encoded (URLSearchParams); replies are JSON.
// Every call resolves to an object with "ok": network problems and
// unexpected replies become friendly {ok:false, error:...} objects, so the
// UI never shows a raw server error.
var HQ = window.HQ || {};

HQ.api = (function () {
  'use strict';

  function friendlyFailure(message) {
    return { ok: false, error: message, field: '' };
  }

  function readReply(response) {
    return response.json().catch(function () {
      return friendlyFailure('The server sent an unexpected reply (status ' + response.status + ').');
    });
  }

  function networkError() {
    return friendlyFailure('Cannot reach the HasseQuest server. Is hassequest.exe still running?');
  }

  function post(path, fields) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(fields || {}).toString()
    }).then(readReply, networkError);
  }

  function get(path, query) {
    var url = query ? path + '?' + new URLSearchParams(query).toString() : path;
    return fetch(url).then(readReply, networkError);
  }

  return {
    analyze: function (fields) { return post('/api/analyze', fields); },
    bounds: function (fields) { return post('/api/bounds', fields); },
    checkHasse: function (fields) { return post('/api/check-hasse', fields); },
    levels: function () { return get('/api/levels'); },
    level: function (id) { return get('/api/levels/' + id); },
    checkLevel: function (id, answer) { return post('/api/levels/' + id + '/check', { answer: answer }); },
    hint: function (id) { return post('/api/levels/' + id + '/hint', {}); },
    generate: function (query) { return get('/api/generate', query); },
    score: function () { return get('/api/score'); },
    reset: function () { return post('/api/reset', {}); },
    unlockAll: function () { return post('/api/unlock-all', {}); }
  };
})();
