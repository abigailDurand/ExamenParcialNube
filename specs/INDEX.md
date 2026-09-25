# Índice de Specs — Proyecto Practica3

Este archivo es la fuente de verdad de qué specs existen y en qué orden 
deben leerse. Cada agente (backend, frontend, test) debe leer TODAS las 
specs listadas aquí antes de generar código.

> Actualiza esta lista cada vez que agregues una spec nueva. 
> No es necesario editar los agentes cuando agregas una feature — 
> solo agrega la línea correspondiente aquí.

## Specs generales (leer siempre, en este orden)

1. specs/oveview-specs.md
2. specs/architecture-specs.md
3. specs/business-rules-specs.md
4. specs/infraestructure-specs.md
5. specs/ui-design-specs.md        (solo relevante para el agente frontend)

## Specs por feature

| Feature | Spec | Agregada |
|---|---|---|
| Login | specs/login-specs.md | inicial |
| Consulta climática con fallback | specs/condicional-api-specs.md | 22/sep/2026 |
| Predicción de visitantes a Las Pavas | specs/prediccion-specs.md | 25/sep/2026 |
| CI/CD (GitHub Actions → AWS EC2) | specs/ci-specs.md | 25/sep/2026 |

## Specs de testing

- specs/test-specs.md