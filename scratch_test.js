window = { GRAPH_DATA: {} }; localStorage = { getItem: () => null, setItem: () => {} }; document = { dataElement: {}, getElementById: () => ({ addEventListener: () => {}, style: {} }), querySelectorAll: () => [] };

    const CACHE_KEY = 'blast_radius_3d_graph_cache_v2';
    let fullGraphData = { nodes: [], links: [] };
    let nodeMap = new Map();
    let filteredNodes = [];
    let currentLayerFilter = 'all';
    let activeSearchQuery = '';
    let Graph = null;
    let selectedNode = null;
    let blastSimulationActive = false;
    let interLayerEdgeWidth = 3;
    let labelsGroup = null;
    let clustersGroup = null;
    let labelsVisible = true;
    let clustersVisible = true;

    function isInterLayerLink(link) {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
      const srcNode = nodeMap.get(srcId);
      const tgtNode = nodeMap.get(tgtId);
      return (srcNode && tgtNode && srcNode.layer !== tgtNode.layer) ||
             ['IMPLEMENTS', 'RENDERS', 'COVERS'].includes(link.rel_type);
    }

    function getLinkWidth(link) {
      return isInterLayerLink(link) ? parseFloat(interLayerEdgeWidth) : 1;
    }

    // Theme Management
    function initTheme() {
      const savedTheme = localStorage.getItem('theme') || 'dark';
      document.documentElement.setAttribute('data-theme', savedTheme);
      updateThemeButtonText(savedTheme);
    }

    function toggleTheme() {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      updateThemeButtonText(next);
      
      if (Graph) {
        Graph.backgroundColor(next === 'dark' ? '#0b0c10' : '#f8f9fa');
      }
    }

    function updateThemeButtonText(theme) {
      document.getElementById('theme-toggle-btn').innerText = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
    }

    document.getElementById('theme-toggle-btn').addEventListener('click', toggleTheme);

    // Edge Width Slider Control
    document.getElementById('edge-width-slider').addEventListener('input', (e) => {
      interLayerEdgeWidth = e.target.value;
      document.getElementById('edge-width-val').innerText = interLayerEdgeWidth + 'px';
      if (Graph) {
        Graph.linkWidth(link => getLinkWidth(link));
      }
    });

    // Labels Toggle Button
    document.getElementById('toggle-labels-btn').addEventListener('click', () => {
      labelsVisible = !labelsVisible;
      document.getElementById('toggle-labels-btn').innerText = labelsVisible ? '🏷️ Labels: ON' : '🏷️ Labels: OFF';
      if (labelsGroup) labelsGroup.visible = labelsVisible;
      else if (labelsVisible) draw3DLabels();
    });

    // Clusters Toggle Button
    document.getElementById('toggle-clusters-btn').addEventListener('click', () => {
      clustersVisible = !clustersVisible;
      document.getElementById('toggle-clusters-btn').innerText = clustersVisible ? '🧩 Clusters: ON' : '🧩 Clusters: OFF';
      if (clustersGroup) clustersGroup.visible = clustersVisible;
      else if (clustersVisible) drawClusterLabels();
    });

    // Dynamic Data Fetcher with Local Caching and file:// fallback
    async function loadGraphData(forceRefresh = false) {
      const loadingScreen = document.getElementById('loading-screen');
      const loadingText = document.getElementById('loading-text');
      loadingScreen.style.opacity = '1';
      loadingScreen.style.pointerEvents = 'all';

      if (!forceRefresh) {
        // 1. Check window.GRAPH_DATA from local script tag first
        if (window.GRAPH_DATA && window.GRAPH_DATA.nodes && window.GRAPH_DATA.nodes.length > 0) {
          console.log('[Script Tag] Loaded graph data from window.GRAPH_DATA');
          fullGraphData = window.GRAPH_DATA;
          localStorage.setItem(CACHE_KEY, JSON.stringify(fullGraphData));
          renderGraph();
          return;
        }

        // 2. Check localStorage cache
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          try {
            const parsed = JSON.parse(cached);
            if (parsed.nodes && parsed.nodes.length > 0) {
              console.log('[Cache] Loaded graph data from localStorage');
              fullGraphData = parsed;
              renderGraph();
              return;
            }
          } catch(e) {
            console.warn('[Cache] Corrupted cache, fetching fresh dataset', e);
          }
        }
      }

      loadingText.innerText = 'Loading graph data...';
      try {
        const resp = await fetch('./graph_data.json');
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        fullGraphData = await resp.json();
        
        // Save to cache
        localStorage.setItem(CACHE_KEY, JSON.stringify(fullGraphData));
        console.log(`[Fetch] Cached ${fullGraphData.nodes.length} nodes to localStorage`);
      } catch (err) {
        console.warn('[Fetch Warning] Local fetch failed/blocked by CORS. Falling back to window.GRAPH_DATA:', err);
        if (window.GRAPH_DATA && window.GRAPH_DATA.nodes) {
          fullGraphData = window.GRAPH_DATA;
          localStorage.setItem(CACHE_KEY, JSON.stringify(fullGraphData));
        }
      }

      renderGraph();
    }

    document.getElementById('refresh-data-btn').addEventListener('click', () => {
      loadGraphData(true);
    });

    // Sidebar Controls
    const sidebar = document.getElementById('sidebar');
    document.getElementById('sidebar-toggle-btn').addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });

    // Render 3D Force Graph
    function renderGraph() {
      const container = document.getElementById('3d-graph');
      container.innerHTML = '';

      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

      // Build quick lookup map for nodes
      nodeMap = new Map(fullGraphData.nodes.map(n => [n.id, n]));

      // Populate DOM text layer for Ctrl+F native searchability
      updateCtrlFOverlay();

      // Update Stats
      document.getElementById('stats-counter').innerText = 
        `${fullGraphData.nodes.length} Nodes | ${fullGraphData.links.length} Links`;

      // Filtered nodes baseline
      filteredNodes = fullGraphData.nodes;

      Graph = ForceGraph3D()(container)
        .graphData(fullGraphData)
        .backgroundColor(isDark ? '#0b0c10' : '#f8f9fa')
        .nodeId('id')
        .nodeLabel(node => {
          return `<div style="color:#fff; background:rgba(15,23,42,0.9); padding:6px 10px; border-radius:6px; border:1px solid #30363d;">
            <b>${node.name}</b> (${node.node_type})<br/>
            <span style="font-size:11px; color:#94a3b8;">Layer: ${node.layer.toUpperCase()}</span>
          </div>`;
        })
        .nodeColor(node => node.color || '#58a6ff')
        .nodeVal(node => {
          if (node.layer === 'req') return 12;
          if (node.layer === 'ui') return 8;
          return 4;
        })
        .linkWidth(link => getLinkWidth(link))
        .linkColor(link => {
          const isInter = isInterLayerLink(link);
          if (isInter) {
            if (link.rel_type === 'IMPLEMENTS') return isDark ? 'rgba(127, 119, 221, 0.75)' : 'rgba(102, 92, 215, 0.75)';
            if (link.rel_type === 'RENDERS') return isDark ? 'rgba(29, 158, 117, 0.75)' : 'rgba(20, 128, 94, 0.75)';
            if (link.rel_type === 'COVERS') return isDark ? 'rgba(88, 166, 255, 0.75)' : 'rgba(9, 105, 218, 0.75)';
          }
          return isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.10)';
        })
        .linkDirectionalParticles(2)
        .linkDirectionalParticleWidth(link => isInterLayerLink(link) ? 3 : 1)
        .linkDirectionalParticleSpeed(0.005)
        .onEngineStop(() => {
          draw3DLabels();
          drawClusterLabels();
        })
        .onNodeClick(node => {
          focusNode(node);
        });

      // Add 3D Layer Planes (Glassmorphism Tier Visualizers at Z = +200, 0, -200)
      addLayerPlanes();

      // Schedule 3D Labels & Connected Component Cluster Labels
      setTimeout(() => {
        draw3DLabels();
        drawClusterLabels();
      }, 2000);

      // Initial Sidebar Populate
      updateNodeList();

      // Hide Loading Screen
      const loadingScreen = document.getElementById('loading-screen');
      loadingScreen.style.opacity = '0';
      setTimeout(() => loadingScreen.style.pointerEvents = 'none', 500);
    }

    // Add semi-transparent 3D Layer Planes (Fixed 600x600 size)
    let layerPlanesGroup = null;

    function addLayerPlanes() {
      if (!Graph) return;
      const scene = Graph.scene();

      if (layerPlanesGroup) {
        scene.remove(layerPlanesGroup);
      }
      layerPlanesGroup = new THREE.Group();

      const layers = [
        { z: 200, color: 0x7f77dd, label: "Requirement Layer (Z=+200)" },
        { z: 0, color: 0x1d9e75, label: "UI Layer (Z=0)" },
        { z: -200, color: 0xba7517, label: "Code Layer (Z=-200)" }
      ];

      layers.forEach(l => {
        const planeGeo = new THREE.PlaneGeometry(600, 600);
        const planeMat = new THREE.MeshBasicMaterial({
          color: l.color,
          transparent: true,
          opacity: 0.05,
          side: THREE.DoubleSide
        });
        const planeMesh = new THREE.Mesh(planeGeo, planeMat);
        planeMesh.position.z = l.z;
        layerPlanesGroup.add(planeMesh);

        // Grid helper
        const grid = new THREE.GridHelper(600, 20, l.color, l.color);
        grid.rotation.x = Math.PI / 2;
        grid.position.z = l.z;
        grid.material.opacity = 0.15;
        grid.material.transparent = true;
        layerPlanesGroup.add(grid);
      });

      scene.add(layerPlanesGroup);
    }

    // 1. Draw 3D Labels for Edge Relationship Types (IMPLEMENTS, RENDERS, COVERS) and Key Nodes
    function draw3DLabels() {
      if (!Graph) return;
      const scene = Graph.scene();

      if (labelsGroup) scene.remove(labelsGroup);
      labelsGroup = new THREE.Group();
      labelsGroup.visible = labelsVisible;

      // Inter-layer Edge Labels (midpoint)
      fullGraphData.links.forEach(link => {
        if (['IMPLEMENTS', 'RENDERS', 'COVERS'].includes(link.rel_type)) {
          const srcId = typeof link.source === 'object' ? link.source.id : link.source;
          const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
          const srcNode = nodeMap.get(srcId);
          const tgtNode = nodeMap.get(tgtId);

          if (srcNode && tgtNode) {
            const midX = ((srcNode.x || 0) + (tgtNode.x || 0)) / 2;
            const midY = ((srcNode.y || 0) + (tgtNode.y || 0)) / 2;
            const midZ = ((srcNode.z !== undefined ? srcNode.z : srcNode.fz || 0) + (tgtNode.z !== undefined ? tgtNode.z : tgtNode.fz || 0)) / 2;

            const colorHex = link.rel_type === 'IMPLEMENTS' ? '#7f77dd' : (link.rel_type === 'RENDERS' ? '#1d9e75' : '#58a6ff');
            const sprite = createTextSprite(`${link.rel_type}`, colorHex, 45, 14);
            sprite.position.set(midX, midY, midZ);
            labelsGroup.add(sprite);
          }
        }
      });

      scene.add(labelsGroup);
    }

    // 2. Interconnected Component Clustering & Group Labeling
    function findConnectedClusters() {
      const adj = new Map();
      fullGraphData.nodes.forEach(n => adj.set(n.id, []));

      fullGraphData.links.forEach(l => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source;
        const tId = typeof l.target === 'object' ? l.target.id : l.target;
        if (adj.has(sId) && adj.has(tId)) {
          adj.get(sId).push(tId);
          adj.get(tId).push(sId);
        }
      });

      const visited = new Set();
      const clusters = [];

      fullGraphData.nodes.forEach(node => {
        if (!visited.has(node.id)) {
          const component = [];
          const queue = [node.id];
          visited.add(node.id);

          while (queue.length > 0) {
            const curr = queue.shift();
            const currNode = nodeMap.get(curr);
            if (currNode) component.push(currNode);

            const neighbors = adj.get(curr) || [];
            neighbors.forEach(nbr => {
              if (!visited.has(nbr)) {
                visited.add(nbr);
                queue.push(nbr);
              }
            });
          }

          if (component.length >= 3) {
            clusters.push(component);
          }
        }
      });

      return clusters;
    }

    function deriveClusterName(nodes) {
      const tokenCounts = new Map();
      const stop = new Set(['page', 'component', 'function', 'handler', 'get', 'set', 'route', 'code', 'ui', 'req', 'with', 'from', 'app']);

      nodes.forEach(n => {
        const text = (n.name + " " + (n.properties?.file || n.file || '')).toLowerCase();
        const words = text.match(/[a-z]{4,}/g) || [];
        words.forEach(w => {
          if (!stop.has(w)) {
            tokenCounts.set(w, (tokenCounts.get(w) || 0) + 1);
          }
        });
      });

      let topWord = 'Interconnected';
      let maxCnt = 0;
      tokenCounts.forEach((cnt, word) => {
        if (cnt > maxCnt) {
          maxCnt = cnt;
          topWord = word;
        }
      });

      const capitalized = topWord.charAt(0).toUpperCase() + topWord.slice(1);
      return `Cluster: ${capitalized} Group (${nodes.length} nodes)`;
    }

    function drawClusterLabels() {
      if (!Graph) return;
      const scene = Graph.scene();

      if (clustersGroup) scene.remove(clustersGroup);
      clustersGroup = new THREE.Group();
      clustersGroup.visible = clustersVisible;

      const clusters = findConnectedClusters();

      clusters.forEach(cluster => {
        let sumX = 0, sumY = 0, sumZ = 0;
        cluster.forEach(n => {
          sumX += (n.x || 0);
          sumY += (n.y || 0);
          sumZ += (n.z !== undefined ? n.z : (n.fz || 0));
        });
        const centerX = sumX / cluster.length;
        const centerY = sumY / cluster.length;
        const centerZ = sumZ / cluster.length;

        const clusterName = deriveClusterName(cluster);
        const sprite = createTextSprite(clusterName, '#bc8cff', 85, 20);
        sprite.position.set(centerX, centerY + 25, centerZ + 8);
        clustersGroup.add(sprite);
      });

      scene.add(clustersGroup);
    }

    // Canvas Text Sprite Creation Helper
    function createTextSprite(text, colorHex, scaleW = 80, scaleH = 20) {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');

      ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
      ctx.strokeStyle = colorHex;
      ctx.lineWidth = 5;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(8, 8, 496, 112, 14);
      } else {
        ctx.rect(8, 8, 496, 112);
      }
      ctx.fill();
      ctx.stroke();

      ctx.font = 'bold 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 256, 64);

      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(scaleW, scaleH, 1);
      return sprite;
    }

    // Searchable DOM overlay for native browser Ctrl+F
    function updateCtrlFOverlay() {
      let overlay = document.getElementById('ctrl-f-overlay');
      if (!overlay) return;

      let html = '';
      fullGraphData.nodes.forEach(n => {
        html += `<div class="searchable-item" onclick="focusNodeById('${n.id}')">Node: ${n.name} (${n.node_type} - ${n.layer.toUpperCase()})</div>`;
      });

      fullGraphData.links.forEach(l => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source;
        const tId = typeof l.target === 'object' ? l.target.id : l.target;
        const sNode = nodeMap.get(sId);
        const tNode = nodeMap.get(tId);
        if (sNode && tNode) {
          html += `<div class="searchable-item">Link ${l.rel_type}: ${sNode.name} to ${tNode.name}</div>`;
        }
      });

      overlay.innerHTML = html;
    }

    function focusNodeById(id) {
      const node = nodeMap.get(id);
      if (node) focusNode(node);
    }

    // Focus Node in 3D Space
    function focusNode(node) {
      selectedNode = node;
      const distance = 120;
      const distRatio = 1 + distance/Math.hypot(node.x || 0, node.y || 0, node.z || node.fz || 0);

      Graph.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: ((node.z || node.fz || 0) + 60) },
        node,
        1500
      );

      // Open Inspector
      openInspector(node);
    }

    // Camera Presets
    function setCameraView(preset) {
      if (!Graph) return;
      if (preset === 'iso') {
        Graph.cameraPosition({ x: 300, y: 300, z: 400 }, { x: 0, y: 0, z: 0 }, 1200);
      } else if (preset === 'req') {
        Graph.cameraPosition({ x: 0, y: 1, z: 450 }, { x: 0, y: 0, z: 200 }, 1200);
      } else if (preset === 'ui') {
        Graph.cameraPosition({ x: 0, y: 1, z: 250 }, { x: 0, y: 0, z: 0 }, 1200);
      } else if (preset === 'code') {
        Graph.cameraPosition({ x: 0, y: 1, z: 50 }, { x: 0, y: 0, z: -200 }, 1200);
      }
    }

    // Sidebar Filtering Logic
    function filterLayer(layer, btnElem) {
      currentLayerFilter = layer;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      if (btnElem) btnElem.classList.add('active');
      updateNodeList();
    }

    document.getElementById('search-input').addEventListener('input', (e) => {
      activeSearchQuery = e.target.value.toLowerCase().trim();
      updateNodeList();
    });

    function updateNodeList() {
      const listContainer = document.getElementById('node-list');
      listContainer.innerHTML = '';

      filteredNodes = fullGraphData.nodes.filter(node => {
        const matchesLayer = (currentLayerFilter === 'all') || (node.layer === currentLayerFilter);
        const matchesQuery = !activeSearchQuery || 
          (node.name && node.name.toLowerCase().includes(activeSearchQuery)) ||
          (node.id && node.id.toLowerCase().includes(activeSearchQuery)) ||
          (node.node_type && node.node_type.toLowerCase().includes(activeSearchQuery));
        
        return matchesLayer && matchesQuery;
      });

      // Display top 100 matching cards for smooth rendering
      filteredNodes.slice(0, 100).forEach(node => {
        const sec = getLayerSpecificSector(node);
        const card = document.createElement('div');
        card.className = 'node-card';
        card.onclick = () => focusNode(node);

        const badgeClass = `badge-${node.layer || 'code'}`;
        card.innerHTML = `
          <div class="node-card-title">
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px;">${node.name}</span>
            <span class="node-badge ${badgeClass}">${node.node_type}</span>
          </div>
          <div class="node-card-desc">Sector: ${sec.name} | Z=${node.fz}</div>
        `;
        listContainer.appendChild(card);
      });
    }

    // Inspector Overlay
    function openInspector(node) {
      const inspector = document.getElementById('inspector');
      const title = document.getElementById('inspector-name');
      const body = document.getElementById('inspector-body');

      title.innerText = node.name;
      const sec = getLayerSpecificSector(node);
      
      let propsHtml = `<div><b>Node ID:</b> ${node.id}</div>`;
      propsHtml += `<div><b>Type:</b> ${node.node_type} (${node.layer.toUpperCase()})</div>`;
      propsHtml += `<div><b>Layer Sector:</b> ${sec.name}</div>`;
      propsHtml += `<div><b>Z-Plane:</b> ${node.fz}</div>`;
      
      if (node.properties) {
        Object.entries(node.properties).forEach(([k, v]) => {
          propsHtml += `<div><b>${k}:</b> ${v}</div>`;
        });
      }

      body.innerHTML = propsHtml;
      inspector.style.display = 'block';
    }

    function closeInspector() {
      document.getElementById('inspector').style.display = 'none';
    }

    // Blast Simulator Shockwave Mode (Traces connected impact paths from selected node)
    document.getElementById('blast-sim-btn').addEventListener('click', () => {
      if (!selectedNode) {
        alert('Please click and select a node first to simulate its blast radius impact!');
        return;
      }
      
      blastSimulationActive = true;
      const selectedId = selectedNode.id;

      // Find 1-hop and 2-hop connected links radiating from selected node
      const impactedLinks = new Set();
      const connectedNodeIds = new Set([selectedId]);

      fullGraphData.links.forEach(l => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source;
        const tId = typeof l.target === 'object' ? l.target.id : l.target;
        if (sId === selectedId || tId === selectedId) {
          impactedLinks.add(l);
          connectedNodeIds.add(sId);
          connectedNodeIds.add(tId);
        }
      });

      // 2-hop propagation
      fullGraphData.links.forEach(l => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source;
        const tId = typeof l.target === 'object' ? l.target.id : l.target;
        if (connectedNodeIds.has(sId) || connectedNodeIds.has(tId)) {
          impactedLinks.add(l);
        }
      });

      // Launch particle shockwave specifically along impact paths
      Graph.linkDirectionalParticles(link => impactedLinks.has(link) ? 8 : 1)
           .linkDirectionalParticleWidth(link => impactedLinks.has(link) ? 5 : 1)
           .linkDirectionalParticleSpeed(link => impactedLinks.has(link) ? 0.025 : 0.003);

      setTimeout(() => {
        Graph.linkDirectionalParticles(2)
             .linkDirectionalParticleWidth(link => isInterLayerLink(link) ? 3 : 1)
             .linkDirectionalParticleSpeed(0.005);
        blastSimulationActive = false;
      }, 6000);
    });

    // Initialize Page
    window.addEventListener('DOMContentLoaded', () => {
      initTheme();
      loadGraphData();
    });
  