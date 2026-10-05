// canvas.js - draws diagrams with SVG and handles dragging / clicking.
// It only draws: the levels it uses for layout come from the C++ server
// (hasseLevels), and it never decides whether anything is mathematically right.
var HQ = window.HQ || {};

HQ.Canvas = (function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';
  var WIDTH = 1000, HEIGHT = 620, RADIUS = 28, MARGIN = 60;

  function make(tag, attrs, parent) {
    var el = document.createElementNS(SVG_NS, tag);
    for (var key in attrs) { if (attrs.hasOwnProperty(key)) el.setAttribute(key, attrs[key]); }
    if (parent) parent.appendChild(el);
    return el;
  }

  function edgeKey(a, b) { return a < b ? a + '|' + b : b + '|' + a; }

  function Canvas(svg) {
    this.svg = svg;
    svg.setAttribute('viewBox', '0 0 ' + WIDTH + ' ' + HEIGHT);
    this.nodes = [];            // {label, x, y}
    this.edges = [];            // {a, b} labels (undirected unless this.directed)
    this.levels = null;         // label -> level, when known from the server
    this.directed = false;
    this.mode = 'move';         // 'move' | 'draw' | 'pick'
    this.nodeClasses = {};      // label -> ['minimal', ...]
    this.edgeClasses = {};      // edgeKey -> 'wrong' | 'correct'
    this.badges = {};           // label -> ['min', 'UB', ...]
    this.selected = null;
    this.message = '';
    this.onNodeClick = null;    // function(label)
    this.onEdgeClick = null;    // function(a, b)
    this.onEdgesChanged = null; // function()
    this.bindPointer();
  }

  // ---------- data ----------

  Canvas.prototype.clear = function (message) {
    this.nodes = []; this.edges = []; this.levels = null;
    this.nodeClasses = {}; this.edgeClasses = {}; this.badges = {};
    this.selected = null; this.message = message || '';
    this.render();
  };

  // Hasse layout: y from the server's levels (smaller lower), x spread per level.
  Canvas.prototype.showLayered = function (labels, levelList, pairs) {
    this.levels = {};
    for (var i = 0; i < labels.length; i++) this.levels[labels[i]] = levelList[i];
    this.setNodes(labels);
    this.setEdges(pairs, false);
    this.autoLayout();
  };

  // Elements scattered in rows (used when the player must build the diagram).
  Canvas.prototype.showScattered = function (labels) {
    this.levels = null;
    var shuffled = labels.slice();
    for (var i = shuffled.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = shuffled[i]; shuffled[i] = shuffled[j]; shuffled[j] = t;
    }
    this.setNodes(labels);
    var perRow = Math.min(6, Math.max(1, shuffled.length));
    var rows = Math.ceil(shuffled.length / perRow);
    for (var k = 0; k < shuffled.length; k++) {
      var node = this.find(shuffled[k]);
      var row = Math.floor(k / perRow), col = k % perRow;
      var inRow = Math.min(perRow, shuffled.length - row * perRow);
      node.x = (col + 1) * WIDTH / (inRow + 1) + (row % 2 ? 25 : -25);
      node.y = HEIGHT / 2 + (row - (rows - 1) / 2) * 110;
    }
    this.edges = [];
    this.render();
  };

  // Elements on a circle; used for directed relation graphs.
  Canvas.prototype.showCircle = function (labels, pairs) {
    this.levels = null;
    this.setNodes(labels);
    // Leave room above the circle for self-loops and the caption.
    var n = labels.length, r = HEIGHT / 2 - 95, cy = HEIGHT / 2 + 35;
    for (var i = 0; i < n; i++) {
      var angle = -Math.PI / 2 + 2 * Math.PI * i / Math.max(1, n);
      this.nodes[i].x = WIDTH / 2 + (n === 1 ? 0 : r * Math.cos(angle));
      this.nodes[i].y = cy + (n === 1 ? 0 : r * Math.sin(angle));
    }
    this.setEdges(pairs || [], true);
    this.render();
  };

  Canvas.prototype.setNodes = function (labels) {
    this.nodes = labels.map(function (l) { return { label: l, x: WIDTH / 2, y: HEIGHT / 2 }; });
    this.nodeClasses = {}; this.badges = {}; this.edgeClasses = {};
    this.selected = null; this.message = '';
  };

  Canvas.prototype.setEdges = function (pairs, directed) {
    this.directed = !!directed;
    this.edges = pairs.map(function (p) { return { a: p[0], b: p[1] }; });
  };

  Canvas.prototype.find = function (label) {
    for (var i = 0; i < this.nodes.length; i++) if (this.nodes[i].label === label) return this.nodes[i];
    return null;
  };

  Canvas.prototype.hasEdge = function (a, b) {
    for (var i = 0; i < this.edges.length; i++) {
      var e = this.edges[i];
      if (this.directed ? (e.a === a && e.b === b) : edgeKey(e.a, e.b) === edgeKey(a, b)) return i;
    }
    return -1;
  };

  Canvas.prototype.toggleEdge = function (a, b) {
    var index = this.hasEdge(a, b);
    if (index >= 0) this.edges.splice(index, 1);
    else this.edges.push({ a: a, b: b });
    delete this.edgeClasses[edgeKey(a, b)];
    if (this.onEdgesChanged) this.onEdgesChanged();
    this.render();
  };

  // The player's edges as [lower, upper] using the current picture:
  // the node drawn lower on screen is the smaller element.
  Canvas.prototype.orientedEdges = function () {
    var result = { pairs: [], flat: [] };
    for (var i = 0; i < this.edges.length; i++) {
      var a = this.find(this.edges[i].a), b = this.find(this.edges[i].b);
      if (Math.abs(a.y - b.y) < 12) result.flat.push([a.label, b.label]);
      if (a.y >= b.y) result.pairs.push([a.label, b.label]);
      else result.pairs.push([b.label, a.label]);
    }
    return result;
  };

  // ---------- layout ----------

  // With server levels: one row per level, ordered to reduce crossings
  // (each node placed near the average x of the nodes it joins below).
  // Without levels: nodes at similar heights form a row and are spread out.
  Canvas.prototype.autoLayout = function () {
    if (this.nodes.length === 0) return;
    var rows = this.levels ? this.rowsFromLevels() : this.rowsFromPositions();
    var usable = HEIGHT - 2 * MARGIN;
    for (var r = 0; r < rows.length; r++) {
      var row = rows[r];
      if (this.levels) {
        var self = this;
        row.forEach(function (node) { node.order = self.barycenter(node); });
        row.sort(function (p, q) { return p.order - q.order; });
      } else {
        row.sort(function (p, q) { return p.x - q.x; });
      }
      var y = this.levels ? HEIGHT - MARGIN - (rows.length === 1 ? usable / 2 : r * usable / (rows.length - 1))
                          : row.reduce(function (s, n) { return s + n.y; }, 0) / row.length;
      for (var i = 0; i < row.length; i++) {
        row[i].x = (i + 1) * WIDTH / (row.length + 1);
        row[i].y = y;
      }
    }
    this.render();
  };

  Canvas.prototype.rowsFromLevels = function () {
    var rows = [];
    for (var i = 0; i < this.nodes.length; i++) {
      var level = this.levels[this.nodes[i].label] || 0;
      while (rows.length <= level) rows.push([]);
      rows[level].push(this.nodes[i]);
    }
    return rows.filter(function (r) { return r.length > 0; });
  };

  Canvas.prototype.rowsFromPositions = function () {
    var sorted = this.nodes.slice().sort(function (p, q) { return q.y - p.y; });
    var rows = [[sorted[0]]];
    for (var i = 1; i < sorted.length; i++) {
      var last = rows[rows.length - 1];
      if (Math.abs(last[0].y - sorted[i].y) < 55) last.push(sorted[i]);
      else rows.push([sorted[i]]);
    }
    return rows;
  };

  // Average x of the neighbours on lower levels (or current x if none).
  Canvas.prototype.barycenter = function (node) {
    var total = 0, count = 0, self = this;
    this.edges.forEach(function (e) {
      var other = e.b === node.label ? e.a : (e.a === node.label ? e.b : null);
      if (other !== null && self.levels[other] < self.levels[node.label]) {
        total += self.find(other).x; count++;
      }
    });
    return count ? total / count : node.x;
  };

  // ---------- drawing ----------

  Canvas.prototype.render = function () {
    var svg = this.svg;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var defs = make('defs', {}, svg);
    var marker = make('marker', { id: 'arrow', viewBox: '0 0 10 10', refX: '9', refY: '5',
                                 markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse' }, defs);
    make('path', { d: 'M0,0 L10,5 L0,10 z', 'class': 'arrow-head' }, marker);
    if (this.nodes.length === 0) {
      var t = make('text', { x: WIDTH / 2, y: HEIGHT / 2, 'class': 'empty-text' }, svg);
      t.textContent = this.message || 'Nothing to draw yet.';
      return;
    }
    for (var i = 0; i < this.edges.length; i++) this.drawEdge(this.edges[i]);
    for (var k = 0; k < this.nodes.length; k++) this.drawNode(this.nodes[k]);
    if (this.message) {
      var m = make('text', { x: WIDTH / 2, y: 30, 'class': 'empty-text' }, svg);
      m.textContent = this.message;
    }
  };

  Canvas.prototype.drawEdge = function (edge) {
    var a = this.find(edge.a), b = this.find(edge.b);
    if (!a || !b) return;
    var cls = 'edge' + (this.directed ? ' directed' : '');
    var extra = this.edgeClasses[edgeKey(edge.a, edge.b)];
    if (extra) cls += ' ' + extra;
    var group = make('g', { 'data-a': edge.a, 'data-b': edge.b, 'class': 'edge-group' }, this.svg);
    if (a === b) {                       // self-loop (directed graphs only)
      var d = 'M' + (a.x - 12) + ',' + (a.y - RADIUS + 4) + ' C' + (a.x - 40) + ',' + (a.y - 90) + ' ' +
              (a.x + 40) + ',' + (a.y - 90) + ' ' + (a.x + 12) + ',' + (a.y - RADIUS + 4);
      make('path', { d: d, fill: 'none', 'class': cls, 'marker-end': 'url(#arrow)' }, group);
      make('path', { d: d, fill: 'none', 'class': 'edge-hit' }, group);
      return;
    }
    var dx = b.x - a.x, dy = b.y - a.y, len = Math.sqrt(dx * dx + dy * dy) || 1;
    var shrink = this.directed ? RADIUS + 4 : 0;
    var x1 = a.x + dx / len * shrink, y1 = a.y + dy / len * shrink;
    var x2 = b.x - dx / len * shrink, y2 = b.y - dy / len * shrink;
    var line = make('line', { x1: x1, y1: y1, x2: x2, y2: y2, 'class': cls }, group);
    if (this.directed) line.setAttribute('marker-end', 'url(#arrow)');
    make('line', { x1: x1, y1: y1, x2: x2, y2: y2, 'class': 'edge-hit' }, group);
  };

  Canvas.prototype.drawNode = function (node) {
    var classes = (this.nodeClasses[node.label] || []).slice();
    if (this.selected === node.label) classes.push('selected');
    var g = make('g', { 'class': 'node ' + classes.join(' '), 'data-label': node.label,
                        transform: 'translate(' + node.x + ',' + node.y + ')' }, this.svg);
    if (classes.indexOf('extreme') >= 0) make('circle', { r: RADIUS + 8, 'class': 'ring' }, g);
    make('circle', { r: RADIUS, 'class': 'body' }, g);
    var text = make('text', { x: 0, y: 1 }, g);
    text.textContent = node.label;
    if (node.label.length > 3) text.setAttribute('style', 'font-size:' + (node.label.length > 4 ? 14 : 17) + 'px');
    var badges = this.badges[node.label];
    if (badges && badges.length) {
      var b = make('text', { x: 0, y: RADIUS + 22, 'class': 'badge-text' }, g);
      b.textContent = badges.join(' · ');
    }
  };

  // ---------- pointer handling: drag to move, click to select ----------

  Canvas.prototype.toSvgPoint = function (event) {
    var point = this.svg.createSVGPoint();
    point.x = event.clientX; point.y = event.clientY;
    return point.matrixTransform(this.svg.getScreenCTM().inverse());
  };

  Canvas.prototype.bindPointer = function () {
    var self = this, drag = null;
    this.svg.addEventListener('pointerdown', function (event) {
      var nodeEl = event.target.closest ? event.target.closest('.node') : null;
      if (nodeEl) {
        var p = self.toSvgPoint(event);
        drag = { node: self.find(nodeEl.getAttribute('data-label')), startX: p.x, startY: p.y, moved: false };
        self.svg.setPointerCapture(event.pointerId);
        return;
      }
      var edgeEl = event.target.closest ? event.target.closest('.edge-group') : null;
      if (edgeEl) self.handleEdgeClick(edgeEl.getAttribute('data-a'), edgeEl.getAttribute('data-b'));
    });
    this.svg.addEventListener('pointermove', function (event) {
      if (!drag) return;
      var p = self.toSvgPoint(event);
      if (!drag.moved && Math.abs(p.x - drag.startX) + Math.abs(p.y - drag.startY) < 5) return;
      drag.moved = true;
      drag.node.x = Math.max(RADIUS, Math.min(WIDTH - RADIUS, p.x));
      drag.node.y = Math.max(RADIUS, Math.min(HEIGHT - RADIUS, p.y));
      self.render();
    });
    var finish = function () {
      if (drag && !drag.moved) self.handleNodeClick(drag.node.label);
      drag = null;
    };
    this.svg.addEventListener('pointerup', finish);
    this.svg.addEventListener('pointercancel', function () { drag = null; });
  };

  Canvas.prototype.handleNodeClick = function (label) {
    if (this.mode === 'draw') {
      if (this.selected === null) {
        this.selected = label;
      } else if (this.selected === label && !this.directed) {
        this.selected = null;
      } else {
        var from = this.selected;
        this.selected = null;
        this.toggleEdge(from, label);
        return;
      }
      this.render();
      return;
    }
    if (this.onNodeClick) this.onNodeClick(label);
  };

  Canvas.prototype.handleEdgeClick = function (a, b) {
    if (this.mode === 'draw') this.toggleEdge(a, b);
    else if (this.onEdgeClick) this.onEdgeClick(a, b);
  };

  Canvas.edgeKey = edgeKey;
  return Canvas;
})();
