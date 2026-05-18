import re

with open('/tmp/floorplan-editor.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update toolbar HTML
toolbar_html_old = """  <button id="btn-connect" class="btn" onclick="toggleConnect()" title="Shift+C">🔗 Verbinden</button>
  <span id="mode-label">— Klick auf Ziel-Node</span>"""

toolbar_html_new = """  <div class="tool-group" style="display:flex; border:1px solid var(--border); border-radius:4px; overflow:hidden">
    <button class="btn active" id="tool-move" style="border-radius:0; border:none; border-right:1px solid var(--border)" onclick="setTool('move')">✋ Move</button>
    <button class="btn" id="tool-connect" style="border-radius:0; border:none; border-right:1px solid var(--border)" onclick="setTool('connect')">🔗 Connect</button>
    <button class="btn" id="tool-delete" style="border-radius:0; border:none;" onclick="setTool('delete')">🗑 Delete</button>
  </div>
  <span id="mode-label" style="display:none;"></span>"""

text = text.replace(toolbar_html_old, toolbar_html_new)

js_additions = """
// ── TOOLS ──────────────────────────────────────────────────────────────
let toolMode = 'move'; // move, connect, delete
let drag = null;
let activeConnectionLine = null;

function setTool(tool) {
  toolMode = tool;
  connectSrc = null;
  document.querySelectorAll('.tool-group .btn').forEach(b => b.classList.remove('active'));
  $(`tool-${tool}`).classList.add('active');
  
  const ml = $('mode-label');
  ml.style.display = 'inline-block';
  if (tool === 'move') ml.textContent = '— Drag & Drop zum Verschieben';
  else if (tool === 'connect') ml.textContent = '— Drag & Drop zum Verbinden';
  else if (tool === 'delete') ml.textContent = '— Klick zum Löschen';
  
  $('svg-canvas').classList.toggle('mode-connect', tool === 'connect');
  renderNodes();
}
"""

text = text.replace("// ── Connect mode ───────────────────────────────────────────────────────────", js_additions + "\n// ── Connect mode ───────────────────────────────────────────────────────────")

# Remove toggleConnect completely (we do it manually to replace)
text = re.sub(r"function toggleConnect\(\)\s*\{[\s\S]*?\}\n", "", text)


# Update clickNode
click_node_old = r"""function clickNode\(e, id\)\{
  e\.stopPropagation\(\);
  if\(connectMode && connectSrc\)\{
    if\(connectSrc === id\)\{ endConnect\(\); return; \}
    const dir = prompt\(`Richtung von "\$\{connectSrc\}" nach "\$\{id\}"\\n\(front / back / left / right / up / down oder eigene\):`, 'front'\);
    if\(dir\)\{
      const src = nodeById\(connectSrc\);
      if\(src\)\{ if\(!src\.exits\) src\.exits=\{\}; src\.exits\[dir\] = id; \}
    \}
    endConnect\(\);
    renderEdges\(\); renderNodes\(\);
    return;
  \}
  selectNode\(id\);
\}"""

click_node_new = """// Removed clickNode locally, handling inside mousedown to allow drag and drop"""
text = re.sub(click_node_old, click_node_new, text)

text = text.replace("let connectMode = false, connectSrc = null;", "let connectSrc = null;")
text = text.replace("connectMode", "toolMode === 'connect'")
text = text.replace("if(e.key==='c'&&e.shiftKey) toggleConnect();", "if(e.key==='c'&&e.shiftKey) setTool('connect');")

# Inject Mousedown/Drag logic into renderNodes
render_nodes_old = """g.addEventListener('click', e => clickNode(e, n.id));"""
render_nodes_new = """g.addEventListener('mousedown', e => onNodeMouseDown(e, n.id));"""
text = text.replace(render_nodes_old, render_nodes_new)

drag_logic = """
function onNodeMouseDown(e, id) {
  e.stopPropagation();
  if (e.button !== 0) return;
  
  selectNode(id);
  
  if (toolMode === 'delete') {
    if(confirm(`Node "${id}" und alle Verbindungen löschen?`)) {
      selectedId = id;
      deleteNode();
    }
    return;
  }
  
  const n = nodeById(id);
  if (!n) return;
  
  if (toolMode === 'move') {
    drag = { type: 'move', id, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y };
  } else if (toolMode === 'connect') {
    connectSrc = id;
    
    // Create temporary line
    activeConnectionLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    // We need to figure out coordinates. Usually n.x, n.y are relative to the floor plan.
    // The SVGs coordinates:
    const cx = n.x, cy = n.y;
    activeConnectionLine.setAttribute('x1', cx);
    activeConnectionLine.setAttribute('y1', cy);
    activeConnectionLine.setAttribute('x2', cx);
    activeConnectionLine.setAttribute('y2', cy);
    activeConnectionLine.setAttribute('stroke', '#7c3aed');
    activeConnectionLine.setAttribute('stroke-width', '4');
    activeConnectionLine.setAttribute('stroke-dasharray', '5,5');
    $('edges').appendChild(activeConnectionLine);
    
    drag = { type: 'connect', id, sx: e.clientX, sy: e.clientY };
  }
}

window.addEventListener('mousemove', e => {
  if (isPanning && !drag) {
    // Existing pan logic is handled in window mousemove for 'canvas-wrap'. Wait, I'll merge my logic.
  }
  
  if (!drag) return;
  const n = nodeById(drag.id);
  if (!n) return;
  
  if (drag.type === 'move') {
    // Current transform: scale(transform.zoom) translate(transform.x, transform.y)
    n.x = drag.ox + (e.clientX - drag.sx) / transform.zoom;
    n.y = drag.oy + (e.clientY - drag.sy) / transform.zoom;
    renderNodes();
    renderEdges();
  } else if (drag.type === 'connect' && activeConnectionLine) {
    const svgLayer = $('svg-layer');
    const pt = svgLayer.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const cursorPt = pt.matrixTransform(svgLayer.getScreenCTM().inverse());
    activeConnectionLine.setAttribute('x2', cursorPt.x);
    activeConnectionLine.setAttribute('y2', cursorPt.y);
  }
});

window.addEventListener('mouseup', e => {
  if (drag) {
    if (drag.type === 'connect' && activeConnectionLine) {
      activeConnectionLine.remove();
      activeConnectionLine = null;
      
      const targetGroup = e.target.closest('.node');
      if (targetGroup) {
        const targetId = targetGroup.dataset.id;
        if (targetId && targetId !== drag.id) {
          const dir = prompt(`Richtung von "${drag.id}" nach "${targetId}"\\n(front / back / left / right / up / down):`, 'front');
          if (dir) {
            const srcNode = nodeById(drag.id);
            if(srcNode) {
              if(!srcNode.exits) srcNode.exits={};
              srcNode.exits[dir] = targetId;
              renderEdges();
              renderNodes();
            }
          }
        }
      }
      endConnect();
    }
    drag = null;
  }
});
"""

text = text.replace("// Keyboard", drag_logic + "\n// Keyboard")

# Inject dataset-id in renderNodes for target dropping
text = text.replace("g.setAttribute('class', 'node');", "g.setAttribute('class', 'node');\n    g.dataset.id = n.id;")

with open('/home/flo/CampusNow/backend/api-service/static/floorplan-editor.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Floorplan patched.")
