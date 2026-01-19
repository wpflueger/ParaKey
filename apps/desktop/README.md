# KeyMuse Desktop

Electron + React 19 + Vite (TypeScript) desktop UI for KeyMuse.

## Development

```powershell
bun install
bun run dev
```

`bun run dev` now also watches and rebuilds Electron main/preload files.

## Native modules

If `naudiodon` fails to load, KeyMuse will attempt to rebuild it on startup.
You can also run it manually:

```powershell
bun run rebuild:native
```

## Build

```powershell
bun run build
```

## Package (Windows)

```powershell
bun run dist
```
