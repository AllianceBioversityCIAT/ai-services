# Partner Request Support - Frontend

Interfaz web minimalista e institucional para procesar solicitudes de partners y mapearlas contra la base de datos CLARISA.

## 🎨 Diseño

El frontend sigue un diseño **minimalista institucional** con:
- Paleta de colores CGIAR (verdes oliva, tonos tierra naturales)
- Tipografía: Crimson Pro (serif) + Work Sans (sans-serif)
- Animaciones sutiles y profesionales
- Componentes cards expandibles para visualizar información de manera organizada

## 🚀 Instalación y Ejecución

### Prerequisitos

- Node.js 18+ 
- Backend API corriendo en `http://localhost:8000`

### Instalación

```bash
cd frontend
npm install
```

### Modo Desarrollo

```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:3000`

### Producción

```bash
npm run build
npm run start
```

## 📝 Uso

1. **Subir Excel**: Haz clic en "Choose Excel File" y selecciona un archivo Excel con la estructura requerida
2. **Procesar**: Haz clic en "Process Partners" para iniciar el análisis
3. **Ver Resultados**: Los resultados se muestran en cards expandibles con tres secciones:
   - **Información del Partner**: Datos básicos del partner solicitado
   - **CLARISA Match**: Información del match encontrado con scores detallados
   - **Web Search**: Resultados de búsqueda web (cuando no hay match en CLARISA)

### Formato del Excel

El archivo Excel debe tener la siguiente estructura:

| Column | Nombre | Requerido | Descripción |
|--------|--------|-----------|-------------|
| 0 | ID | Opcional | Identificador único del partner |
| 1 | Partner Name | **Requerido** | Nombre de la institución |
| 2 | Acronym | Opcional | Acrónimo de la institución |
| 3 | Website | Opcional | Sitio web de la institución |
| 5 | Country | Opcional | País de la institución |

## 🎯 Características

- ✨ Diseño minimalista e institucional
- 📊 Estadísticas visuales en tiempo real
- 🎭 Animaciones sutiles con Framer Motion
- 📱 Diseño responsivo
- 🎨 Paleta de colores CGIAR
- 🔍 Vista detallada de matches con scores
- 🌐 Integración con web search fallback
- ⚡ Procesamiento rápido con feedback visual

## 🛠️ Tecnologías

- **Framework**: Next.js 16+ (App Router)
- **Styling**: Tailwind CSS 4 + CSS Variables
- **Animaciones**: Framer Motion
- **Iconos**: Lucide React
- **HTTP Client**: Axios
- **TypeScript**: Para type safety

## 📂 Estructura

```
frontend/
├── app/
│   ├── page.tsx          # Página principal con upload y resultados
│   ├── layout.tsx        # Layout global
│   └── globals.css       # Estilos globales y variables CGIAR
├── public/               # Archivos estáticos
└── package.json          # Dependencias
```

## 🎨 Sistema de Colores

La paleta está basada en colores institucionales de CGIAR:

- **Primary**: `#5a6b3f` (Olive)
- **Forest**: `#3d4a2c` (Dark Green)
- **Earth**: `#8b7355` (Brown)
- **Sand**: `#d4c4a8` (Beige)
- **Cream**: `#f5f1e8` (Background)

### Match Quality Colors

- **Excellent** (≥0.85): `#2d5f3f`
- **Good** (≥0.70): `#5a7c59`
- **Fair** (≥0.50): `#8b9d79`
- **No Match**: `#a08577`

## 🔧 Configuración

Para conectar con un backend diferente, actualiza la URL en `page.tsx`:

```typescript
const response = await axios.post<ProcessingResults>(
  'http://localhost:8000/api/process-partners',  // Cambiar URL aquí
  formData
);
```

## 📄 Licencia

Este proyecto es parte del sistema de soporte de partner requests de CGIAR.

