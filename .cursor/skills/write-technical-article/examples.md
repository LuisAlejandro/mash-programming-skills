# Voice and structure anchors

Short excerpts only. Do not copy these posts wholesale. Gold standard: numbered `###`, code as the explanation, `tú`.

## Do: IMAP-style tutorial

From `2015-08-30-vaciando-la-papelera-de-tu-buzon-de-correo-a-traves-de-python-generated.md`. Intro has no heading. Section is `### 2.`. Pitfall uses ✅ / ❌. Commands and code follow immediately.

````markdown
Mi buzón de correo se estaba llenando y el proceso de borrar mensajes uno por uno
para luego vaciar la papelera era un fastidio total. Como desarrollador, mi primer
instinto fue: "Tiene que haber una forma de automatizar esto". Hoy quiero mostrarte
cómo puedes construir el tuyo.

### 2. Preparando nuestro script de Python

✅ **Correcto:**
Nunca, pero nunca, escribas tu contraseña directamente en el código.

❌ **Incorrecto:**

```python
# NO HAGAS ESTO. ¡NUNCA!
user = "tu_correo@ejemplo.com"
password = "tu_contraseña_super_secreta"
```
````

(The real post continues with `.env` + `pip install python-dotenv` + `imaplib` login. Same rhythm: problem → wrong way → commands → working snippet.)

## Do: gist citation

Every runnable fence is a named file from the gist. Clone command matches the handoff `CLONE` line. `❌ Incorrecto` may be original.

````markdown
El ejemplo para clonar está en [este gist](https://gist.github.com/LuisAlejandro/<id>).

```bash
git clone https://gist.github.com/<id>.git
```

```typescript
// extract.ts
export async function extractAuthor(authorId: string): Promise<void> {
  // … contiguous excerpt from the gist file, not a rewrite
}
```
````

## Do: local image (pre-publish)

What **this skill** writes. `blog-post` rewrites `images/` markdown into Cosmic figure HTML.

```markdown
![Three-step flow: backtesting, dry-run, then live trading.](images/freqtrade-flow.jpg)
```

## Recognize: Cosmic figure (already published)

Existing output files look like this **after** upload. Do not author this HTML in a new post.

```html
<span class="figure figure-right-40" data-figure-src="https://cdn.cosmicjs.com/…" data-figure-href="https://imgix.cosmicjs.com/…" data-figure-alt="A clean flowchart with three steps: Backtesting, Dry-Run, Live Trading."></span>

<!-- Uploaded to Cosmic CDN -->
```

## Don't: Gemini essay headings

Recent Gemini posts drift to unnumbered `##`. That is wrong for this skill.

```markdown
## El mito del modelo omnipotente: ¿Por qué cambiar de LLM no resolverá tus agentes rotos?
```

Write this instead:

```markdown
### 1. El mito del modelo omnipotente
```

## Footer (exact)

```markdown
---
Otros proyectos en [mi perfil de GitHub](https://github.com/LuisAlejandro).
```
