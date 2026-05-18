import re

with open('/tmp/graph-editor.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update toolbar HTML
toolbar_html_old = """  <button class="btn" id="btn-add">+ Node</button>
  <button class="btn" id="btn-connect">Verbinden</button>
  <button class="btn danger" id="btn-delete">✕</button>"""

toolbar_html_new = """  <div class="tool-group" style="display:flex; border:1px solid var(--border); border-radius:4px; overflow:hidden">
    <button class="btn active" id="tool-move" style="border-radius:0; border:none; border-right:1px solid var(--border)" title="Knoten verschieben">✋ Move</button>
    <button class="btn" id="tool-connect" style="border-radius:0; border:none; border-right:1px solid var(--border)" title="Drag & Drop zum Verbinden">🔗 Connect</button>
    <button class="btn" id="tool-delete" style="border-radius:0; border:none;" title="Knoten durch Klick löschen">🗑 Delete</button>
  </div>
  <button class="btn" id="btn-add">+ Node</button>"""

text = text.replace(toolbar_html_old, toolbar_html_new)

# Remove old Event Listeners for btn-connect and btn-delete
text = re.sub(r"\$\('btn-connect'\)\.addEventListener\('click', toggleConnect\);", "", text)
text = re.sub(r"\$\('btn-delete'\)\.addEventListener\('click', \(\) => \{[\s\S]*?\}\);", "", text)
text = re.sub(r"function toggleConnect\(\) \{[\s\S]*?\}\n", "", text)
text = re.sub(r"async function handleConnectClick\(nodeId\) \{[\s\S]*?return;\n\}", "", text)


# Update State
text = text.replace("connectMode: false,", "toolMode: 'move', // move, connect, delete")

# Add Logic for tools
js_additions = """
// ── TOOLS ────────────────────────────────────────────────────────────────────
function setTool(tool) {
  S.toolMode = tool;
  S.connectSrc = null;
  document.querySelectorAll('.tool-group .btn').forEach(b => b.classList.remove('active'));
  $(`tool-${tool}`).classList.add('active');
  renderAllNodes();
  if (tool === 'move') setStatus('Modus: Verschieben (Drag & Drop)');
  else if (tool === 'connect') setStatus('Modus: Verbinden (Von Node A nach Node B ziehen)');
  else if (tool === 'delete') setStatus('Modus: Löschen (Node anklicken)');
}

$('tool-move').addEventListener('click', () => setTool('move'));
$('tool-connect').addEventListener('click', () => setTool('connect'));
$('tool-delete').addEventListener('click', () => setTool('delete'));

let activeConnectionLine = null;

async function doConnect(srcId, tgtId) {
  if (srcId === tgtId) return;
  const existing = S.edges.find(e => e.from === srcId && e.to === tgtId);
  if (existing) { setStatus('Verbindung existiert bereits.', 'warn'); return; }
  
  const fromNode = findNode(srcId);
  const toNode   = findNode(tgtId);
  if (fromNode.floor !== toNode.floor) {
    if (!['staircase','elevator'].includes(fromNode.nodeType) && !['staircase','elevator'].includes(toNode.nodeType)) {
      if (!confirm('Unterschiedliche Stockwerke verbinden (ohne Treppe/Aufzug)?')) return;
    }
  }
  
  const res = await openModal('edge', {
    title: `Verbindung: ${srcId} → ${tgtId}`,
    sub: 'Beispiel: front, back, left, right, up, down',
    dir: 'front', edgeId: `e-${S.edgeCounter++}`
  });
  if (!res || !res.dir) { setStatus('Verbindung abgebrochen', 'warn'); return; }
  
  S.edges.push({ id: res.edgeId, from: srcId, to: tgtId, direction: res.dir });
  renderSVG();
  setStatus(`Verbindung ${srcId} → ${tgtId} (${res.dir}) erstellt.`, 'success');
}
"""

text = text.replace("// ── CONNECT MODE ──────────────────────────────────────────────────────────────", js_additions)


# Rewrite onNodeMouseDown, onDragMove, onDragUp
mouse_down_old = r"""function onNodeMouseDown\(e, nodeId\) \{
  e\.stopPropagation\(\);
  if \(e\.button !== 0 \|\| spaceDown\) return;
  if \(S\.connectMode\) \{ handleConnectClick\(nodeId\); return; \}
  selectNode\(nodeId\);
  const n = findNode\(nodeId\);
  drag = \{ nodeId, sx: e\.clientX, sy: e\.clientY, ox: n\.x, oy: n\.y \};
  document\.addEventListener\('mousemove', onDragMove\);
  document\.addEventListener\('mouseup',   onDragUp\);
\}"""

mouse_down_new = """function onNodeMouseDown(e, nodeId) {
  e.stopPropagation();
  if (e.button !== 0 || spaceDown) return;
  
  selectNode(nodeId);
  
  if (S.toolMode === 'delete') {
    if (confirm(`Node "${nodeId}" und alle Verbindungen löschen?`)) deleteNode(nodeId);
    return;
  }
  
  const n = findNode(nodeId);
  
  if (S.toolMode === 'move') {
    drag = { type: 'move', nodeId, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y };
  } else if (S.toolMode === 'connect') {
    S.connectSrc = nodeId;
    activeConnectionLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    activeConnectionLine.setAttribute('x1', n.x + NODE_W/2);
    activeConnectionLine.setAttribute('y1', n.y + NODE_H/2);
    activeConnectionLine.setAttribute('x2', n.x + NODE_W/2);
    activeConnectionLine.setAttribute('y2', n.y + NODE_H/2);
    activeConnectionLine.setAttribute('stroke', '#7c3aed');
    activeConnectionLine.setAttribute('stroke-width', '3');
    activeConnectionLine.setAttribute('stroke-dasharray', '5,5');
    svg.appendChild(activeConnectionLine);
    drag = { type: 'connect', nodeId, sx: e.clientX, sy: e.clientY };
  }
  
  document.addEventListener('mousemove', onDragMove);
  document.addEventListener('mouseup',   onDragUp);
}"""
text = re.sub(mouse_down_old, mouse_down_new, text)


drag_move_old = r"""function onDragMove\(e\) \{
  if \(!drag\) return;
  const n = findNode\(drag\.nodeId\);
  if \(!n\) return;
  n\.x = Math\.max\(0, drag\.ox \+ \(e\.clientX - drag\.sx\) / VIEW\.zoom\);
  n\.y = Math\.max\(0, drag\.oy \+ \(e\.clientY - drag\.sy\) / VIEW\.zoom\);
  const c = document\.getElementById\(`card-\$\{drag\.nodeId\}`\);
  if \(c\) \{ c\.style\.left = n\.x \+ 'px'; c\.style\.top = n\.y \+ 'px'; \}
  renderSVG\(\);
\}"""

drag_move_new = """function onDragMove(e) {
  if (!drag) return;
  const n = findNode(drag.nodeId);
  if (!n) return;
  
  if (drag.type === 'move') {
    n.x = Math.max(0, drag.ox + (e.clientX - drag.sx) / VIEW.zoom);
    n.y = Math.max(0, drag.oy + (e.clientY - drag.sy) / VIEW.zoom);
    const c = document.getElementById(`card-${drag.nodeId}`);
    if (c) { c.style.left = n.x + 'px'; c.style.top = n.y + 'px'; }
    renderSVG();
  } else if (drag.type === 'connect' && activeConnectionLine) {
    const rect = canvasWrap.getBoundingClientRect();
    const cx = (e.clientX - rect.left - VIEW.x) / VIEW.zoom;
    const cy = (e.clientY - rect.top - VIEW.y) / VIEW.zoom;
    activeConnectionLine.setAttribute('x2', cx);
    activeConnectionLine.setAttribute('y2', cy);
  }
}"""
text = re.sub(drag_move_old, drag_move_new, text)

drag_up_old = r"""function onDragUp\(e\) \{
  if \(drag\) \{ drag = null; document\.removeEventListener\('mousemove', onDragMove\); document\.removeEventListener\('mouseup',   onDragUp\); \}
\}"""

drag_up_new = """function onDragUp(e) {
  if (drag) {
    if (drag.type === 'connect' && activeConnectionLine) {
      activeConnectionLine.remove();
      activeConnectionLine = null;
      
      // Find node under cursor
      const card = e.target.closest('.node-card');
      if (card) {
        const targetId = card.id.replace('card-', '');
        if (targetId && targetId !== drag.nodeId) {
          doConnect(drag.nodeId, targetId);
        }
      }
      S.connectSrc = null;
      renderAllNodes();
    }
    
    drag = null;
    document.removeEventListener('mousemove', onDragMove);
    document.removeEventListener('mouseup',   onDragUp);
  }
}"""
text = re.sub(drag_up_old, drag_up_new, text)


# Update rendering class
text = text.replace("S.connectMode ? 'connect-tgt' : '',", "S.toolMode === 'connect' ? 'connect-tgt' : '',")

# Canvas click logic
text = text.replace("if (S.connectMode) { toggleConnect(); return; }", "if (S.toolMode === 'connect') return;")


with open('/home/flo/CampusNow/backend/api-service/static/graph-editor.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patching complete.")
