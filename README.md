# Conéctate — Sistema de Educación Emocional
## Versión 2.0 — Guía de cambios y setup

---

## 🚀 Cómo ejecutar el proyecto

```bash
pip install django pillow
cd conectate_v2
python manage.py migrate
python manage.py runserver
```

---

## ✅ Bugs corregidos (vs versión anterior)

| # | Archivo | Descripción |
|---|---------|-------------|
| 1 | `accounts/views.py` → `ver_perfil_estudiante` | `[:30]` antes del `.filter()` causaba `TypeError` |
| 2 | `emotions/views.py` → `historial_propio` | Mismo error de slice antes de filter |
| 3 | `emotions/views.py` → `alertas_view` | `alertas.model.objects` incorrecto; mostraba alertas de todos los usuarios al profesor |

---

## 🆕 Nuevas funcionalidades

### 👨‍🎓 Estudiante
| Feature | Dónde |
|---------|-------|
| **Meta semanal** — El estudiante define una meta para la semana y puede marcarla como cumplida | Registro de emoción + Dashboard |
| **Gráfica de emociones frecuentes** — Donut chart con distribución de emociones históricas | Historial |
| **Estadísticas personales** — Promedio general y racha actual visibles en historial | Historial |
| **Dashboard mejorado** — Muestra meta de la semana con estado de progreso | Dashboard |

### 👩‍🏫 Profesor
| Feature | Dónde |
|---------|-------|
| **Resumen del Grupo** — Vista por curso con estado emocional, tendencia (↑↓→) y alertas de cada estudiante | Sidebar → Resumen del Grupo |
| **Notas privadas** — El profesor puede escribir, editar y eliminar notas confidenciales sobre cada estudiante | Perfil del estudiante |
| **Indicador de tendencia** — Compara el puntaje del primer y último día de la semana para cada estudiante | Resumen del grupo |
| **Perfil enriquecido** — Stats de racha, promedio y total de registros del estudiante | Perfil del estudiante |
| **Alertas con tabs** — Separación clara entre alertas activas y resueltas | Alertas |
| **Acciones rápidas** — Botones directos desde el dashboard para las tareas más comunes | Dashboard profesor |

### 🔧 Admin
| Feature | Dónde |
|---------|-------|
| **Acceso al perfil emocional** desde la tabla de usuarios | Gestión → Usuarios |
| **Dashboard mejorado** — Acceso a Resumen del Grupo y métricas agrupadas | Dashboard admin |
| **Tabla de usuarios con más acciones** | Gestión → Usuarios |

### 🎨 Diseño general
- Sidebar más compacto y organizado por secciones claras
- Topbar con botón de "Registrar emoción" siempre visible para estudiantes
- Todas las tablas usan font-size pequeño para no saturar
- Tarjetas en formato grid para cursos y actividades (en lugar de tablas)
- Tabs en las vistas de alertas y perfil del estudiante

---

## 📁 Nuevos modelos

### `NotaProfesor` (en `apps/emotions/models.py`)
Nota privada que un profesor escribe sobre un estudiante. Solo visible para quien la creó.

### `MetaSemanal` (en `apps/emotions/models.py`)
Meta semanal del estudiante. Se crea automáticamente al entrar al registro de emoción. Una por estudiante por semana.

### Migración incluida
`apps/emotions/migrations/0002_nota_meta.py`

---

## 📋 URLs nuevas

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/emotions/resumen/` | `emotions:resumen_grupo` | Resumen emocional por curso |

