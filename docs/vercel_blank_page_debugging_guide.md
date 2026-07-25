# Guide: Fixing a Blank Vercel Static App When the Page Loads but Renders Nothing

This is the workflow I used to fix `https://cascade-graph-explorer.vercel.app/` when it showed a blank page.

---

## 1. Separate the problem into 3 layers

When a deployed frontend is blank, treat it as one of these:

1. **Deployment/routing problem**
   - wrong files deployed
   - wrong alias/domain pointing to an old deployment
   - missing `index.html`

2. **Asset loading problem**
   - JS/CSS/data file 404
   - path mismatch like `./graph_data.js` vs `/graph_data.js`
   - CORS or fetch failure

3. **Runtime JS crash**
   - app loads, but a JS exception kills rendering
   - usually visible as a blank canvas or empty page with controls partially missing

Do not guess which one it is.

---

## 2. Reproduce locally from the deployed bundle, not just source files

If you have a deploy folder like:

```text
outputs/deploy_vercel_explorer/
  index.html
  graph_explorer.html
  graph_data.js
```

test **that exact folder** first.

Why:
- source HTML may work
- deployed copy may differ
- alias may still point to an older deployment

---

## 3. Check the browser runtime error first

For blank pages, browser console errors are usually the fastest truth source.

### What I checked
I loaded the deployed HTML locally and captured:
- `pageerror`
- console `error`
- whether a `<canvas>` was created
- whether the body had content

That exposed the real failure:

```text
Uncaught TypeError: Cannot read properties of undefined (reading 'tick')
```

That meant:
- Vercel was not the root cause
- the JS app was crashing after load

---

## 4. Reduce the app until the crash disappears

This is the key debugging move.

Instead of staring at a large HTML file, create a **minimal reproduction**:

1. load `three`
2. load `3d-force-graph`
3. load `graph_data.js`
4. render a small subset of nodes/links
5. add features back one by one

### Why this works
It tells you whether the crash comes from:
- the library combo
- the dataset
- your custom hooks/options
- post-render scene mutations

---

## 5. Identify the smallest safe graph config

My minimal test proved that these were fine:
- `three@0.160.0`
- `3d-force-graph@1.73.0`
- the graph dataset itself
- node/link styling
- shared geometries
- renderer pixel ratio cap
- layer planes

That narrowed the problem to **extra startup work in the real explorer**.

---

## 6. Remove or defer risky startup work

The real explorer had a lot happening during initial render:
- force tuning immediately after graph creation
- extra post-init graph mutations
- lazy overlay logic
- scene additions
- cached recomputation paths

To get the site back online fast, I used the safe approach:

### Keep
- basic graph render
- node/link styles
- sidebar
- controls
- default node limiting

### Remove or defer
- nonessential startup mutations
- anything that touches the graph engine immediately after init if it might destabilize it

In this case, removing the unsafe startup steps stopped the crash.

---

## 7. Verify locally before redeploying

Before touching Vercel, verify:

- page title is correct
- canvas exists
- no runtime JS errors
- some visible graph/UI text appears

If local deployed files still crash, Vercel deploys will not save you.

---

## 8. Deploy with Vercel CLI from the correct folder

Deploy from the folder that actually contains the static site:

```bash
cd outputs/deploy_vercel_explorer
npx vercel deploy --prod --yes
```

Important:
- deploying from repo root can publish the wrong thing
- static Vercel projects often depend entirely on cwd

---

## 9. Check what alias/domain points where

This was the second real issue.

The new fixed deployment was live, but the public domain still pointed to an **older deployment**.

### Inspect current target
```bash
npx vercel inspect cascade-graph-explorer.vercel.app
```

That showed the alias was still attached to the previous production deployment.

---

## 10. Repoint the alias to the fixed deployment

After deploying, explicitly map the public alias to the new deployment:

```bash
npx vercel alias set <new-deployment-url> cascade-graph-explorer.vercel.app
```

Example pattern:

```bash
npx vercel alias set cascade-graph-explorer-xyz.vercel.app cascade-graph-explorer.vercel.app
```

This is the step many people miss.

A successful deploy does **not** guarantee your custom domain or alias moved where you think it did.

---

## 11. Verify the live site, not just the deployment URL

Check the real public URL:

```text
https://cascade-graph-explorer.vercel.app/
```

Confirm:
- correct title
- page content visible
- canvas exists
- graph loads
- no fatal console errors

A nonfatal `404` for something like `favicon.ico` is acceptable.
A JS exception is not.

---

# Fast Triage Checklist

Use this in order:

## A. Is the right site deployed?
```bash
npx vercel whoami
npx vercel inspect <your-domain>
```

## B. Does the deployed folder have the expected files?
```text
index.html
graph_data.js
other static assets
```

## C. Does local deployed HTML crash?
- load the built HTML locally
- capture `pageerror` and console errors

## D. Does a minimal graph render?
- same libraries
- same dataset
- smaller feature surface

## E. What exact feature reintroduces the crash?
- add back features one by one

## F. Redeploy
```bash
npx vercel deploy --prod --yes
```

## G. Reattach alias/domain if needed
```bash
npx vercel alias set <deployment-url> <public-domain>
```

---

# Practical Rules That Help

## Rule 1: Never debug Vercel before debugging the browser error
Blank pages are often just uncaught JS exceptions.

## Rule 2: Test the deployed artifact, not only source code
`outputs/deploy_vercel_explorer/index.html` matters more than `data/graph_explorer.html`.

## Rule 3: Minimal reproductions beat long prompting
When an app is complex, reduce it to:
- libs
- data
- tiny render
- reintroduce features incrementally

## Rule 4: Production alias drift is real
A working deployment URL is not enough. The public alias may still point to an older deploy.

## Rule 5: Restore service first, optimize second
If a performance fix causes instability, back off to the last safe configuration, get the site live, then optimize in smaller steps.

---

# Commands I'd Reuse Next Time

```bash
# Inspect current public alias target
npx vercel inspect cascade-graph-explorer.vercel.app

# Deploy the static site from its actual folder
cd outputs/deploy_vercel_explorer
npx vercel deploy --prod --yes

# Point public alias to the new deployment
npx vercel alias set <deployment-url> cascade-graph-explorer.vercel.app
```

---

# Template Debugging Strategy

```md
1. Reproduce locally from the deployed artifact.
2. Capture browser runtime errors.
3. Confirm whether the issue is deploy, asset, or runtime.
4. Build a minimal reproduction.
5. Add features back until the crash returns.
6. Keep the smallest safe version.
7. Deploy from the correct directory.
8. Inspect alias/domain mapping.
9. Rebind alias if necessary.
10. Verify the public URL directly.
```

---

# Why this worked when repeated prompting didn't

Because this was not really a “generate a clever fix” problem.

It was a **systems debugging** problem:
- reproduce
- isolate
- remove variables
- verify each layer
- redeploy carefully
- fix alias mapping

That process beats model cleverness most of the time.
